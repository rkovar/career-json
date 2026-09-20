---
name: build-career-pack
description: "Build or extend a career datapack from source material, apply user-supplied review decisions, or continue a saved career-pack review. Also checks workspace health, explains achievement history, prepares reviewed merge/split/refresh proposals, and backs up or restores a career workspace. No target job is required."
---

# Build my career pack

## Purpose

Turn source material into a durable career record. Review evidence here so later
applications can reuse it. Resume-specific direction and choices belong in their
own brief.

Run `ingest-career-materials`, finish the proposal and its readable overview, then
help the person confirm useful work. Use `review-evidence` for specific factual
uncertainties, not a compulsory interview before the first save. Do not ask the user to operate the scripts.

## Guided start

Use **Build my career pack** as the user-facing path label. The `make start` launcher
routes here. For a named saved setup, resolve its latest revision and reuse its
answers or completed handoff. At a pause/handoff, show what is saved, the next
step and the exact `continue_prompt` from the startup report with the summary link.

For an uncertain first start, help gathering material, or a wizard request, follow
`docs/operators/career-start.md`. Inspect the workspace and relevant saved sessions;
reuse supplied choices, ask at most five concise prompts, and save each answer
with its readable summary. Offer existing material, a source checklist, or a
conversational account. Keep none, not-applicable, later and skipped distinct.

Honor explicit source scope without asking it again. Specific imports, quick
capture, maintenance and existing evidence reviews keep their direct paths.
Use the startup handoff's career-source list and user accounts for ingestion.
Keep job descriptions and writing guides as context. Preserve category deferrals
and restrictions when preparing later questions. Setup is not factual acceptance
or permission for external use.

## First session and returning reviews

Follow `docs/operators/first-pack.md` for the short conversational path. With no existing
pack, start from the one source the person supplied; do not request their full
archive or a target job. If they explicitly supplied a larger scope, honor it.
Keep the first pack private. Extract name/location when present; defer requests
for email, phone and external-publication choices until they are needed.

Present the review-page link, a short career timeline and recorded contributions
before asking questions. Describe supported observations without inventing a
career narrative. Offer one useful question; allow the person to stop after a
few accepted achievements. An unmeasured result, architectural judgment, incident
prevention or mentoring can be valuable without a fabricated financial outcome.

When the person says “apply my saved review decisions,” use the exact file they
supplied. Copy it into `data/private/` if needed, then run `career_core.py review
apply --input <file>`. The file identifies its session.
Never fill in supporting-record approvals yourself. If acceptance is blocked,
show the relevant unresolved supporting records for review, preserve the decisions
and explain what remains. Rerender the page after applying decisions.

For “continue my career-pack review,” run `career_core.py review resume`. Use the
session named in the conversation, or the sole unfinished session. If several
are plausible, ask which one; do not create another proposal merely to resume.
Use `review open --session <session> --open` for a temporary connected review.
The page saves directly into the pack and refreshes its readable view. Keep the
connection alive while the person reviews; offline downloads remain available.
Literal role/achievement edits use `review correct`; structural corrections use
recorded answers and `review revise`. Show exact revised wording for confirmation.
Reuse unchanged decisions with their original receipts and prior answers.
See `docs/pack-review.md` for these shared browser/conversation operations.

End with the saved roles/achievements, pending corrections/questions and a clear
stopping point from the review summary. Counts do not establish completeness.
Offer one recall example from the accepted pack: a recorded contribution plus
its original source. If nothing is accepted yet, explain that the proposal is
saved and identify the records needed for the first coherent acceptance.

For a first session, use a compact handover: the clickable review-page link,
timeline and two contributions, at most one question, and the stopping point.
Keep full validation counts, IDs and file inventories in the review record rather
than duplicating them in the conversation. Explain errors that block saving;
missing email/phone or an unmeasured business outcome are not first-pack defects.
The detailed final-report checklist below applies to broader intake runs.
After rendering the first-session page, run `career_core.py review handover
--session <session-path> --page <rendered-page-path>` and return that grounded
handover without extra validation tables, connector notes or file inventories.
If the person wants to interview now, follow it with one answerable question.

## Inputs

- new or changed material within the explicit request or saved startup scope; inspect all `data/sources/` only when that broader scope is requested
- the current pack, if one exists (resolve its supersedes chain with `current_pack.py`)

## Workflow

1. Run `career_core.py intake <authorized-path>` and `ingest-career-materials`.
   Inspect all authorized new material before starting review. Report duplicates,
   unchanged sources and extraction failures. Classify ambiguous text by content;
   advice and job context never become career facts. Use existing extraction tools.
   For a large archive, save a valid partial candidate and staged review after the
   first useful source, then revise it as subsequent batches are inspected. State
   which sources remain in the handoff. Do not hold the entire reconstruction in
   conversation memory until the end. These checkpoints are proposals, never
   accepted packs; finish the authorized inventory before presenting final review.
   Follow the intake report's `reading_batches`; read oversized sources in sections.
   Keep writes bounded too: derive the next candidate from the saved proposal and
   apply a small coherent set of record changes with `review revise --changes`
   (see `docs/pack-review.md`). Supply changed top-level fields keyed by collection
   and ID; omitted records and fields are preserved. New records need their
   required fields and sources. Use this existing command before writing a custom
   helper script. Do not re-emit every unchanged record in one large model write.
   Write and execute one small update at a time; a script containing several
   future batches is not a checkpoint until it runs. Validate and stage each
   useful batch before writing the next update. A larger time budget
   does not replace these checkpoints; resume from the last valid saved batch.
   Chain each revision from the session just returned, including repairs to a
   batch, so an abandoned draft does not become an accidental review branch.
   Staging reports validation warnings directly while keeping the session path
   on standard output. Use that result; inspect the saved session or runtime
   implementation only when a warning or error needs investigation.
   If a helper captures subprocess output, also surface standard error so it
   does not hide the staging warnings.
   These are reading limits, not permission to omit later material. Continue from
   the saved proposal and remaining source paths after each checkpoint.
2. Compare with the current pack; preserve IDs, facts, unknowns and conflicts.
   Include supplied presentation preferences in `positioning_preferences`; optional
   strengths discovery does not mean discarding intent the person already gave.
   Do not create another proposal when nothing meaningful changed. New notes may
   remain quick captures until the person wants to review them.
3. Write the complete proposed pack to `data/candidates/`, validate with
   `python3 scripts/validate_pack.py <candidate-path>`, and create a default grouped
   review. Never edit historical packs or make unreviewed extraction current.
   Before staging, check that every explicit direction, presentation preference
   and privacy boundary supplied by the person is retained in the appropriate
   record, not only in metadata or a chat summary. `positioning_preferences`
   uses `status: active` for current intent; that does not approve the candidate.
   A supplied first-person written account is a legitimate pinned `person`
   source. Do not ask for the same preference again merely to create a chat log.
   Run the answer-to-candidate reconciliation in `docs/questions-and-updates.md`
   before final handoff. Review claim meaning across all affected fields and
   dependent records, not just excerpt matches or question-import counts.
4. Present the readable overview, then roles once and complete achievements in
   batches of five. Supporting source excerpts remain available. Verifiable source
   metadata is registered automatically with an import receipt, never a fabricated
   user decision. Other source changes remain reviewable.
5. Save the actual supplied choices and show what is saved versus pending. Source
   integrity and factual support still matter; optional enrichment must not delay a
   useful private pack. Accepted versions preserve `metadata.supersedes`.
6. `python3 scripts/open_questions.py --pack <candidate-path>` collects accuracy
   questions. Start with consequential uncertainty, conflicts and ownership; allow
   unknowns and deferrals. The queue is how questions are *collected*, never how they are *asked*.
   Ask one answerable follow-up at a time only when it helps the requested review.
   Do not fill atom `open_questions` with optional dates, extra outcomes, metrics
   or coaching prompts. Store those as `kind: enrichment, required: false` in
   question history only when useful. Honest unknowns and approximate dates do
   not need another interview before saving. An explicit presentation preference
   can be retained as a preference without asking whether it is a factual claim.

## Durable strengths and direction

After saving useful career facts, offer `review-strengths` as an optional later
conversation. It can prepare supported interpretations and a resumable queue.
Do not start it automatically or require it before accepting a career record. Read
`docs/core-workflow.md` for schema 1.4 migration and storage. Preserve existing
strengths, preferences, rejected interpretations and answer references in every
new pack version. Changed supporting atoms make interpretations stale until
reassessed. Never recover factual authority from a previously generated document;
trace its claims back to source evidence before importing anything new.

## Accuracy first; enrichment later

Ask about ambiguous ownership, conflicting dates or numbers, and unsupported
assertions that affect the accuracy of the recorded claim. Distinguish the client
from the employer_of_record when sources make that ambiguous. Preserve source-grounded
facts with honest limits. An unknown or unmeasured outcome need not invalidate the
known contribution. A role can remain a timeline entry with no achievements yet.

Use `open_questions.py --optional` only for a requested enrichment pass: additional
outcomes, missing dates, richer scope, or itemising public work. Extract public-work
items already present in authorized sources; do not demand an extra catalogue.
Use `--application` only for target-role or resume questions.

**Corroboration is optional and off by default.** `self_asserted` is normal.
Record volunteered support; do not seek third-party confirmation unless requested.
Classify known outcomes as activity, output or business_outcome without inventing
metrics. Commercial consequence, publication permission and role_fit_notes are
useful when relevant, never first-pack completion requirements.

## Importing an annual write-up

An end-of-year self-review is the largest capture event of the year, and it has
properties a generic document import does not.

1. **Establish the review period first** and set `capture.review_period` on every
   atom it produces, with `capture.method` set to `annual_review`. Next year's
   import uses this to know what it has already seen.
2. **Check for duplicates before adding anything.** Run
   `python3 scripts/dedupe.py --text "<claim>"` for each substantive claim. A
   write-up restates continuing work, and the second year of a programme belongs
   in the existing atom as a stronger Result, not in a new atom that splits the
   evidence.
3. **Set `occurred` from the review period**, narrowed to the actual month where
   the document says so. Do not inherit the employment window when the write-up
   gives you something better: an inferred nine-year span is barely a date.
4. **Default `external_safe` to false.** A self-review is written for an employer
   and is full of internal system names, ratings, and org detail. Ask which claims
   may be used externally only when external use is requested. Preserve useful
   private details in the pack and keep them out of external projections.
5. **Sweep the capture notes at the same time.** Run
   `scripts/capture.py --list`: the user is already in a remembering frame of
   mind, which is the cheapest moment all year to promote notes.
6. Performance ratings, manager comments, and calibration language are private
   signals. Record them only if asked, always `external_safe: false`, and never
   let them reach an artefact.

## Contact details

`private_profile` is optional for career capture. Contact details may be needed
for a later sendable resume; they are not required for saving career facts.

On the first run, extract what the source contains into `private_profile` without
inventing missing values. Name/location are enough for private career capture;
when the person wants a sendable document, queue any needed email, phone, LinkedIn
or website details. Never ask for a street address or a photo; record them only
if the user supplies them unprompted, and never place either in an artefact.

Set `publication_policy` to private by default: the full block appears on a
document sent to a named recipient, name and location only on anything public.

## Question policy

- Finish ingestion and the readable proposal before follow-up questions.
- Prioritize accuracy and conflicts; describe the fact a question would clarify.
- Never re-ask settled answers or deferrals from the pack or review history.
- Never invent an answer or soften a question so an unsupported claim passes.
- Unknown facts can remain open. Mark genuinely uncertain claims `unresolved`;
  optional missing detail alone does not make known facts false.
- Stop when useful work has been saved or whenever asked. Preserve pending work.

## Answering

When the user answers in a later message, re-run review for the affected atoms
only. Do not re-ingest unchanged sources. Answers are user assertions: record them
as `self_asserted`, regardless of how confidently they were given. Promotion to
`corroborated` needs a named third party or public artefact; promotion to
`externally_verified` needs that source recorded, per `review-evidence`.

## Readiness and final report

End with what was saved, what changed, what remains uncertain and the reading-page
link. Offer one recall example with its original source. A private pack containing
self_asserted achievements is useful; no target job, complete profile, financial
metric, publication permission or strength interpretation is required.

For a broad import, keep the source inventory and detailed validation in the review
record. Explain actual conflicts and save blockers in conversation. Optional gaps
can wait. Do not assess resume readiness unless the person requests that output.

## Human review checkpoint

The deliverable is the proposed pack, its private readable review page and a
concise change summary. Show where the person can inspect dates, ownership,
source excerpts, strengths and future preferences. Surface important missing work
as well as doubtful statements. Do not make the person reread JSON.

Use `docs/pack-review.md` for exact commands and choices. Save decisions only when
the person supplies them. A skipped review leaves the existing accepted pack
usable; a first import stays a proposal until sufficient items are accepted.
Never label `self_asserted` extraction as user-reviewed. Accepting wording does not
increase evidence confidence or grant permission for external use. Preserve
corrections, uncertain answers, deferred items and omission feedback across turns.

## Maintain an existing workspace

For health, achievement history, merge/split/refresh, or backup/restore, use
`docs/workspace-maintenance.md`. These are core operations. Use `health` to explain
integrity separately from completeness. Render `history` when the person asks why
an achievement changed or where it came from. Maintenance creates candidates and
retains historical IDs; never invent replacement prose or retarget strength support
automatically. Backups contain private sources and decisions; restore into a new
directory and continue the saved session.

Use the connected achievement/source controls and save preview during review.
Before applying supplied decisions, run `review preview` against the exact file
to explain dependency or source problems. Missing files are distinct from known
excerpt mismatches. Never change a quote to pass validation without source support.
A status promotion needs the person's separate sourced reassessment decision;
wording acceptance alone cannot resolve an evidence question or establish
corroboration. Bind strengths only into `data/candidates/`, then use review.


## Durable questions and updates

Follow `docs/questions-and-updates.md` for the shared question, reassessment and
recovery contract. Save scoped questions before asking and exact answers before
changing a candidate. Answered, deferred and declined work stays settled; optional
enrichment does not block saving. Use `health --summary --json` for current work,
and `career_core.py recover` after interruption. Reassess affected strengths with
`bind-strength --assessment`; never renew fingerprints alone.
