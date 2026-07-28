"""Adversarial verification of trend_aligned claimed config: aligned|4h|ATRx2.0|k=3.

Checks:
1. Reproduce the exact config OOS with COST_MODELS["BTCUSD"], then re-run with costs x1.5.
2. Split OOS trades by calendar year (of entry_time) with per-year expectancy + CI.
3. Concentration: trades per day, top-day shares, exit-reason mix.

Everything walk-forward OOS (6m train / 3m test) per the framework rules.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from smc_research import load
from smc_research.detectors import LiquiditySweepDetector, StructureDetector
from smc_research.detectors.types import Bar, Signal
from smc_research.engine import COST_MODELS, walk_forward
from smc_research.engine.costs import CostModel
from smc_research.engine.strategy import EntryIntent, Strategy
from smc_research.stats import expectancy_ci, summarize


# --- Exact copy of the strategy from scripts/experiments/trend_aligned.py ---
class TrendAlignedSweepStrategy(Strategy):
    def __init__(
        self,
        swing_strength: int = 3,
        atr_mult: float = 2.0,
        atr_len: int = 14,
        mode: str = "aligned",
    ):
        self.params = {
            "swing_strength": swing_strength,
            "atr_mult": atr_mult,
            "atr_len": atr_len,
            "mode": mode,
        }
        self._sweeps = LiquiditySweepDetector(swing_strength=swing_strength)
        self._structure = StructureDetector(swing_strength=swing_strength)
        self.atr_mult = atr_mult
        self.atr_len = atr_len
        self.mode = mode
        self._trend = "none"
        self._trs: list[float] = []
        self._prev_close: float | None = None

    def _update_atr(self, bar: Bar) -> float | None:
        tr = bar.high - bar.low
        if self._prev_close is not None:
            tr = max(tr, abs(bar.high - self._prev_close), abs(bar.low - self._prev_close))
        self._trs.append(tr)
        if len(self._trs) > self.atr_len:
            self._trs.pop(0)
        self._prev_close = bar.close
        if len(self._trs) < self.atr_len:
            return None
        return sum(self._trs) / self.atr_len

    def update(self, bar: Bar) -> EntryIntent | None:
        atr = self._update_atr(bar)
        for sig in self._structure.update(bar):
            if sig.kind in ("bos", "choch") and sig.direction in ("bullish", "bearish"):
                self._trend = sig.direction
        signals: list[Signal] = self._sweeps.update(bar)
        if atr is None:
            return None
        buffer = self.atr_mult * atr
        for sig in signals:
            if sig.kind != "liquidity_sweep":
                continue
            if sig.direction == "bullish":
                want = "bullish" if self.mode == "aligned" else "bearish"
                if self._trend == want:
                    return EntryIntent(
                        direction="long",
                        stop_price=bar.low - buffer,
                        reason=f"sweep_sellside_{self.mode}",
                        meta={"level": sig.price, "trend": self._trend},
                    )
            elif sig.direction == "bearish":
                want = "bearish" if self.mode == "aligned" else "bullish"
                if self._trend == want:
                    return EntryIntent(
                        direction="short",
                        stop_price=bar.high + buffer,
                        reason=f"sweep_buyside_{self.mode}",
                        meta={"level": sig.price, "trend": self._trend},
                    )
        return None


def run(df, costs, label):
    wf = walk_forward(
        df,
        TrendAlignedSweepStrategy,
        [{"swing_strength": 3, "atr_mult": 2.0, "mode": "aligned"}],
        costs=costs,
        train_months=6,
        test_months=3,
        time_stop_bars=30,
        target_r=2.0,
    )
    trades = wf.oos_trades
    s = summarize(trades)
    ci = expectancy_ci(trades, iters=1000)
    print(
        f"{label:22s} n={s.n_trades:4d} hit={s.hit_rate:5.1%} "
        f"exp={s.expectancy_r:+.4f}R [{ci.lo:+.4f},{ci.hi:+.4f}] "
        f"pf={s.profit_factor:.3f} maxDD={s.max_drawdown_r:.2f}R totR={s.total_r:+.2f}"
    )
    return trades, s, ci


def main() -> None:
    df = load("BTCUSD", "4h", "2023-01-01", "2026-07-28")
    base = COST_MODELS["BTCUSD"]

    print("=== 1) Reproduction + cost stress ===")
    trades, s, ci = run(df, base, "base costs")
    stressed = CostModel(
        spread_bps=base.spread_bps * 1.5,
        slippage_bps=base.slippage_bps * 1.5,
        commission_bps=base.commission_bps * 1.5,
    )
    trades15, s15, ci15 = run(df, stressed, "costs x1.5")

    print("\n=== 2) Year split (base costs, by entry_time year) ===")
    years = {}
    by_year = {}
    for t in trades:
        by_year.setdefault(t.entry_time.year, []).append(t)
    for yr in sorted(by_year):
        tl = by_year[yr]
        ys = summarize(tl)
        yci = expectancy_ci(tl, iters=1000)
        years[yr] = {
            "n": ys.n_trades,
            "hit": round(ys.hit_rate, 4),
            "exp_r": round(ys.expectancy_r, 4),
            "ci": [round(yci.lo, 4), round(yci.hi, 4)],
            "total_r": round(ys.total_r, 3),
        }
        print(
            f"{yr}: n={ys.n_trades:3d} hit={ys.hit_rate:5.1%} exp={ys.expectancy_r:+.4f}R "
            f"[{yci.lo:+.4f},{yci.hi:+.4f}] totR={ys.total_r:+.2f}"
        )

    print("\n=== 3) Concentration / sanity ===")
    day_r = Counter()
    for t in trades:
        day_r[t.entry_time.date()] += t.realized_r
    n_days = len(day_r)
    total_r = sum(t.realized_r for t in trades)
    top_pos = sorted(day_r.items(), key=lambda kv: kv[1], reverse=True)[:5]
    print(f"distinct entry days: {n_days} for {len(trades)} trades, total {total_r:+.2f}R")
    print("top-5 days by R:", [(str(d), round(r, 2)) for d, r in top_pos])
    top5_r = sum(r for _, r in top_pos)
    print(f"top-5 days contribute {top5_r:+.2f}R of {total_r:+.2f}R total")
    ex_top5 = total_r - top5_r
    print(f"total R excluding top-5 days: {ex_top5:+.2f}R "
          f"-> expectancy ex-top5 = {ex_top5 / max(len(trades) - sum(1 for t in trades if t.entry_time.date() in dict(top_pos)), 1):+.4f}R")
    reasons = Counter(t.exit_reason for t in trades)
    dirs = Counter(t.direction for t in trades)
    print("exit reasons:", dict(reasons), "| directions:", dict(dirs))

    out = {
        "config": "aligned|4h|ATRx2.0|k=3",
        "base": {
            "n": s.n_trades, "hit": round(s.hit_rate, 4), "exp_r": round(s.expectancy_r, 4),
            "ci": [round(ci.lo, 4), round(ci.hi, 4)],
            "pf": round(s.profit_factor, 4), "max_dd_r": round(s.max_drawdown_r, 3),
            "total_r": round(s.total_r, 3),
        },
        "costs_x1_5": {
            "n": s15.n_trades, "hit": round(s15.hit_rate, 4), "exp_r": round(s15.expectancy_r, 4),
            "ci": [round(ci15.lo, 4), round(ci15.hi, 4)],
            "pf": round(s15.profit_factor, 4), "total_r": round(s15.total_r, 3),
        },
        "by_year": {str(k): v for k, v in years.items()},
        "n_entry_days": n_days,
        "top5_days_r": round(top5_r, 3),
        "total_r": round(total_r, 3),
        "exit_reasons": dict(reasons),
        "directions": dict(dirs),
    }
    outp = ROOT / "reports_out" / "experiments" / "verify_trend_aligned_aligned_4h_ATRx2_0_k_3.json"
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(out, indent=2))
    print(f"\nWrote {outp}")


if __name__ == "__main__":
    main()
