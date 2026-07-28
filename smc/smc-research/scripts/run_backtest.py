"""M3 exit criterion: one command regenerates the full backtest report.

    uv run python scripts/run_backtest.py [--start 2023-01-01] [--end now]

Instruments run whatever the data layer can currently serve (BTCUSD via
Binance Vision archive; EURUSD/ES join once their CSVs are dropped in —
see smc_research.data.csv_loader).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from smc_research import load  # noqa: E402
from smc_research.data.canonical import integrity_report  # noqa: E402
from smc_research.engine import (  # noqa: E402
    COST_MODELS,
    SweepConfirmationStrategy,
    walk_forward,
)
from smc_research.reports import InstrumentResult, render_report, to_pdf  # noqa: E402

PARAM_GRID = [
    {"swing_strength": 3, "stop_buffer_frac": 0.1},
    {"swing_strength": 5, "stop_buffer_frac": 0.1},
    {"swing_strength": 3, "stop_buffer_frac": 0.25},
    {"swing_strength": 5, "stop_buffer_frac": 0.25},
]
TARGET_R = 2.0
TIME_STOP_BARS = 96  # 24h of 15m bars
TRAIN_MONTHS, TEST_MONTHS = 6, 3


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2023-01-01")
    ap.add_argument("--end", default=None)
    ap.add_argument("--timeframe", default="15m")
    ap.add_argument("--out", default="reports_out/backtest_report.html")
    args = ap.parse_args()
    end = args.end or pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")

    results = []
    for symbol in ["BTCUSD"]:
        print(f"[{symbol}] loading {args.timeframe} {args.start} → {end} ...", flush=True)
        df = load(symbol, args.timeframe, args.start, end)
        rep = integrity_report(df, args.timeframe)
        print(
            f"[{symbol}] {rep.rows} bars, gap_ratio={rep.gap_ratio:.5f}, "
            f"largest_gap={rep.largest_gap}",
            flush=True,
        )
        wf = walk_forward(
            df,
            SweepConfirmationStrategy,
            PARAM_GRID,
            costs=COST_MODELS[symbol],
            train_months=TRAIN_MONTHS,
            test_months=TEST_MONTHS,
            target_r=TARGET_R,
            time_stop_bars=TIME_STOP_BARS,
        )
        print(
            f"[{symbol}] {len(wf.splits)} walk-forward windows, "
            f"{len(wf.oos_trades)} out-of-sample trades",
            flush=True,
        )
        results.append(
            InstrumentResult(
                symbol=symbol,
                timeframe=args.timeframe,
                trades=wf.oos_trades,
                costs=COST_MODELS[symbol],
                chosen_params=wf.chosen_params,
            )
        )

    out = render_report(
        results,
        strategy_name="SweepConfirmation (liquidity sweep of a confirmed swing, close back inside)",
        methodology={
            "signals": (
                "wick takes out a confirmed swing high/low (pivot, k bars each side) and the "
                "bar closes back on the original side; entry against the sweep direction"
            ),
            "target_r": TARGET_R,
            "time_stop_bars": TIME_STOP_BARS,
            "train_months": TRAIN_MONTHS,
            "test_months": TEST_MONTHS,
            "data_note": (
                "Binance Vision monthly kline archive (public), UTC bar-open timestamps; "
                "recent tail via Hyperliquid candleSnapshot; integrity-gated (monotonic, "
                "deduped, gap ratio reported above)"
            ),
        },
        out_path=args.out,
    )
    print(f"report → {out}")
    pdf = to_pdf(out, Path(args.out).with_suffix(".pdf"))
    print(f"pdf    → {pdf}" if pdf else "pdf    → skipped (WeasyPrint not installed)")


if __name__ == "__main__":
    main()
