"""Local Parquet cache. One file per (source, symbol, timeframe, month).

M0 rule: never re-download during a backtest run. Loaders check the cache
month-by-month and only fetch months that are absent. The current
(incomplete) month is cached with a `.partial` marker so it gets refreshed.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

DEFAULT_CACHE_DIR = Path(os.environ.get("SMC_CACHE_DIR", "data_cache"))


def month_key(ts: pd.Timestamp) -> str:
    return f"{ts.year:04d}-{ts.month:02d}"


def months_between(start: pd.Timestamp, end: pd.Timestamp) -> list[str]:
    cur = pd.Timestamp(year=start.year, month=start.month, day=1, tz="UTC")
    stop = pd.Timestamp(year=end.year, month=end.month, day=1, tz="UTC")
    out = []
    while cur <= stop:
        out.append(month_key(cur))
        cur = cur + pd.offsets.MonthBegin(1)
    return out


class ParquetCache:
    def __init__(self, root: Path | str = DEFAULT_CACHE_DIR):
        self.root = Path(root)

    def _path(self, source: str, symbol: str, timeframe: str, month: str) -> Path:
        return self.root / source / symbol / timeframe / f"{month}.parquet"

    def has(self, source: str, symbol: str, timeframe: str, month: str) -> bool:
        p = self._path(source, symbol, timeframe, month)
        return p.exists() and not p.with_suffix(".partial").exists()

    def get(self, source: str, symbol: str, timeframe: str, month: str) -> pd.DataFrame | None:
        p = self._path(source, symbol, timeframe, month)
        if not p.exists():
            return None
        return pd.read_parquet(p)

    def put(
        self,
        source: str,
        symbol: str,
        timeframe: str,
        month: str,
        df: pd.DataFrame,
        partial: bool = False,
    ) -> None:
        p = self._path(source, symbol, timeframe, month)
        p.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(p)
        marker = p.with_suffix(".partial")
        if partial:
            marker.touch()
        elif marker.exists():
            marker.unlink()
