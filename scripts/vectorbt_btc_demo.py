# -*- coding: utf-8 -*-
"""vectorbt backtest on real BTC-USD data.

Fetches ~2 years of daily BTC-USD candles from Coinbase's public Exchange API
(no API key required) and runs a 10/50 moving-average crossover backtest,
compared against buy-and-hold. Setup (same venv as vectorbt_demo.py):

    uv venv .venv-vbt --python 3.11
    uv pip install --python .venv-vbt/bin/python \
        "git+https://github.com/polakowo/vectorbt.git" "plotly<6" requests
    .venv-vbt/bin/python scripts/vectorbt_btc_demo.py
"""

import datetime as dt

import pandas as pd
import requests
import vectorbt as vbt

API = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
GRANULARITY = 86400  # daily candles
DAYS = 730  # ~2 years
BATCH = 300  # Coinbase's max candles per request


def fetch_btc_daily(days: int = DAYS) -> pd.Series:
    """Fetch daily BTC-USD closes from Coinbase, paginating in 300-day chunks."""
    end = dt.datetime.now(dt.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - dt.timedelta(days=days)
    rows = []
    chunk_start = start
    while chunk_start < end:
        chunk_end = min(chunk_start + dt.timedelta(days=BATCH), end)
        resp = requests.get(
            API,
            params={
                "granularity": GRANULARITY,
                "start": chunk_start.isoformat(),
                "end": chunk_end.isoformat(),
            },
            timeout=30,
        )
        resp.raise_for_status()
        rows.extend(resp.json())  # [time, low, high, open, close, volume]
        chunk_start = chunk_end
    df = pd.DataFrame(rows, columns=["time", "low", "high", "open", "close", "volume"])
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.drop_duplicates("time").sort_values("time").set_index("time")
    return df["close"].astype(float).rename("BTC-USD")


def main() -> None:
    print(f"vectorbt version: {vbt.__version__}")
    price = fetch_btc_daily()
    print(
        f"Fetched {len(price)} daily candles: "
        f"{price.index[0].date()} -> {price.index[-1].date()}, "
        f"latest close ${price.iloc[-1]:,.0f}"
    )

    fast_ma = vbt.MA.run(price, window=10)
    slow_ma = vbt.MA.run(price, window=50)
    entries = fast_ma.ma_crossed_above(slow_ma)
    exits = fast_ma.ma_crossed_below(slow_ma)

    pf = vbt.Portfolio.from_signals(price, entries, exits, init_cash=10_000, fees=0.001)

    print("\n=== MA(10/50) crossover on real BTC-USD (Coinbase daily) ===")
    print(pf.stats())

    hold_pf = vbt.Portfolio.from_holding(price, init_cash=10_000)
    print(f"\nStrategy total return:     {pf.total_return():>8.2%}")
    print(f"Buy-and-hold total return: {hold_pf.total_return():>8.2%}")


if __name__ == "__main__":
    main()
