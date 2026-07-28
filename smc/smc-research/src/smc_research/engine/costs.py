"""Per-instrument transaction cost model.

Plan B M3: an SMC backtest without costs is fiction. Every fill is adjusted
by half-spread + slippage against the trader, and commission is charged per
side. Defaults are deliberately conservative round numbers — the report
prints them, and overstating costs is the safe direction.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CostModel:
    spread_bps: float       # full spread; half is paid per fill
    slippage_bps: float     # adverse move per fill
    commission_bps: float   # per side

    def buy_fill(self, price: float) -> float:
        return price * (1 + (self.spread_bps / 2 + self.slippage_bps) / 1e4)

    def sell_fill(self, price: float) -> float:
        return price * (1 - (self.spread_bps / 2 + self.slippage_bps) / 1e4)

    def commission(self, notional: float) -> float:
        return abs(notional) * self.commission_bps / 1e4


# Instrument presets. Sources for revisiting: BTC perp taker fee ~2-4.5bps,
# spread on liquid perps ~1bp; EURUSD retail spread ~0.6-1.5 pips.
COST_MODELS: dict[str, CostModel] = {
    "BTCUSD": CostModel(spread_bps=1.0, slippage_bps=2.0, commission_bps=4.5),
    "ETHUSD": CostModel(spread_bps=1.5, slippage_bps=2.5, commission_bps=4.5),
    "EURUSD": CostModel(spread_bps=1.2, slippage_bps=0.5, commission_bps=0.5),
    "SPY": CostModel(spread_bps=0.5, slippage_bps=0.5, commission_bps=0.5),
}

ZERO_COSTS = CostModel(0.0, 0.0, 0.0)
