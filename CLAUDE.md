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
8. Keep PII in the private profile section and never expose it in public artefacts unless the user explicitly requests it. A resume sent to a named recipient is not a public artefact and carries a contact block appropriate to employer instructions (including anonymous applications); a website or published CV is, and carries name and location only.
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

1. Reuse supplied context or run a resumable startup wizard, then inspect sources and provenance. Distinguish career evidence from job descriptions and writing references.
2. Extract candidate evidence without upgrading its confidence.
3. Show the proposed record, then ask focused questions only where accuracy or conflicting claims need clarification. Leave optional enrichment for later.
4. Record answers and unresolved gaps in `reviews/`.
5. Stage the proposal, present human review, and save only explicitly accepted items in a new datapack version.
6. Prepare or reuse a durable output brief, scoped selection and resume plan; select complementary evidence for the role and supported strengths.
7. Generate the requested artefact using STAR-grounded claims.
8. Evaluate factual grounding, privacy, ATS coverage, length, and anti-slop quality.
9. Screen the artefact as a recruiter and hiring manager would, and return a shortlist verdict.
10. Mark the artefact publishable only when the evaluation passes. Publishable means fit to send, not likely to succeed.

This sequence runs as two phases, and the difference between them is deliberate.

- Setup: `build-career-pack` covers guided intake, extraction and human review.
  Show the overview first, present five decisions at a time, and preserve
  corrections and deferred items. Evidence and strengths interviews ask focused
  follow-up questions; the person can pause without losing progress.
- Delivery: `make-resume` reuses the accepted pack and saved context. The resume
  wizard fills missing targeting information. Honor automatic or interactive
  review mode; requested review waits for the person's response. Automatic
  delivery narrows thin evidence and reports gaps. New facts return through Core.

Do not repeat answered questions or infer approval from silence. A saved startup
answer is neither factual acceptance nor external-use permission. Neither phase
relaxes the evidence, privacy, or publication rules above.

## Claude behaviour

Use the skills in `.claude/skills/` when their trigger applies. Keep questions focused and explain why a claim needs support. Do not ask the user to repeat information already present in the datapack or source material.

## Durable editorial context

Use `docs/editorial-memory.md` for schema 1.4 strengths and preferences, resumable
`review-strengths`, optional `review-selection`, and `review-representation`.
Briefs and selections live in private data directories; decisions live in reviews.
Generated documents are never new evidence merely because the system wrote them.
Resume generation follows `docs/resume-authoring.md`: create a typed application
brief and ready plan, offer first-time selection/voice review, and honor explicit
automatic delivery. Every resume requires verified PDF, TXT and DOCX exports
from shared content before being called publishable.


## Human review of proposed data

Use `docs/pack-review.md`. Unreviewed extraction and corrections live in
`data/candidates/`; they must not become current by being written to `data/packs/`.
Present the private readable review and save only explicit user decisions. Exact
wording acceptance, evidence confidence and external-use permission are separate.
The review helper saves accepted local pack versions and preserves deferred items,
correction notes and omission feedback. Never fill in approvals for the person.

## Career creation and maintenance defaults

Honor the requested source scope; use `career_core.py intake` to inventory it.
Skip byte-identical sources and compare new material with stable existing IDs.
Show the full readable proposed career before follow-up questions. Review roles
once and complete achievements in batches of five, with supporting detail available.
Use `review open` for the temporary local browser connection, or conversation
choices through `review apply`. Offline decisions remain supported.

This stdlib loopback review connection is supported; do not add a hosted web app,
database, model-provider integration or new Python dependency without a request.
Literal corrections use `review correct`; structural corrections use recorded
answers and `review revise`. Show revised wording before acceptance and carry
unchanged approvals. Source registration is never human factual approval.

A useful saved private record is the first milestone. Contact details, strengths,
publication permissions, richer outcomes and corroboration are optional later work.
Prioritize factual accuracy and conflicts. `open_questions.py` defaults to that
queue; use `--optional` for enrichment or `--application` for resume diagnostics.
Quick capture saves supplied notes without an interview. Keep recurring updates
short: only review meaningful changes, then show the saved reading view.


Use `docs/questions-and-updates.md` for durable scoped questions, strength
reassessment, shared summary and recovery. Record questions before asking and
answers before proposing changes. Saved answers are evidence, never automatic
wording acceptance. Use `career_core.py health --summary --json` for a quick state
view, `view` for the saved career record and `recover` after interruption.
