"""Adversarial verification of confluence_zone claimed config ob|1h|ATRx2.0|k=3.

Checks:
1. Reproduce the exact config (base costs) -> compare to claimed numbers.
2. Re-run with costs x 1.5 (scaled CostModel) -> does expectancy stay > 0?
3. Split OOS trades by calendar year (entry_time year): n, hit, expectancy, CI.
4. Concentration: distinct entry days, top-day / top-5-day share of |total R| and counts.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from smc_research import load
from smc_research.engine import COST_MODELS, walk_forward
from smc_research.engine.costs import CostModel
from smc_research.stats import expectancy_ci, summarize

# Import the exact strategy under test from the original experiment script.
sys.path.insert(0, str(ROOT / "scripts" / "experiments"))
from confluence_zone import ConfluenceZoneSweepStrategy  # noqa: E402

BASE = COST_MODELS["BTCUSD"]
SCALED = CostModel(
    spread_bps=BASE.spread_bps * 1.5,
    slippage_bps=BASE.slippage_bps * 1.5,
    commission_bps=BASE.commission_bps * 1.5,
)


def run(costs: CostModel):
    df = load("BTCUSD", "1h", "2023-01-01", "2026-07-28")
    wf = walk_forward(
        df,
        ConfluenceZoneSweepStrategy,
        [{"zone_source": "ob", "swing_strength": 3, "atr_mult": 2.0}],
        costs=costs,
        train_months=6,
        test_months=3,
        time_stop_bars=24,
        target_r=2.0,
    )
    return wf.oos_trades


def stats_block(trades):
    if not trades:
        return {"n": 0}
    s = summarize(trades)
    ci = expectancy_ci(trades, iters=1000)
    return {
        "n": s.n_trades,
        "hit_rate": round(s.hit_rate, 4),
        "expectancy_r": round(s.expectancy_r, 4),
        "exp_ci_lo": round(ci.lo, 4),
        "exp_ci_hi": round(ci.hi, 4),
        "profit_factor": round(s.profit_factor, 4) if s.profit_factor != float("inf") else None,
        "total_r": round(s.total_r, 4),
        "max_drawdown_r": round(s.max_drawdown_r, 4),
    }


def main() -> None:
    out: dict = {}

    base_trades = run(BASE)
    out["base_reproduction"] = stats_block(base_trades)
    print("BASE  :", out["base_reproduction"])

    scaled_trades = run(SCALED)
    out["costs_x1.5"] = stats_block(scaled_trades)
    print("x1.5  :", out["costs_x1.5"])

    # Year split (by entry_time year) on the BASE run.
    by_year = defaultdict(list)
    for t in base_trades:
        by_year[t.entry_time.year].append(t)
    out["by_year"] = {}
    for yr in sorted(by_year):
        out["by_year"][str(yr)] = stats_block(by_year[yr])
        print(f"{yr}  :", out["by_year"][str(yr)])

    # Concentration by entry day.
    day_r = Counter()
    day_n = Counter()
    for t in base_trades:
        d = t.entry_time.date().isoformat()
        day_r[d] += t.realized_r
        day_n[d] += 1
    total_r = sum(t.realized_r for t in base_trades)
    top_pos_days = sorted(day_r.items(), key=lambda kv: kv[1], reverse=True)[:5]
    out["concentration"] = {
        "n_trades": len(base_trades),
        "n_distinct_entry_days": len(day_n),
        "max_trades_one_day": max(day_n.values()),
        "total_r": round(total_r, 4),
        "top5_days_by_r": [(d, round(r, 3), day_n[d]) for d, r in top_pos_days],
        "top5_days_r_sum": round(sum(r for _, r in top_pos_days), 4),
    }
    print("CONC  :", out["concentration"])

    # Exit-reason mix for context.
    out["exit_reasons"] = dict(Counter(t.exit_reason for t in base_trades))
    print("EXITS :", out["exit_reasons"])

    dest = ROOT / "reports_out" / "experiments" / "verify_confluence_zone_ob_1h_ATRx2_0_k_3.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2))
    print(f"Wrote {dest}")


if __name__ == "__main__":
    main()
