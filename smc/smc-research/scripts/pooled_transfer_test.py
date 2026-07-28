"""Pooled transfer test of the trend-aligned 4h configuration.

The config (4h, ATR×2, k=3, aligned, target 2R, 30-bar time stop) was
selected on BTCUSD. Running it FROZEN — no re-selection, no walk-forward
optimization — on instruments it has never seen (ETHUSD, EURUSD, SPX500)
is a clean out-of-sample transfer test. Decision rule fixed in advance
(RESEARCH_LOG.md): if the pooled 95% CI on expectancy still straddles
zero, retire the sweep family; if it clears zero, the mechanism earns a
deeper confirmation pass.

BTCUSD is reported alongside for reference but EXCLUDED from the pooled
CI — it selected the config, so including it would double-dip.

    uv run python scripts/pooled_transfer_test.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from smc_research import load  # noqa: E402
from smc_research.engine import (  # noqa: E402
    COST_MODELS,
    TrendAlignedSweepStrategy,
    run_backtest,
)
from smc_research.stats import expectancy_ci, hit_rate_ci, summarize  # noqa: E402

CONFIG = {"swing_strength": 3, "atr_mult": 2.0, "mode": "aligned"}
TARGET_R = 2.0
TIME_STOP_BARS = 30  # ~5 days of 4h bars
START, END = "2023-01-01", "2026-07-28"

INSTRUMENTS = ["ETHUSD", "EURUSD", "SPX500"]  # transfer set (config never saw these)
REFERENCE = "BTCUSD"                          # selection instrument, excluded from pool


def run_symbol(symbol: str):
    df = load(symbol, "4h", START, END)
    trades = run_backtest(
        df,
        TrendAlignedSweepStrategy(**CONFIG),
        COST_MODELS[symbol],
        target_r=TARGET_R,
        time_stop_bars=TIME_STOP_BARS,
    )
    return df, trades


def describe(name: str, trades) -> None:
    s = summarize(trades)
    exp = expectancy_ci(trades, iters=2000)
    hit = hit_rate_ci(trades, iters=2000)
    print(
        f"{name:22s} n={s.n_trades:4d} hit={s.hit_rate:5.1%} [{hit.lo:.1%},{hit.hi:.1%}] "
        f"exp={s.expectancy_r:+.3f}R [{exp.lo:+.3f},{exp.hi:+.3f}] "
        f"pf={s.profit_factor:.2f} maxDD={s.max_drawdown_r:.1f}R total={s.total_r:+.1f}R"
    )


def main() -> None:
    pooled = []
    print(f"Frozen config: {CONFIG}, target {TARGET_R}R, time stop {TIME_STOP_BARS} bars\n")
    for symbol in INSTRUMENTS:
        df, trades = run_symbol(symbol)
        print(f"[{symbol}] {len(df)} bars {df.index[0].date()} → {df.index[-1].date()}")
        describe(symbol, trades)
        pooled.extend(trades)

    print("\n--- POOLED (transfer instruments only; decision sample) ---")
    describe("POOLED", pooled)

    _, ref = run_symbol(REFERENCE)
    print("\n--- reference (selection instrument, NOT in pool) ---")
    describe(REFERENCE, ref)

    exp = expectancy_ci(pooled, iters=2000)
    print(
        f"\nDECISION: pooled CI [{exp.lo:+.3f}, {exp.hi:+.3f}] → "
        + ("CI clears zero — mechanism earns a confirmation pass."
           if exp.lo > 0
           else "CI straddles/below zero — per the pre-registered rule, retire the sweep family.")
    )


if __name__ == "__main__":
    main()
