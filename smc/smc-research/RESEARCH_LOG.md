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

## Standing conclusions

1. The liquidity-sweep signal family, in every structural variant tried
   (~120 configs OOS), has no statistically demonstrable post-cost edge on
   BTCUSD alone. Do not build product claims on it.
2. Two mechanisms measurably reduce bleed and should persist in any future
   design: trend alignment (structure-state gate) and wide structural stops
   (ATR×2) on slow timeframes.
3. Next discriminating test (cheap, high information): pool the
   trend-aligned 4h configuration across instruments (ETH, EURUSD, ES) —
   needs the EURUSD/ES data path (M0 leftover). If the pooled CI still
   straddles zero, retire the family and evaluate a different signal class
   (e.g., FVG-retrace continuation) with the same harness.
4. Product implication (Plan A/B): the sellable differentiator was never a
   magic win rate — it is the measurement infrastructure itself. The Pro
   stats panel shows measured per-setup hit rates with sample sizes; these
   findings are publishable as forward-test honesty content once framed as
   research, with no performance promises.
