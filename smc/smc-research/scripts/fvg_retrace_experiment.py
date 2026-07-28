"""PRE-REGISTERED session-5 experiment: FVG-retrace continuation family.

Registered BEFORE any result was computed (RESEARCH_LOG.md conclusion #3,
grid frozen here):

- Strategy: FVGRetraceStrategy (trend-aligned FVG → retrace entry, stop
  beyond the far edge − ATR buffer, 2R target).
- Grid (4 configs, selected per walk-forward window on train data only):
  entry_frac {0.5, 1.0} × stop_atr_mult {0.5, 1.0}.
  Fixed: swing_strength 3, atr_len 14, expiry_bars 12, target 2R.
- Sample: BTCUSD, ETHUSD, EURUSD, SPX500 × {1h (24-bar stop), 4h (30-bar
  stop)}, 2023-01-01 → 2026-07-28, per-instrument costs, walk-forward
  6m train / 3m test.
- PRIMARY METRIC: pooled OOS expectancy across all eight instrument×
  timeframe cells. DECISION RULE (identical to session 4): pooled 95%
  bootstrap CI lower bound > 0 → confirmation pass; otherwise the family
  is retired. Per-cell numbers are reported for context, not for decisions.

    uv run python scripts/fvg_retrace_experiment.py
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from smc_research import load  # noqa: E402
from smc_research.engine import COST_MODELS, FVGRetraceStrategy, walk_forward  # noqa: E402
from smc_research.stats import expectancy_ci, hit_rate_ci, summarize  # noqa: E402

GRID = [
    {"entry_frac": ef, "stop_atr_mult": sm}
    for ef, sm in itertools.product([0.5, 1.0], [0.5, 1.0])
]
START, END = "2023-01-01", "2026-07-28"
CELLS = [
    (symbol, tf, ts)
    for symbol in ["BTCUSD", "ETHUSD", "EURUSD", "SPX500"]
    for tf, ts in [("1h", 24), ("4h", 30)]
]


def describe(name: str, trades) -> dict:
    s = summarize(trades)
    exp = expectancy_ci(trades, iters=2000)
    hit = hit_rate_ci(trades, iters=2000)
    print(
        f"{name:16s} n={s.n_trades:4d} hit={s.hit_rate:5.1%} "
        f"exp={s.expectancy_r:+.3f}R [{exp.lo:+.3f},{exp.hi:+.3f}] "
        f"pf={s.profit_factor:.2f} maxDD={s.max_drawdown_r:.1f}R total={s.total_r:+.1f}R"
    )
    return {
        "cell": name, "n": s.n_trades, "hit": round(s.hit_rate, 4),
        "hit_lo": round(hit.lo, 4), "hit_hi": round(hit.hi, 4),
        "exp": round(s.expectancy_r, 4), "exp_lo": round(exp.lo, 4),
        "exp_hi": round(exp.hi, 4),
        "pf": None if s.profit_factor == float("inf") else round(s.profit_factor, 4),
        "max_dd": round(s.max_drawdown_r, 4), "total_r": round(s.total_r, 4),
    }


def main() -> None:
    pooled, rows = [], []
    for symbol, tf, time_stop in CELLS:
        df = load(symbol, tf, START, END)
        wf = walk_forward(
            df,
            FVGRetraceStrategy,
            GRID,
            costs=COST_MODELS[symbol],
            train_months=6,
            test_months=3,
            time_stop_bars=time_stop,
            target_r=2.0,
        )
        rows.append(describe(f"{symbol} {tf}", wf.oos_trades))
        pooled.extend(wf.oos_trades)

    print("\n--- POOLED (primary metric) ---")
    pooled_row = describe("POOLED", pooled)

    out = Path("reports_out/experiments/fvg_retrace.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"cells": rows, "pooled": pooled_row, "grid": GRID}, indent=2))
    print(f"\ntable → {out}")

    exp = expectancy_ci(pooled, iters=2000)
    print(
        f"DECISION: pooled CI [{exp.lo:+.3f}, {exp.hi:+.3f}] → "
        + ("CI clears zero — family earns a confirmation pass."
           if exp.lo > 0
           else "CI straddles/below zero — per the pre-registered rule, retire the family.")
    )


if __name__ == "__main__":
    main()
