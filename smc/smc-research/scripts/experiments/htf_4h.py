"""Experiment: htf_4h.

Hypothesis: cost drag shrinks with bar size. The ~15bp round-trip cost of
COST_MODELS["BTCUSD"] ate every 15m/1h config (all 48 prior configs negative
OOS; best 1h was -0.10R). On 4h bars a sweep of a multi-day swing level risks
a much larger absolute distance, so the same friction is a smaller fraction
of R — 4h (and 1d, which the loader serves from the Binance Vision monthly
archive) may be the only place this signal family clears costs.

Grid (12 configs, each its own single-config walk_forward run so every cell
is a clean OOS read with no per-fold selection):

  4h (10): swing_strength {3,5,8} x atr_mult {1.0,2.0} x target_r {2.0,3.0},
           dropping target_r=3.0 for ss=8 (per plan, to stay under the cap
           where samples would be thinnest anyway). time_stop_bars=30 (~5d).
  1d (2):  swing_strength 3, atr_mult {1.0,2.0}, target_r 2.0,
           time_stop_bars=5 (~5d).

All numbers walk-forward OOS (6m train / 3m test) with COST_MODELS["BTCUSD"].
Sample sizes at these timeframes are small — the CI is the answer.
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

START, END = "2023-01-01", "2026-07-28"

# (timeframe, swing_strength, atr_mult, target_r, time_stop_bars)
CONFIGS: list[tuple[str, int, float, float, int]] = []
for ss in (3, 5, 8):
    for am in (1.0, 2.0):
        for tr in (2.0, 3.0):
            if ss == 8 and tr == 3.0:
                continue  # cap at 12: drop target 3.0 for ss=8
            CONFIGS.append(("4h", ss, am, tr, 30))
for am in (1.0, 2.0):
    CONFIGS.append(("1d", 3, am, 2.0, 5))

assert len(CONFIGS) == 12


def main() -> None:
    frames = {tf: load("BTCUSD", tf, START, END) for tf in {c[0] for c in CONFIGS}}
    rows = []
    for tf, ss, am, tr, ts in CONFIGS:
        wf = walk_forward(
            frames[tf],
            SweepConfirmationStrategy,
            [{"swing_strength": ss, "atr_mult": am}],  # single config: no selection
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
            "label": f"{tf} ss={ss} atr={am:g} target_r={tr:g}",
            "timeframe": tf,
            "swing_strength": ss,
            "atr_mult": am,
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

    out = ROOT / "reports_out" / "experiments" / "htf_4h.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "experiment": "htf_4h",
                "hypothesis": "cost drag shrinks with bar size; 4h/1d sweeps may clear costs",
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
