"""Pine ↔ Python parity harness (Plan B M4 — the keystone).

Workflow:
1. Add the parity variant of the Pine script to a chart (it plots one numeric
   series per signal kind; na when no signal).
2. TradingView chart → "Export chart data" → CSV for a fixed
   symbol/timeframe/range.
3. `diff_export(csv_path, detectors)` runs the Python detectors over the
   exact same bars (taken FROM the export, so both sides see identical data)
   and reports matched / Pine-only / Python-only signals.

Gate: ≥98% match on BTCUSD 15m over 12 months. Below that → fix Pine,
never the threshold. Every unmatched signal must be individually explained.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from smc_research.data.canonical import to_canonical
from smc_research.detectors.types import Detector, Signal, run

# Export column name -> (kind, direction) emitted by the Python detectors.
# The parity Pine script must plot with exactly these series titles.
DEFAULT_COLUMN_MAP: dict[str, tuple[str, str]] = {
    "fvg_bull": ("fvg_created", "bullish"),
    "fvg_bear": ("fvg_created", "bearish"),
    "ob_bull": ("ob_created", "bullish"),
    "ob_bear": ("ob_created", "bearish"),
    "bos_bull": ("bos", "bullish"),
    "bos_bear": ("bos", "bearish"),
    "choch_bull": ("choch", "bullish"),
    "choch_bear": ("choch", "bearish"),
    "sweep_bull": ("liquidity_sweep", "bullish"),
    "sweep_bear": ("liquidity_sweep", "bearish"),
}


@dataclass(frozen=True)
class ParityKey:
    timestamp: pd.Timestamp
    kind: str
    direction: str


@dataclass
class ParityReport:
    matched: list[ParityKey] = field(default_factory=list)
    pine_only: list[ParityKey] = field(default_factory=list)
    python_only: list[ParityKey] = field(default_factory=list)
    price_drift: list[tuple[ParityKey, float, float]] = field(default_factory=list)

    @property
    def match_rate(self) -> float:
        total = len(self.matched) + len(self.pine_only) + len(self.python_only)
        return len(self.matched) / total if total else 1.0

    @property
    def passes_gate(self) -> bool:
        return self.match_rate >= 0.98

    def summary(self) -> str:
        return (
            f"matched={len(self.matched)} pine_only={len(self.pine_only)} "
            f"python_only={len(self.python_only)} match_rate={self.match_rate:.2%} "
            f"gate(≥98%)={'PASS' if self.passes_gate else 'FAIL'}"
        )


def load_tv_export(path: str | Path) -> pd.DataFrame:
    """Parse a TradingView chart-data CSV export: `time` column (unix seconds
    or ISO), OHLCV, plus the parity plot columns."""
    raw = pd.read_csv(path)
    raw.columns = [c.strip().lower() for c in raw.columns]
    if "time" not in raw.columns:
        raise ValueError(f"no 'time' column in export; got {list(raw.columns)}")
    t = raw["time"]
    if pd.api.types.is_numeric_dtype(t):
        idx = pd.to_datetime(t, unit="s", utc=True)
    else:
        idx = pd.to_datetime(t, utc=True, format="ISO8601")
    return raw.drop(columns=["time"]).set_index(idx).rename_axis("timestamp")


def pine_signals_from_export(
    export: pd.DataFrame, column_map: dict[str, tuple[str, str]] | None = None
) -> list[ParityKey]:
    column_map = column_map or DEFAULT_COLUMN_MAP
    out: list[ParityKey] = []
    for col, (kind, direction) in column_map.items():
        if col not in export.columns:
            continue
        series = pd.to_numeric(export[col], errors="coerce")
        for ts in export.index[series.notna()]:
            out.append(ParityKey(ts, kind, direction))
    return sorted(out, key=lambda k: (k.timestamp.isoformat(), k.kind, k.direction))


def diff_signals(
    pine: list[ParityKey],
    python_signals: list[Signal],
    kinds: set[str],
    tolerance_bars: int = 0,
    bar_step: pd.Timedelta | None = None,
) -> ParityReport:
    """Match by (timestamp, kind, direction); tolerance_bars allows ±N bars of
    timestamp drift (needs bar_step). Report every leftover on both sides."""
    report = ParityReport()
    py = [
        ParityKey(s.timestamp, s.kind, s.direction)
        for s in python_signals
        if s.kind in kinds
    ]
    py_pool: dict[tuple, list[ParityKey]] = {}
    for k in py:
        py_pool.setdefault((k.timestamp, k.kind, k.direction), []).append(k)

    def take(ts: pd.Timestamp, kind: str, direction: str) -> ParityKey | None:
        bucket = py_pool.get((ts, kind, direction))
        if bucket:
            return bucket.pop()
        return None

    for pk in pine:
        hit = take(pk.timestamp, pk.kind, pk.direction)
        if hit is None and tolerance_bars > 0 and bar_step is not None:
            for off in range(1, tolerance_bars + 1):
                hit = take(pk.timestamp + off * bar_step, pk.kind, pk.direction) or take(
                    pk.timestamp - off * bar_step, pk.kind, pk.direction
                )
                if hit is not None:
                    break
        if hit is not None:
            report.matched.append(pk)
        else:
            report.pine_only.append(pk)

    for bucket in py_pool.values():
        report.python_only.extend(bucket)
    report.python_only.sort(key=lambda k: (k.timestamp.isoformat(), k.kind, k.direction))
    return report


def diff_export(
    export_path: str | Path,
    detectors: list[Detector],
    column_map: dict[str, tuple[str, str]] | None = None,
    tolerance_bars: int = 0,
    bar_step: pd.Timedelta | None = None,
) -> ParityReport:
    """End-to-end: export CSV → Pine signal keys + Python detector run over
    the export's own OHLCV bars → diff."""
    export = load_tv_export(export_path)
    column_map = column_map or DEFAULT_COLUMN_MAP
    kinds = {kind for kind, _ in column_map.values()}

    bars = to_canonical(export[["open", "high", "low", "close", "volume"]])
    python_signals: list[Signal] = []
    for det in detectors:
        python_signals.extend(run(det, bars))

    pine = pine_signals_from_export(export, column_map)
    return diff_signals(pine, python_signals, kinds, tolerance_bars, bar_step)
