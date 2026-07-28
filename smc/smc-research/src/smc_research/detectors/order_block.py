"""Order blocks (basic, Lite-tier semantics): the last opposing candle before
a displacement move.

Displacement: a candle whose body exceeds `displacement_factor` × the rolling
mean absolute body over `body_lookback` bars. On a bullish displacement the
most recent down-close candle before it becomes a bullish OB zone (its full
range); mirrored for bearish. Mitigation when price trades back into the zone.

Quality scoring (Pro tier) deliberately lives elsewhere — this module's output
must match the free Pine script.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from smc_research.detectors.types import Bar, Detector, Signal


@dataclass
class _Block:
    direction: str
    top: float
    bottom: float
    created_at: object


class OrderBlockDetector(Detector):
    def __init__(
        self,
        displacement_factor: float = 2.0,
        body_lookback: int = 20,
        max_opposing_age: int = 10,
    ):
        self.displacement_factor = displacement_factor
        self.body_lookback = body_lookback
        self.max_opposing_age = max_opposing_age
        self._bodies: deque[float] = deque(maxlen=body_lookback)
        self._recent: deque[Bar] = deque(maxlen=max_opposing_age + 1)
        self._active: list[_Block] = []

    def update(self, bar: Bar) -> list[Signal]:
        signals: list[Signal] = []

        # 1) Mitigation of existing blocks.
        still_active: list[_Block] = []
        for blk in self._active:
            hit = (
                bar.low <= blk.top if blk.direction == "bullish" else bar.high >= blk.bottom
            )
            if hit:
                signals.append(
                    Signal(
                        timestamp=bar.timestamp,
                        kind="ob_mitigated",
                        direction=blk.direction,
                        price=blk.top if blk.direction == "bullish" else blk.bottom,
                        meta={
                            "top": blk.top,
                            "bottom": blk.bottom,
                            "created_at": blk.created_at.isoformat(),
                        },
                    )
                )
            else:
                still_active.append(blk)
        self._active = still_active

        # 2) Displacement check against the PRIOR baseline (this bar excluded).
        body = abs(bar.close - bar.open)
        window_full = len(self._bodies) == self.body_lookback
        baseline = sum(self._bodies) / len(self._bodies) if window_full else None
        if baseline is not None and baseline > 0 and body > self.displacement_factor * baseline:
            direction = "bullish" if bar.close > bar.open else "bearish"
            opposing = None
            for prev in reversed(self._recent):
                if direction == "bullish" and prev.close < prev.open:
                    opposing = prev
                    break
                if direction == "bearish" and prev.close > prev.open:
                    opposing = prev
                    break
            if opposing is not None:
                blk = _Block(
                    direction=direction,
                    top=opposing.high,
                    bottom=opposing.low,
                    created_at=bar.timestamp,
                )
                self._active.append(blk)
                signals.append(
                    Signal(
                        timestamp=bar.timestamp,
                        kind="ob_created",
                        direction=direction,
                        price=(blk.top + blk.bottom) / 2,
                        meta={
                            "top": blk.top,
                            "bottom": blk.bottom,
                            "source_time": opposing.timestamp.isoformat(),
                        },
                    )
                )

        self._bodies.append(body)
        self._recent.append(bar)
        return signals
