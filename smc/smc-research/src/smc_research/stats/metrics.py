"""Trade-list statistics (Plan B M3).

Everything is computed in R (risk multiples), so instruments aggregate
cleanly. Sample size travels with every rate — the report is required to
print it next to the number.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from smc_research.engine.backtester import Trade


@dataclass(frozen=True)
class Summary:
    n_trades: int
    hit_rate: float          # fraction of trades with realized_r > 0
    avg_win_r: float
    avg_loss_r: float
    expectancy_r: float      # mean realized R per trade
    profit_factor: float     # gross wins / gross losses (inf if no losses)
    max_drawdown_r: float    # deepest peak-to-trough on the cumulative-R curve
    longest_flat: pd.Timedelta  # longest span between successive equity highs
    total_r: float


def equity_curve(trades: list[Trade]) -> pd.Series:
    """Cumulative realized R indexed by exit time."""
    if not trades:
        return pd.Series(dtype="float64")
    s = pd.Series(
        [t.realized_r for t in trades],
        index=pd.DatetimeIndex([t.exit_time for t in trades]),
    ).sort_index()
    return s.cumsum()


def summarize(trades: list[Trade]) -> Summary:
    if not trades:
        return Summary(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, pd.Timedelta(0), 0.0)
    r = np.array([t.realized_r for t in trades])
    wins, losses = r[r > 0], r[r <= 0]
    gross_win = float(wins.sum()) if len(wins) else 0.0
    gross_loss = float(-losses.sum()) if len(losses) else 0.0

    curve = equity_curve(trades)
    running_max = curve.cummax()
    max_dd = float((running_max - curve).max())

    at_high = curve >= running_max - 1e-12
    high_times = curve.index[at_high]
    longest_flat = pd.Timedelta(0)
    if len(high_times) > 0:
        gaps = pd.Series(high_times).diff().dropna()
        if len(gaps):
            longest_flat = gaps.max()
        # tail: still underwater at the end counts too
        tail = curve.index[-1] - high_times[-1]
        longest_flat = max(longest_flat, tail)

    return Summary(
        n_trades=len(r),
        hit_rate=float(len(wins) / len(r)),
        avg_win_r=float(wins.mean()) if len(wins) else 0.0,
        avg_loss_r=float(losses.mean()) if len(losses) else 0.0,
        expectancy_r=float(r.mean()),
        profit_factor=float(gross_win / gross_loss) if gross_loss > 0 else float("inf"),
        max_drawdown_r=max_dd,
        longest_flat=longest_flat,
        total_r=float(r.sum()),
    )
