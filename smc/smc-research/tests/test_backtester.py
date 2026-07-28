import pandas as pd

from smc_research.detectors.types import Bar
from smc_research.engine import (
    ZERO_COSTS,
    CostModel,
    EntryIntent,
    Strategy,
    run_backtest,
)


def make_df(bars: list[tuple[float, float, float, float]]) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=len(bars), freq="15min", tz="UTC")
    o, h, lo, c = zip(*bars, strict=True)
    return pd.DataFrame(
        {"open": o, "high": h, "low": lo, "close": c, "volume": [1.0] * len(bars)},
        index=idx,
    )


class OneShot(Strategy):
    """Emits a single long intent on a chosen bar index."""

    def __init__(self, on_bar: int, stop: float, direction: str = "long"):
        self.on_bar = on_bar
        self.stop = stop
        self.direction = direction
        self._i = -1

    def update(self, bar: Bar):
        self._i += 1
        if self._i == self.on_bar:
            return EntryIntent(direction=self.direction, stop_price=self.stop, reason="test")
        return None


def test_entry_fills_at_next_bar_open_not_signal_close():
    df = make_df([
        (100, 101, 99, 100),   # bar 0: signal fires here (close 100)
        (105, 106, 104, 105),  # bar 1: entry must be at THIS open (105)
        (105, 111, 104.5, 110),
        (110, 116, 109, 115),  # target 2R = 105 + 2*(105-95)=125 not yet
        (115, 126, 114, 125),  # target hit
    ])
    trades = run_backtest(df, OneShot(on_bar=0, stop=95.0), ZERO_COSTS, target_r=2.0)
    assert len(trades) == 1
    t = trades[0]
    assert t.entry_price == 105.0          # next-bar open, not 100
    assert t.entry_time == df.index[1]
    assert t.exit_reason == "target"
    assert t.target_price == 125.0
    assert abs(t.realized_r - 2.0) < 1e-9


def test_stop_wins_ambiguous_bar():
    """A bar that touches both stop and target must fill the stop."""
    df = make_df([
        (100, 101, 99, 100),
        (100, 100.5, 99.5, 100),        # entry at 100, stop 95, target 110
        (100, 115, 90, 100),            # touches both → stop
    ])
    trades = run_backtest(df, OneShot(on_bar=0, stop=95.0), ZERO_COSTS, target_r=2.0)
    assert len(trades) == 1
    assert trades[0].exit_reason == "stop"
    assert abs(trades[0].realized_r - (-1.0)) < 1e-9


def test_time_stop_exits_at_close():
    flat = [(100, 100.6, 99.4, 100)] * 12
    df = make_df([(100, 101, 99, 100)] + flat)
    trades = run_backtest(df, OneShot(on_bar=0, stop=95.0), ZERO_COSTS, time_stop_bars=5)
    assert len(trades) == 1
    assert trades[0].exit_reason == "time"


def test_gap_through_stop_skips_entry():
    df = make_df([
        (100, 101, 99, 100),
        (90, 91, 89, 90),   # opens below the 95 stop → setup invalid, no trade
        (90, 91, 89, 90),
    ])
    trades = run_backtest(df, OneShot(on_bar=0, stop=95.0), ZERO_COSTS)
    assert trades == []


def test_costs_reduce_realized_r():
    df = make_df([
        (100, 101, 99, 100),
        (100, 100.5, 99.5, 100),
        (100, 111, 99.9, 110),  # clean 2R target hit (stop 95 → target 110)
    ])
    costly = CostModel(spread_bps=10, slippage_bps=10, commission_bps=10)
    free = run_backtest(df, OneShot(on_bar=0, stop=95.0), ZERO_COSTS)
    paid = run_backtest(df, OneShot(on_bar=0, stop=95.0), costly)
    assert free[0].realized_r > paid[0].realized_r
    assert abs(free[0].realized_r - 2.0) < 1e-9


def test_short_side_symmetry():
    df = make_df([
        (100, 101, 99, 100),
        (100, 100.5, 99.5, 100),  # short entry 100, stop 105, target 90
        (100, 100.4, 89, 90),     # target
    ])
    trades = run_backtest(
        df, OneShot(on_bar=0, stop=105.0, direction="short"), ZERO_COSTS, target_r=2.0
    )
    assert len(trades) == 1
    assert trades[0].exit_reason == "target"
    assert abs(trades[0].realized_r - 2.0) < 1e-9


def test_single_position_at_a_time():
    class Always(Strategy):
        def update(self, bar):
            return EntryIntent(direction="long", stop_price=bar.low - 5, reason="always")

    df = make_df([(100, 101, 99, 100)] * 30)
    trades = run_backtest(df, Always(), ZERO_COSTS, time_stop_bars=5)
    # With a 5-bar time stop over 30 bars, overlapping entries are impossible.
    for a, b in zip(trades, trades[1:], strict=False):
        assert a.exit_time <= b.entry_time
