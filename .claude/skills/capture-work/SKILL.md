---
name: capture-work
description: "Use when the user mentions something they did at work that should not be forgotten, or asks to note, log, or capture an achievement, project, incident, or win. Also use to turn accumulated notes into evidence atoms. Triggers on phrases such as remember that I, log this, capture this, note that I just, or don't let me forget."
---

# Capture Work Before It Is Forgotten

## Why this exists

Ingestion can only capture what the user already remembered and wrote down.
Nobody writes a document when they clear a stalled backlog on a Tuesday, and
eighteen months later it is gone. This is the only part of the workspace that
runs against forgetting rather than after it.

## Capturing

When the user mentions something they did, offer to capture it. Keep it to one
exchange.

```sh
scripts/capture.py "what they did, in their words" --tag <thread> --skill <skill> --occurred YYYY-MM
```

- **Do not interrogate.** No STAR, no metrics, no corroboration, no follow-up
  questions. A note is a hook for memory, not evidence. Every question asked here
  makes the next capture less likely to happen.
- Use the user's own words. Precision comes later, when the note is promoted.
- Default `occurred` to now. Set it explicitly only if they say when.
- Suggest a tag only if an existing thread in the pack obviously fits.

Correct a note with `--edit <id> "new text"`, and remove one with
`--delete <id>`. Note ids are never reused, so a deleted id cannot silently
repoint an atom that cited it.

Notes land in `data/capture/notes.jsonl`, never in the pack. A note must not
require a new pack version, because that friction is what stops people capturing.

## Promoting notes into the pack

Do this when the user asks, or as part of `build-career-pack`, or when they sit
down to write an annual review. Not before: promoting a note takes real work and
notes are cheap.

1. `scripts/capture.py --list` for what is waiting.
2. `scripts/dedupe.py --notes` to see what the pack already holds. Prefer
   strengthening an existing atom over adding a near-duplicate.
3. For each note worth keeping, run `review-evidence` to build the STAR fields.
   **This is where questions belong**, because the user has already decided the
   thing matters.
4. Set `occurred` from the note, `capture.method` to `note`, and
   `capture.note_id` to the note it came from.
5. `scripts/capture.py --promote <note_id> --atom <atom_id>`.

A note that turns out not to matter is closed by promoting it to nothing: say so
and leave it. Do not delete the user's notes.

## Finding what is missing

`python3 scripts/coverage.py` shows atoms per year, gaps of two or more years with
nothing recorded, undated atoms, and skills not seen recently. A gap is not proof
that nothing happened; it is where forgetting has already won. Use it to prompt
the user during an annual review, not to nag them.

## The annual write-up

An end-of-year review for an employer is the single biggest capture event of the
year, and it is handled by `build-career-pack`. Read that skill's review-period
section before importing one.
