"""Experiment: limit_retrace.

HYPOTHESIS: market entry at next-bar open pays the spread at the worst moment.
Instead, after a liquidity-sweep signal, work a LIMIT at the swept level
(bullish sweep -> buy limit at the swept low level). Fill when a later bar's
low <= limit (fill price = limit; conservative-correct for limits). Cancel if
unfilled after N bars {4, 8}, or if the market gaps through the stop level
before the fill (no entry). Stop = fill - ATR*mult {1.0, 2.0}; target 2R.
Timeframes {1h, 4h}.

Custom fill loop lives HERE (engine untouched), copying the engine's
conventions exactly:
- The limit only starts resting on the bar AFTER the signal bar closes
  (no lookahead: detector + ATR see only completed bars up to the signal bar).
- Stop-first on ambiguous bars.
- On the FILL bar itself, only the stop can exit (price provably crossed the
  limit before it could reach the stop, since the stop is beyond the limit);
  the target is NOT allowed on the fill bar because the high/low that would
  hit it may have printed before the fill -- unknowable from OHLC, so we
  forgo it (conservative).
- Realized R measured against RAW risk; all fills through CostModel.

Cost treatment: main configs charge FULL taker costs (half-spread+slippage)
even on the limit fill -- strictly conservative, a real resting limit pays
neither. Two sensitivity configs ("maker") fill the entry at the raw limit
price (commission still charged both sides; exits still pay full taker costs).

All reported numbers are walk-forward OUT-OF-SAMPLE (6m train / 3m test)
with COST_MODELS["BTCUSD"].
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from smc_research import load  # noqa: E402
from smc_research.detectors import LiquiditySweepDetector  # noqa: E402
from smc_research.detectors.types import iter_bars  # noqa: E402
from smc_research.engine.backtester import Trade  # noqa: E402
from smc_research.engine.costs import COST_MODELS, CostModel  # noqa: E402
from smc_research.engine.walkforward import iter_split_frames, make_splits  # noqa: E402
from smc_research.stats import expectancy_ci, summarize  # noqa: E402

SYMBOL = "BTCUSD"
START, END = "2023-01-01", "2026-07-28"
TARGET_R = 2.0
SWING_STRENGTH = 3
ATR_LEN = 14
TIME_STOP = {"1h": 24, "4h": 30}  # ~1d @1h, ~5d @4h (per-rules horizon band)


def run_limit_backtest(
    df,
    cancel_bars: int,
    atr_mult: float,
    costs: CostModel,
    time_stop_bars: int,
    entry_style: str = "taker",   # "taker" = full costs on limit fill; "maker" = raw fill
    counters: dict[str, int] | None = None,
) -> list[Trade]:
    """Custom event loop: limit-at-swept-level entries, engine-identical exits."""
    if counters is None:
        counters = {}
    for k in ("signals", "placed", "replaced", "filled", "expired", "gap_cancel"):
        counters.setdefault(k, 0)

    detector = LiquiditySweepDetector(swing_strength=SWING_STRENGTH)
    trades: list[Trade] = []
    trs: list[float] = []
    prev_close: float | None = None
    pending: dict[str, Any] | None = None   # resting limit order
    pos: dict[str, Any] | None = None       # open position

    def close_position(bar_ts, raw_exit: float, reason: str) -> None:
        nonlocal pos
        long = pos["direction"] == "long"
        exit_fill = costs.sell_fill(raw_exit) if long else costs.buy_fill(raw_exit)
        risk = abs(pos["entry_raw"] - pos["stop"])
        pnl = (exit_fill - pos["entry_fill"]) if long else (pos["entry_fill"] - exit_fill)
        commission = costs.commission(pos["entry_fill"]) + costs.commission(exit_fill)
        trades.append(
            Trade(
                entry_time=pos["entry_time"],
                exit_time=bar_ts,
                direction=pos["direction"],
                entry_price=pos["entry_fill"],
                exit_price=exit_fill,
                stop_price=pos["stop"],
                target_price=pos["target"],
                exit_reason=reason,
                risk=risk,
                realized_r=(pnl - commission) / risk,
                reason=pos["reason"],
            )
        )
        pos = None

    for bar in iter_bars(df):
        # ---- 1) Resting limit: fill / gap-cancel / expiry (bars AFTER signal bar).
        if pending is not None and pos is None:
            long = pending["direction"] == "long"
            lim, stop = pending["limit"], pending["stop"]
            gap_through_stop = (bar.open <= stop) if long else (bar.open >= stop)
            touched = (bar.low <= lim) if long else (bar.high >= lim)
            if gap_through_stop:
                # Market opened beyond the stop before the limit could fill at
                # its price: per hypothesis spec, NO entry.
                counters["gap_cancel"] += 1
                pending = None
            elif touched:
                counters["filled"] += 1
                raw = lim  # conservative: never better than the limit price
                risk = (raw - stop) if long else (stop - raw)
                if entry_style == "taker":
                    fill = costs.buy_fill(raw) if long else costs.sell_fill(raw)
                else:  # maker: resting limit fills at its own price
                    fill = raw
                target = raw + TARGET_R * risk if long else raw - TARGET_R * risk
                pos = {
                    "direction": pending["direction"],
                    "entry_time": bar.timestamp,
                    "entry_fill": fill,
                    "entry_raw": raw,
                    "stop": stop,
                    "target": target,
                    "bars_held": 0,
                    "reason": pending["reason"],
                }
                pending = None
                # Fill-bar exit: stop only (stop is beyond the limit, so any
                # touch of the stop provably happened after the fill).
                hit_stop = (bar.low <= stop) if long else (bar.high >= stop)
                if hit_stop:
                    close_position(bar.timestamp, stop, "stop")
            else:
                pending["bars_waited"] += 1
                if pending["bars_waited"] >= cancel_bars:
                    counters["expired"] += 1
                    pending = None

        # ---- 2) Manage open position (bars after the fill bar) — engine copy.
        elif pos is not None:
            long = pos["direction"] == "long"
            stop, target = pos["stop"], pos["target"]
            hit_stop = (bar.low <= stop) if long else (bar.high >= stop)
            hit_target = (bar.high >= target) if long else (bar.low <= target)
            if hit_stop:                      # stop-first on ambiguous bars
                close_position(bar.timestamp, stop, "stop")
            elif hit_target:
                close_position(bar.timestamp, target, "target")
            else:
                pos["bars_held"] += 1
                if pos["bars_held"] >= time_stop_bars:
                    close_position(bar.timestamp, bar.close, "time")

        # ---- 3) Feed the bar to ATR + detector; a new limit rests from NEXT bar.
        tr = bar.high - bar.low
        if prev_close is not None:
            tr = max(tr, abs(bar.high - prev_close), abs(bar.low - prev_close))
        trs.append(tr)
        if len(trs) > ATR_LEN:
            trs.pop(0)
        prev_close = bar.close
        atr = sum(trs) / ATR_LEN if len(trs) >= ATR_LEN else None

        for sig in detector.update(bar):
            if sig.kind != "liquidity_sweep":
                continue
            counters["signals"] += 1
            if pos is not None or atr is None:
                continue  # drop signals while positioned / before ATR warm-up
            buffer = atr_mult * atr
            if sig.direction == "bullish":
                order = {
                    "direction": "long",
                    "limit": sig.price,
                    "stop": sig.price - buffer,
                    "bars_waited": 0,
                    "reason": "limit_retrace_sellside",
                }
            elif sig.direction == "bearish":
                order = {
                    "direction": "short",
                    "limit": sig.price,
                    "stop": sig.price + buffer,
                    "bars_waited": 0,
                    "reason": "limit_retrace_buyside",
                }
            else:
                continue
            if pending is not None:
                counters["replaced"] += 1
            counters["placed"] += 1
            pending = order  # cancel-and-replace with the freshest level
            break  # engine analog: at most one intent per bar

    return trades


def walk_forward_limit(
    df,
    grid: list[dict[str, Any]],
    costs: CostModel,
    time_stop_bars: int,
    entry_style: str,
    counters: dict[str, int],
    train_months: int = 6,
    test_months: int = 3,
    min_train_trades: int = 20,
):
    """Mirror of engine walk_forward for the custom fill loop. OOS trades only."""
    splits = make_splits(df.index[0], df.index[-1], train_months, test_months)
    oos: list[Trade] = []
    chosen: list[dict[str, Any]] = []
    for split, train, test in iter_split_frames(df, splits):
        best, best_score = None, float("-inf")
        for params in grid:
            tr = run_limit_backtest(
                train, costs=costs, time_stop_bars=time_stop_bars,
                entry_style=entry_style, **params,
            )
            score = (
                sum(t.realized_r for t in tr) / len(tr)
                if len(tr) >= min_train_trades else float("-inf")
            )
            if score > best_score:
                best, best_score = params, score
        if best is None:
            best = grid[0]
        chosen.append({**best, "_split": str(split.train_end.date()), "_train_score": best_score})
        oos.extend(
            run_limit_backtest(
                test, costs=costs, time_stop_bars=time_stop_bars,
                entry_style=entry_style, counters=counters, **best,
            )
        )
    return oos, chosen


def main() -> None:
    costs = COST_MODELS[SYMBOL]
    frames = {tf: load(SYMBOL, tf, START, END) for tf in ("1h", "4h")}

    base_grid = [
        {"cancel_bars": n, "atr_mult": m} for n in (4, 8) for m in (1.0, 2.0)
    ]

    configs: list[dict[str, Any]] = []
    for tf in ("1h", "4h"):
        for g in base_grid:
            configs.append({
                "label": f"{tf} fixed N={g['cancel_bars']} ATRx{g['atr_mult']} taker",
                "tf": tf, "grid": [g], "entry_style": "taker",
            })
        configs.append({
            "label": f"{tf} adaptive(grid4) taker",
            "tf": tf, "grid": base_grid, "entry_style": "taker",
        })
        configs.append({
            "label": f"{tf} adaptive(grid4) maker-entry",
            "tf": tf, "grid": base_grid, "entry_style": "maker",
        })

    rows = []
    for cfg in configs:
        counters: dict[str, int] = {}
        oos, chosen = walk_forward_limit(
            frames[cfg["tf"]], cfg["grid"], costs,
            time_stop_bars=TIME_STOP[cfg["tf"]],
            entry_style=cfg["entry_style"], counters=counters,
        )
        s = summarize(oos)
        ci = expectancy_ci(oos, iters=1000)
        pf = s.profit_factor if math.isfinite(s.profit_factor) else None
        row = {
            "label": cfg["label"],
            "timeframe": cfg["tf"],
            "entry_style": cfg["entry_style"],
            "grid": cfg["grid"],
            "n": s.n_trades,
            "hit_rate": round(s.hit_rate, 4),
            "expectancy_r": round(s.expectancy_r, 4),
            "exp_ci_lo": round(ci.lo, 4),
            "exp_ci_hi": round(ci.hi, 4),
            "profit_factor": round(pf, 4) if pf is not None else None,
            "max_drawdown_r": round(s.max_drawdown_r, 4),
            "total_r": round(s.total_r, 4),
            "avg_win_r": round(s.avg_win_r, 4),
            "avg_loss_r": round(s.avg_loss_r, 4),
            "exit_mix": {
                k: sum(1 for t in oos if t.exit_reason == k)
                for k in ("stop", "target", "time")
            },
            "oos_counters": counters,
            "chosen_params": chosen,
        }
        rows.append(row)
        print(
            f"{row['label']:44s} n={row['n']:4d} hit={row['hit_rate']:.3f} "
            f"exp={row['expectancy_r']:+.3f}R CI[{row['exp_ci_lo']:+.3f},{row['exp_ci_hi']:+.3f}] "
            f"PF={row['profit_factor']} maxDD={row['max_drawdown_r']:.1f}R "
            f"fills={counters['filled']} exp'd={counters['expired']} gap={counters['gap_cancel']}"
        )

    out = ROOT / "reports_out" / "experiments" / "limit_retrace.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "experiment": "limit_retrace",
        "symbol": SYMBOL,
        "period": [START, END],
        "costs": {"spread_bps": costs.spread_bps, "slippage_bps": costs.slippage_bps,
                  "commission_bps": costs.commission_bps},
        "walk_forward": {"train_months": 6, "test_months": 3},
        "target_r": TARGET_R,
        "time_stop_bars": TIME_STOP,
        "configs": rows,
    }, indent=2))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
