import pandas as pd

from smc_research.engine import ZERO_COSTS, SweepConfirmationStrategy, make_splits, walk_forward
from smc_research.engine.backtester import Trade
from smc_research.stats import expectancy_ci, hit_rate_ci, summarize


def mk_trade(i: int, r: float) -> Trade:
    t0 = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=i)
    return Trade(
        entry_time=t0,
        exit_time=t0 + pd.Timedelta(minutes=30),
        direction="long",
        entry_price=100.0,
        exit_price=100.0 + r,
        stop_price=99.0,
        target_price=102.0,
        exit_reason="target" if r > 0 else "stop",
        risk=1.0,
        realized_r=r,
        reason="test",
    )


def test_summarize_known_values():
    trades = [mk_trade(i, r) for i, r in enumerate([2.0, -1.0, 2.0, -1.0, -1.0])]
    s = summarize(trades)
    assert s.n_trades == 5
    assert abs(s.hit_rate - 0.4) < 1e-9
    assert abs(s.expectancy_r - 0.2) < 1e-9
    assert abs(s.avg_win_r - 2.0) < 1e-9
    assert abs(s.avg_loss_r - (-1.0)) < 1e-9
    assert abs(s.profit_factor - 4.0 / 3.0) < 1e-9
    # equity: 2,1,3,2,1 → max drawdown 2 (from 3 down to 1)
    assert abs(s.max_drawdown_r - 2.0) < 1e-9


def test_summarize_empty():
    s = summarize([])
    assert s.n_trades == 0 and s.expectancy_r == 0.0


def test_bootstrap_ci_brackets_point_and_is_reproducible():
    trades = [mk_trade(i, r) for i, r in enumerate([2.0, -1.0] * 25)]
    hit1, hit2 = hit_rate_ci(trades), hit_rate_ci(trades)
    assert (hit1.lo, hit1.hi) == (hit2.lo, hit2.hi)  # seeded
    assert hit1.lo <= hit1.point <= hit1.hi
    assert hit1.point == 0.5
    exp = expectancy_ci(trades)
    assert exp.lo <= exp.point <= exp.hi
    assert abs(exp.point - 0.5) < 1e-9
    assert exp.n == 50


def test_make_splits_roll_correctly():
    splits = make_splits(
        pd.Timestamp("2024-01-01", tz="UTC"),
        pd.Timestamp("2025-01-01", tz="UTC"),
        train_months=6,
        test_months=3,
    )
    assert len(splits) == 2
    assert splits[0].train_end == pd.Timestamp("2024-07-01", tz="UTC")
    assert splits[0].test_end == pd.Timestamp("2024-10-01", tz="UTC")
    assert splits[1].train_start == pd.Timestamp("2024-04-01", tz="UTC")
    # test windows tile without overlap
    assert splits[1].train_end == splits[0].test_end


def test_walk_forward_only_reports_oos():
    from tests.conftest import make_fixture

    df = make_fixture(n=8000)  # ~83 days of 15m bars: room for 1m train + 1m test
    result = walk_forward(
        df,
        SweepConfirmationStrategy,
        param_grid=[{"swing_strength": 3}, {"swing_strength": 5}],
        costs=ZERO_COSTS,
        train_months=1,
        test_months=1,
        min_train_trades=1,
        time_stop_bars=48,
    )
    assert len(result.splits) >= 1
    assert len(result.chosen_params) == len(result.splits)
    # every OOS trade's entry falls inside some test window, never a train-only span
    for t in result.oos_trades:
        assert any(s.train_end <= t.entry_time < s.test_end for s in result.splits)
