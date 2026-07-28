"""`load()` — the M0 exit-criterion entry point.

    from smc_research import load
    df = load("BTCUSD", "15m", "2023-01-01", "2026-07-01")

Crypto: deep history from cached Binance Vision monthly files (downloading
only missing months) + recent tail from Hyperliquid. FX/indices: Dukascopy
public hour candles (native 1h; 4h/1d by resample). Every frame passes the
canonical integrity gate before it is returned; FX/index symbols default to
the looser session-market gap threshold because market-closed hours are
structural, not data loss.
"""

from __future__ import annotations

import pandas as pd

from smc_research.data import binance_vision, dukascopy, hyperliquid
from smc_research.data.cache import DEFAULT_CACHE_DIR, ParquetCache, month_key, months_between
from smc_research.data.canonical import (
    MAX_GAP_RATIO_24_7,
    MAX_GAP_RATIO_SESSION_MARKET,
    IntegrityError,
    assert_integrity,
    to_canonical,
)

# Instrument registry: canonical symbol -> source + per-source identifiers.
SYMBOLS: dict[str, dict[str, str]] = {
    "BTCUSD": {"source": "binance", "binance_vision": "BTCUSDT", "hyperliquid": "BTC"},
    "ETHUSD": {"source": "binance", "binance_vision": "ETHUSDT", "hyperliquid": "ETH"},
    "EURUSD": {"source": "dukascopy", "dukascopy": "EURUSD"},
    "SPX500": {"source": "dukascopy", "dukascopy": "USA500IDXUSD"},
}

_DUKA_RESAMPLE = {"1h": None, "4h": "4h", "1d": "1D"}


def load(
    symbol: str,
    timeframe: str,
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
    cache_dir=DEFAULT_CACHE_DIR,
    max_gap_ratio: float | None = None,
    validate: bool = True,
) -> pd.DataFrame:
    if symbol not in SYMBOLS:
        raise KeyError(f"unknown symbol {symbol!r}; known: {list(SYMBOLS)}")
    start = pd.Timestamp(start, tz="UTC")
    end = pd.Timestamp(end, tz="UTC")
    if start >= end:
        raise ValueError("start must be before end")

    spec = SYMBOLS[symbol]
    cache = ParquetCache(cache_dir)

    if spec["source"] == "binance":
        out = _load_binance(symbol, spec, timeframe, start, end, cache)
        default_gap = MAX_GAP_RATIO_24_7
    else:
        out = _load_dukascopy(symbol, spec, timeframe, start, end, cache)
        default_gap = MAX_GAP_RATIO_SESSION_MARKET

    out = out[(out.index >= start) & (out.index < end)]
    if len(out) == 0:
        raise IntegrityError(f"no data available for {symbol} {timeframe} in [{start}, {end})")
    if validate:
        assert_integrity(
            out, timeframe, max_gap_ratio=default_gap if max_gap_ratio is None else max_gap_ratio
        )
    return out


def _load_binance(symbol, spec, timeframe, start, end, cache) -> pd.DataFrame:
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
        df = binance_vision.fetch_month(spec["binance_vision"], timeframe, month)
        if df is None:
            continue  # month predates listing or not yet published
        cache.put("binance_vision", symbol, timeframe, month, df)
        frames.append(df)

    history = pd.concat(frames) if frames else None
    tail_start = history.index[-1] + pd.Timedelta(seconds=1) if history is not None else start
    if end > tail_start:
        tail = hyperliquid.fetch_candles(spec["hyperliquid"], timeframe, tail_start, min(end, now))
        if len(tail):
            frames.append(tail)
    if not frames:
        raise IntegrityError(f"no data for {symbol} {timeframe}")
    return to_canonical(pd.concat(frames))


def _load_dukascopy(symbol, spec, timeframe, start, end, cache) -> pd.DataFrame:
    if timeframe not in _DUKA_RESAMPLE:
        raise IntegrityError(
            f"{symbol}: dukascopy loader serves {list(_DUKA_RESAMPLE)} (native 1h), "
            f"not {timeframe!r}"
        )
    now = pd.Timestamp.now(tz="UTC")
    current_month = month_key(now)
    frames: list[pd.DataFrame] = []
    for month in months_between(start, end - pd.Timedelta(microseconds=1)):
        if month > current_month:
            continue
        # Current month is cached as partial so it refreshes on the next run.
        if month < current_month and cache.has("dukascopy", symbol, "1h", month):
            frames.append(cache.get("dukascopy", symbol, "1h", month))
            continue
        df = dukascopy.fetch_month(spec["dukascopy"], month)
        if df is None:
            continue
        cache.put("dukascopy", symbol, "1h", month, df, partial=(month == current_month))
        frames.append(df)
    if not frames:
        raise IntegrityError(f"no data for {symbol} 1h")
    out = to_canonical(pd.concat(frames))
    rule = _DUKA_RESAMPLE[timeframe]
    if rule is not None:
        out = to_canonical(dukascopy.resample_ohlcv(out, rule))
    return out
