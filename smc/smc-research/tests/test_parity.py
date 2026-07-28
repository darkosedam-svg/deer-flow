"""M4 harness self-test: build a synthetic 'TradingView export' from the
Python detectors' own signals, perturb it, and check the diff arithmetic."""

import pandas as pd
import pytest

from smc_research.detectors import FVGDetector, StructureDetector
from smc_research.detectors.types import run
from smc_research.parity import (
    DEFAULT_COLUMN_MAP,
    diff_export,
    diff_signals,
    pine_signals_from_export,
)
from smc_research.parity.diff import ParityKey


@pytest.fixture()
def export_csv(tmp_path, fixture_df):
    """Synthetic export: OHLCV + parity columns filled from Python signals."""
    df = fixture_df.iloc[:800].copy()
    signals = run(FVGDetector(), df) + run(StructureDetector(), df)
    inverse = {v: k for k, v in DEFAULT_COLUMN_MAP.items()}
    for col in DEFAULT_COLUMN_MAP:
        df[col] = float("nan")
    for s in signals:
        col = inverse.get((s.kind, s.direction))
        if col:
            df.loc[s.timestamp, col] = s.price
    out = df.reset_index()
    # int(.timestamp()) is resolution-independent; astype("int64") is not.
    out["time"] = out["timestamp"].map(lambda t: int(t.timestamp()))
    out = out.drop(columns=["timestamp"])
    path = tmp_path / "export.csv"
    out.to_csv(path, index=False)
    return path


def test_perfect_export_matches_100_percent(export_csv):
    report = diff_export(export_csv, [FVGDetector(), StructureDetector()])
    assert report.pine_only == []
    assert report.python_only == []
    assert report.match_rate == 1.0
    assert report.passes_gate


def test_missing_pine_signals_fail_gate(export_csv, tmp_path):
    df = pd.read_csv(export_csv)
    col = "fvg_bull"
    hits = df.index[df[col].notna()]
    df.loc[hits[: max(1, len(hits) // 2)], col] = float("nan")  # Pine "misses" half
    broken = tmp_path / "broken.csv"
    df.to_csv(broken, index=False)
    report = diff_export(broken, [FVGDetector(), StructureDetector()])
    assert len(report.python_only) > 0
    assert report.match_rate < 1.0


def test_timestamp_tolerance():
    step = pd.Timedelta(minutes=15)
    t0 = pd.Timestamp("2024-01-01 00:00", tz="UTC")
    pine = [ParityKey(t0 + step, "bos", "bullish")]  # one bar late

    from smc_research.detectors.types import Signal

    python = [Signal(t0, "bos", "bullish", 100.0)]
    strict = diff_signals(pine, python, kinds={"bos"}, tolerance_bars=0)
    assert strict.match_rate == 0.0
    loose = diff_signals(pine, python, kinds={"bos"}, tolerance_bars=1, bar_step=step)
    assert loose.match_rate == 1.0


def test_export_parses_iso_and_unix(tmp_path, fixture_df):
    df = fixture_df.iloc[:10].reset_index()
    df["time"] = df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    df = df.drop(columns=["timestamp"])
    path = tmp_path / "iso.csv"
    df.to_csv(path, index=False)
    signals = pine_signals_from_export(pd.read_csv(path).set_index("time"))
    assert signals == []  # no parity columns → no signals, but parsing survived
