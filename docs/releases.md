# Two components, one repository

Career Evidence Core and Resume Application have separate promises, versions and
release gates. The current local release candidates are **career-core
0.1.0-alpha.3** (early access) and **career-resume 0.1.0-beta.3** (beta companion).
These names describe prepared artifacts, not an announcement of publication.

| Responsibility | Career Evidence Core | Resume Application |
| --- | --- | --- |
| Durable truth | Sources, STAR atoms, employment, education, evidence status, disclosure rules | References core IDs and exact pack hashes |
| Career interpretation | Supported strengths, rejected interpretations, future preferences, source answers | Chooses relevant strengths for a document |
| Workflow | Capture, staged intake, offline human review, recall, correction, versioning, lossless private export | Role analysis, ranking, briefs, selection decisions, tailoring, reviews, rendering |
| Success | A person can retrieve, understand, correct and reuse their career record | A reader understands the person's relevant, distinctive contribution |
| Evaluation | Data preservation, provenance, privacy boundaries, usable onboarding across different careers | Grounding, representation, reader assessment and final document layout |

The dependency is one way: the application uses the core. Core Python modules do
not import the resume modules, and the core archive runs without them. Shared
primitives (eligibility, references, quantity extraction, schema validation) live
in the core. Role or screen records can suggest evidence-review questions when
present; they never supply facts and are not required for the core to operate.

## Contracts and authority

The versioned career schema and stable evidence/employment IDs are the boundary.
Both initial releases read schema 1.3 and 1.4; the current writing schema is 1.4.
Component versions are independent from that schema version. The resume manifest
pins its required core version exactly during these initial releases. Update that
pin only after compatibility tests pass. Unsupported combinations fail
`check_components.py --require resume` and the add-on's `make check` target.

Core intake stages proposals under `data/candidates/`. The human-review workflow
records explicit choices and saves accepted changes as a new pack version;
correction notes never silently become facts. Existing legacy packs remain usable
without automatic review approval. Confirmation of a strength does not promote the evidence itself.
An application changes prose, selection or a scoped preference; it must route new
facts through core review. Generated text cannot silently write back into atoms.

Existing combined checkouts and `scripts/` paths remain usable. Core strengths,
migration and export now live in `career_core.py`; existing `editorial.py` core
commands forward to it. No existing pack or output needs relocation or migration
because of this component split.

## Build and install

```sh
make check-core
make check-resume
make test-releases
make release-core
make release-resume
```

The developer checkout can also test the real strengths interview against the
core-only archive (uses the configured Claude CLI and spends tokens):

```sh
python3 tests/run_editorial_scenarios.py --scenario interview --installation core --budget 2 --report reviews/core-interview.json
```

Builds use explicit destination-to-source allowlists in
`components/core/component.json` and `components/resume/component.json`. There
are no recursive repository exports. The builder rejects private paths, path
traversal and symlinked sources, checks dependency closure, and emits deterministic
ZIP files with per-file SHA-256 inventories in `dist/`. Data, outputs, review
answers, repository metadata and local caches are excluded. Archives never
contain someone's career pack, even if one exists in the developer checkout.

For a new installation, unzip the core into an empty directory. Run `make check`,
then open it in Claude Code for onboarding. To add resume generation, unzip the
matching add-on into the same directory and run `make -f Makefile.resume check`.
The add-on has no file overlap with the core and carries no private workspace
content. Component manifests and release inventories live under `components/`.

Keep `data/`, `reviews/` and any generated documents when upgrading, and review
local code changes before replacing release files. Existing output reviews may
become stale when workflow hashes change; regenerate those reviews when using the
new workflow. The release builder never rewrites personal data or reviews.

## Independent release gates

**Core early access:** its clean archive must validate, migrate and export packs
without the resume application; exports preserve facts, IDs, strengths and
preferences. Review tests must preserve pending proposals, exact-content
acceptance, partial progress, corrections and independent disclosure choices.
Source excerpts and lineage must be checkable. Declined or rejected
interviews must remain resumable without pressure to confirm. Run onboarding with
people across career stages and disciplines and record where they need help.
The current fictional fixtures establish mechanics, not real-user onboarding
success. Broader testing remains a gate for leaving early access.

**Resume beta:** require compatible core/schema versions, safe evidence projection,
scoped feedback persistence, exact review provenance, and the deterministic
regressions. Run the interview, representation, grounding and formats model
scenarios after material workflow changes. Record model, settings, fixture,
checks and manual findings. Inspect final prose and requested PDF layout.

**Resume promotion:** assemble professionally reviewed benchmark documents across
career types and seniority levels. Have reviewers assess factual grounding,
distinctive contribution, relevance, readability and layout separately. Track
whether unsupported claims or lost strengths recur after shortening/retargeting.
Do not infer production quality or hiring outcomes from green validators. The
benchmark and broader user studies remain work to do; this split does not claim
they have happened.

Each component keeps its own version, release notes and gate evidence. A resume
quality finding can delay the resume release without delaying a passing core
release. Keep one repository until separate maintainers or release operations
justify splitting it. Publishing releases is a separate distribution action;
these commands prepare reviewable local artifacts only.
