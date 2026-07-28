"""Recent candles from Hyperliquid's public info endpoint.

Hyperliquid retains roughly the most recent 5000 candles per interval
(~52 days of 15m bars), so this source covers the live tail while
Binance Vision covers deep history. No API key required.
"""

from __future__ import annotations

import httpx
import pandas as pd

from smc_research.data.canonical import to_canonical

INFO_URL = "https://api.hyperliquid.xyz/info"
MAX_CANDLES_PER_REQUEST = 5000


def fetch_candles(
    coin: str,
    timeframe: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    client: httpx.Client | None = None,
) -> pd.DataFrame:
    """Fetch [start, end) candles. Silently truncated to Hyperliquid's retention window."""
    own_client = client is None
    client = client or httpx.Client(timeout=30.0)
    rows: list[dict] = []
    cursor = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    try:
        while cursor < end_ms:
            resp = client.post(
                INFO_URL,
                json={
                    "type": "candleSnapshot",
                    "req": {
                        "coin": coin,
                        "interval": timeframe,
                        "startTime": cursor,
                        "endTime": end_ms,
                    },
                },
            )
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            rows.extend(batch)
            last_open = batch[-1]["t"]
            if len(batch) < MAX_CANDLES_PER_REQUEST:
                break
            cursor = last_open + 1
    finally:
        if own_client:
            client.close()

    if not rows:
        return _empty_frame()
    df = pd.DataFrame(rows)
    idx = pd.to_datetime(df["t"], unit="ms", utc=True)
    # .to_numpy() strips the RangeIndex — raw Series would align against the
    # datetime index and silently produce all-NaN columns.
    out = pd.DataFrame(
        {
            "open": pd.to_numeric(df["o"]).to_numpy(),
            "high": pd.to_numeric(df["h"]).to_numpy(),
            "low": pd.to_numeric(df["l"]).to_numpy(),
            "close": pd.to_numeric(df["c"]).to_numpy(),
            "volume": pd.to_numeric(df["v"]).to_numpy(),
        },
        index=pd.DatetimeIndex(idx.to_numpy()),
    )
    out.index.name = "timestamp"
    out = to_canonical(out)
    return out[(out.index >= start) & (out.index < end)]


def _empty_frame() -> pd.DataFrame:
    idx = pd.DatetimeIndex([], tz="UTC", name="timestamp")
    return pd.DataFrame(
        {c: pd.Series(dtype="float64") for c in ["open", "high", "low", "close", "volume"]},
        index=idx,
    )
