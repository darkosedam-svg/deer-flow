"""EURUSD and index-CFD history from Dukascopy's public datafeed.

Monthly hour-candle files: no API key, LZMA ("bi5") compressed, 24-byte
big-endian records (seconds offset from month start, open, close, low,
high, volume:float32) with prices scaled by an instrument point value.
URL months are 0-indexed. Flat zero-volume records are market-closed
filler and are dropped, which is why FX/index frames use the
session-market gap threshold.

Point scale is auto-detected against a plausible price band per instrument
and cached — Dukascopy uses 1e5 for FX pairs but 1e3 for index CFDs.
"""

from __future__ import annotations

import lzma
import struct
import time

import httpx
import pandas as pd

from smc_research.data.canonical import to_canonical

FEED_URL = "https://datafeed.dukascopy.com/datafeed/{instrument}/{year}/{month0:02d}/BID_candles_hour_1.bi5"
_RECORD = struct.Struct(">IIIIIf")

# instrument -> (plausible min, plausible max) for scale detection
PRICE_BANDS: dict[str, tuple[float, float]] = {
    "EURUSD": (0.8, 1.6),
    "USA500IDXUSD": (1500.0, 20000.0),
}
_SCALES = (1e5, 1e3, 1e2, 10.0, 1.0)
_scale_cache: dict[str, float] = {}


def _detect_scale(instrument: str, sample_price: int) -> float:
    if instrument in _scale_cache:
        return _scale_cache[instrument]
    lo, hi = PRICE_BANDS.get(instrument, (1e-9, 1e12))
    for scale in _SCALES:
        if lo <= sample_price / scale <= hi:
            _scale_cache[instrument] = scale
            return scale
    raise ValueError(
        f"{instrument}: no scale in {_SCALES} puts sample {sample_price} inside band ({lo}, {hi})"
    )


def fetch_month(
    instrument: str, month: str, client: httpx.Client | None = None
) -> pd.DataFrame | None:
    """One month of 1h candles ('YYYY-MM'). None on 404/empty (not yet published)."""
    year, mm = month.split("-")
    url = FEED_URL.format(instrument=instrument, year=year, month0=int(mm) - 1)
    own_client = client is None
    client = client or httpx.Client(timeout=60.0, follow_redirects=True)
    try:
        # Dukascopy rate-limits sustained pulls (429): pace politely and back
        # off hard on throttle responses. Bulk history lands in the Parquet
        # cache, so this cost is paid once per month-file ever.
        time.sleep(0.4)
        for attempt in range(6):
            try:
                resp = client.get(url)
                if resp.status_code == 404:
                    return None
                if resp.status_code == 429:
                    time.sleep(5 * (attempt + 1))
                    continue
                resp.raise_for_status()
                break
            except httpx.TransportError:
                if attempt == 5:
                    raise
                time.sleep(2**attempt)
        else:
            raise RuntimeError(f"rate-limited on {url} after 6 attempts")
        if not resp.content:
            return None
        raw = lzma.decompress(resp.content, format=lzma.FORMAT_AUTO)
    finally:
        if own_client:
            client.close()

    n = len(raw) // _RECORD.size
    if n == 0:
        return None
    month_start = pd.Timestamp(f"{year}-{mm}-01", tz="UTC")
    rows = []
    scale = None
    for i in range(n):
        sec, o, c, lo, hi, vol = _RECORD.unpack_from(raw, i * _RECORD.size)
        if vol == 0.0 and o == c == lo == hi:
            continue  # market-closed filler
        if scale is None:
            scale = _detect_scale(instrument, o)
        rows.append(
            (
                month_start + pd.Timedelta(seconds=sec),
                o / scale, hi / scale, lo / scale, c / scale, float(vol),
            )
        )
    if not rows:
        return None
    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df = df.set_index("timestamp")
    return to_canonical(df)


def resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """1h → 4h etc. Bars with no trading hours inside are dropped."""
    out = df.resample(rule).agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    return out.dropna(subset=["open"])
