# smc-research

Private research repo for the SMC indicator business (Plan B). Python is the
**source of truth** for detection logic; the Pine scripts are ports verified
against it by the parity harness (M4).

## Layout

```
src/smc_research/
  data/        loaders → canonical OHLCV (Binance Vision + Hyperliquid + CSV), Parquet cache
  detectors/   bar-by-bar signal detectors (no lookahead; prefix-invariance enforced by test)
tests/
  golden/      committed 5000-bar fixture + expected signal JSON per detector
```

Planned (Plan B M3/M4): `engine/` (event-driven backtester, walk-forward),
`stats/` (bootstrap CIs), `parity/` (Pine-vs-Python diff), `reports/`,
`presets/`.

## Usage

```bash
uv sync --extra dev
uv run pytest -m "not live"     # offline suite (fast, hermetic)
uv run pytest -m live           # hits real Binance Vision + Hyperliquid endpoints
uv run ruff check .
```

```python
from smc_research import load
df = load("BTCUSD", "15m", "2023-01-01", "2026-07-01")   # M0 exit criterion
```

## Data source notes

- `api.binance.com` is geo-blocked from many hosting regions. Deep history
  therefore comes from the public archive `data.binance.vision` (monthly
  kline zips, CDN, not blocked). Files from 2025-01 use microsecond
  timestamps — handled by magnitude detection.
- Hyperliquid `candleSnapshot` retains ~5000 most recent candles per
  interval (~52 days of 15m), so it serves the live tail only.
- EURUSD and the ES/SPX proxy enter via `csv_loader` (Dukascopy/SPY exports)
  until dedicated loaders exist.

## Invariants (do not break)

1. Every detector is incremental; a signal's timestamp is its confirmation
   bar. `test_prefix_invariance` is the lookahead-bias gate.
2. Golden files change only via `tests/generate_golden.py`, deliberately,
   with the diff reviewed — and the Pine parity harness re-run afterwards.
3. Cached months are never re-downloaded during a backtest run.
