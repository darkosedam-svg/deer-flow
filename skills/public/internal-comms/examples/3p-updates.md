# 3P Updates (Progress / Plans / Problems)

> Default house format bundled with DeerFlow. Adapt section names, cadence, and tone to your organization's conventions — the structure below is the contract, the wording is yours.

## When to use

Weekly (or sprint-cadence) team updates that keep peers and leadership informed without a meeting. One update per team or workstream.

## Format

```markdown
# [Team/Project] 3P Update — [Week of YYYY-MM-DD]

**TL;DR**: One sentence: the single most important thing this week.

## Progress
- [Shipped/completed item — start with a verb, include the concrete outcome]
- [Metric moved: X went from A to B]
- [Milestone reached, with link to artifact/PR/doc]

## Plans
- [What will be done by next update — specific and checkable]
- [Owner named if not obvious: "Alex lands the migration"]

## Problems
- [Blocker or risk — say what you need and from whom]
- [If nothing: "No blockers." Never omit the section.]
```

## Rules

1. **Bullets, not paragraphs.** Each bullet is one line, two at most.
2. **Lead with outcomes, not activity.** "Shipped X" beats "worked on X". If it's not done, it belongs in Plans.
3. **Problems are requests.** Every problem names what would unblock it and who can help. A problem without an ask is a status, not a problem.
4. **Plans must be checkable.** Next week's Progress should be verifiable against this week's Plans. Carry-overs are flagged: "(carried from last week)".
5. **3–5 bullets per section.** More means you're listing tasks, not signal.
6. **No jargon walls.** Assume a smart reader from a different team.

## Content gathering

Before drafting, collect from the requester (or the conversation):
- What actually shipped/finished this period (with links if available)
- What's committed for next period, and who owns each item
- Anything blocked, at risk, or needing a decision — and the specific ask
- Any metric worth reporting (before → after)

If Progress is empty, say why in one honest line (e.g. "Heads-down week on the migration; no user-visible changes").

## Example

```markdown
# Payments Team 3P Update — Week of 2026-01-12

**TL;DR**: Refund pipeline is live in prod; chargeback backlog is our main risk.

## Progress
- Shipped the automated refund pipeline — median refund time 3.2 days → 4 hours
- Closed 14 of 20 chargeback backlog cases
- Finished PCI audit prep doc (link) — review scheduled Thursday

## Plans
- Priya lands retry logic for failed refund webhooks
- Clear remaining 6 chargeback cases
- Dry-run of the PCI audit with Security

## Problems
- Chargeback volume is growing 8%/week; we need a decision from Risk on the
  auto-dispute threshold by Friday or the backlog reopens — ask: 30 min with Dana
```
