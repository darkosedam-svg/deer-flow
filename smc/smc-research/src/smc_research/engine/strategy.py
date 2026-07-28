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

from smc_research.detectors import FVGDetector, LiquiditySweepDetector, StructureDetector
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

    Stop placement (the session-2 research axis — sweep-extreme stops proved
    uneconomically tight vs costs on 15m):
    - atr_mult=None: stop beyond the sweep bar's extreme, widened by
      stop_buffer_frac × bar range (the original naive baseline).
    - atr_mult set: structural stop at sweep extreme ± atr_mult × ATR(atr_len)
      — ATR is computed incrementally from completed bars only.
    """

    def __init__(
        self,
        swing_strength: int = 3,
        stop_buffer_frac: float = 0.1,
        atr_mult: float | None = None,
        atr_len: int = 14,
    ):
        self.params = {
            "swing_strength": swing_strength,
            "stop_buffer_frac": stop_buffer_frac,
            "atr_mult": atr_mult,
            "atr_len": atr_len,
        }
        self._detector = LiquiditySweepDetector(swing_strength=swing_strength)
        self.stop_buffer_frac = stop_buffer_frac
        self.atr_mult = atr_mult
        self.atr_len = atr_len
        self._trs: list[float] = []
        self._prev_close: float | None = None

    def _update_atr(self, bar: Bar) -> float | None:
        tr = bar.high - bar.low
        if self._prev_close is not None:
            tr = max(tr, abs(bar.high - self._prev_close), abs(bar.low - self._prev_close))
        self._trs.append(tr)
        if len(self._trs) > self.atr_len:
            self._trs.pop(0)
        self._prev_close = bar.close
        if len(self._trs) < self.atr_len:
            return None
        return sum(self._trs) / self.atr_len

    def update(self, bar: Bar) -> EntryIntent | None:
        atr = self._update_atr(bar)  # includes this bar; entry fills next bar
        signals: list[Signal] = self._detector.update(bar)
        for sig in signals:
            if sig.kind != "liquidity_sweep":
                continue
            if self.atr_mult is not None:
                if atr is None:
                    continue  # ATR not warmed up yet
                buffer = self.atr_mult * atr
            else:
                buffer = self.stop_buffer_frac * (bar.high - bar.low)
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


class TrendAlignedSweepStrategy(Strategy):
    """Sweep entry gated by StructureDetector trend state (session-3b lead).

    mode="aligned": long on sell-side sweeps only in a bullish trend, short
    on buy-side sweeps only in a bearish trend. mode="counter" is the exact
    mirror, kept as the experiment control. Stop: sweep-bar extreme
    ± atr_mult × ATR(atr_len), ATR incremental from completed bars only.

    Promoted from scripts/experiments/trend_aligned.py — the only variant of
    the sweep family whose best cell (4h, ATR×2, k=3) was positive OOS every
    calendar year; still statistically unresolved (see RESEARCH_LOG.md).
    """

    def __init__(
        self,
        swing_strength: int = 3,
        atr_mult: float = 2.0,
        atr_len: int = 14,
        mode: str = "aligned",
    ):
        self.params = {
            "swing_strength": swing_strength,
            "atr_mult": atr_mult,
            "atr_len": atr_len,
            "mode": mode,
        }
        self._sweeps = LiquiditySweepDetector(swing_strength=swing_strength)
        self._structure = StructureDetector(swing_strength=swing_strength)
        self.atr_mult = atr_mult
        self.atr_len = atr_len
        self.mode = mode
        self._trend = "none"
        self._trs: list[float] = []
        self._prev_close: float | None = None

    def _update_atr(self, bar: Bar) -> float | None:
        tr = bar.high - bar.low
        if self._prev_close is not None:
            tr = max(tr, abs(bar.high - self._prev_close), abs(bar.low - self._prev_close))
        self._trs.append(tr)
        if len(self._trs) > self.atr_len:
            self._trs.pop(0)
        self._prev_close = bar.close
        if len(self._trs) < self.atr_len:
            return None
        return sum(self._trs) / self.atr_len

    def update(self, bar: Bar) -> EntryIntent | None:
        atr = self._update_atr(bar)

        # Structure first, so a break closing on this bar updates the trend
        # before the sweep gate is evaluated. Both see only completed bars.
        for sig in self._structure.update(bar):
            if sig.kind in ("bos", "choch"):
                self._trend = sig.direction

        signals: list[Signal] = self._sweeps.update(bar)
        if atr is None:
            return None
        buffer = self.atr_mult * atr

        for sig in signals:
            if sig.kind != "liquidity_sweep":
                continue
            if sig.direction == "bullish":  # sell-side liquidity taken -> long
                want = "bullish" if self.mode == "aligned" else "bearish"
                if self._trend == want:
                    return EntryIntent(
                        direction="long",
                        stop_price=bar.low - buffer,
                        reason=f"sweep_sellside_{self.mode}",
                        meta={"level": sig.price, "trend": self._trend},
                    )
            elif sig.direction == "bearish":  # buy-side taken -> short
                want = "bearish" if self.mode == "aligned" else "bullish"
                if self._trend == want:
                    return EntryIntent(
                        direction="short",
                        stop_price=bar.high + buffer,
                        reason=f"sweep_buyside_{self.mode}",
                        meta={"level": sig.price, "trend": self._trend},
                    )
        return None


class FVGRetraceStrategy(Strategy):
    """Pre-registered session-5 family: FVG-retrace continuation.

    Mechanism: displacement creates a fair value gap in the direction of the
    prevailing structure trend; price retracing INTO the gap is the entry.
    Concretely (bullish case, mirrored for bearish):
    - StructureDetector trend must be bullish when the FVG is created;
    - the gap (bottom, top) becomes the pending setup, entry level
      top − entry_frac × height (entry_frac=0.5 is the gap midpoint / CE);
    - a later bar trading down to the entry level arms the entry — the
      engine fills at the NEXT bar's open (no lookahead);
    - stop = gap bottom − stop_atr_mult × ATR(atr_len) (beyond the far edge);
    - the setup expires untouched after expiry_bars; a newer aligned FVG
      replaces an older pending one.

    Retained mechanisms from retired families (RESEARCH_LOG conclusions):
    trend gating and ATR-buffered structural stops.
    """

    def __init__(
        self,
        entry_frac: float = 0.5,
        stop_atr_mult: float = 1.0,
        swing_strength: int = 3,
        atr_len: int = 14,
        expiry_bars: int = 12,
    ):
        self.params = {
            "entry_frac": entry_frac,
            "stop_atr_mult": stop_atr_mult,
            "swing_strength": swing_strength,
            "atr_len": atr_len,
            "expiry_bars": expiry_bars,
        }
        self._fvg = FVGDetector()
        self._structure = StructureDetector(swing_strength=swing_strength)
        self.entry_frac = entry_frac
        self.stop_atr_mult = stop_atr_mult
        self.atr_len = atr_len
        self.expiry_bars = expiry_bars
        self._trend = "none"
        self._trs: list[float] = []
        self._prev_close: float | None = None
        # pending: (direction, entry_level, stop_price, age)
        self._pending: tuple[str, float, float, int] | None = None

    def _update_atr(self, bar: Bar) -> float | None:
        tr = bar.high - bar.low
        if self._prev_close is not None:
            tr = max(tr, abs(bar.high - self._prev_close), abs(bar.low - self._prev_close))
        self._trs.append(tr)
        if len(self._trs) > self.atr_len:
            self._trs.pop(0)
        self._prev_close = bar.close
        if len(self._trs) < self.atr_len:
            return None
        return sum(self._trs) / self.atr_len

    def update(self, bar: Bar) -> EntryIntent | None:
        atr = self._update_atr(bar)

        for sig in self._structure.update(bar):
            if sig.kind in ("bos", "choch"):
                self._trend = sig.direction

        # 1) Does this bar touch the pending entry level? (Checked BEFORE new
        #    setups so a gap created on this bar can't be entered on itself.)
        intent: EntryIntent | None = None
        if self._pending is not None:
            direction, entry_level, stop_price, age = self._pending
            touched = bar.low <= entry_level if direction == "long" else bar.high >= entry_level
            if touched:
                intent = EntryIntent(
                    direction=direction,
                    stop_price=stop_price,
                    reason=f"fvg_retrace_{direction}",
                    meta={"entry_level": entry_level},
                )
                self._pending = None
            elif age + 1 >= self.expiry_bars:
                self._pending = None
            else:
                self._pending = (direction, entry_level, stop_price, age + 1)

        # 2) New aligned FVG becomes (replaces) the pending setup.
        if atr is not None:
            for sig in self._fvg.update(bar):
                if sig.kind != "fvg_created":
                    continue
                top, bottom = sig.meta["top"], sig.meta["bottom"]
                height = top - bottom
                if sig.direction == "bullish" and self._trend == "bullish":
                    self._pending = (
                        "long",
                        top - self.entry_frac * height,
                        bottom - self.stop_atr_mult * atr,
                        0,
                    )
                elif sig.direction == "bearish" and self._trend == "bearish":
                    self._pending = (
                        "short",
                        bottom + self.entry_frac * height,
                        top + self.stop_atr_mult * atr,
                        0,
                    )
        else:
            self._fvg.update(bar)  # keep detector state warm during ATR warm-up

        return intent
