# Career Evidence Core

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
