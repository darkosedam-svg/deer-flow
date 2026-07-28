"""BTCUSD deep history via Binance public data archive (data.binance.vision).

Why not the live REST API: api.binance.com is geo-blocked from many hosting
regions (returns "Service unavailable from a restricted location"). The
archive is a public CDN and is not blocked, ships full monthly kline files,
and is faster for bulk history anyway. The current month is not in the
monthly archive; the Hyperliquid loader covers the recent tail.
"""

from __future__ import annotations

import io
import zipfile

import httpx
import pandas as pd

from smc_research.data.canonical import to_canonical

ARCHIVE_URL = "https://data.binance.vision/data/spot/monthly/klines/{symbol}/{tf}/{symbol}-{tf}-{month}.zip"

_KLINE_COLS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades", "taker_base", "taker_quote", "ignore",
]

# Archive files dated 2025-01 onward switched open_time from milliseconds to
# microseconds. Detect by magnitude instead of by date so a re-export of old
# months can't break parsing.
_MS_MAX = 10**14


def fetch_month(
    symbol: str, timeframe: str, month: str, client: httpx.Client | None = None
) -> pd.DataFrame | None:
    """Download one monthly kline zip. Returns None on 404 (month not archived)."""
    url = ARCHIVE_URL.format(symbol=symbol, tf=timeframe, month=month)
    own_client = client is None
    client = client or httpx.Client(timeout=60.0, follow_redirects=True)
    try:
        resp = client.get(url)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            name = zf.namelist()[0]
            raw = pd.read_csv(zf.open(name), header=None, names=_KLINE_COLS)
    finally:
        if own_client:
            client.close()

    # Some newer archive files carry a header row; drop it if present.
    if raw.iloc[0]["open_time"] == "open_time":
        raw = raw.iloc[1:]
    open_time = pd.to_numeric(raw["open_time"])
    unit = "us" if open_time.iloc[0] > _MS_MAX else "ms"
    idx = pd.to_datetime(open_time, unit=unit, utc=True)
    df = pd.DataFrame(
        {
            "open": pd.to_numeric(raw["open"]),
            "high": pd.to_numeric(raw["high"]),
            "low": pd.to_numeric(raw["low"]),
            "close": pd.to_numeric(raw["close"]),
            "volume": pd.to_numeric(raw["volume"]),
        },
        index=idx,
    )
    df.index.name = "timestamp"
    return to_canonical(df)
