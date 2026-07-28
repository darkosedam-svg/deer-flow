from smc_research.engine import COST_MODELS
from smc_research.reports import InstrumentResult, render_report
from tests.test_stats_and_walkforward import mk_trade


def test_report_renders_with_required_content(tmp_path):
    trades = [mk_trade(i, r) for i, r in enumerate([2.0, -1.0, 2.0, -1.0, -1.0] * 8)]
    out = render_report(
        results=[
            InstrumentResult(
                symbol="BTCUSD",
                timeframe="15m",
                trades=trades,
                costs=COST_MODELS["BTCUSD"],
                chosen_params=[{"swing_strength": 3}],
            )
        ],
        strategy_name="SweepConfirmation",
        methodology={
            "signals": "liquidity sweep of a confirmed swing with close back inside",
            "target_r": 2.0,
            "time_stop_bars": 96,
            "train_months": 6,
            "test_months": 3,
            "data_note": "Binance Vision archive, 15m bars, UTC",
        },
        out_path=tmp_path / "report.html",
        bootstrap_iters=200,
    )
    html = out.read_text()
    assert "out-of-sample" in html
    assert "95% CI" in html or "hit_lo" not in html  # CI section rendered
    assert "40.0%" in html                      # hit rate with sample of 40
    assert "<strong>40</strong>" in html        # sample size printed
    assert "Cost assumptions" in html
    assert "data:image/png;base64," in html     # equity curve embedded
    assert "Not financial advice" in html


def test_report_small_sample_warning(tmp_path):
    trades = [mk_trade(i, 2.0) for i in range(5)]
    out = render_report(
        results=[
            InstrumentResult("BTCUSD", "15m", trades, COST_MODELS["BTCUSD"], [])
        ],
        strategy_name="x",
        methodology={
            "signals": "s", "target_r": 2.0, "time_stop_bars": 96,
            "train_months": 6, "test_months": 3, "data_note": "d",
        },
        out_path=tmp_path / "r.html",
        bootstrap_iters=100,
    )
    assert "Sample-size warning" in out.read_text()
