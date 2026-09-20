# First-pack review: assistant reference

For the user-facing path, use [Your first session](../getting-started.md).
The assistant operates the commands; the person reviews their career.

## Intake the requested scope

One document, all of `data/sources/`, or the person's own account is enough.
Honor explicit scope without another setup interview. Use the
[guided start](career-start.md) when the person needs help choosing material.
No target job or contact profile is required.

```sh
python3 scripts/career_core.py intake data/sources
```

Use a filename instead for a narrower request. Read the inventory and newly
extracted text. Inspect ambiguous material and classify it; filenames are not
proof of purpose. Job descriptions and writing advice do not become career facts.
Report unreadable files and duplicates. Reuse existing sources and stable record
IDs; unchanged material alone needs no new proposal. Preserve conflicting values.
Record conversation accounts verbatim as private person sources.

## Show the proposed career, then review useful work

Stage the complete proposed pack under `data/candidates/`, preserving existing
facts and metadata. Validate it and create the default grouped review:

```sh
python3 scripts/career_core.py review start --candidate data/candidates/proposal.json --id first-review
python3 scripts/career_core.py review open --session reviews/pack-reviews/first-review/session.json --open
```

The second command runs a temporary loopback connection. Keep it alive while the
person reviews; stop it when finished. The printed private URL is the browser
entry point. Use `review render` for a portable offline page if preferred.

Present a short grounded timeline and a link to the full proposed overview before
asking questions. Review roles once, followed by their achievements. All proposed
contributions remain available; do not discard less prominent work to shorten the
review. Show action, outcome and role context first, with supporting detail nearby.

Verifiable source metadata is registered automatically, with an import receipt
separate from human approval. Changes to existing source records or metadata that
cannot be registered still require review. Never invent role, achievement, privacy
or evidence-status decisions. Profile details and strengths can wait.

## Correct, confirm and save

The connected page saves through **Save reviewed changes** or **Save and next
five**. Conversation decisions use the same review contract. Offline downloads
use `review apply --input <supplied-file>`; output version names are automatic.
Tell the person when facts are saved versus when only review choices are saved.
GitHub backup is a separate operation.

Literal role/achievement corrections use `review correct`; richer corrections
use recorded answers and a complete revised candidate with `review revise`.
See [the exact contracts](../pack-review.md#operator-reference). Changed wording
needs new confirmation. Unchanged decisions retain their original receipts;
a changed role invalidates dependent approval. Never paraphrase a correction
into accepted fact without showing it again.

Save coherent independent work even while other items need their supporting role.
Known source mismatches and invalid structures still block acceptance. Explain the
actual blocker; missing contact details, private status, optional strengths and
unmeasured outcomes are not first-pack defects.

## Stop and retrieve

A role and a few supported achievements is a useful stopping point. An education
or other supported record can also start a pack. State what is saved and what
remains pending. Do not turn counts into a completeness or quality score.

Offer: **Show me one recorded achievement and its original source.**
Link the derived `outputs/career-record.html`. It reads accepted data only.

For **Continue my career-pack review**, resolve saved sessions with `review resume`.
Prefer a successor revision over its superseded review; clarify only genuinely
ambiguous work. Do not re-ingest sources merely because a conversation ended.
Strengths, richer outcomes, public-work cataloguing and corroboration are optional
later passes. Accuracy questions come first; ask one answerable question at a time.

Back up `data/` and `reviews/` together. See [workspace maintenance](../workspace-maintenance.md).
