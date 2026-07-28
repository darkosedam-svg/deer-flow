from smc_research.detectors.types import iter_bars
from smc_research.engine import ZERO_COSTS, TrendAlignedSweepStrategy, run_backtest


def collect_intents(df, **kwargs):
    s = TrendAlignedSweepStrategy(**kwargs)
    out = []
    for bar in iter_bars(df):
        intent = s.update(bar)
        if intent is not None:
            out.append((bar.timestamp, intent.direction, round(intent.stop_price, 6)))
    return out


def test_prefix_invariance(fixture_df):
    full = collect_intents(fixture_df)
    for n in [500, 2000, 4000]:
        prefix = fixture_df.iloc[:n]
        cutoff = prefix.index[-1]
        assert collect_intents(prefix) == [x for x in full if x[0] <= cutoff]


def test_aligned_and_counter_partition_the_sweeps(fixture_df):
    """Every gated sweep is taken by exactly one of aligned/counter mode
    (once the trend state is established)."""
    aligned = set(collect_intents(fixture_df, mode="aligned"))
    counter = set(collect_intents(fixture_df, mode="counter"))
    assert aligned and counter
    assert not (aligned & counter)


def test_produces_trades_on_fixture(fixture_df):
    trades = run_backtest(
        fixture_df, TrendAlignedSweepStrategy(), ZERO_COSTS, time_stop_bars=48
    )
    assert len(trades) > 5
    directions = {t.direction for t in trades}
    assert directions <= {"long", "short"}
