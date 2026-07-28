import pandas as pd
import pytest

from smc_research.data.canonical import (
    IntegrityError,
    assert_integrity,
    integrity_report,
    to_canonical,
)


def test_to_canonical_sorts_dedupes_and_casts(fixture_df):
    shuffled = fixture_df.sample(frac=1.0, random_state=1)
    doubled = pd.concat([shuffled, shuffled.iloc[:100]])
    out = to_canonical(doubled)
    assert out.index.is_monotonic_increasing
    assert not out.index.has_duplicates
    assert list(out.columns) == ["open", "high", "low", "close", "volume"]
    assert all(dt == "float64" for dt in out.dtypes)
    assert len(out) == len(fixture_df)


def test_integrity_clean_frame_passes(fixture_df):
    report = assert_integrity(fixture_df, "15m")
    assert report.missing_bars == 0
    assert report.gap_ratio == 0.0
    assert report.ohlc_violations == 0


def test_integrity_rejects_excess_gaps(fixture_df):
    holey = fixture_df.drop(fixture_df.index[100:200])
    with pytest.raises(IntegrityError, match="gap ratio"):
        assert_integrity(holey, "15m", max_gap_ratio=0.005)
    # Same frame is fine under the session-market threshold.
    assert_integrity(holey, "15m", max_gap_ratio=0.35)


def test_integrity_rejects_naive_index(fixture_df):
    naive = fixture_df.copy()
    naive.index = naive.index.tz_localize(None)
    with pytest.raises(IntegrityError):
        integrity_report(naive, "15m")


def test_integrity_counts_ohlc_violations(fixture_df):
    bad = fixture_df.copy()
    bad.iloc[10, bad.columns.get_loc("high")] = bad.iloc[10]["low"] - 1
    with pytest.raises(IntegrityError, match="violate"):
        assert_integrity(bad, "15m")
