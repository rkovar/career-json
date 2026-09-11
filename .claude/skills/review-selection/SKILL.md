---
name: review-selection
description: "Use when the person requests an evidence preview or wants to choose achievements for an output. Explains a ranked recommendation with alternatives and records scoped choices. Optional before make-resume; never an unsolicited delivery checkpoint."
---

# Review the proposed evidence selection

Read `docs/editorial-memory.md`. Use or create a durable output brief, then run
`editorial.py prepare`. The result is a candidate retrieval baseline, not a final
editorial recommendation. Use `select_evidence.py --selection` for safe content;
read the private pack and decisions only for planning, never copy private reasons
or unsupported strength interpretations into a generation-facing instruction.

Evaluate the whole set against requirements, the person's relevant strengths,
future direction, evidence limitations and available space. Explain marginal
contribution: what each example establishes that the other selected examples do
not. Recency, outcome type and corroboration are signals, not universal priority
rules. An older or unmeasured achievement may be the strongest proof of a relevant
capability. A set may reasonably omit a strength with a saved explanation.

Save a new selection version with a small recommended set and useful alternatives.
For each candidate, record `recommended`, `reserve`, or `omit`, with a reason,
contribution, limitations, and any candidate it would replace. Rank for this
brief; do not show numerical scores as career value or interview probability.
Read every candidate's allowed evidence before deciding. Do not invent tradeoffs
merely to fill the record.

Report `unavailable_priorities` and `strength_readiness` privately; an inclusion
preference cannot make evidence eligible. Present the recommendation and alternatives, offering acceptance of the whole
set or corrections. Wait only because the person requested this review. In the
normal make-resume path, make the selection autonomously and report it afterward.

Record the person's answer verbatim. Acceptance sets `review_status: accepted`
and cites its person source; it does not confirm requirement-to-evidence links.
For individual choices save decisions with explicit scope, subject, reason,
source and author. A correction to contribution goes through evidence review;
publication restrictions update the atom; future direction updates preferences.
An omission for this application stays in this application. Never infer a
role-family or person-wide rule from one choice.

Use explicit supersession to change an old decision. System decisions cannot
override user decisions. Rebuild the selection after changing applicable decisions,
then validate. This workflow never rewrites factual evidence merely to make a
preferred selection look supported.
