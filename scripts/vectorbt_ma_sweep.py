# -*- coding: utf-8 -*-
"""Sweep MA crossover windows on real BTC-USD data, SMA vs EMA.

Backtests every fast/slow moving-average pair from a grid (70 combinations)
twice — once with simple and once with exponential moving averages — in
vectorized vectorbt runs, on ~2 years of daily BTC-USD candles from
Coinbase's public API, and ranks them against buy-and-hold. Uses the same
venv as vectorbt_btc_demo.py:

    .venv-vbt/bin/python scripts/vectorbt_ma_sweep.py
"""

import pandas as pd
import vectorbt as vbt

from vectorbt_btc_demo import fetch_btc_daily

FAST_WINDOWS = [5, 8, 10, 15, 20, 25, 30, 40, 50]
SLOW_WINDOWS = [20, 30, 40, 50, 75, 100, 125, 150, 200]

FMT = {
    "total_return": "{:.2%}".format,
    "sharpe": "{:.2f}".format,
    "max_dd": "{:.1%}".format,
    "win_rate": "{:.0%}".format,
}


def sweep(price: pd.Series, pairs: list, ewm: bool) -> pd.DataFrame:
    """Backtest all fast/slow pairs at once; ewm=True uses EMAs, else SMAs."""
    fasts, slows = zip(*pairs)
    fast_ma = vbt.MA.run(price, window=list(fasts), ewm=ewm, short_name="fast")
    slow_ma = vbt.MA.run(price, window=list(slows), ewm=ewm, short_name="slow")
    entries = fast_ma.ma_crossed_above(slow_ma)
    exits = fast_ma.ma_crossed_below(slow_ma)
    pf = vbt.Portfolio.from_signals(price, entries, exits, init_cash=10_000, fees=0.001)
    return pd.DataFrame(
        {
            "total_return": pf.total_return().values,
            "sharpe": pf.sharpe_ratio().values,
            "max_dd": pf.max_drawdown().values,
            "trades": pf.trades.count().values,
            "win_rate": pf.trades.win_rate().values,
        },
        index=pd.MultiIndex.from_tuples(pairs, names=["fast", "slow"]),
    )


def main() -> None:
    price = fetch_btc_daily()
    print(
        f"Fetched {len(price)} daily candles: "
        f"{price.index[0].date()} -> {price.index[-1].date()}"
    )

    pairs = [(f, s) for f in FAST_WINDOWS for s in SLOW_WINDOWS if f < s]
    sma = sweep(price, pairs, ewm=False)
    ema = sweep(price, pairs, ewm=True)

    hold_ret = vbt.Portfolio.from_holding(price, init_cash=10_000).total_return()
    print(f"\nBuy-and-hold total return: {hold_ret:.2%}")
    print(f"Combinations tested: {len(pairs)} (x2 for SMA and EMA)")

    for name, res in [("SMA", sma), ("EMA", ema)]:
        print(f"\n=== {name} crossover: Top 10 by total return ===")
        print(
            res.sort_values("total_return", ascending=False)
            .head(10)
            .to_string(formatters=FMT)
        )
        beat = (res["total_return"] > hold_ret).sum()
        print(
            f"{name}: {beat}/{len(res)} beat buy-and-hold, "
            f"median return {res['total_return'].median():.2%}"
        )

    diff = ema["total_return"] - sma["total_return"]
    print(f"\nPairs where EMA beats SMA: {(diff > 0).sum()}/{len(diff)}")
    print(f"Mean EMA-SMA return difference: {diff.mean():.2%}")


if __name__ == "__main__":
    main()
