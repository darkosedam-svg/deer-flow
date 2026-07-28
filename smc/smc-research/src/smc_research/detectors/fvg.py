"""Fair Value Gap detection with mitigation tracking.

Definition (3-candle imbalance):
- Bullish FVG at bar i: low[i] > high[i-2]  → gap zone (high[i-2], low[i]).
- Bearish FVG at bar i: high[i] < low[i-2]  → gap zone (high[i], low[i-2]).
Created on bar i (the bar that completes the pattern). Mitigated when a later
bar trades into the zone beyond `mitigation_fraction` of its height; fully
filled when price crosses the far edge.
"""

from __future__ import annotations

from dataclasses import dataclass

from smc_research.detectors.types import Bar, Detector, Signal


@dataclass
class _Gap:
    direction: str
    top: float
    bottom: float
    created_at: object


class FVGDetector(Detector):
    def __init__(self, min_gap_fraction: float = 0.0, mitigation_fraction: float = 0.5):
        # min_gap_fraction: minimum gap height as fraction of the middle bar's range.
        self.min_gap_fraction = min_gap_fraction
        self.mitigation_fraction = mitigation_fraction
        self._window: list[Bar] = []
        self._active: list[_Gap] = []

    def update(self, bar: Bar) -> list[Signal]:
        signals: list[Signal] = []

        # 1) Mitigation of existing gaps by this bar.
        still_active: list[_Gap] = []
        for gap in self._active:
            height = gap.top - gap.bottom
            threshold = (
                gap.top - self.mitigation_fraction * height
                if gap.direction == "bullish"
                else gap.bottom + self.mitigation_fraction * height
            )
            hit = bar.low <= threshold if gap.direction == "bullish" else bar.high >= threshold
            if hit:
                signals.append(
                    Signal(
                        timestamp=bar.timestamp,
                        kind="fvg_mitigated",
                        direction=gap.direction,
                        price=threshold,
                        meta={
                            "top": gap.top,
                            "bottom": gap.bottom,
                            "created_at": gap.created_at.isoformat(),
                        },
                    )
                )
            else:
                still_active.append(gap)
        self._active = still_active

        # 2) New gap completed by this bar.
        self._window.append(bar)
        if len(self._window) > 3:
            self._window.pop(0)
        if len(self._window) == 3:
            a, b, c = self._window
            mid_range = b.high - b.low
            min_height = self.min_gap_fraction * mid_range
            if c.low > a.high and (c.low - a.high) > min_height:
                gap = _Gap("bullish", top=c.low, bottom=a.high, created_at=c.timestamp)
                self._active.append(gap)
                signals.append(
                    Signal(
                        timestamp=c.timestamp,
                        kind="fvg_created",
                        direction="bullish",
                        price=(gap.top + gap.bottom) / 2,
                        meta={"top": gap.top, "bottom": gap.bottom},
                    )
                )
            elif c.high < a.low and (a.low - c.high) > min_height:
                gap = _Gap("bearish", top=a.low, bottom=c.high, created_at=c.timestamp)
                self._active.append(gap)
                signals.append(
                    Signal(
                        timestamp=c.timestamp,
                        kind="fvg_created",
                        direction="bearish",
                        price=(gap.top + gap.bottom) / 2,
                        meta={"top": gap.top, "bottom": gap.bottom},
                    )
                )
        return signals
