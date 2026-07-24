# -*- coding: utf-8 -*-
"""Smoke-test demo for vectorbt (https://github.com/polakowo/vectorbt).

Runs a simple moving-average crossover backtest on synthetic GBM price data,
so it works fully offline. See Install.md / docs for setup instructions:

    uv venv .venv-vbt --python 3.11
    uv pip install --python .venv-vbt/bin/python "git+https://github.com/polakowo/vectorbt.git"
    .venv-vbt/bin/python scripts/vectorbt_demo.py
"""

import numpy as np
import pandas as pd
import vectorbt as vbt


def main() -> None:
    print(f"vectorbt version: {vbt.__version__}")

    # Generate one year of synthetic daily prices (geometric Brownian motion).
    rng = np.random.default_rng(seed=42)
    n = 365
    returns = rng.normal(loc=0.0005, scale=0.02, size=n)
    price = pd.Series(
        100.0 * np.exp(np.cumsum(returns)),
        index=pd.date_range("2025-01-01", periods=n, freq="D"),
        name="close",
    )

    # Classic 10/50 moving-average crossover strategy.
    fast_ma = vbt.MA.run(price, window=10)
    slow_ma = vbt.MA.run(price, window=50)
    entries = fast_ma.ma_crossed_above(slow_ma)
    exits = fast_ma.ma_crossed_below(slow_ma)

    pf = vbt.Portfolio.from_signals(price, entries, exits, init_cash=10_000, fees=0.001)

    print("\n=== MA(10/50) crossover on synthetic data ===")
    print(pf.stats())

    # Compare against buy-and-hold.
    hold_pf = vbt.Portfolio.from_holding(price, init_cash=10_000)
    print(f"\nStrategy total return:     {pf.total_return():>8.2%}")
    print(f"Buy-and-hold total return: {hold_pf.total_return():>8.2%}")


if __name__ == "__main__":
    main()
