"""Session-3 strategy research: can any sweep-confirmation configuration
clear costs out-of-sample?

Axes (from EXECUTION.md's research queue):
- stop placement: sweep-extreme (naive) vs ATR-buffered structural
- cost-aware min-risk filter (skip setups where costs dominate the R math)
- timeframe: 15m vs 1h

Discipline: every per-config number below is walk-forward OUT-OF-SAMPLE
(params fixed per config; the walk-forward merely rolls the windows).
The combined-grid run at the end is the deployable procedure: per-window
selection on train data only. Nothing here touches a holdout-free number.

    uv run python scripts/research_strategies.py
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from smc_research import load  # noqa: E402
from smc_research.engine import (  # noqa: E402
    COST_MODELS,
    SweepConfirmationStrategy,
    walk_forward,
)
from smc_research.stats import expectancy_ci, summarize  # noqa: E402

START, END = "2023-01-01", None  # None → now
SYMBOL = "BTCUSD"

GRID = [
    {"swing_strength": ss, "atr_mult": am, "min_risk_bps": mr}
    for ss, am, mr in itertools.product([3, 5], [None, 0.5, 1.0, 2.0], [0.0, 30.0, 60.0])
]

TIMEFRAMES = {
    "15m": {"time_stop_bars": 96},   # 24h
    "1h": {"time_stop_bars": 24},    # 24h
}


def config_label(p: dict) -> str:
    am = p["atr_mult"]
    return (
        f"ss={p['swing_strength']} "
        f"stop={'extreme' if am is None else f'ATR×{am}'} "
        f"minrisk={int(p['min_risk_bps'])}bps"
    )


def main() -> None:
    end = END or pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")
    rows = []
    for tf, tf_cfg in TIMEFRAMES.items():
        df = load(SYMBOL, tf, START, end)
        print(f"\n=== {SYMBOL} {tf}: {len(df)} bars ===", flush=True)
        for params in GRID:
            wf = walk_forward(
                df,
                SweepConfirmationStrategy,
                [params],  # singleton grid → this config's own OOS record
                costs=COST_MODELS[SYMBOL],
                train_months=6,
                test_months=3,
                time_stop_bars=tf_cfg["time_stop_bars"],
            )
            s = summarize(wf.oos_trades)
            ci = expectancy_ci(wf.oos_trades, iters=1000)
            rows.append(
                {
                    "tf": tf,
                    "config": config_label(params),
                    "n": s.n_trades,
                    "hit": s.hit_rate,
                    "exp_r": s.expectancy_r,
                    "exp_lo": ci.lo,
                    "exp_hi": ci.hi,
                    "pf": s.profit_factor,
                    "max_dd": s.max_drawdown_r,
                    "total_r": s.total_r,
                }
            )
            print(
                f"  {config_label(params):44s} n={s.n_trades:5d} hit={s.hit_rate:5.1%} "
                f"exp={s.expectancy_r:+.3f}R [{ci.lo:+.3f},{ci.hi:+.3f}] pf={s.profit_factor:.2f}",
                flush=True,
            )

    out = pd.DataFrame(rows).sort_values("exp_r", ascending=False)
    out_path = Path("reports_out/strategy_research.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    print(f"\nfull table → {out_path}")

    print("\n=== Combined-grid walk-forward (deployable procedure, per-window selection) ===")
    for tf, tf_cfg in TIMEFRAMES.items():
        df = load(SYMBOL, tf, START, end)
        wf = walk_forward(
            df,
            SweepConfirmationStrategy,
            GRID,
            costs=COST_MODELS[SYMBOL],
            train_months=6,
            test_months=3,
            time_stop_bars=tf_cfg["time_stop_bars"],
        )
        s = summarize(wf.oos_trades)
        ci = expectancy_ci(wf.oos_trades, iters=1000)
        print(
            f"  {tf}: n={s.n_trades} hit={s.hit_rate:.1%} exp={s.expectancy_r:+.3f}R "
            f"[{ci.lo:+.3f},{ci.hi:+.3f}] pf={s.profit_factor:.2f} maxDD={s.max_drawdown_r:.1f}R",
            flush=True,
        )


if __name__ == "__main__":
    main()
