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
hand over to `review-evidence`. Do not ask the user to operate the scripts.

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
apply --input <file> --output <new-pack-path>`. The file identifies its session.
Never fill in supporting-record approvals yourself. If acceptance is blocked,
show the relevant role/source/profile records for review, preserve the decisions
and explain what remains. Rerender the page after applying decisions.

For “continue my career-pack review,” run `career_core.py review resume`. Use the
session named in the conversation, or the sole unfinished session. If several
are plausible, ask which one; do not create another proposal merely to resume.
Corrections go through recorded answers and a revised candidate with exact wording
shown again. Reuse unchanged accepted facts and prior answers.

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

1. Run `ingest-career-materials` on sources whose `sha256` does not already match
   a record in the current pack. Report which sources were skipped as unchanged.
   Use `scripts/extract_text.sh --record <file>` for text and provenance fields;
   see `docs/extraction.md`. Do not improvise an extractor, and do not record a
   file's byte size as its `character_count`.
2. Identify review questions for every atom that is new, incomplete, vague,
   inflated, or consequential. Include atoms carried over from earlier runs whose
   questions are still unanswered. Finish extraction before asking them.
3. Write the proposed pack to `data/candidates/` and the review record to
   `reviews/`. Follow `docs/pack-review.md`: stage the candidate and render its
   offline review page. Never edit a previous pack or make unreviewed extraction
   current. An accepted version later sets `metadata.supersedes` to its predecessor.
4. Run `python3 scripts/validate_pack.py <candidate-path>` and fix every error before reporting.
   When an accepted pack exists, confirm its chain with `python3 scripts/current_pack.py`.
   Report the warnings; they are the pack's honest weaknesses, not noise.
5. Collect every question into the queue (`python3 scripts/open_questions.py --pack <candidate-path>`
   holds it) and do not wait for an answer mid-run: ingestion must finish with
   the proposed pack written. Then hand over to `review-evidence`, which asks them one at
   a time. The batch is how questions are *collected*; it is never how they are
   *asked*.

## Durable strengths and direction

After staging the evidence proposal, follow `review-strengths` to prepare supported
interpretations and their resumable question queue. Ingestion still finishes
before the interview starts. Offer the strengths interview as normal onboarding;
a user can pause or skip it and generate from the available evidence. Read
`docs/core-workflow.md` for schema 1.4 migration and storage. Preserve existing
strengths, preferences, rejected interpretations and answer references in every
new pack version. Changed supporting atoms make interpretations stale until
reassessed. Never recover factual authority from a previously generated document;
trace its claims back to source evidence before importing anything new.

## What the questions must cover

Provenance alone is not enough. Every batch must reach for four things:

0. **Public work, itemised.** If the sources describe speaking, writing, teaching
   or publishing but yield no `publications` records, or the pack has none at
   all, ask once for the items (or a catalogue, author archive or speaker
   profile to extract them from). "None" is a complete answer: record it as a
   `No publications: <why>` constraint on the achievement so the queue in
   `open_questions.py`, which raises this on its own, stops asking.

1. **Grounding.** Missing STAR fields, ownership, scope, timeframe, measurement.
2. **Corroboration is optional and off by default.** Do not ask who would confirm
   a claim unless the user asks for a corroboration pass. `self_asserted` is the
   normal resting state for career evidence and is not a defect. Record
   `corroborators` if the user volunteers one.
3. **Commercial consequence.** What changed for the organisation beyond the work
   being done. Set `outcome_type` to `activity`, `output`, or `business_outcome`.
   Never invent a number to reach `business_outcome`.

Also record `role_fit_notes` where evidence cuts both ways. Reach and speaking
metrics can establish technical influence, but their relevance depends on the
target and the rest of the selection. Record context, not a universal penalty.

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
   may be used externally rather than assuming, and keep the internal framing out
   of the atom text.
5. **Sweep the capture notes at the same time.** Run
   `scripts/capture.py --list`: the user is already in a remembering frame of
   mind, which is the cheapest moment all year to promote notes.
6. Performance ratings, manager comments, and calibration language are private
   signals. Record them only if asked, always `external_safe: false`, and never
   let them reach an artefact.

## Contact details

A pack without `private_profile` cannot produce a sendable resume, because
`make-resume` has no contact block to build. Creating it is part of setup.

On the first run, extract what the source contains into `private_profile` without
inventing missing values. Name/location are enough for private career capture;
when the person wants a sendable document, queue any needed email, phone, LinkedIn
or website details. Never ask for a street address or a photo; record them only
if the user supplies them unprompted, and never place either in an artefact.

Set `publication_policy` to private by default: the full block appears on a
document sent to a named recipient, name and location only on anything public.

## Question policy

- Collect questions once, at the end, into the queue; report how many there are
  and the top three by what they unlock, then hand over to `review-evidence` to
  ask them one at a time. Never present the whole list as a numbered batch to
  be answered.
- Order by how much each answer would improve future resumes, and say for each
  question which claim it would unlock and what status that claim has now.
- Never ask about anything already answered in the pack or a prior review record.
- Never invent an answer, and never soften a question so a weak claim passes.
- An unanswered question is not a failure. Record it, set the atom to
  `unresolved`, and finish the run.

Collecting is right **here** and asking is wrong here. Ingestion must not
block, so the questions are queued at the end. Working through them is a
different activity: hand over to `review-evidence`, which asks them one at a
time, adapts each question to the last answer, and records each answer as it is
given. Do not attempt that inside this run. `python3 scripts/open_questions.py`
holds the queue, so nothing is lost between the two.

## Answering

When the user answers in a later message, re-run review for the affected atoms
only. Do not re-ingest unchanged sources. Answers are user assertions: record them
as `self_asserted`, regardless of how confidently they were given. Promotion to
`corroborated` needs a named third party or public artefact; promotion to
`externally_verified` needs that source recorded, per `review-evidence`.

## Readiness

End every run by stating how ready the career record is for reuse. Resume
generation is an optional application; a target role is not required:

- counts by `evidence_status`
- how many are `external_safe: true`
- counts by `outcome_type`, called out plainly if no atom is `business_outcome`
- employment records, and any with an unknown `end` or an unconfirmed
  `employer_of_record`
- publications: how many items are recorded by kind, how many are independently
  verified, and whether any body of work named in an achievement (talks, books,
  posts) has no itemised records behind it
- which unanswered questions would most improve a future resume

Report these plainly. A pack of entirely `self_asserted` atoms is a normal,
usable pack: say what it contains and move on. Do not editorialise about
corroboration, and do not run `corroboration_plan.py` unless the user asks for a
corroboration pass.

The exception is employment. Employers, titles, and dates are what a background
check actually tests, so flag a missing `end` date or an unconfirmed
`employer_of_record` even though corroboration generally is optional.

A pack with open questions is usable; describe its limits. When the Resume
Application is installed, also say whether it is usable for `make-resume` now;
remaining gaps will produce a narrower resume.

## Final report

1. Sources ingested, and sources skipped as unchanged.
2. Evidence added or changed, by ID; publications added, by kind and count.
3. Conflicts preserved, by ID.
4. Files written.
5. The question batch.
6. The readiness statement.


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
