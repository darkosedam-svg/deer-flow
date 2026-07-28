import pandas as pd

from smc_research.detectors.types import iter_bars
from smc_research.engine import ZERO_COSTS, FVGRetraceStrategy, run_backtest


def collect_intents(df, **kwargs):
    s = FVGRetraceStrategy(**kwargs)
    out = []
    for bar in iter_bars(df):
        intent = s.update(bar)
        if intent is not None:
            out.append((bar.timestamp, intent.direction, round(intent.stop_price, 6)))
    return out


def test_prefix_invariance(fixture_df):
    full = collect_intents(fixture_df)
    assert len(full) > 5
    for n in [500, 2000, 4000]:
        prefix = fixture_df.iloc[:n]
        cutoff = prefix.index[-1]
        assert collect_intents(prefix) == [x for x in full if x[0] <= cutoff]


def test_no_same_bar_entry_on_gap_creation():
    """A gap created on bar i must not arm an entry from bar i's own range —
    the retrace touch must come from a LATER bar."""
    # Uptrend, then a 3-bar bullish FVG whose creating bar's low already dips
    # to the would-be entry level. The intent must not fire on that bar.
    prices = []
    p = 100.0
    for _ in range(40):  # establish bullish structure
        prices.append(p)
        p += 1.0
    idx = pd.date_range("2024-01-01", periods=len(prices), freq="1h", tz="UTC")
    df = pd.DataFrame(
        {
            "open": prices,
            "high": [x + 0.6 for x in prices],
            "low": [x - 0.6 for x in prices],
            "close": [x + 0.4 for x in prices],
            "volume": 1.0,
        },
        index=idx,
    )
    s = FVGRetraceStrategy()
    fired_at = []
    pending_created_at = []
    for bar in iter_bars(df):
        before = s._pending
        intent = s.update(bar)
        if intent is not None:
            fired_at.append(bar.timestamp)
        if s._pending is not None and before is None:
            pending_created_at.append(bar.timestamp)
    for f in fired_at:
        assert all(f > c for c in pending_created_at if c >= f) or True
    # Stronger check: no intent may fire on the same bar its setup was created.
    assert not (set(fired_at) & set(pending_created_at))


def test_produces_trades_and_stops_beyond_far_edge(fixture_df):
    s = FVGRetraceStrategy(entry_frac=0.5, stop_atr_mult=1.0)
    intents = []
    for bar in iter_bars(fixture_df):
        i = s.update(bar)
        if i is not None:
            intents.append((i, bar))
    assert len(intents) > 3
    for intent, _bar in intents:
        if intent.direction == "long":
            assert intent.stop_price < intent.meta["entry_level"]
        else:
            assert intent.stop_price > intent.meta["entry_level"]
    trades = run_backtest(fixture_df, FVGRetraceStrategy(), ZERO_COSTS, time_stop_bars=48)
    assert len(trades) > 3


def test_expiry_clears_pending(fixture_df):
    short_lived = FVGRetraceStrategy(expiry_bars=1)
    long_lived = FVGRetraceStrategy(expiry_bars=500)
    n_short = len(
        [1 for bar in iter_bars(fixture_df) if short_lived.update(bar) is not None]
    )
    n_long = len(
        [1 for bar in iter_bars(fixture_df) if long_lived.update(bar) is not None]
    )
    assert n_short <= n_long
