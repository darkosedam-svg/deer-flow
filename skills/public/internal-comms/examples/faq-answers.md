# FAQ Answers

> Default house format bundled with DeerFlow. Adapt section names, cadence, and tone to your organization's conventions — the structure below is the contract, the wording is yours.

## When to use

Answering recurring internal questions: policy, process, tooling, benefits, "how do I…". Output is either a single answer or an FAQ document compiling several.

## Format — single answer

```markdown
**Q: [The question, phrased the way people actually ask it]**

[Direct answer in the first sentence — yes/no/the actual value/the actual step.]
[1–3 sentences of essential context or caveats, only if they change what the
reader does.]

[Optional: numbered steps if there's a procedure.]

→ Canonical source: [link or doc name] · Owner: [team/role]
```

## Format — FAQ document

```markdown
# FAQ: [Topic]
_Last updated: [YYYY-MM-DD] · Owner: [team]_

[Group questions under H2 headings by sub-topic if more than ~6 questions.]

**Q: ...**
[Answer]

**Q: ...**
[Answer]
```

## Rules

1. **Answer first.** The first sentence resolves the question. Context comes after, never before. Nobody should read three sentences to find out the answer is "no".
2. **Write the question as asked,** not as the policy names it ("Can I expense my home internet?" not "Remote connectivity reimbursement eligibility").
3. **One question, one answer.** If the answer forks ("it depends on X"), split into two questions or use a short bullet fork — never a wall of caveats.
4. **Steps are numbered, verbs first.** "1. Open the portal. 2. Select…"
5. **Every answer names its source of truth** (the canonical doc/policy) and an owner, so readers know where to verify and who to ask when the FAQ is stale.
6. **Honest edges.** If something is unknown or in flux, say so and point to the owner — never guess policy into existence.
7. **Tone: helpful desk-mate.** Plain words, no legalese unless quoting policy verbatim (then quote it and mark it as a quote).

## Content gathering

Collect before drafting:
- The actual questions (verbatim where possible — from chat, tickets, or the requester)
- The authoritative answer for each, from the requester or a linked policy/doc
- Who owns each policy/process, and where the canonical doc lives
- Any known exceptions worth naming (and which ones to deliberately leave out)

Flag any answer you were not given a source for as `[verify with owner]` rather than presenting it with confidence.

## Example

```markdown
**Q: Can I expense my home internet?**

Partially — up to $40/month for fully-remote employees. Hybrid employees are
not eligible. Submit it as a recurring expense once; it auto-renews monthly.

1. Open Expensify → New Expense → category "Remote stipend".
2. Attach any bill from the last 90 days.
3. Set "recurring: monthly" — one submission covers the year.

→ Canonical source: Remote Work Policy §3.2 · Owner: People Ops
```
