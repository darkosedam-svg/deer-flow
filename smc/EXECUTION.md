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
| M3 backtest + PDF report | **Mon 24 Aug** | ⬜ Not started — **critical path**, start next session (`engine/`, `stats/`, `reports/`) |
| M4 parity harness ≥98% | Mon 24 Aug | ⬜ Not started (needs a TradingView chart export; `parity/diff.py` next) |
| M5 Pro script | Mon 7 Sep | ⬜ Not started |
| M6 payment stack tested live | **Mon 14 Sep** | 🟡 Core scaffold done+tested: HMAC verify, idempotency, entitlements, grant/revoke queue, lifetime-immunity. Remaining: email/Discord workers, reconciliation, admin auth, live €1 test |
| M7 forward-test automation | Mon 28 Sep | ⬜ Not started |

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

1. M3 backtester: event-driven engine, next-bar-open entries, per-instrument
   costs, walk-forward splitter — this gates the W5 demo video.
2. M3 stats: hit rate, avg R, expectancy, PF, max DD, bootstrap 95% CIs.
3. M4 `parity/diff.py` (consumes a TradingView CSV export you produce once).
4. Real-data cache warm: `load()` BTCUSD 5m/15m/1h 2023→now via archive.
