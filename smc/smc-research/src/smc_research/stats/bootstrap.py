"""Bootstrap confidence intervals (Plan B M3).

The CI is the differentiator versus vendors quoting "78% win rate" off 40
trades. Percentile bootstrap, resampling trades with replacement; seeded so
the published report is reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from smc_research.engine.backtester import Trade


@dataclass(frozen=True)
class CI:
    point: float
    lo: float
    hi: float
    level: float
    n: int


def _bootstrap(values: np.ndarray, stat, iters: int, level: float, seed: int) -> CI:
    rng = np.random.RandomState(seed)
    n = len(values)
    samples = np.empty(iters)
    for i in range(iters):
        samples[i] = stat(values[rng.randint(0, n, size=n)])
    alpha = (1 - level) / 2
    return CI(
        point=float(stat(values)),
        lo=float(np.quantile(samples, alpha)),
        hi=float(np.quantile(samples, 1 - alpha)),
        level=level,
        n=n,
    )


def hit_rate_ci(trades: list[Trade], iters: int = 2000, level: float = 0.95, seed: int = 7) -> CI:
    r = np.array([t.realized_r for t in trades])
    if len(r) == 0:
        return CI(0.0, 0.0, 0.0, level, 0)
    return _bootstrap(r, lambda x: float((x > 0).mean()), iters, level, seed)


def expectancy_ci(trades: list[Trade], iters: int = 2000, level: float = 0.95, seed: int = 7) -> CI:
    r = np.array([t.realized_r for t in trades])
    if len(r) == 0:
        return CI(0.0, 0.0, 0.0, level, 0)
    return _bootstrap(r, lambda x: float(x.mean()), iters, level, seed)
