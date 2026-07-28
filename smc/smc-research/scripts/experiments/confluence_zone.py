"""Experiment: confluence_zone.

Hypothesis: a liquidity sweep INTO a fresh unmitigated FVG or order-block zone
is the textbook SMC setup; a sweep in a vacuum is noise. Track active zones
incrementally from FVGDetector / OrderBlockDetector created/mitigated events
(mirroring their mitigation timing) and take a sweep only if the sweep bar's
extreme is inside (or within 0.25 x ATR of) an active opposite-side zone:
bullish sweep (long) -> bullish FVG/OB zone below; bearish sweep -> bearish
zone above.

Zone freshness is judged as of the bar's OPEN: the snapshot of active zones is
taken before this bar's created/mitigated events are applied, so the sweep bar
tapping into a zone (which may itself mitigate it) still counts, while a zone
created on the sweep bar itself does not.

Grid (6 configs): zone source {fvg, ob, either} x timeframe {1h, 15m},
ATR x 2.0 stops, swing_strength=3. All reported numbers are walk-forward OOS
(6m train / 3m test) with COST_MODELS["BTCUSD"]. Time stops ~24h-5d:
24 bars @1h, 96 bars @15m. target_r=2.0.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from smc_research import load
from smc_research.detectors import (
    FVGDetector,
    LiquiditySweepDetector,
    OrderBlockDetector,
)
from smc_research.detectors.types import Bar
from smc_research.engine import COST_MODELS, walk_forward
from smc_research.engine.strategy import EntryIntent, Strategy
from smc_research.stats import expectancy_ci, summarize


class ConfluenceZoneSweepStrategy(Strategy):
    """Sweep-reversal gated by confluence with a fresh FVG / order-block zone.

    zone_source: "fvg" | "ob" | "either".
    Active-zone bookkeeping mirrors the detectors exactly: zones are added on
    *_created events and removed on *_mitigated events, keyed by
    (direction, top, bottom, created_at). The confluence check uses the zone
    set as of the bar's open (before this bar's events are applied).

    Stop: sweep-bar extreme -/+ atr_mult * ATR(atr_len), ATR incremental from
    completed bars only. Entries fill next-bar open (engine rule).
    """

    def __init__(
        self,
        zone_source: str = "either",
        swing_strength: int = 3,
        atr_mult: float = 2.0,
        atr_len: int = 14,
        zone_tol_atr: float = 0.25,
    ):
        self.params = {
            "zone_source": zone_source,
            "swing_strength": swing_strength,
            "atr_mult": atr_mult,
            "atr_len": atr_len,
            "zone_tol_atr": zone_tol_atr,
        }
        self.zone_source = zone_source
        self.atr_mult = atr_mult
        self.atr_len = atr_len
        self.zone_tol_atr = zone_tol_atr
        self._sweeps = LiquiditySweepDetector(swing_strength=swing_strength)
        self._fvg = FVGDetector()
        self._ob = OrderBlockDetector()
        # key -> (direction, top, bottom); key includes created_at for uniqueness
        self._active_fvg: dict[tuple, tuple[str, float, float]] = {}
        self._active_ob: dict[tuple, tuple[str, float, float]] = {}
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

    @staticmethod
    def _apply_events(active: dict, signals, created_kind: str, mitigated_kind: str) -> None:
        for sig in signals:
            top = sig.meta.get("top")
            bottom = sig.meta.get("bottom")
            if sig.kind == created_kind:
                key = (sig.direction, top, bottom, sig.timestamp.isoformat())
                active[key] = (sig.direction, top, bottom)
            elif sig.kind == mitigated_kind:
                key = (sig.direction, top, bottom, sig.meta.get("created_at"))
                active.pop(key, None)

    def _zones(self) -> list[tuple[str, float, float]]:
        zones: list[tuple[str, float, float]] = []
        if self.zone_source in ("fvg", "either"):
            zones.extend(self._active_fvg.values())
        if self.zone_source in ("ob", "either"):
            zones.extend(self._active_ob.values())
        return zones

    def update(self, bar: Bar) -> EntryIntent | None:
        atr = self._update_atr(bar)

        # Snapshot of zones active as of this bar's OPEN.
        snapshot = self._zones()

        # Advance zone detectors and mirror their created/mitigated timing.
        self._apply_events(self._active_fvg, self._fvg.update(bar), "fvg_created", "fvg_mitigated")
        self._apply_events(self._active_ob, self._ob.update(bar), "ob_created", "ob_mitigated")

        sweep_signals = self._sweeps.update(bar)
        if atr is None:
            return None
        tol = self.zone_tol_atr * atr
        buffer = self.atr_mult * atr

        for sig in sweep_signals:
            if sig.kind != "liquidity_sweep":
                continue
            if sig.direction == "bullish":  # sell-side taken -> long candidate
                in_zone = any(
                    d == "bullish" and (b - tol) <= bar.low <= (t + tol)
                    for d, t, b in snapshot
                )
                if in_zone:
                    return EntryIntent(
                        direction="long",
                        stop_price=bar.low - buffer,
                        reason=f"sweep_into_{self.zone_source}_zone",
                        meta={"level": sig.price},
                    )
            elif sig.direction == "bearish":  # buy-side taken -> short candidate
                in_zone = any(
                    d == "bearish" and (b - tol) <= bar.high <= (t + tol)
                    for d, t, b in snapshot
                )
                if in_zone:
                    return EntryIntent(
                        direction="short",
                        stop_price=bar.high + buffer,
                        reason=f"sweep_into_{self.zone_source}_zone",
                        meta={"level": sig.price},
                    )
        return None


TIME_STOP = {"1h": 24, "15m": 96}  # ~24h horizon per instructions
COSTS = COST_MODELS["BTCUSD"]


def run_config(df, timeframe: str, zone_source: str) -> dict:
    label = f"{zone_source}|{timeframe}|ATRx2.0|k=3"
    wf = walk_forward(
        df,
        ConfluenceZoneSweepStrategy,
        [{"zone_source": zone_source, "swing_strength": 3, "atr_mult": 2.0}],
        costs=COSTS,
        train_months=6,
        test_months=3,
        time_stop_bars=TIME_STOP[timeframe],
        target_r=2.0,
    )
    trades = wf.oos_trades
    s = summarize(trades)
    ci = expectancy_ci(trades, iters=1000)
    row = {
        "label": label,
        "zone_source": zone_source,
        "timeframe": timeframe,
        "atr_mult": 2.0,
        "swing_strength": 3,
        "zone_tol_atr": 0.25,
        "time_stop_bars": TIME_STOP[timeframe],
        "target_r": 2.0,
        "n": s.n_trades,
        "hit_rate": round(s.hit_rate, 4),
        "expectancy_r": round(s.expectancy_r, 4),
        "exp_ci_lo": round(ci.lo, 4),
        "exp_ci_hi": round(ci.hi, 4),
        "profit_factor": round(s.profit_factor, 4) if s.profit_factor != float("inf") else None,
        "max_drawdown_r": round(s.max_drawdown_r, 4),
        "total_r": round(s.total_r, 4),
        "avg_win_r": round(s.avg_win_r, 4),
        "avg_loss_r": round(s.avg_loss_r, 4),
        "n_splits": len(wf.splits),
    }
    print(
        f"{label:28s} n={s.n_trades:4d} hit={s.hit_rate:5.1%} "
        f"exp={s.expectancy_r:+.3f}R [{ci.lo:+.3f},{ci.hi:+.3f}] "
        f"pf={s.profit_factor:.2f} maxDD={s.max_drawdown_r:.1f}R"
    )
    return row


def main() -> None:
    frames = {
        tf: load("BTCUSD", tf, "2023-01-01", "2026-07-28") for tf in ("1h", "15m")
    }
    rows: list[dict] = []
    for tf in ("1h", "15m"):
        for zone_source in ("fvg", "ob", "either"):
            rows.append(run_config(frames[tf], tf, zone_source))

    out = ROOT / "reports_out" / "experiments" / "confluence_zone.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"experiment": "confluence_zone", "configs": rows}, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
