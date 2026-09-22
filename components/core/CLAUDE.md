# Career Evidence Core

For “Help me start my career notebook,” follow `docs/operators/desktop-start.md`.
Run setup checks yourself, use conversation review, and verify the first saved
achievement by reading it back with its source. Resume existing work on return.

This workspace uses Career Evidence Core (early access). Read
`docs/core-workflow.md`. The core supplies five skills for intake, evidence review,
strengths review and capture. Core work finishes with a useful career pack and
its open questions; a target role is optional. Resume generation and recruiter
screening are available only when `components/resume/component.json` is present.
When it is present, follow `docs/resume-workflow.md` for document requests.

Facts, sources, employment and education belong in versioned packs. Strengths
are supported interpretations; preferences describe intent. Never invent facts,
convert preferences into achievements, or treat generated text as new evidence.
Every claim needs traceable evidence IDs and sources. Preserve conflicts and
unknowns. `self_asserted` is normal; corroboration is optional and never chased
unless requested. Record answers verbatim; ask one answerable question at a time.

Keep `external_safe: false` material private. Keep contacts in private_profile.
Never overwrite a historical pack: write a new version with metadata.supersedes.
Use `career_core.py` for status, migration, reassessed fingerprints and private
export. Validate packs and resolve the chain after changes. Data, outputs and
reviews stay outside source control and release archives. Use fictional test
fixtures only. No database, web app, provider integration or Python dependency
is needed. All scripts honor CAREER_WORKSPACE.

If the Resume Application add-on is installed, read `docs/resume-workflow.md`
when the user requests a document. Application choices cannot change career facts
without returning through the core review process.


## Human review of proposed data

Use `docs/pack-review.md`. Unreviewed extraction and corrections live in
`data/candidates/`; they must not become current by being written to `data/packs/`.
Present the private readable review and save only explicit user decisions. Exact
wording acceptance, evidence confidence and external-use permission are separate.
The review helper saves accepted local pack versions and preserves deferred items,
correction notes and omission feedback. Never fill in approvals for the person.

When Resume Application is installed, follow its `docs/resume-authoring.md` for
application context, optional review, durable plans and PDF/TXT/DOCX delivery.
Resume-specific instructions remain in that component.

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
