---
name: review-representation
description: "Called during output evaluation to assess whether a document communicates the supported strengths intended by its saved brief. Also use directly to review representation; distinct from factual validation and the cold recruiter screen."
---

# Review career representation

Read `docs/editorial-memory.md`. First read only the artifact and record concise
`reader_impressions`. Then read its pinned brief, selection, relevant decisions,
the ready resume plan when present, and eligible career evidence, including
alternatives omitted from the selection.
This staged reading reduces priming; do not describe it as an independent cold
review if the context already knows the pack or wrote the document.

For every strength in the brief, record exactly one status:
`clearly_represented`, `inadequately_represented`, `intentionally_omitted`,
`withheld`, or `unsupported`. For clear representation, cite supporting atoms and
an exact artifact excerpt. Judge the meaning: an atom ID or keyword appearing in
the document does not prove its strength is communicated. A bullet can preserve
an achievement's citation while deleting the contribution that made it useful.

Compare the whole document with its intended reader impressions. Look for lost
sole examples, redundant achievements, disproportionate space, obsolete emphasis,
and loss of contribution or ownership during compression. Do not require every
career strength on every output. Respect audience, direction, length and recorded
tradeoffs. Private evidence may explain withheld/unsupported status privately;
it cannot supply an external claim through this review.

Write a review body in `data/private/<artifact-stem>-representation-body.json`
using `schemas/representation-record.schema.json`, omitting `run`. Assemble the
sidecar with `scripts/save_review.py` as described in `docs/editorial-memory.md`.
Use the exact saved manifest file shared with the integrity evaluation; never
copy or retype its hashes. Each finding needs severity, category, message, affected
strength/section and remediation. Run `validate_records.py` on the record.

For inadequate representation, revise within eligible evidence or explicitly
revise the selection with a justified omission decision. Missing or withheld
support remains a reported limit. Do not ask the user to resolve routine editorial
choices during quiet delivery. Never relax evidence rules to obtain a passing
review. After edits, review the final artifact again and update all hashes.

For each plan impression, write an `impressions` row with `impression_id`, status,
evidence IDs, exact artifact excerpt and reason in the representation sidecar.
Compare what the reader actually understood with the
intended message and cite the passage that establishes it. Include findings for
unsupported or inadequately conveyed impressions even when no strengths profile
exists. Inspect related atoms for repeated projects and double-counted results.
After shortening, examine the revision report for lost contribution, ownership,
method, timeframe or scope. Record uncertainty instead of inferring semantic truth
from a citation or an automatic qualifier check.

For planned resumes, complete the `prominence` rows in the exact-draft process
record described in `docs/resume-process.md`. Compare the intended leading or
supporting emphasis with the initial reader observations, locate the passages and
explain their salience. A leading strength buried in a dense bullet is inadequate
even when its citation and excerpt are present. Keep this judgment consistent
with the representation sidecar. Do not invent reader observations after seeing
the plan or call shared context independent.
