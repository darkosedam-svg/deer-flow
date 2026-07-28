# pine

Pine scripts for the indicator product. **Python (`smc-research`) is the
source of truth** — these are ports, kept honest by the parity harness
(Plan B M4). Any semantic change lands in Python first.

```
lite/ict_smc_lite.pine   → publish OPEN SOURCE on TradingView (M1, by Mon 17 Aug)
pro/                     → invite-only, protected source (M5) — not started
lib/                     → shared drawing plumbing library (optional) — not started
presets/                 → generated from smc-research/presets — not started
```

## M1 publication checklist (Lite)

Pre-publication (all must pass — a ban kills Track B permanently):

- [ ] Read TradingView **House Rules** and **Script Publishing Rules** end to
      end, once, in full.
- [ ] Load on 5 instruments × 3 timeframes (BTC, ETH, EURUSD, SPY/ES, one
      more × 5m/15m/1h): no runtime errors, no "max objects" warnings,
      loads < ~3 s on a 20k-bar chart.
- [ ] Verify **no repainting**: bar replay, confirm no historical signal
      moves. All signals confirm on bar close by construction — verify anyway.
- [ ] Description: honest explanation of method. **Zero mention of any paid
      version, no sales links, no teaser framing, no performance claims.**
- [ ] Educational / not-financial-advice disclaimer in description.
- [ ] Replace `© [your TradingView username]` in the header.

Known port-fidelity notes (for the parity harness):

- `ta.pivothigh/pivotlow` confirm swings `swingStrength` bars after the
  pivot — same delay as Python `StructureDetector`.
- OB displacement baseline is `ta.sma(|body|, 20)[1]` — prior 20 bars,
  current bar excluded, matching Python's deque-then-append order.
- Sessions anchor to UTC via `time(tf, session, "UTC")`, never
  `syminfo.timezone`.

## Verification status

- [x] Ports Python detector semantics 1:1 (by construction, reviewed)
- [ ] Compiled on TradingView (cannot be done from this environment — paste
      into the Pine editor)
- [ ] 5×3 instrument/timeframe visual pass
- [ ] Parity diff vs Python ≥98% (M4 harness, not yet built)
