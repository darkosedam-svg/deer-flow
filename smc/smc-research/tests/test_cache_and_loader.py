import pandas as pd
import pytest

from smc_research.data import binance_vision, hyperliquid
from smc_research.data.cache import ParquetCache, months_between
from smc_research.data.loader import load


def test_months_between():
    assert months_between(
        pd.Timestamp("2024-11-15", tz="UTC"), pd.Timestamp("2025-02-01", tz="UTC")
    ) == ["2024-11", "2024-12", "2025-01", "2025-02"]


def test_parquet_cache_roundtrip(tmp_path, fixture_df):
    cache = ParquetCache(tmp_path)
    month = "2024-01"
    assert not cache.has("src", "BTCUSD", "15m", month)
    cache.put("src", "BTCUSD", "15m", month, fixture_df.iloc[:100])
    assert cache.has("src", "BTCUSD", "15m", month)
    back = cache.get("src", "BTCUSD", "15m", month)
    pd.testing.assert_frame_equal(back, fixture_df.iloc[:100])


def test_parquet_cache_partial_marker(tmp_path, fixture_df):
    cache = ParquetCache(tmp_path)
    cache.put("src", "BTCUSD", "15m", "2024-02", fixture_df.iloc[:10], partial=True)
    assert not cache.has("src", "BTCUSD", "15m", "2024-02")  # partial → re-fetch
    cache.put("src", "BTCUSD", "15m", "2024-02", fixture_df.iloc[:20], partial=False)
    assert cache.has("src", "BTCUSD", "15m", "2024-02")


def test_load_uses_cache_and_never_refetches(tmp_path, fixture_df, monkeypatch):
    """M0 rule: months already cached must not trigger a download."""
    calls = []

    def fake_fetch_month(symbol, timeframe, month, client=None):
        calls.append(month)
        month_start = pd.Timestamp(month + "-01", tz="UTC")
        month_end = month_start + pd.offsets.MonthBegin(1)
        chunk = fixture_df[(fixture_df.index >= month_start) & (fixture_df.index < month_end)]
        return chunk if len(chunk) else None

    monkeypatch.setattr(binance_vision, "fetch_month", fake_fetch_month)
    monkeypatch.setattr(
        hyperliquid, "fetch_candles", lambda *a, **k: hyperliquid._empty_frame()
    )

    df1 = load("BTCUSD", "15m", "2024-01-01", "2024-03-01", cache_dir=tmp_path)
    assert calls == ["2024-01", "2024-02"]
    assert len(df1) > 0
    assert df1.index[0] == pd.Timestamp("2024-01-01", tz="UTC")

    calls.clear()
    df2 = load("BTCUSD", "15m", "2024-01-01", "2024-03-01", cache_dir=tmp_path)
    assert calls == []  # fully served from cache
    pd.testing.assert_frame_equal(df1, df2)


def test_load_unknown_symbol(tmp_path):
    with pytest.raises(KeyError):
        load("DOGEUSD", "15m", "2024-01-01", "2024-02-01", cache_dir=tmp_path)


@pytest.mark.live
def test_load_btc_live_smoke(tmp_path):
    """M0 exit criterion against the real archive (one month, small)."""
    df = load("BTCUSD", "15m", "2024-01-01", "2024-02-01", cache_dir=tmp_path)
    assert len(df) == 31 * 96  # complete 24/7 month of 15m bars
    assert df.index.is_monotonic_increasing and not df.index.has_duplicates
    # Values must be real prices, not NaN (regression: index-alignment bug
    # once produced an all-NaN frame that passed the shape checks).
    assert df.isna().sum().sum() == 0
    assert 10_000 < df["close"].iloc[0] < 1_000_000


@pytest.mark.live
def test_hyperliquid_recent_tail_live():
    end = pd.Timestamp.now(tz="UTC").floor("15min")
    start = end - pd.Timedelta(hours=6)
    df = hyperliquid.fetch_candles("BTC", "15m", start, end)
    assert len(df) >= 20
    assert df.index.is_monotonic_increasing
