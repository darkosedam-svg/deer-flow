"""HTML backtest report generator (Plan B M3).

HTML is the canonical artifact (self-contained, base64-embedded charts).
PDF conversion is a deploy-time concern (WeasyPrint needs system libraries);
`to_pdf` attempts it and says so if unavailable.
"""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from jinja2 import Environment, FileSystemLoader

from smc_research.engine.backtester import Trade
from smc_research.engine.costs import CostModel
from smc_research.stats import equity_curve, expectancy_ci, hit_rate_ci, summarize

TEMPLATE_DIR = Path(__file__).parent / "templates"


@dataclass
class InstrumentResult:
    symbol: str
    timeframe: str
    trades: list[Trade]
    costs: CostModel
    chosen_params: list[dict[str, Any]]


def _curve_png(trades: list[Trade]) -> str:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    curve = equity_curve(trades)
    fig, ax = plt.subplots(figsize=(9, 3.2), dpi=120)
    if len(curve):
        ax.plot(curve.index, curve.values, linewidth=1.4)
        running_max = curve.cummax()
        underwater = curve < running_max
        ax.fill_between(
            curve.index, curve.values, running_max.values,
            where=underwater, alpha=0.25, linewidth=0, color="tab:red",
        )
    ax.set_ylabel("cumulative R")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def render_report(
    results: list[InstrumentResult],
    strategy_name: str,
    methodology: dict[str, Any],
    out_path: str | Path,
    bootstrap_iters: int = 2000,
) -> Path:
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
    template = env.get_template("report.html.j2")

    cost_rows, result_rows = [], []
    for res in results:
        s = summarize(res.trades)
        hit = hit_rate_ci(res.trades, iters=bootstrap_iters)
        exp = expectancy_ci(res.trades, iters=bootstrap_iters)
        cost_rows.append(
            {
                "symbol": res.symbol,
                "spread_bps": res.costs.spread_bps,
                "slippage_bps": res.costs.slippage_bps,
                "commission_bps": res.costs.commission_bps,
            }
        )
        result_rows.append(
            {
                "symbol": res.symbol,
                "timeframe": res.timeframe,
                "n": s.n_trades,
                "hit_rate": s.hit_rate, "hit_lo": hit.lo, "hit_hi": hit.hi,
                "expectancy": s.expectancy_r, "exp_lo": exp.lo, "exp_hi": exp.hi,
                "avg_win": s.avg_win_r, "avg_loss": s.avg_loss_r,
                "profit_factor": (
                    "∞" if s.profit_factor == float("inf") else f"{s.profit_factor:.2f}"
                ),
                "total_r": s.total_r,
                "max_dd": s.max_drawdown_r,
                "longest_flat": _fmt_timedelta(s.longest_flat),
                "curve_png": _curve_png(res.trades),
                "chosen_params": res.chosen_params,
            }
        )

    html = template.render(
        generated_at=pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC"),
        strategy_name=strategy_name,
        methodology={**methodology, "bootstrap_iters": bootstrap_iters},
        cost_rows=cost_rows,
        result_rows=result_rows,
        any_small_sample=any(r["n"] < 30 for r in result_rows),
    )
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html)
    return out_path


def _fmt_timedelta(td: pd.Timedelta) -> str:
    days = td.days
    hours = td.components.hours if hasattr(td, "components") else 0
    return f"{days}d {hours}h"


def to_pdf(html_path: str | Path, pdf_path: str | Path) -> Path | None:
    """Best-effort PDF; returns None (with a hint) if WeasyPrint/system libs
    are absent. The HTML is the canonical artifact either way."""
    try:
        from weasyprint import HTML  # type: ignore[import-not-found]
    except Exception:
        return None
    HTML(str(html_path)).write_pdf(str(pdf_path))
    return Path(pdf_path)
