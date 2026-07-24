# General Internal Comms

> Default house format bundled with DeerFlow. Adapt section names, cadence, and tone to your organization's conventions — the structure below is the contract, the wording is yours.

## When to use

Any internal communication not covered by a more specific guideline: status reports, leadership/exec updates, project updates, incident reports, org announcements. This file carries the house style plus templates for the common types.

## House style (applies to everything)

1. **BLUF — bottom line up front.** The first line states the conclusion, decision, or ask. Detail follows for those who need it.
2. **Calibrate to audience.** Leadership gets outcomes, risks, and asks; peers get specifics and links. When in doubt, ask who's reading before drafting.
3. **State asks explicitly.** Every comm ends knowing what (if anything) the reader must do, by when. "FYI, no action needed" is a valid and kind ending.
4. **Honest posture.** Green is green, red is red. Bad news travels in the first paragraph, never buried in the fourth. No spin, no "learnings-washing" of failures.
5. **Scannable.** Headers, bold leads, short bullets. Assume a phone screen.
6. **Dates are absolute** (2026-01-15, not "next Friday"); owners are named.

## Status / project update

```markdown
# [Project] Status — [YYYY-MM-DD]

**Status**: 🟢 On track / 🟡 At risk / 🔴 Off track
**TL;DR**: [One sentence: where things stand and the one thing to know.]

## Since last update
- [Outcome-first bullet]

## Next
- [Committed item — owner — date]

## Risks & asks
- [Risk] — [impact if it lands] — **Ask**: [what you need, from whom, by when]
```

- A 🟡/🔴 status must explain what changed, the recovery plan, and the new date in the TL;DR block — not lower down.
- Status color is about the goal, not the mood: slipping the date while working hard is still 🔴.

## Leadership / exec update

```markdown
# [Area] Update for [audience] — [YYYY-MM-DD]

**Headline**: [The one-sentence takeaway you'd want repeated in their next meeting.]

**Wins**: [2–3 outcome bullets, each with a number or concrete artifact]
**Watch**: [1–2 risks with your mitigation — show you own them]
**Decisions needed**: [Explicit list with options + your recommendation, or "None."]
```

- Maximum one screen. Every extra scroll halves readership.
- Never surprise an exec in writing with something their team hasn't heard first — flag such items to the requester instead of sending.

## Incident report / postmortem

```markdown
# Incident: [short name] — [YYYY-MM-DD]
**Severity**: SEV[0-3] · **Status**: Resolved/Monitoring/Ongoing
**Duration**: [start] → [end] ([total]) · **Author**: [name] · **Reviewed by**: [names]

## Summary
[3–5 sentences: what broke, who/what was affected and how much, how it was
resolved. Written for someone with zero context.]

## Impact
- [Users/customers affected, requests failed, revenue/SLA effect — numbers]

## Timeline (all times [TZ])
- HH:MM — [detection: how did we find out?]
- HH:MM — [key decision/action]
- HH:MM — [resolution]

## Root cause
[The causal chain, plainly. "The deploy removed X, which Y depended on because Z."
Name systems and decisions, not people.]

## What went well / what went poorly
- [Honest bullets — include response process, not just the code]

## Action items
- [ ] [Preventive fix] — [owner] — [due date]
- [ ] [Detection improvement] — [owner] — [due date]
```

- **Blameless**: causes are systems, gaps, and pressures — never a person's name in the causal chain.
- Every action item has an owner and a date or it doesn't ship in the report.
- Severity, duration, and impact numbers come from the requester or monitoring — mark unknowns `[TBD]` rather than estimating.

## Announcement (org/process change)

```markdown
**What's changing**: [one sentence]
**When**: [date it takes effect]
**Why**: [1–2 sentences — the real reason]
**What you need to do**: [specific action + deadline, or "Nothing."]
**Questions** → [owner/channel]
```

## Content gathering

Before drafting any of the above, collect: audience, occasion/cadence, the facts (outcomes, numbers, dates, owners), known risks or bad news, and the asks. If the type genuinely fits none of these templates, ask what format the reader expects rather than inventing one.
