"""Market structure: swing points → BOS / CHoCH.

Swing high at bar i: high[i] is strictly greater than the highs of `k` bars on
each side. It is only KNOWABLE k bars later, so the detector confirms swings
with a k-bar delay and stamps structure events on the bar where the break
CLOSES, not where the swing formed. Mirrors what the Pine port must do.

- BOS  (break of structure): close beyond the last confirmed swing in the
  direction of the current trend.
- CHoCH (change of character): first close beyond the last confirmed swing
  AGAINST the current trend; flips the trend state.
"""

from __future__ import annotations

from collections import deque

from smc_research.detectors.types import Bar, Detector, Signal


class StructureDetector(Detector):
    def __init__(self, swing_strength: int = 3):
        self.k = swing_strength
        self._buffer: deque[Bar] = deque(maxlen=2 * swing_strength + 1)
        self._last_swing_high: float | None = None
        self._last_swing_low: float | None = None
        self._trend: str = "none"  # "bullish" | "bearish" | "none"
        # Once a level is broken it can't be re-broken until a new swing forms.
        self._high_broken = False
        self._low_broken = False

    def update(self, bar: Bar) -> list[Signal]:
        signals: list[Signal] = []
        self._buffer.append(bar)

        # 1) Confirm the candidate swing at the center of the buffer.
        if len(self._buffer) == self._buffer.maxlen:
            center = self._buffer[self.k]
            left = list(self._buffer)[: self.k]
            right = list(self._buffer)[self.k + 1 :]
            if all(center.high > b.high for b in left) and all(center.high > b.high for b in right):
                self._last_swing_high = center.high
                self._high_broken = False
                signals.append(
                    Signal(
                        timestamp=bar.timestamp,  # confirmation bar, k bars after the pivot
                        kind="swing_high",
                        direction="none",
                        price=center.high,
                        meta={"pivot_time": center.timestamp.isoformat()},
                    )
                )
            if all(center.low < b.low for b in left) and all(center.low < b.low for b in right):
                self._last_swing_low = center.low
                self._low_broken = False
                signals.append(
                    Signal(
                        timestamp=bar.timestamp,
                        kind="swing_low",
                        direction="none",
                        price=center.low,
                        meta={"pivot_time": center.timestamp.isoformat()},
                    )
                )

        # 2) Structure breaks on close.
        high_break = (
            self._last_swing_high is not None
            and not self._high_broken
            and bar.close > self._last_swing_high
        )
        if high_break:
            self._high_broken = True
            kind = "bos" if self._trend == "bullish" else "choch"
            if self._trend == "none":
                kind = "bos"
            self._trend = "bullish"
            signals.append(
                Signal(
                    timestamp=bar.timestamp,
                    kind=kind,
                    direction="bullish",
                    price=self._last_swing_high,
                    meta={},
                )
            )
        low_break = (
            self._last_swing_low is not None
            and not self._low_broken
            and bar.close < self._last_swing_low
        )
        if low_break:
            self._low_broken = True
            kind = "bos" if self._trend == "bearish" else "choch"
            if self._trend == "none":
                kind = "bos"
            self._trend = "bearish"
            signals.append(
                Signal(
                    timestamp=bar.timestamp,
                    kind=kind,
                    direction="bearish",
                    price=self._last_swing_low,
                    meta={},
                )
            )
        return signals
