"""Experiment: exit_design.

Hypothesis: maybe the entries are fine and the EXITS are the problem.
Fix the entry at the best-known base — SweepConfirmationStrategy(
swing_strength=3, atr_mult=2.0) on BTCUSD 1h — and grid ONLY the exit:

    target_r      in {1.0, 1.5, 2.0, 3.0, 4.0}
    time_stop_bars in {12, 24, 48}      (12h / 24h / 48h at 1h bars)

15 configs total. Because target_r and time_stop_bars are engine-level
parameters of walk_forward (not strategy params), each config is its own
walk_forward run with a SINGLE-entry param grid — the walk-forward split
machinery (6m train / 3m test) is identical to the baseline, there is no
per-fold exit selection, so every cell of the matrix is a clean OOS read
of "same entries, different exit".

All reported numbers are walk-forward OOS with COST_MODELS["BTCUSD"].
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from smc_research import load
from smc_research.engine import COST_MODELS, SweepConfirmationStrategy, walk_forward
from smc_research.stats import expectancy_ci, summarize

TIMEFRAME = "1h"
ENTRY_PARAMS = {"swing_strength": 3, "atr_mult": 2.0}
TARGETS = [1.0, 1.5, 2.0, 3.0, 4.0]
TIME_STOPS = [12, 24, 48]


def main() -> None:
    df = load("BTCUSD", TIMEFRAME, "2023-01-01", "2026-07-28")
    rows = []
    for tr in TARGETS:
        for ts in TIME_STOPS:
            wf = walk_forward(
                df,
                SweepConfirmationStrategy,
                [dict(ENTRY_PARAMS)],  # single config: entry is fixed
                costs=COST_MODELS["BTCUSD"],
                train_months=6,
                test_months=3,
                target_r=tr,
                time_stop_bars=ts,
            )
            trades = wf.oos_trades
            s = summarize(trades)
            ci = expectancy_ci(trades, iters=1000)
            row = {
                "label": f"target_r={tr:g} time_stop={ts}bars",
                "timeframe": TIMEFRAME,
                "target_r": tr,
                "time_stop_bars": ts,
                "n": s.n_trades,
                "hit_rate": round(s.hit_rate, 4),
                "expectancy_r": round(s.expectancy_r, 4),
                "exp_ci_lo": round(ci.lo, 4),
                "exp_ci_hi": round(ci.hi, 4),
                "profit_factor": round(s.profit_factor, 4),
                "max_drawdown_r": round(s.max_drawdown_r, 2),
                "avg_win_r": round(s.avg_win_r, 4),
                "avg_loss_r": round(s.avg_loss_r, 4),
                "total_r": round(s.total_r, 2),
            }
            rows.append(row)
            print(
                f"{row['label']:32s} n={row['n']:4d} hit={row['hit_rate']:.3f} "
                f"exp={row['expectancy_r']:+.3f}R [{row['exp_ci_lo']:+.3f},{row['exp_ci_hi']:+.3f}] "
                f"pf={row['profit_factor']:.2f} dd={row['max_drawdown_r']:.1f}R",
                flush=True,
            )

    out = ROOT / "reports_out" / "experiments" / "exit_design.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "experiment": "exit_design",
                "entry": ENTRY_PARAMS,
                "timeframe": TIMEFRAME,
                "costs": "COST_MODELS['BTCUSD']",
                "walk_forward": {"train_months": 6, "test_months": 3},
                "configs": rows,
            },
            indent=2,
        )
    )
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
