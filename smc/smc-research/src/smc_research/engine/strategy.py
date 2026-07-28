"""Strategy layer: turns detector signals into entry intents.

A Strategy sees each bar's confirmed signals and may emit an EntryIntent.
The BACKTESTER (not the strategy) fills it at the NEXT bar's open — entering
on the signal bar's close is the classic lookahead cheat (Plan B M3).

Reference strategy = the Pro tier's headline setup: liquidity-sweep
confirmation. Enter after a sweep signal, stop beyond the sweep extreme,
fixed-R target, time-stop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from smc_research.detectors import LiquiditySweepDetector
from smc_research.detectors.types import Bar, Signal


@dataclass(frozen=True)
class EntryIntent:
    direction: str          # "long" | "short"
    stop_price: float       # structural invalidation
    reason: str
    meta: dict[str, Any] = field(default_factory=dict)


class Strategy:
    """Subclasses implement update(); must be incremental, no lookahead."""

    params: dict[str, Any] = {}

    def update(self, bar: Bar) -> EntryIntent | None:  # pragma: no cover - interface
        raise NotImplementedError


class SweepConfirmationStrategy(Strategy):
    """Long after a sell-side liquidity sweep, short after a buy-side sweep.

    Stop goes beyond the sweep bar's extreme (the level that, if traded
    through, invalidates the stop-hunt read). stop_buffer_frac widens it by a
    fraction of the sweep bar's range.
    """

    def __init__(self, swing_strength: int = 3, stop_buffer_frac: float = 0.1):
        self.params = {"swing_strength": swing_strength, "stop_buffer_frac": stop_buffer_frac}
        self._detector = LiquiditySweepDetector(swing_strength=swing_strength)
        self.stop_buffer_frac = stop_buffer_frac

    def update(self, bar: Bar) -> EntryIntent | None:
        signals: list[Signal] = self._detector.update(bar)
        for sig in signals:
            if sig.kind != "liquidity_sweep":
                continue
            bar_range = bar.high - bar.low
            buffer = self.stop_buffer_frac * bar_range
            if sig.direction == "bullish":
                return EntryIntent(
                    direction="long",
                    stop_price=bar.low - buffer,
                    reason="sweep_sellside",
                    meta={"level": sig.price},
                )
            if sig.direction == "bearish":
                return EntryIntent(
                    direction="short",
                    stop_price=bar.high + buffer,
                    reason="sweep_buyside",
                    meta={"level": sig.price},
                )
        return None
