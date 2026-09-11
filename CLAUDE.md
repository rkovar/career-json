# career.json

This repository is a Claude-native career evidence and artefact workspace. Claude is the primary operator. Do not introduce a web application, API provider integration, database, or Python dependency unless the user explicitly asks for one.

## Component boundaries

One repository contains Career Evidence Core (early access) and Resume Application
(beta). See `docs/releases.md`. The core must run without resume modules. Core
intake, validation, sources, facts, supported strengths and preferences are shared
contracts; role targeting, briefs, selections, output decisions, writing and reviews
belong to the application. New facts discovered during generation return through
core review. Never treat a generated document as a factual update automatically.
Use `career_core.py` for core status, migration, reassessment and private export.
Existing `editorial.py` core commands remain compatibility entry points. Release
builds use explicit public allowlists and do not touch data, outputs or reviews.

## Mission

Keep one durable, evidence-backed record of a career in `career.json`, and treat resumes, CVs, cover letters, and websites as disposable projections of it. The record is the product. Two failure modes drive the design: the user forgets what they did, and they have too much to fit any single document.

## Non-negotiable rules

1. Never invent employers, dates, titles, metrics, responsibilities, qualifications, certifications, awards, or outcomes.
2. Use the STAR method for substantive achievement claims: Situation, Task, Action, Result.
3. Every generated claim must reference one or more evidence IDs in the datapack.
4. Challenge weak, vague, inflated, or consequential claims with Socratic questions before treating them as resume-ready.
5. Distinguish `self_asserted`, `corroborated`, `externally_verified`, `unresolved`, and `declined` evidence. A claim repeated across the user's own resume, LinkedIn profile, and personal site is `self_asserted`. Repetition is not corroboration. `self_asserted` is the normal resting state: corroboration is an optional signal, never a requirement, and its absence is not a defect. Do not chase it unless the user asks.
6. Do not publish evidence marked `external_safe: false`.
7. Preserve conflicting source values. Do not silently choose a convenient number or date.
8. Keep PII in the private profile section and never expose it in public artefacts unless the user explicitly requests it. A resume sent to a named recipient is not a public artefact and carries a full contact block; a website or published CV is, and carries name and location only.
9. Never put draft status, publication warnings, or notes about withheld evidence inside an artefact. Status belongs in the evaluation record.
10. Record what a claim is worth as well as whether it is true: whether it measures activity, output, or business outcome. Employers, titles, and dates must trace to an `employment` record, because those are what a background check tests.
11. Run the evaluation skill, then the recruiter screen, before calling any artefact publishable. Integrity and shortlistability are different properties and both are required.
12. If evidence is incomplete, say so plainly. A careful gap is better than polished fiction.

## Workspace layout

- `schemas/`: canonical JSON Schema.
- `examples/`: committed, fully fictional format examples only. Never place real personal or employer material here.
- `data/sources/`: user-provided source material. Treat as private.
- `data/packs/`: versioned career datapacks.
- `data/private/`: private profiles and other personal working files. Treat as private.
- `reviews/`: Socratic questions, answers, conflicts, and approval records.
- `outputs/`: generated drafts and evaluation reports.
- `.claude/skills/`: reusable Claude workflows.

Create private working directories only when needed. Do not commit raw PII or generated personal artefacts unless the user explicitly wants them tracked.

## Operating sequence

1. Inspect source material and identify provenance.
2. Extract candidate evidence without upgrading its confidence.
3. Ask Socratic questions for missing STAR fields, ownership, scope, timeframe, measurement, or corroboration.
4. Record answers and unresolved gaps in `reviews/`.
5. Produce or update a versioned datapack.
6. Prepare or reuse a durable output brief and scoped selection; select evidence against the requested role, supported strengths, preferences and modifiers.
7. Generate the requested artefact using STAR-grounded claims.
8. Evaluate factual grounding, privacy, ATS coverage, length, and anti-slop quality.
9. Screen the artefact as a recruiter and hiring manager would, and return a shortlist verdict.
10. Mark the artefact publishable only when the evaluation passes. Publishable means fit to send, not likely to succeed.

This sequence runs as two phases, and the difference between them is deliberate.

- Setup, occasional: `build-career-pack` covers steps 1 to 5. Questions are
  expected here and are batched at the end of the run.
- Delivery, repeated: `make-resume` covers steps 6 to 10. It asks nothing. Thin
  evidence narrows or drops a claim; it never produces a question in place of a
  document.

Front-loading questions into setup is what keeps delivery quiet. Neither phase
relaxes the evidence, privacy, or publication rules above.

## Claude behaviour

Use the skills in `.claude/skills/` when their trigger applies. Keep questions focused and explain why a claim needs support. Do not ask the user to repeat information already present in the datapack or source material.

## Durable editorial context

Use `docs/editorial-memory.md` for schema 1.4 strengths and preferences, resumable
`review-strengths`, optional `review-selection`, and `review-representation`.
Briefs and selections live in private data directories; decisions live in reviews.
Generated documents are never new evidence merely because the system wrote them.
Delivery remains quiet; evidence preview is a separately requested workflow.


## Human review of proposed data

Use `docs/pack-review.md`. Unreviewed extraction and corrections live in
`data/candidates/`; they must not become current by being written to `data/packs/`.
Present the private readable review and save only explicit user decisions. Exact
wording acceptance, evidence confidence and external-use permission are separate.
The review helper saves accepted local pack versions and preserves deferred items,
correction notes and omission feedback. Never fill in approvals for the person.
