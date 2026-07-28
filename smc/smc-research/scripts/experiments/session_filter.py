"""Experiment: session_filter.

Hypothesis: liquidity sweeps during London / NY kill zones (when institutional
flow is real) behave differently from Asia-session chop. Wrap the baseline
SweepConfirmationStrategy and only pass through entry intents when the SIGNAL
bar's UTC hour falls inside a session window.

Windows (UTC, half-open [start, end)):
  london     07-10
  ny         12-15
  london_ny  union of the two
  asia       00-04 (control)

Grid (8 configs): timeframe {15m, 1h} x window {london, ny, london_ny, asia},
all with ATR x 2.0 stops, swing_strength=3, target 2R.
Time stops ~24h-5d horizon: 96 bars @15m, 24 bars @1h.

All reported numbers are walk-forward OOS (6m train / 3m test) with
COST_MODELS["BTCUSD"].
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from smc_research import load
from smc_research.detectors.types import Bar
from smc_research.engine import COST_MODELS, SweepConfirmationStrategy, walk_forward
from smc_research.engine.strategy import EntryIntent, Strategy
from smc_research.stats import expectancy_ci, summarize

WINDOWS: dict[str, tuple[tuple[int, int], ...]] = {
    "london": ((7, 10),),
    "ny": ((12, 15),),
    "london_ny": ((7, 10), (12, 15)),
    "asia": ((0, 4),),
}


class SessionFilteredSweepStrategy(Strategy):
    """SweepConfirmationStrategy wrapper: pass intents only when the signal
    bar's UTC hour is inside the configured session window.

    The inner strategy is fed EVERY bar (its detector/ATR state must stay
    identical to the baseline); only the emitted intent is gated. Uses only the
    current bar's timestamp -> no lookahead. Entry still fills next-bar open
    (engine rule, untouched).
    """

    def __init__(
        self,
        window: str = "london",
        swing_strength: int = 3,
        atr_mult: float = 2.0,
        atr_len: int = 14,
    ):
        self.params = {
            "window": window,
            "swing_strength": swing_strength,
            "atr_mult": atr_mult,
            "atr_len": atr_len,
        }
        self._inner = SweepConfirmationStrategy(
            swing_strength=swing_strength, atr_mult=atr_mult, atr_len=atr_len
        )
        self._ranges = WINDOWS[window]
        self.window = window

    def _in_window(self, bar: Bar) -> bool:
        ts = bar.timestamp
        if ts.tzinfo is not None:
            ts = ts.tz_convert("UTC")
        h = ts.hour
        return any(lo <= h < hi for lo, hi in self._ranges)

    def update(self, bar: Bar) -> EntryIntent | None:
        intent = self._inner.update(bar)  # always update inner state
        if intent is None or not self._in_window(bar):
            return None
        return EntryIntent(
            direction=intent.direction,
            stop_price=intent.stop_price,
            reason=f"{intent.reason}|{self.window}",
            meta=intent.meta,
        )


TIME_STOP = {"15m": 96, "1h": 24}  # ~24h horizon per instructions
COSTS = COST_MODELS["BTCUSD"]


def run_config(df, timeframe: str, window: str) -> dict:
    label = f"{window}|{timeframe}|ATRx2.0|ss=3"
    wf = walk_forward(
        df,
        SessionFilteredSweepStrategy,
        [{"window": window, "swing_strength": 3, "atr_mult": 2.0}],
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
        "window": window,
        "timeframe": timeframe,
        "atr_mult": 2.0,
        "swing_strength": 3,
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
        f"{label:28s} n={s.n_trades:4d} hit={s.hit_rate:5.1%} "
        f"exp={s.expectancy_r:+.3f}R [{ci.lo:+.3f},{ci.hi:+.3f}] "
        f"pf={s.profit_factor:.2f} maxDD={s.max_drawdown_r:.1f}R"
    )
    return row


def main() -> None:
    frames = {
        tf: load("BTCUSD", tf, "2023-01-01", "2026-07-28") for tf in ("15m", "1h")
    }
    rows: list[dict] = []
    for tf in ("15m", "1h"):
        for window in ("london", "ny", "london_ny", "asia"):
            rows.append(run_config(frames[tf], tf, window))

    out = ROOT / "reports_out" / "experiments" / "session_filter.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"experiment": "session_filter", "configs": rows}, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
