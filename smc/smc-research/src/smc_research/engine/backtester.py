"""Event-driven backtester (Plan B M3).

Rules, all non-negotiable:
- Entry at the NEXT bar's open after the signal bar (never signal-bar close).
- Stop at structural invalidation (from the EntryIntent), target at
  `target_r` × risk, time-stop after `time_stop_bars` bars (exit at close).
- If stop AND target are both touched within one bar, the STOP fills —
  conservative, since intrabar sequence is unknowable from OHLC.
- One position at a time; intents arriving while positioned are dropped.
- All fills go through the CostModel; realized R is measured against the
  RAW (uncosted) risk so costs show up as R degradation, not hidden.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from smc_research.detectors.types import iter_bars
from smc_research.engine.costs import CostModel
from smc_research.engine.strategy import EntryIntent, Strategy


@dataclass(frozen=True)
class Trade:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    direction: str
    entry_price: float      # costed fill
    exit_price: float       # costed fill
    stop_price: float
    target_price: float
    exit_reason: str        # "stop" | "target" | "time"
    risk: float             # raw per-unit risk at entry
    realized_r: float
    reason: str             # strategy's entry reason


@dataclass
class _Open:
    intent: EntryIntent
    entry_time: pd.Timestamp
    entry_fill: float
    entry_raw: float
    target_price: float
    bars_held: int = 0


def run_backtest(
    df: pd.DataFrame,
    strategy: Strategy,
    costs: CostModel,
    target_r: float = 2.0,
    time_stop_bars: int = 96,
    min_risk_bps: float = 0.0,
) -> list[Trade]:
    trades: list[Trade] = []
    pending: EntryIntent | None = None
    pos: _Open | None = None

    for bar in iter_bars(df):
        # 1) Fill last bar's intent at this bar's open (the no-lookahead rule).
        if pending is not None and pos is None:
            raw = bar.open
            risk = (
                raw - pending.stop_price
                if pending.direction == "long"
                else pending.stop_price - raw
            )
            # Cost-aware filter: risk narrower than min_risk_bps of price means
            # round-trip costs dominate the R math — skip the setup entirely.
            wide_enough = risk > 0 and (risk / raw) * 1e4 >= min_risk_bps
            if wide_enough:  # a gap through the stop also invalidates the setup
                fill = costs.buy_fill(raw) if pending.direction == "long" else costs.sell_fill(raw)
                target = (
                    raw + target_r * risk
                    if pending.direction == "long"
                    else raw - target_r * risk
                )
                pos = _Open(
                    intent=pending,
                    entry_time=bar.timestamp,
                    entry_fill=fill,
                    entry_raw=raw,
                    target_price=target,
                )
        pending = None

        # 2) Manage the open position on this bar (skip the entry bar itself
        #    for stop/target since entry was at its open — conservative would
        #    check it too; we check it: entry at open, exits evaluated on the
        #    same bar's range).
        if pos is not None:
            exit_reason = None
            raw_exit = None
            long = pos.intent.direction == "long"
            stop = pos.intent.stop_price
            hit_stop = bar.low <= stop if long else bar.high >= stop
            hit_target = bar.high >= pos.target_price if long else bar.low <= pos.target_price
            if hit_stop:            # stop-first on ambiguous bars
                exit_reason, raw_exit = "stop", stop
            elif hit_target:
                exit_reason, raw_exit = "target", pos.target_price
            else:
                pos.bars_held += 1
                if pos.bars_held >= time_stop_bars:
                    exit_reason, raw_exit = "time", bar.close

            if exit_reason is not None:
                exit_fill = costs.sell_fill(raw_exit) if long else costs.buy_fill(raw_exit)
                risk = abs(pos.entry_raw - stop)
                pnl = (exit_fill - pos.entry_fill) if long else (pos.entry_fill - exit_fill)
                commission = costs.commission(pos.entry_fill) + costs.commission(exit_fill)
                realized_r = (pnl - commission) / risk
                trades.append(
                    Trade(
                        entry_time=pos.entry_time,
                        exit_time=bar.timestamp,
                        direction=pos.intent.direction,
                        entry_price=pos.entry_fill,
                        exit_price=exit_fill,
                        stop_price=stop,
                        target_price=pos.target_price,
                        exit_reason=exit_reason,
                        risk=risk,
                        realized_r=realized_r,
                        reason=pos.intent.reason,
                    )
                )
                pos = None

        # 3) Let the strategy see the bar; its intent fills NEXT bar.
        intent = strategy.update(bar)
        if intent is not None and pos is None:
            pending = intent

    return trades


def trades_to_frame(trades: list[Trade]) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame(
            columns=[
                "entry_time", "exit_time", "direction", "entry_price", "exit_price",
                "stop_price", "target_price", "exit_reason", "risk", "realized_r", "reason",
            ]
        )
    return pd.DataFrame([t.__dict__ for t in trades])
