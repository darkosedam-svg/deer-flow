import lzma

import pandas as pd
import pytest

from smc_research.data import dukascopy
from smc_research.data.dukascopy import _RECORD, fetch_month, resample_ohlcv


def make_bi5(records) -> bytes:
    raw = b"".join(_RECORD.pack(*r) for r in records)
    return lzma.compress(raw)


class FakeResponse:
    def __init__(self, content, status_code=200):
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        pass


class FakeClient:
    def __init__(self, content):
        self._content = content

    def get(self, url):
        return FakeResponse(self._content)

    def close(self):
        pass


def test_fetch_month_parses_and_scales(monkeypatch):
    # Two trading hours + one weekend filler record (flat, zero volume).
    records = [
        (0, 110000, 110500, 109800, 110700, 100.0),      # 2024-01-01 00:00
        (3600, 110500, 110300, 110100, 110600, 80.0),    # 2024-01-01 01:00
        (7200, 110300, 110300, 110300, 110300, 0.0),     # filler → dropped
    ]
    dukascopy._scale_cache.clear()
    df = fetch_month("EURUSD", "2024-01", client=FakeClient(make_bi5(records)))
    assert len(df) == 2
    assert df.index[0] == pd.Timestamp("2024-01-01 00:00", tz="UTC")
    assert abs(df.iloc[0]["open"] - 1.10) < 1e-9      # scale 1e5 detected
    assert abs(df.iloc[0]["high"] - 1.107) < 1e-9     # (o, c, l, h) record order
    assert abs(df.iloc[0]["low"] - 1.098) < 1e-9
    assert abs(df.iloc[0]["close"] - 1.105) < 1e-9


def test_scale_detection_index_cfd(monkeypatch):
    # S&P at ~4742.0 stored ×1e3.
    records = [(0, 4742000, 4750000, 4740000, 4755000, 10.0)]
    dukascopy._scale_cache.clear()
    df = fetch_month("USA500IDXUSD", "2024-01", client=FakeClient(make_bi5(records)))
    assert abs(df.iloc[0]["open"] - 4742.0) < 1e-9


def test_scale_detection_rejects_impossible():
    dukascopy._scale_cache.clear()
    with pytest.raises(ValueError, match="no scale"):
        dukascopy._detect_scale("EURUSD", 3)  # 3/any scale falls outside (0.8, 1.6)


def test_resample_4h(fixture_df):
    hourly = fixture_df.resample("1h").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    ).dropna()
    four = resample_ohlcv(hourly, "4h")
    assert (four.index.hour % 4 == 0).all()
    first = hourly.iloc[:4]
    assert four.iloc[0]["open"] == first.iloc[0]["open"]
    assert four.iloc[0]["high"] == first["high"].max()
    assert four.iloc[0]["low"] == first["low"].min()
    assert four.iloc[0]["close"] == first.iloc[-1]["close"]


@pytest.mark.live
def test_eurusd_live_month():
    dukascopy._scale_cache.clear()
    df = fetch_month("EURUSD", "2024-01")
    assert df is not None and len(df) > 400          # ~22 trading days × 24h
    assert 0.9 < df["close"].iloc[0] < 1.3
    assert df.isna().sum().sum() == 0


@pytest.mark.live
def test_spx500_live_month():
    dukascopy._scale_cache.clear()
    df = fetch_month("USA500IDXUSD", "2024-01")
    assert df is not None and len(df) > 300
    assert 3000 < df["close"].iloc[0] < 8000


@pytest.mark.live
def test_load_eurusd_4h_end_to_end(tmp_path):
    from smc_research import load

    df = load("EURUSD", "4h", "2024-01-01", "2024-03-01", cache_dir=tmp_path)
    assert len(df) > 200
    assert df.isna().sum().sum() == 0
    assert 0.9 < df["close"].median() < 1.3
