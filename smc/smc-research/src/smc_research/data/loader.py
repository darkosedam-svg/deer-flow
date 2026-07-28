"""`load()` — the M0 exit-criterion entry point.

    from smc_research import load
    df = load("BTCUSD", "15m", "2023-01-01", "2026-07-01")

Assembles deep history from cached Binance Vision monthly files (downloading
only missing months), tops up the recent tail from Hyperliquid, validates the
result against the canonical integrity contract, and returns the clean frame.
"""

from __future__ import annotations

import pandas as pd

from smc_research.data import binance_vision, hyperliquid
from smc_research.data.cache import DEFAULT_CACHE_DIR, ParquetCache, month_key, months_between
from smc_research.data.canonical import (
    MAX_GAP_RATIO_24_7,
    IntegrityError,
    assert_integrity,
    to_canonical,
)

# Instrument registry: canonical symbol -> per-source identifiers.
SYMBOLS: dict[str, dict[str, str]] = {
    "BTCUSD": {"binance_vision": "BTCUSDT", "hyperliquid": "BTC"},
    "ETHUSD": {"binance_vision": "ETHUSDT", "hyperliquid": "ETH"},
    # EURUSD / ES-proxy arrive via csv_loader until dedicated loaders exist (M0 note).
}


def load(
    symbol: str,
    timeframe: str,
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
    cache_dir=DEFAULT_CACHE_DIR,
    max_gap_ratio: float = MAX_GAP_RATIO_24_7,
    validate: bool = True,
) -> pd.DataFrame:
    if symbol not in SYMBOLS:
        raise KeyError(f"unknown symbol {symbol!r}; known: {list(SYMBOLS)}")
    start = pd.Timestamp(start, tz="UTC")
    end = pd.Timestamp(end, tz="UTC")
    if start >= end:
        raise ValueError("start must be before end")

    cache = ParquetCache(cache_dir)
    bv_symbol = SYMBOLS[symbol]["binance_vision"]
    now = pd.Timestamp.now(tz="UTC")
    current_month = month_key(now)

    frames: list[pd.DataFrame] = []
    # end is exclusive: an end exactly on a month boundary needs nothing from that month
    for month in months_between(start, end - pd.Timedelta(microseconds=1)):
        if month >= current_month:
            continue  # monthly archive only has completed months
        if cache.has("binance_vision", symbol, timeframe, month):
            frames.append(cache.get("binance_vision", symbol, timeframe, month))
            continue
        df = binance_vision.fetch_month(bv_symbol, timeframe, month)
        if df is None:
            continue  # month predates listing or not yet published
        cache.put("binance_vision", symbol, timeframe, month, df)
        frames.append(df)

    history = pd.concat(frames) if frames else None
    tail_start = history.index[-1] + pd.Timedelta(seconds=1) if history is not None else start
    if end > tail_start:
        hl_coin = SYMBOLS[symbol]["hyperliquid"]
        tail = hyperliquid.fetch_candles(hl_coin, timeframe, tail_start, min(end, now))
        if len(tail):
            frames.append(tail)

    if not frames:
        raise IntegrityError(f"no data available for {symbol} {timeframe} in [{start}, {end})")

    out = to_canonical(pd.concat(frames))
    out = out[(out.index >= start) & (out.index < end)]
    if validate:
        assert_integrity(out, timeframe, max_gap_ratio=max_gap_ratio)
    return out
