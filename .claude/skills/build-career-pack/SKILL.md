---
name: build-career-pack
description: "Use for the setup phase: building or extending the career datapack from source material. Triggers on requests such as build my career pack, ingest these, I have more material to add, here is my new resume or LinkedIn export, or update my pack with this project. Chains ingestion and Socratic review in one invocation. This is the phase where questions are expected."
---

# Build Or Extend The Career Datapack

## Purpose

The setup phase. Turn source material into a datapack that later resume requests
can be answered from without further interrogation. Questions are the deliverable
here, not an interruption. The goal is to front-load them so that
`make-resume` never has to ask.

Run `ingest-career-materials` then `review-evidence` in a single invocation. Do
not stop between them and do not ask the user to advance.

## Inputs

- new or changed source material (default: everything in `data/sources/`)
- the current pack, if one exists (default: newest in `data/packs/`)

## Workflow

1. Run `ingest-career-materials` on sources whose `sha256` does not already match
   a record in the current pack. Report which sources were skipped as unchanged.
   Use `scripts/extract_text.sh --record <file>` for text and provenance fields;
   see `docs/extraction.md`. Do not improvise an extractor, and do not record a
   file's byte size as its `character_count`.
2. Run `review-evidence` across every atom that is new, incomplete, vague,
   inflated, or consequential. Include atoms carried over from earlier runs whose
   questions are still unanswered.
3. Write the updated pack to `data/packs/` with a new version, and the review
   record to `reviews/`. Never edit a previous pack in place. Set
   `metadata.supersedes` to the previous pack's path.
4. Run `python3 scripts/validate_pack.py` and fix every error before reporting.
   Confirm the chain resolves with `python3 scripts/current_pack.py`.
   Report the warnings; they are the pack's honest weaknesses, not noise.
5. Collect every question into one batch. Do not deliver them one at a time and
   do not wait for an answer mid-run.

## What the questions must cover

Provenance alone is not enough. Every batch must reach for three things:

1. **Grounding.** Missing STAR fields, ownership, scope, timeframe, measurement.
2. **Corroboration is optional and off by default.** Do not ask who would confirm
   a claim unless the user asks for a corroboration pass. `self_asserted` is the
   normal resting state for career evidence and is not a defect. Record
   `corroborators` if the user volunteers one.
3. **Commercial consequence.** What changed for the organisation beyond the work
   being done. Set `outcome_type` to `activity`, `output`, or `business_outcome`.
   Never invent a number to reach `business_outcome`.

Also record `role_fit_notes` where evidence cuts both ways. Reach and speaking
metrics support advocacy roles and undercut hands-on engineering ones. The pack
should know that before generation does.

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

On the first run, or whenever `private_profile` is missing or has no email and no
phone, extract what the sources contain and include the remainder in the question
batch: name, location, email, phone, LinkedIn, and personal website. Ask once,
with everything else. Never ask for a street address or a photo; record them only
if the user supplies them unprompted, and never place either in an artefact.

Set `publication_policy` to private by default: the full block appears on a
document sent to a named recipient, name and location only on anything public.

## Question policy

- Deliver questions once, at the end, as a single numbered batch.
- Order by how much each answer would improve future resumes, and say for each
  question which claim it would unlock and what status that claim has now.
- Never ask about anything already answered in the pack or a prior review record.
- Never invent an answer, and never soften a question so a weak claim passes.
- An unanswered question is not a failure. Record it, set the atom to
  `unresolved`, and finish the run.

Batching is right **here** and wrong afterwards. Ingestion must not block, so the
questions arrive at the end as one list. Working through them is a different
activity: hand the batch over by pointing at `review-evidence`, which asks them
one at a time, adapts each question to the last answer, and shows what each one
moved. Do not attempt that inside this run. `python3 scripts/open_questions.py`
holds the queue, so nothing is lost between the two.

## Answering

When the user answers in a later message, re-run review for the affected atoms
only. Do not re-ingest unchanged sources. Answers are user assertions: record them
as `self_asserted`, regardless of how confidently they were given. Promotion to
`corroborated` needs a named third party or public artefact; promotion to
`externally_verified` needs that source recorded, per `review-evidence`.

## Readiness

End every run by stating how ready the pack is for resume generation:

- counts by `evidence_status`
- how many are `external_safe: true`
- counts by `outcome_type`, called out plainly if no atom is `business_outcome`
- employment records, and any with an unknown `end` or an unconfirmed
  `employer_of_record`
- which unanswered questions would most improve a future resume

Report these plainly. A pack of entirely `self_asserted` atoms is a normal,
usable pack: say what it contains and move on. Do not editorialise about
corroboration, and do not run `corroboration_plan.py` unless the user asks for a
corroboration pass.

The exception is employment. Employers, titles, and dates are what a background
check actually tests, so flag a missing `end` date or an unconfirmed
`employer_of_record` even though corroboration generally is optional.

Say plainly whether the pack is usable for `make-resume` now. A pack with open
questions is usable; it will simply produce a narrower resume.

## Final report

1. Sources ingested, and sources skipped as unchanged.
2. Evidence added or changed, by ID.
3. Conflicts preserved, by ID.
4. Files written.
5. The question batch.
6. The readiness statement.
