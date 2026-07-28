# Research log

Chronological record of strategy research. Every number is walk-forward
out-of-sample (6m train / 3m test) on BTCUSD with `COST_MODELS["BTCUSD"]`
(~15 bps round trip) unless stated. Regenerate any experiment with its
script under `scripts/experiments/`.

## Session 3 (2026-07-28) — naive sweep family, 48-config sweep

`scripts/research_strategies.py`. Stop mode {extreme, ATR×0.5/1/2} ×
swing {3,5} × min-risk {0/30/60bps} × {15m,1h}. **All 48 negative.**
Best: 1h ATR×2 ss=3 → −0.10R [−0.17,−0.04], n=950. Wider stops + slower
bars cut cost drag ~9× (worst 15m cell −0.90R). Raw (cost-free) edge on
15m ≈ +0.06R — the signal is nearly all noise, and costs finish it.

## Session 3b (2026-07-28) — six structural redesigns (multi-agent)

Six hypotheses, ~70 configs total, plus adversarial verification of every
positive. Scripts: `scripts/experiments/*.py`.

| Hypothesis | Best OOS cell | n | Expectancy [95% CI] | Verdict |
|---|---|---|---|---|
| trend_aligned | 4h ATR×2 k=3, with-trend only | 101 | **+0.089R** [−0.138,+0.320] | unrefuted but NOT significant |
| exit_design (15 exits on best entries) | tr=4, ts=48, 1h | 642 | −0.065R [−0.179,+0.055] | no exit rescues the entries |
| session_filter | London+NY, 1h | 508 | −0.071R [−0.161,+0.025] | directional help, still negative |
| htf_4h (unconditioned) | ss=3 ATR×2 tr=2 | 193 | −0.053R [−0.213,+0.093] | negative |
| limit_retrace | 1h adaptive maker | 866 | −0.126R [−0.203,−0.045] | REFUTED — adverse selection on limit fills |
| confluence_zone (FVG/OB) | OB, 1h | 165 | +0.019R [−0.133,+0.173] | REFUTED — flips negative at 1.5× costs; negative in the 2 largest years |

**trend_aligned detail** (the one live thread): with-trend gating beats the
fade-everything baseline at comparable settings (1h: −0.07R vs −0.10R on
half the trades), the counter-trend mirror control is clearly worse
(−0.122R, PF 0.78), and the 4h aligned cell is positive every calendar year
and survives 1.5× costs on the point estimate (+0.066R). But: n=101, the
CI spans zero, it is the max of 8 cells (winner's curse), and excluding the
top 5 days the expectancy is −0.008R. **Treat as "zero-to-slightly-positive
mechanism", not an edge.**

## Session 4 (2026-07-28) — pooled transfer test: VERDICT, family retired

`scripts/pooled_transfer_test.py`. The BTC-selected trend-aligned config
(4h, ATR×2, k=3, aligned, 2R target, 30-bar time stop) run FROZEN on
instruments it never saw, full 2023→2026, per-instrument costs; BTC
excluded from the pool (it selected the config):

| Instrument | n | Hit rate | Expectancy [95% CI] | PF | Total R |
|---|---|---|---|---|---|
| ETHUSD | 135 | 37.0% | −0.067R [−0.254, +0.123] | 0.87 | −9.1 |
| EURUSD | 102 | 39.2% | −0.131R [−0.337, +0.084] | 0.77 | −13.4 |
| SPX500 | 97 | 45.4% | +0.067R [−0.160, +0.308] | 1.13 | +6.5 |
| **POOLED** | **334** | **40.1%** | **−0.048R [−0.166, +0.072]** | 0.91 | −15.9 |
| BTCUSD (reference, not pooled) | 129 | 49.6% | +0.105R [−0.107, +0.319] | 1.23 | +13.6 |

**Pre-registered decision rule applied: the pooled CI straddles zero with a
negative point estimate → the sweep family is RETIRED.** The BTC +0.09R
cell was selection bias, exactly as the winner's-curse caveat predicted —
the mechanism does not transfer. The one soft note: SPX500 is the only
transfer instrument with a positive point estimate and BTC remains
non-negative, so if the sweep concept ever returns it returns as an
index/crypto-trend phenomenon — but that is a new hypothesis for a new
pre-registered test, not a reprieve for this one.

## Session 5 (2026-07-28) — FVG-retrace continuation: RETIRED, decisively

`scripts/fvg_retrace_experiment.py` (pre-registered in the prior commit —
grid, cells, and rule frozen before any result existed). Trend-aligned FVG
→ retrace entry, stop beyond far edge − ATR buffer, 2R target; grid
entry_frac {0.5,1.0} × stop_atr_mult {0.5,1.0} selected per walk-forward
window; 8 cells = {BTC, ETH, EURUSD, SPX500} × {1h, 4h}:

| Cell | n | Expectancy [95% CI] |
|---|---|---|
| BTCUSD 1h / 4h | 1326 / 297 | −0.401 / −0.312 |
| ETHUSD 1h / 4h | 1283 / 284 | −0.263 / −0.635 |
| EURUSD 1h / 4h | 863 / 218 | −0.355 / −0.998 |
| SPX500 1h / 4h | 831 / 237 | −0.257 / −0.314 |
| **POOLED** | **5339** | **−0.366R [−0.453, −0.290]** |

Every cell negative; the pooled CI sits entirely below zero. This is not
"insignificant" — the naive fill-the-gap continuation entry is measurably
a losing proposition after costs at these horizons. **Family retired per
the pre-registered rule.**

## Standing conclusions

1. **The liquidity-sweep signal family is retired** (session 4): ~120
   configs OOS on BTC plus a frozen-config transfer test across ETH/EURUSD/
   SPX500 (pooled n=334, −0.048R [−0.166, +0.072]). Do not build product
   claims on it; do not re-tune it without a genuinely new mechanism and a
   pre-registered test.
2. Two mechanisms measurably reduced bleed and should persist in any future
   design: trend alignment (structure-state gate) and wide structural stops
   (ATR×2) on slow timeframes.
3. **FVG-retrace continuation retired** (session 5): pooled n=5,339,
   −0.366R [−0.453, −0.290] — significantly negative in every cell. Two SMC
   entry families are now measured and retired with tight CIs.
   Research posture going forward: new families only with a pre-registered
   test AND a mechanistic reason to expect post-cost edge; the program's
   product-relevant output — honest measurement infrastructure plus the
   demonstrated discipline of killing losers — is already in hand.
4. Product implication (Plan A/B): the sellable differentiator was never a
   magic win rate — it is the measurement infrastructure itself, which has
   now killed two false positives that a typical vendor would have shipped.
   The Pro stats panel shows measured per-setup hit rates with sample
   sizes; these findings are publishable as research-honesty content with
   no performance promises.
