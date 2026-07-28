"""Experiment: trend_aligned.

Hypothesis: the sweep-reversal baseline loses because it fades EVERY sweep.
Only take sweeps ALIGNED with the prevailing structure trend as tracked by
StructureDetector (bullish after a bullish bos/choch, bearish after a bearish
one): sell-side sweeps (long entries) only while the trend is bullish,
buy-side sweeps (short entries) only while the trend is bearish.

Grid (8 configs): timeframe {1h, 4h} x atr_mult {1.0, 2.0} x swing_strength {3, 5}.
Control: the exact mirror (counter-trend only) at the best aligned config.

All reported numbers are walk-forward OOS (6m train / 3m test) with
COST_MODELS["BTCUSD"]. Time stops ~5d: 24 bars @1h, 30 bars @4h.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from smc_research import load
from smc_research.detectors import LiquiditySweepDetector, StructureDetector
from smc_research.detectors.types import Bar, Signal
from smc_research.engine import COST_MODELS, walk_forward
from smc_research.engine.strategy import EntryIntent, Strategy
from smc_research.stats import expectancy_ci, summarize


class TrendAlignedSweepStrategy(Strategy):
    """Sweep-reversal gated by StructureDetector trend state.

    mode="aligned": long on sell-side sweep only in a bullish trend,
                    short on buy-side sweep only in a bearish trend.
    mode="counter": the exact mirror (control).

    Stop: sweep-bar extreme +/- atr_mult * ATR(atr_len), ATR incremental from
    completed bars only. Entries fill next-bar open (engine rule).
    """

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

        # Structure first, so a break closing on this bar updates the trend
        # before the sweep gate is evaluated. Both use only bars already seen.
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
            if sig.direction == "bullish":  # sell-side liquidity taken -> long
                want = "bullish" if self.mode == "aligned" else "bearish"
                if self._trend == want:
                    return EntryIntent(
                        direction="long",
                        stop_price=bar.low - buffer,
                        reason=f"sweep_sellside_{self.mode}",
                        meta={"level": sig.price, "trend": self._trend},
                    )
            elif sig.direction == "bearish":  # buy-side taken -> short
                want = "bearish" if self.mode == "aligned" else "bullish"
                if self._trend == want:
                    return EntryIntent(
                        direction="short",
                        stop_price=bar.high + buffer,
                        reason=f"sweep_buyside_{self.mode}",
                        meta={"level": sig.price, "trend": self._trend},
                    )
        return None


TIME_STOP = {"1h": 24, "4h": 30}  # ~1d @1h ... 5d @4h horizon per instructions
COSTS = COST_MODELS["BTCUSD"]


def run_config(df, timeframe: str, atr_mult: float, k: int, mode: str) -> dict:
    label = f"{mode}|{timeframe}|ATRx{atr_mult}|k={k}"
    wf = walk_forward(
        df,
        TrendAlignedSweepStrategy,
        [{"swing_strength": k, "atr_mult": atr_mult, "mode": mode}],
        costs=COSTS,
        train_months=6,
        test_months=3,
        time_stop_bars=TIME_STOP[timeframe],
        target_r=2.0,
    )
    trades = wf.oos_trades
    s = summarize(trades)
    ci = expectancy_ci(trades, iters=1000)
    row = {
        "label": label,
        "mode": mode,
        "timeframe": timeframe,
        "atr_mult": atr_mult,
        "swing_strength": k,
        "time_stop_bars": TIME_STOP[timeframe],
        "target_r": 2.0,
        "n": s.n_trades,
        "hit_rate": round(s.hit_rate, 4),
        "expectancy_r": round(s.expectancy_r, 4),
        "exp_ci_lo": round(ci.lo, 4),
        "exp_ci_hi": round(ci.hi, 4),
        "profit_factor": round(s.profit_factor, 4) if s.profit_factor != float("inf") else None,
        "max_drawdown_r": round(s.max_drawdown_r, 4),
        "total_r": round(s.total_r, 4),
        "avg_win_r": round(s.avg_win_r, 4),
        "avg_loss_r": round(s.avg_loss_r, 4),
        "n_splits": len(wf.splits),
    }
    print(
        f"{label:32s} n={s.n_trades:4d} hit={s.hit_rate:5.1%} "
        f"exp={s.expectancy_r:+.3f}R [{ci.lo:+.3f},{ci.hi:+.3f}] "
        f"pf={s.profit_factor:.2f} maxDD={s.max_drawdown_r:.1f}R"
    )
    return row


def main() -> None:
    frames = {
        tf: load("BTCUSD", tf, "2023-01-01", "2026-07-28") for tf in ("1h", "4h")
    }
    rows: list[dict] = []
    for tf in ("1h", "4h"):
        for atr_mult in (1.0, 2.0):
            for k in (3, 5):
                rows.append(run_config(frames[tf], tf, atr_mult, k, "aligned"))

    # Control: mirror (counter-trend) at the best aligned config by OOS expectancy
    # among configs with a non-trivial sample.
    eligible = [r for r in rows if r["n"] >= 30]
    best = max(eligible or rows, key=lambda r: r["expectancy_r"])
    print(f"\nBest aligned config: {best['label']} -> running counter-trend mirror control")
    rows.append(
        run_config(
            frames[best["timeframe"]],
            best["timeframe"],
            best["atr_mult"],
            best["swing_strength"],
            "counter",
        )
    )

    out = ROOT / "reports_out" / "experiments" / "trend_aligned.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"experiment": "trend_aligned", "configs": rows}, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
