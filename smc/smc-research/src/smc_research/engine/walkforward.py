"""Walk-forward optimization (Plan B M3).

Rolling windows: optimize on `train` months, evaluate untouched on the next
`test` months, step forward by `test`. ONLY the concatenated out-of-sample
trades are reported — in-sample numbers exist solely to pick parameters.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

import pandas as pd

from smc_research.engine.backtester import Trade, run_backtest
from smc_research.engine.costs import CostModel
from smc_research.engine.strategy import Strategy

# Grid keys consumed by run_backtest rather than the strategy constructor.
ENGINE_PARAM_KEYS = {"min_risk_bps"}


@dataclass(frozen=True)
class Split:
    train_start: pd.Timestamp
    train_end: pd.Timestamp   # == test_start
    test_end: pd.Timestamp


def make_splits(
    start: pd.Timestamp, end: pd.Timestamp, train_months: int = 6, test_months: int = 3
) -> list[Split]:
    splits = []
    cursor = start
    while True:
        train_end = cursor + pd.DateOffset(months=train_months)
        test_end = train_end + pd.DateOffset(months=test_months)
        if test_end > end:
            break
        splits.append(Split(cursor, train_end, test_end))
        cursor = cursor + pd.DateOffset(months=test_months)
    return splits


def iter_split_frames(
    df: pd.DataFrame, splits: list[Split]
) -> Iterator[tuple[Split, pd.DataFrame, pd.DataFrame]]:
    for s in splits:
        train = df[(df.index >= s.train_start) & (df.index < s.train_end)]
        test = df[(df.index >= s.train_end) & (df.index < s.test_end)]
        yield s, train, test


@dataclass
class WalkForwardResult:
    oos_trades: list[Trade]
    chosen_params: list[dict[str, Any]]   # one per split, for the report's audit trail
    splits: list[Split]


def _score(trades: list[Trade], min_trades: int) -> float:
    """Selection criterion on the train window: expectancy in R, but a window
    with too few trades scores -inf so noise can't win the grid."""
    if len(trades) < min_trades:
        return float("-inf")
    return sum(t.realized_r for t in trades) / len(trades)


def walk_forward(
    df: pd.DataFrame,
    strategy_factory: Callable[..., Strategy],
    param_grid: list[dict[str, Any]],
    costs: CostModel,
    train_months: int = 6,
    test_months: int = 3,
    min_train_trades: int = 20,
    target_r: float = 2.0,
    time_stop_bars: int = 96,
) -> WalkForwardResult:
    splits = make_splits(df.index[0], df.index[-1], train_months, test_months)
    oos: list[Trade] = []
    chosen: list[dict[str, Any]] = []

    def _run(frame: pd.DataFrame, params: dict[str, Any]) -> list[Trade]:
        # Reserved keys route to the engine; everything else is a strategy param.
        engine_kwargs = {k: v for k, v in params.items() if k in ENGINE_PARAM_KEYS}
        strat_params = {k: v for k, v in params.items() if k not in ENGINE_PARAM_KEYS}
        return run_backtest(
            frame, strategy_factory(**strat_params), costs,
            target_r=target_r, time_stop_bars=time_stop_bars, **engine_kwargs,
        )

    for split, train, test in iter_split_frames(df, splits):
        best_params, best_score = None, float("-inf")
        for params in param_grid:
            score = _score(_run(train, params), min_train_trades)
            if score > best_score:
                best_params, best_score = params, score
        if best_params is None:
            best_params = param_grid[0]  # nothing qualified; fall back, still OOS-honest
        chosen.append(
            {**best_params, "_train_score": best_score, "_split": str(split.train_end.date())}
        )
        oos.extend(_run(test, best_params))
    return WalkForwardResult(oos_trades=oos, chosen_params=chosen, splits=splits)
