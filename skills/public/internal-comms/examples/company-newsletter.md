# Company Newsletter

> Default house format bundled with DeerFlow. Adapt section names, cadence, and tone to your organization's conventions — the structure below is the contract, the wording is yours.

## When to use

Recurring company-wide (or org-wide) digest: monthly or bi-weekly. Goal: everyone finishes it in under 3 minutes and knows what mattered.

## Format

```markdown
# [Company/Org] Newsletter — [Month YYYY]

## The Big One
[2–4 sentences on the single most important development this period.
Why it matters, not just what happened.]

## Highlights
- **[Team]** — [One-line win with the concrete outcome or number]
- **[Team]** — [...]
- **[Team]** — [...]

## Coming Up
- [Date] — [Event/launch/deadline and what's expected of readers, if anything]
- [Date] — [...]

## Kudos
- [Name/team] for [specific thing — what they did and the effect it had]

## One Number
**[Metric]**: [value] ([direction vs last period]) — [one line on why it moved]
```

## Rules

1. **One "Big One" only.** If everything is important, nothing is. The rest goes to Highlights.
2. **Highlights are one line each,** team-attributed, outcome-first. 4–7 items; rotate teams across issues so the same three teams don't dominate.
3. **Kudos are specific.** "For debugging the checkout outage at 2am" — never "for being awesome".
4. **Coming Up items state the reader's obligation** (attend, review, migrate, nothing) so nobody has to guess.
5. **Tone: warm, plain, zero corporate filler.** Write like a sharp colleague, not a press release. Contractions are fine. Exclamation points: one per issue, maximum.
6. **Everything scannable.** Bold the lead of each bullet; no paragraph longer than 4 sentences.

## Content gathering

Collect before drafting:
- Candidate items from each team (or mine recent 3P updates / release notes if provided)
- The one company-level story worth "The Big One"
- Upcoming dates: launches, all-hands, deadlines, onboarding cohorts
- Shout-out nominations, with the specific act
- One company metric the audience is allowed to see, with prior-period value

If material is thin, shrink the issue — never pad. A short newsletter that's all signal beats a long one that isn't.

## Example (abbreviated)

```markdown
# Acme Monthly — January 2026

## The Big One
We signed Northwind — our largest customer to date. Beyond the revenue, it
validates the enterprise SSO work three teams carried through Q4. Rollout
starts in February; expect Northwind-specific load tests on staging.

## Highlights
- **Platform** — Cut CI time from 24 to 9 minutes; everyone gets ~an hour/day back
- **Mobile** — 4.8★ average after the offline-mode release
- **Support** — First-response time under 2h for the first time ever

## Coming Up
- Feb 3 — All-hands (roadmap review; no prep needed)
- Feb 10 — Password manager migration deadline — action required, see IT's guide

## Kudos
- Sam T. for rewriting the flaky payments test suite nobody wanted to touch

## One Number
**Weekly active teams**: 412 (+9%) — driven by the template gallery launch
```
