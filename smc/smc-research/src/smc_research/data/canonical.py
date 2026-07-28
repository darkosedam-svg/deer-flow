"""Canonical OHLCV frame: the single format every loader must produce.

Spec (M0):
- pandas DataFrame indexed by a tz-aware UTC DatetimeIndex named "timestamp"
  (bar OPEN time), strictly increasing, no duplicates.
- Columns exactly: open, high, low, close, volume — all float64.
- Gaps are allowed in the index (exchange downtime, market close) but must stay
  under a documented threshold; `integrity_report` quantifies them.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

CANONICAL_COLUMNS = ["open", "high", "low", "close", "volume"]

TIMEFRAMES: dict[str, pd.Timedelta] = {
    "1m": pd.Timedelta(minutes=1),
    "5m": pd.Timedelta(minutes=5),
    "15m": pd.Timedelta(minutes=15),
    "1h": pd.Timedelta(hours=1),
    "4h": pd.Timedelta(hours=4),
    "1d": pd.Timedelta(days=1),
}

# Documented gap thresholds per M0 exit criterion. Crypto trades 24/7 so the
# bar grid should be near-complete; FX/equities close, so missing weekend/night
# bars are structural, not data loss — hence the looser bound.
MAX_GAP_RATIO_24_7 = 0.005
MAX_GAP_RATIO_SESSION_MARKET = 0.35


class IntegrityError(ValueError):
    """Raised when a frame violates the canonical OHLCV contract."""


@dataclass(frozen=True)
class IntegrityReport:
    rows: int
    start: pd.Timestamp
    end: pd.Timestamp
    expected_bars: int
    missing_bars: int
    gap_ratio: float
    largest_gap: pd.Timedelta
    ohlc_violations: int


def to_canonical(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize a raw loader frame into the canonical format (sort, dedupe, cast)."""
    out = df.copy()
    if not isinstance(out.index, pd.DatetimeIndex):
        raise IntegrityError("index must be a DatetimeIndex")
    if out.index.tz is None:
        out.index = out.index.tz_localize("UTC")
    else:
        out.index = out.index.tz_convert("UTC")
    out.index.name = "timestamp"
    out = out[~out.index.duplicated(keep="first")].sort_index()
    missing = [c for c in CANONICAL_COLUMNS if c not in out.columns]
    if missing:
        raise IntegrityError(f"missing columns: {missing}")
    out = out[CANONICAL_COLUMNS].astype("float64")
    return out


def integrity_report(df: pd.DataFrame, timeframe: str) -> IntegrityReport:
    if timeframe not in TIMEFRAMES:
        raise IntegrityError(f"unknown timeframe {timeframe!r}; known: {list(TIMEFRAMES)}")
    if len(df) == 0:
        raise IntegrityError("empty frame")
    step = TIMEFRAMES[timeframe]
    idx = df.index
    if not isinstance(idx, pd.DatetimeIndex) or idx.tz is None or str(idx.tz) != "UTC":
        raise IntegrityError("index must be a UTC tz-aware DatetimeIndex")
    if not idx.is_monotonic_increasing:
        raise IntegrityError("index is not monotonically increasing")
    if idx.has_duplicates:
        raise IntegrityError("index has duplicate timestamps")

    expected = int((idx[-1] - idx[0]) / step) + 1
    missing = expected - len(df)
    diffs = idx.to_series().diff().dropna()
    largest_gap = diffs.max() if len(diffs) else pd.Timedelta(0)

    ohlc_bad = int(
        (
            (df["high"] < df[["open", "close", "low"]].max(axis=1))
            | (df["low"] > df[["open", "close", "high"]].min(axis=1))
        ).sum()
    )

    return IntegrityReport(
        rows=len(df),
        start=idx[0],
        end=idx[-1],
        expected_bars=expected,
        missing_bars=missing,
        gap_ratio=missing / expected if expected else 0.0,
        largest_gap=largest_gap,
        ohlc_violations=ohlc_bad,
    )


def assert_integrity(
    df: pd.DataFrame, timeframe: str, max_gap_ratio: float = MAX_GAP_RATIO_24_7
) -> IntegrityReport:
    """M0 exit-criterion check: raise IntegrityError unless the frame is clean."""
    report = integrity_report(df, timeframe)
    if report.gap_ratio > max_gap_ratio:
        raise IntegrityError(
            f"gap ratio {report.gap_ratio:.4f} exceeds threshold {max_gap_ratio} "
            f"({report.missing_bars}/{report.expected_bars} bars missing)"
        )
    if report.ohlc_violations:
        raise IntegrityError(
            f"{report.ohlc_violations} bars violate high>=max(o,c,l)/low<=min(o,c,h)"
        )
    return report
