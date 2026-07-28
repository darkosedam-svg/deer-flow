# Execution tracker — Plan A / Plan B

Working tracker for the 90-day plan (W1 = 28 Jul 2026). Engineering work
lives in this `smc/` directory until it's split into the repos Plan B
specifies. Update this file every session.

## Why this is inside the deer-flow fork

This Claude session is scoped to `darkosedam-svg/deer-flow` only. Each
subdirectory is a self-contained project (own `pyproject.toml`, `.gitignore`,
tests) so splitting out is `git mv` + push, no rework:

| Directory | Destined repo | Visibility |
|---|---|---|
| `smc-research/` | `darkosedam-svg/smc-research` (NEW) | private |
| `vendor-ops/` | `darkosedam-svg/vendor-ops` (NEW) | private |
| `pine/` | private repo, public artifacts | private |

`smc_research/detectors/` mirrors the intended public API of
`ict-smc-detector` — sync it there once that repo is in a session's scope.

## Milestone status (Plan B)

| Milestone | Deadline | Status |
|---|---|---|
| M0 scaffolding & data | Mon 3 Aug | ✅ **DONE, exit criterion verified live** — `load("BTCUSD","15m",...)` returns a clean frame; integrity test asserts monotonic index, no dupes, gap threshold; live tests pass against real endpoints |
| M1 Lite script published | **Mon 17 Aug** | 🟡 Script drafted (`pine/lite/`), publication checklist in `pine/README.md`. Needs: TradingView compile, 5×3 visual pass, read House Rules, publish |
| M2 detectors parity-quality | Mon 24 Aug | 🟡 5 detectors done with prefix-invariance + golden tests (26 offline tests green). Remaining: parameter surface alignment during M4 |
| M3 backtest + PDF report | **Mon 24 Aug** | 🟡 **Pipeline done & exit criterion met**: one command (`scripts/run_backtest.py`) regenerates the report — walk-forward (6m/3m), per-instrument costs, bootstrap CIs, drawdown-annotated equity curve, sample sizes everywhere. Ran live on 125k real BTC 15m bars. **Remaining:** EURUSD + ES/SPX CSVs, strategy research (see finding below), PDF (WeasyPrint at deploy) |
| M4 parity harness ≥98% | Mon 24 Aug | 🟡 `parity/diff.py` built + self-tested (synthetic export → 100% match; perturbation → gate fails correctly). **Remaining:** parity Pine variant + one real TradingView CSV export from you |
| M5 Pro script | Mon 7 Sep | ⬜ Not started |
| M6 payment stack tested live | **Mon 14 Sep** | 🟡 Core scaffold done+tested: HMAC verify, idempotency, entitlements, grant/revoke queue, lifetime-immunity. Remaining: email/Discord workers, reconciliation, admin auth, live €1 test |
| M7 forward-test automation | Mon 28 Sep | ⬜ Not started |

## Research finding (session 5) — FVG-retrace family RETIRED decisively

Pre-registered pooled test (8 cells, 4 instruments × 2 timeframes,
n=5,339): expectancy −0.366R [−0.453, −0.290], every cell negative. The
naive gap-fill continuation entry measurably loses after costs. Strategic
consequence: two families retired with tight CIs; further family
exploration is optional research, not launch-critical. Engineering time
now shifts back to the launch path: M1 publication prep, M5 Pro script
(whose stats panel presents *measured descriptive statistics*, not edge
claims — fully supported by this program), M4 parity, M6 completion.

## Research finding (session 4) — transfer verdict: sweep family RETIRED

The BTC-selected trend-aligned 4h config, run frozen on instruments it
never saw (ETH, EURUSD, SPX500 — Dukascopy loader now serves FX/index
data): pooled n=334, expectancy −0.048R [−0.166, +0.072]. Pre-registered
rule applied → **family retired**; the BTC positive cell was winner's-curse
selection bias. Next signal class through the identical harness:
FVG-retrace continuation (pre-registration written in RESEARCH_LOG.md).
Side benefit: EURUSD + SPX500 data paths now exist, unblocking the
3-instrument M3 report.

## Research finding (session 3b) — six structural redesigns, multi-agent

Six hypothesis families explored in parallel (trend alignment, limit
entries, exit design, session filters, FVG/OB confluence, 4h), ~70 configs,
all walk-forward OOS with costs, positives adversarially verified (1.5×
costs, year-split stability, lookahead audit). **Nothing clears the CI
gate.** One live thread: with-trend 4h sweeps (+0.089R, n=101, CI spans
zero; mirror control clearly worse) — a real bleed-reduction mechanism, not
yet an edge. Full table + standing conclusions in
`smc-research/RESEARCH_LOG.md`. Next discriminating test: pool the
trend-aligned 4h config across ETH/EURUSD/ES (needs the multi-instrument
data path). Strategy pivot to consider after that: FVG-retrace continuation
family through the same harness.

## Research finding (session 3) — systematic sweep of the naive family

48-config walk-forward sweep (stop mode {extreme, ATR×0.5/1.0/2.0} ×
swing strength {3,5} × min-risk filter {0/30/60bps} × {15m, 1h}), all
out-of-sample with costs: **every config is negative.** Best: 1h, ATR×2.0
stops, ss=3 → −0.10R [−0.17, −0.04], n=950. The axes worked as predicted
(worst 15m config −0.90R → best 1h config −0.10R; wider stops and slower
bars cut cost drag ~9×) but the raw sweep-fade signal carries no edge that
clears zero. Conclusion: stop re-tuning this family; redesign the signal.
Full table: `smc-research/reports_out/strategy_research.csv` (regenerate
with `scripts/research_strategies.py`). Next: structurally different
hypotheses (trend alignment, limit entries at the swept level, exit design,
session filters, FVG/OB confluence, 4h) — multi-agent exploration in flight.

## Research finding (session 2) — read before recording the W5 video

First honest walk-forward run of the naive baseline (sweep-confirmation,
stop at the sweep extreme, 2R target, BTCUSD 15m, 2023→2026, 3,664 OOS
trades): **expectancy −0.63R [−0.67, −0.58], hit rate 31.4% [30.0, 32.9] —
the naive setup loses.** Decomposition: cost-free expectancy is +0.06R;
median stop distance is 27.7 bps of price vs ~15 bps round-trip costs, so
costs alone are ~0.55R/trade of drag. Conclusion: the signal concept has a
small raw edge, but stops at the sweep-bar extreme are uneconomically tight
on 15m. Next research steps, in order: (1) structural stops (beyond the
swept level + ATR buffer, not the bar extreme), (2) cost-aware filter (skip
setups with risk < k × round-trip cost), (3) 1h timeframe, (4) confluence
filters (OB/FVG context). This is exactly the finding the pipeline exists
to surface — do NOT publish product claims until a configuration clears
costs out-of-sample.

## Engineering decisions made this session

1. **Binance API is geo-blocked from cloud hosts** → deep history comes from
   the `data.binance.vision` public archive (monthly zips, CDN, works);
   Hyperliquid `candleSnapshot` serves the live tail (~5000-candle
   retention). Verified live 2026-07-28.
2. Golden-file fixture is **synthetic** (seeded, committed CSV, 5000 bars)
   rather than a real BTC slice: hermetic tests, no licensing questions, and
   regime-switching drift guarantees every detector fires. Real-data golden
   files can be added alongside once M3 caches real history.
3. vendor-ops uses SQLite for dev/tests, `DATABASE_URL` → Postgres in
   deploy. Alembic deferred until schema stabilizes.
4. Signal timestamps are always the **confirmation bar** (swings confirm
   `k` bars after the pivot). The Pine port uses the identical delay — this
   is what makes M4 parity achievable.

## Blockers needing YOU (can't be done from this session)

1. **Add repos to session scope** (say "add darkosedam-svg/ict-smc-detector"
   etc. in a Claude session) to: sync detectors to the public repo, add the
   Plan A W1 "Paid setup & customization" README blocks to all three public
   repos, and align Pro alert payloads with `tradingview-webhook-relay`.
2. **Create `smc-research` + `vendor-ops` private repos** (or ask Claude to
   once repo-creation scope is granted) and split the directories out.
3. **TradingView side of M1** (manual by design): compile `ict_smc_lite.pine`
   in the Pine editor, run the 5×3 visual pass, read House Rules + Script
   Publishing Rules in full, publish open-source by Mon 17 Aug.
4. **Plan A W1 business tasks** (not code): Lemon Squeezy store registration,
   Discord server, 60-target cold-email list, batch 1 of 20 emails,
   knjigovođa call. Deadline for W1 exit check: Mon 3 Aug.

## Next session (engineering priority order)

1. Strategy research per the finding above — a configuration that clears
   costs OOS gates the W5 video content.
2. EURUSD + ES/SPX data (drop Dukascopy/SPY CSVs into the csv_loader path,
   or build dedicated loaders) → 3-instrument report per plan.
3. Parity Pine variant script (plots the DEFAULT_COLUMN_MAP series) so a
   single TradingView export can be diffed.
4. M5 Pro script features (quality score, MTF filter, stats panel) once a
   viable configuration exists to encode.
