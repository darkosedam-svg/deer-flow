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
