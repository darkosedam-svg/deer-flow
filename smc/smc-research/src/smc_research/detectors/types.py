"""Shared detector types.

Design rules (M2, non-negotiable):
- Detectors are incremental state machines: `update(bar)` consumes exactly one
  bar and returns the signals confirmed ON that bar. No detector may look at a
  bar it has not been fed yet — prefix invariance is enforced by test.
- A signal's timestamp is the bar on which it became KNOWABLE (confirmation
  bar), never the bar where the pattern "started". This is what makes the
  backtest honest and the Pine port comparable.

This module mirrors the intended public API of `ict-smc-detector` (types.py);
sync there once that repo is in a session's scope.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class Bar:
    timestamp: pd.Timestamp
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class Signal:
    timestamp: pd.Timestamp  # confirmation bar
    kind: str                # e.g. "fvg_created", "bos", "choch", "liquidity_sweep"
    direction: str           # "bullish" | "bearish" | "none"
    price: float             # reference price for the signal
    meta: dict[str, Any] = field(default_factory=dict)

    def key(self) -> tuple:
        return (self.timestamp.isoformat(), self.kind, self.direction, round(self.price, 8))


class Detector:
    """Base class. Subclasses implement `update`."""

    def update(self, bar: Bar) -> list[Signal]:  # pragma: no cover - interface
        raise NotImplementedError


def iter_bars(df: pd.DataFrame):
    for ts, row in zip(df.index, df.itertuples(index=False), strict=True):
        yield Bar(
            timestamp=ts,
            open=float(row.open),
            high=float(row.high),
            low=float(row.low),
            close=float(row.close),
            volume=float(row.volume),
        )


def run(detector: Detector, df: pd.DataFrame) -> list[Signal]:
    """Feed a canonical frame through a detector, collecting all signals."""
    out: list[Signal] = []
    for bar in iter_bars(df):
        out.extend(detector.update(bar))
    return out
