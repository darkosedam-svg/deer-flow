"""M2 gate tests.

The prefix-invariance test is the one that catches lookahead bias: a detector
fed bars 0..n must emit exactly the signals that the full run emitted on bars
0..n. If any future bar can change a past signal, the backtest is fiction.
"""

import json

import pandas as pd
import pytest

from smc_research.detectors import ALL_DETECTORS, run
from tests.conftest import GOLDEN_DIR


def signals_to_jsonable(signals):
    return [
        {
            "timestamp": s.timestamp.isoformat(),
            "kind": s.kind,
            "direction": s.direction,
            "price": round(s.price, 8),
            "meta": s.meta,
        }
        for s in signals
    ]


@pytest.mark.parametrize("name", sorted(ALL_DETECTORS))
def test_prefix_invariance(name, fixture_df):
    detector_cls = ALL_DETECTORS[name]
    full = run(detector_cls(), fixture_df)
    for n in [50, 250, 1000, 2500, 4999]:
        prefix_df = fixture_df.iloc[:n]
        cutoff = prefix_df.index[-1]
        prefix_signals = run(detector_cls(), prefix_df)
        expected = [s for s in full if s.timestamp <= cutoff]
        assert [s.key() for s in prefix_signals] == [s.key() for s in expected], (
            f"{name}: prefix at n={n} diverges from full run — lookahead bias"
        )


@pytest.mark.parametrize("name", sorted(ALL_DETECTORS))
def test_detectors_fire_on_fixture(name, fixture_df):
    signals = run(ALL_DETECTORS[name](), fixture_df)
    assert len(signals) > 0, f"{name} emitted nothing on 5000 varied bars — dead detector?"


@pytest.mark.parametrize("name", sorted(ALL_DETECTORS))
def test_golden(name, fixture_df):
    """Byte-exact signal set on the committed fixture. Regenerate deliberately
    with tests/generate_golden.py when detector logic changes — and treat a
    diff here as a semver event for the parity harness."""
    golden_path = GOLDEN_DIR / f"{name}.json"
    if not golden_path.exists():
        pytest.skip("golden file missing; run tests/generate_golden.py")
    actual = signals_to_jsonable(run(ALL_DETECTORS[name](), fixture_df))
    expected = json.loads(golden_path.read_text())
    assert actual == expected


def test_structure_choch_flips_trend():
    """Hand-built sequence: uptrend break then downtrend break → bos then choch."""
    idx = pd.date_range("2024-01-01", periods=40, freq="15min", tz="UTC")
    prices = (
        [100, 101, 102, 103, 104, 103, 102, 101, 102, 103]  # swing high at 104
        + [105, 106, 107, 108, 109, 108, 107, 106, 105, 104]  # break above 104 → bos bull
        + [103, 102, 101, 100, 99, 100, 101, 102, 101, 100]  # falls
        + [99, 98, 97, 96, 95, 94, 93, 92, 91, 90]  # break below swing low → choch bear
    )
    df = pd.DataFrame(
        {
            "open": prices,
            "high": [p + 0.5 for p in prices],
            "low": [p - 0.5 for p in prices],
            "close": prices,
            "volume": [1.0] * 40,
        },
        index=idx,
    )
    signals = run(ALL_DETECTORS["structure"](), df)
    kinds = [(s.kind, s.direction) for s in signals if s.kind in ("bos", "choch")]
    assert ("bos", "bullish") in kinds
    assert ("choch", "bearish") in kinds
    first_bear = next(k for k in kinds if k[1] == "bearish")
    assert first_bear[0] == "choch", "first break against trend must be CHoCH, not BOS"
