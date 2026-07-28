from smc_research.detectors.fvg import FVGDetector
from smc_research.detectors.liquidity import LiquiditySweepDetector
from smc_research.detectors.order_block import OrderBlockDetector
from smc_research.detectors.sessions import SessionDetector
from smc_research.detectors.structure import StructureDetector
from smc_research.detectors.types import Bar, Detector, Signal, iter_bars, run

ALL_DETECTORS = {
    "fvg": FVGDetector,
    "order_block": OrderBlockDetector,
    "structure": StructureDetector,
    "liquidity": LiquiditySweepDetector,
    "sessions": SessionDetector,
}

__all__ = [
    "ALL_DETECTORS",
    "Bar",
    "Detector",
    "FVGDetector",
    "LiquiditySweepDetector",
    "OrderBlockDetector",
    "SessionDetector",
    "Signal",
    "StructureDetector",
    "iter_bars",
    "run",
]
