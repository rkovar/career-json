# Review your career record

Start with [Your first session](getting-started.md). The assistant proposes a
readable career record. You confirm accurate information, correct wording or
leave items for later. Only confirmed facts enter your accepted pack; previous
versions and sources remain available.

The review shows five items at a time, grouped by role. Confirm each role once,
then review complete achievements with their contribution and outcome visible.
Source excerpts, full fields and previous values are available when needed.
The proposed overview includes all roles and achievements; the saved reading
page contains only the accepted record.

Use **Save reviewed changes** in the connected page. **Save and next five** saves
and advances without losing the next batch. Enter your name under **How review
and saving work**. **Correct the recorded wording** lets you edit role details or
an achievement; **Show revised wording** creates a revision for you to confirm.
All edited cards are included in that preview, so correcting one card keeps your
work on the others. Clicking **Save reviewed changes**, **Save and next five** or
**Save and pause** while wording is edited also opens this preview first. Choose
**Looks accurate** for each revised item and save again to accept the wording.
Unchanged approvals carry forward only while their accepted baseline remains
valid; an older review cannot silently undo a newer correction.

New and changed content stays private by default. Wording acceptance, evidence
confidence and external-use permission are separate. You can stop after useful
work is saved; optional strengths, contact details and enrichment can wait.

## Operator reference

### Intake and create a review

```sh
python3 scripts/career_core.py intake data/sources
python3 scripts/career_core.py review start --candidate data/candidates/proposal.json --id onboarding-v1
python3 scripts/career_core.py review open --session reviews/pack-reviews/onboarding-v1/session.json --open
```

Inventory only the authorized scope. The report distinguishes unchanged, duplicate,
read, deferred and unreadable material. Inspect ambiguous extracted text and keep
writing references/job context out of career evidence. `--classifications <json>`
accepts a mapping of inspected paths to `career_evidence`, `job_context`,
`writing_reference` or `defer`; classification never grants factual authority.

Author a complete candidate preserving existing facts, IDs and metadata. Deletions
are proposed removals and need explicit acceptance. Review creation snapshots
proposal/base hashes without changing the current pack. Existing legacy packs can
be reviewed; schema errors must be corrected before saving a new accepted version.

The CLI defaults to grouped reviews. `--records` preserves the legacy per-record
layout for compatibility. Verified local source metadata can be registered as
needed by accepted claims. Its `metadata.source_imports` receipt records an import,
not human approval or independent corroboration. Modified source records and
nonstandard metadata remain explicit review items. Roles are never autoapproved.

### Connected and offline pages

`review open` starts a temporary Python standard-library HTTP server on 127.0.0.1.
The printed URL contains a random token. It accepts requests only from its own
origin and serves only the review and saved reading view. No source-file directory
is exposed. Keep it running during review; Ctrl-C stops it. It also expires after
an idle period. It does not call a model or push to GitHub.

For a standalone HTML page:

```sh
python3 scripts/career_core.py review render --session reviews/pack-reviews/onboarding-v1/session.json --output outputs/career-review.html
```

This file works offline. Its navigation saves a browser draft; it cannot write a
pack directly. Choose **Download review decisions**, then give the file location
to the assistant. A download does not change career facts. Portable decisions
can be reloaded only into their exact proposal. Keep review pages private.

Both pages retain five stable items while answering, filters, batch jumps and
scroll/focus navigation. The connected page refuses a stale save when the pack
or review changed in another session. Reload to inspect the current state.
Browser storage is a convenience; the workspace review ledger is authoritative.

### Record and apply actual decisions

```sh
python3 scripts/career_core.py review apply --input data/private/my-decisions.json
python3 scripts/career_core.py review status --session reviews/pack-reviews/onboarding-v1/session.json
python3 scripts/career_core.py review resume
```

Copy only the user-supplied file into the workspace if needed. Conversation
choices use the same JSON contract, with the person's actual name, decisions and
notes. Never fill in supporting-record approvals. `apply` assigns a new immutable
pack filename, refreshes `outputs/career-record.html`, and reports saved facts,
pending items and blockers. `--output data/packs/<new-name>.json` is optional.
Notes-only/repeated saves do not create another pack version.

**Looks accurate** accepts exact wording; **Correct this** needs an explanation;
**Not sure** and **Review later** remain pending. **Keep private** can restrict
existing content while correction is pending. **Allow this exact content
externally** also requires accepting it. Acceptance cannot raise confidence;
[evidence reassessment](workspace-maintenance.md#resolve-an-evidence-question)
requires a separate sourced decision.

Grouped reviews can save independent coherent choices while other selections
need supporting records. The blocked selections stay pending with their original
choices. Known source mismatches, changed support for existing accepted facts and
schema errors still block invalid results. Schema 1.4 permits starting with roles
or education before achievements; the archived 1.3 contract remains unchanged. A nonzero `apply` exit with
`save_blocked` can accompany a partial save: inspect `saved_pack` and the message.
Changed proposals and dependencies cannot reuse earlier approval.

The lower-level `review record`, `preview`, `accept` and legacy `publish` commands
remain available. `accept`/`publish` mean saving a local pack, not external
publication. Preview does not write facts. Omission answers stay follow-up notes.

### Correct without losing earlier review

For a literal role or achievement edit, `review correct --session <session>
--input <file>` expects:

```json
{
  "decisions": {"review_id": "...", "proposal_sha256": "...", "reviewed_by": "Actual reviewer", "decisions": [], "omissions": []},
  "edits": [{"key": "evidence_atoms/E_PROJECT", "fingerprint": "...", "fields": {"star.action": "The person's exact revised wording"}}]
}
```

Use actual session hashes and user text. Editable fields are achievement `title`
and `star.situation/task/action/result`, or role `employer/title/start/end`.
The helper saves the literal correction as a person source and creates a new
proposal. Blank dates remain unknown. Changed wording is private and needs new
confirmation; a correction does not establish independent corroboration.

For structural edits, record the actual answer with `answer.py`, revise the full
candidate and run:

```sh
python3 scripts/career_core.py review revise --session reviews/pack-reviews/onboarding-v1/session.json --candidate data/candidates/revision.json --id onboarding-v2
```

Unchanged decisions carry their original receipts only when the accepted baseline
still matches, or the exact decision is already applied. Changed content or dependencies
lose approval. Reopen the resulting session. The old proposals and answers remain
available. `resume` and **Continue saved work** show the latest revision of each review,
using its original name. Independent reviews and branches remain separate.
Use `python3 scripts/career_core.py review resume --history` to inspect earlier
versions. An approval invalidated by another accepted correction needs a fresh
choice; check the proposed wording against what was recorded before.

### Handover and tests

`review handover --session <session> --page <page>` produces a short grounded
handover with recorded examples and a stopping point. Keep technical inventories
in the private review rather than repeating them in the conversation.

See [development](development.md) for deterministic, HTTP and optional real-browser
checks; see [workspace maintenance](workspace-maintenance.md) for history,
merge/split/refresh and portable private backup.

## Accurate handoffs and recovery

`review handover --session <session> --page <page>` describes the offline download
path. Add `--connected` only while the local browser connection is running; the
handoff then explains direct Save. Unknown dates retain their qualification in
both the overview and handoff. Source import commentary is expandable and does
not create an extra approval question.

`career_core.py recover` regenerates a handoff from valid saved sessions after an
interruption. `career_core.py view` refreshes the saved reading page atomically.
Use [the shared question/update contract](questions-and-updates.md) for interview
state; pending review items and required clarification questions are distinct.
