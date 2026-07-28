from pathlib import Path

import numpy as np
import pandas as pd
import pytest

GOLDEN_DIR = Path(__file__).parent / "golden"
FIXTURE_CSV = GOLDEN_DIR / "fixture_5000.csv"


def make_fixture(n: int = 5000, seed: int = 42) -> pd.DataFrame:
    """Deterministic synthetic 15m OHLCV series with trending and ranging
    regimes so every detector fires. Committed to CSV; regenerate only by
    deliberate choice (golden files must change with it)."""
    rng = np.random.RandomState(seed)
    idx = pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC")
    # Regime-switching drift to create displacement moves and sweeps.
    regime = np.repeat(rng.choice([-1.0, 0.0, 1.0], size=n // 50 + 1), 50)[:n]
    returns = regime * 8e-4 + rng.normal(0, 1.6e-3, n)
    close = 40000.0 * np.exp(np.cumsum(returns))
    open_ = np.concatenate([[40000.0], close[:-1]])
    spread = np.abs(rng.normal(0, 1.1e-3, n)) * close
    high = np.maximum(open_, close) + spread
    low = np.minimum(open_, close) - np.abs(rng.normal(0, 1.1e-3, n)) * close
    volume = np.abs(rng.normal(100, 30, n))
    df = pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=idx,
    )
    df.index.name = "timestamp"
    return df.round(2)


@pytest.fixture(scope="session")
def fixture_df() -> pd.DataFrame:
    if FIXTURE_CSV.exists():
        df = pd.read_csv(FIXTURE_CSV, index_col="timestamp", parse_dates=True)
        df.index = df.index.tz_convert("UTC")
        return df
    return make_fixture()
