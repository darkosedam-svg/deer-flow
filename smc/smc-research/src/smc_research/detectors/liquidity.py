"""Liquidity sweeps: a wick takes out a confirmed swing high/low but the bar
closes back on the original side — stop-hunt behaviour.

Uses the same swing-confirmation delay as StructureDetector (knowable k bars
after the pivot). Each swing level can be swept once.
"""

from __future__ import annotations

from collections import deque

from smc_research.detectors.types import Bar, Detector, Signal


class LiquiditySweepDetector(Detector):
    def __init__(self, swing_strength: int = 3, max_levels: int = 50):
        self.k = swing_strength
        self.max_levels = max_levels
        self._buffer: deque[Bar] = deque(maxlen=2 * swing_strength + 1)
        self._highs: list[float] = []
        self._lows: list[float] = []

    def update(self, bar: Bar) -> list[Signal]:
        signals: list[Signal] = []

        # 1) Sweep checks against confirmed levels (before adding new ones).
        for level in list(self._highs):
            if bar.high > level and bar.close < level:
                self._highs.remove(level)
                signals.append(
                    Signal(
                        timestamp=bar.timestamp,
                        kind="liquidity_sweep",
                        direction="bearish",  # buy-side liquidity taken, rejection down
                        price=level,
                        meta={"side": "buyside"},
                    )
                )
            elif bar.close > level:
                self._highs.remove(level)  # cleanly broken, no longer a pool
        for level in list(self._lows):
            if bar.low < level and bar.close > level:
                self._lows.remove(level)
                signals.append(
                    Signal(
                        timestamp=bar.timestamp,
                        kind="liquidity_sweep",
                        direction="bullish",
                        price=level,
                        meta={"side": "sellside"},
                    )
                )
            elif bar.close < level:
                self._lows.remove(level)

        # 2) Confirm new swing levels.
        self._buffer.append(bar)
        if len(self._buffer) == self._buffer.maxlen:
            center = self._buffer[self.k]
            left = list(self._buffer)[: self.k]
            right = list(self._buffer)[self.k + 1 :]
            if all(center.high > b.high for b in left) and all(center.high > b.high for b in right):
                self._highs.append(center.high)
                self._highs = self._highs[-self.max_levels :]
            if all(center.low < b.low for b in left) and all(center.low < b.low for b in right):
                self._lows.append(center.low)
                self._lows = self._lows[-self.max_levels :]
        return signals
