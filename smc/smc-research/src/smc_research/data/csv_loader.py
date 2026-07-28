"""Generic CSV → canonical OHLCV, for sources without a programmatic loader yet.

EURUSD (Dukascopy export) and the ES/SPX proxy (SPY bars) enter through this
path in W1; dedicated loaders can replace it later without touching callers.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from smc_research.data.canonical import to_canonical

_COLUMN_ALIASES = {
    "time": "timestamp", "date": "timestamp", "datetime": "timestamp", "gmt time": "timestamp",
    "o": "open", "h": "high", "l": "low", "c": "close",
    "vol": "volume", "vol.": "volume", "tickvol": "volume", "tick_volume": "volume",
}


def load_csv(path: str | Path, tz: str = "UTC") -> pd.DataFrame:
    raw = pd.read_csv(path)
    raw.columns = [_COLUMN_ALIASES.get(c.strip().lower(), c.strip().lower()) for c in raw.columns]
    if "timestamp" not in raw.columns:
        raise ValueError(f"{path}: no timestamp column found in {list(raw.columns)}")
    ts = pd.to_datetime(raw["timestamp"], utc=False, format="mixed", dayfirst=False)
    if ts.dt.tz is None:
        ts = ts.dt.tz_localize(tz)
    df = raw.drop(columns=["timestamp"]).set_index(ts)
    if "volume" not in df.columns:
        df["volume"] = 0.0
    df.index.name = "timestamp"
    return to_canonical(df)
