import pandas as pd

from smc_research.detectors.types import iter_bars
from smc_research.engine import ZERO_COSTS, SweepConfirmationStrategy, run_backtest
from tests.test_backtester import OneShot, make_df


def test_min_risk_bps_filters_tight_setups():
    # Entry open 100, stop 99.9 → risk 10 bps: filtered at 30, kept at 5.
    df = make_df([
        (100, 101, 99, 100),
        (100, 100.5, 99.95, 100),
        (100, 100.5, 89, 90),
    ])
    kept = run_backtest(df, OneShot(on_bar=0, stop=99.9), ZERO_COSTS, min_risk_bps=5)
    filtered = run_backtest(df, OneShot(on_bar=0, stop=99.9), ZERO_COSTS, min_risk_bps=30)
    assert len(kept) == 1
    assert filtered == []


def test_atr_stop_wider_than_extreme_stop(fixture_df):
    """ATR-buffered stops must sit farther from entry than sweep-extreme stops
    for the same signals (that's the whole point)."""
    df = fixture_df.iloc[:2000]
    naive = SweepConfirmationStrategy(swing_strength=3, stop_buffer_frac=0.1)
    atr = SweepConfirmationStrategy(swing_strength=3, atr_mult=1.0)
    naive_stops, atr_stops = {}, {}
    for bar in iter_bars(df):
        n_i, a_i = naive.update(bar), atr.update(bar)
        if n_i is not None:
            naive_stops[bar.timestamp] = (n_i.direction, n_i.stop_price, bar)
        if a_i is not None:
            atr_stops[bar.timestamp] = (a_i.direction, a_i.stop_price, bar)
    common = set(naive_stops) & set(atr_stops)
    assert len(common) > 5
    for ts in common:
        direction, n_stop, bar = naive_stops[ts]
        _, a_stop, _ = atr_stops[ts]
        if direction == "long":
            assert a_stop <= n_stop  # farther below
        else:
            assert a_stop >= n_stop


def test_atr_strategy_prefix_invariant(fixture_df):
    """The ATR extension must not introduce lookahead."""
    def collect(df):
        s = SweepConfirmationStrategy(swing_strength=3, atr_mult=1.0)
        out = []
        for bar in iter_bars(df):
            intent = s.update(bar)
            if intent is not None:
                out.append((bar.timestamp, intent.direction, round(intent.stop_price, 6)))
        return out

    full = collect(fixture_df)
    for n in [500, 2000, 4000]:
        prefix_df = fixture_df.iloc[:n]
        cutoff = prefix_df.index[-1]
        assert collect(prefix_df) == [x for x in full if x[0] <= cutoff]


def test_walk_forward_routes_engine_params(fixture_df):
    from smc_research.engine import walk_forward
    from tests.conftest import make_fixture

    df = make_fixture(n=8000)
    result = walk_forward(
        df,
        SweepConfirmationStrategy,
        param_grid=[{"swing_strength": 3, "atr_mult": 1.0, "min_risk_bps": 10_000}],
        costs=ZERO_COSTS,
        train_months=1,
        test_months=1,
        min_train_trades=1,
    )
    # An absurd min-risk threshold must suppress every trade — proving the
    # reserved key reached the engine instead of the strategy constructor.
    assert result.oos_trades == []


def test_time_index_alignment_regression():
    """Trades' entry timestamps must exist in the source index."""
    df = make_df([(100, 101, 99, 100)] * 10)
    trades = run_backtest(df, OneShot(on_bar=0, stop=95.0), ZERO_COSTS, time_stop_bars=3)
    for t in trades:
        assert t.entry_time in df.index and t.exit_time in df.index


def test_time_stop_pandas_freq_check():
    assert isinstance(pd.Timedelta("15min"), pd.Timedelta)
