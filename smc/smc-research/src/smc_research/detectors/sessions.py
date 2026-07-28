"""Session / kill-zone events, anchored to explicit UTC windows.

Defaults follow common ICT kill-zone convention; windows are constructor
parameters so per-instrument presets can override them. All boundaries are
UTC — the Pine port must anchor with timestamp() on an explicit timezone,
never syminfo.timezone (Plan B M1 note).
"""

from __future__ import annotations

import datetime as dt

from smc_research.detectors.types import Bar, Detector, Signal

DEFAULT_SESSIONS: dict[str, tuple[dt.time, dt.time]] = {
    "asia": (dt.time(0, 0), dt.time(4, 0)),
    "london": (dt.time(7, 0), dt.time(10, 0)),
    "ny_am": (dt.time(12, 0), dt.time(15, 0)),
    "ny_pm": (dt.time(17, 30), dt.time(20, 0)),
}


class SessionDetector(Detector):
    def __init__(self, sessions: dict[str, tuple[dt.time, dt.time]] | None = None):
        self.sessions = sessions or dict(DEFAULT_SESSIONS)
        self._inside: dict[str, bool] = {name: False for name in self.sessions}

    def update(self, bar: Bar) -> list[Signal]:
        signals: list[Signal] = []
        t = bar.timestamp.timetz().replace(tzinfo=None)
        for name, (start, end) in self.sessions.items():
            inside = start <= t < end
            was_inside = self._inside[name]
            if inside and not was_inside:
                signals.append(
                    Signal(
                        timestamp=bar.timestamp,
                        kind="session_open",
                        direction="none",
                        price=bar.open,
                        meta={"session": name},
                    )
                )
            elif was_inside and not inside:
                signals.append(
                    Signal(
                        timestamp=bar.timestamp,
                        kind="session_close",
                        direction="none",
                        price=bar.open,
                        meta={"session": name},
                    )
                )
            self._inside[name] = inside
        return signals
