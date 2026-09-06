# Claude Workflow

See also [getting-started.md](getting-started.md) for a first session,
[data-model.md](data-model.md) for the schema, and [architecture.md](architecture.md)
for what is code versus what is a skill.

This project runs as a Claude Code workspace. The repository is the durable memory; Claude is the conversational operator.

## The two phases

**Setup, now and then.** Ask Claude to use `build-career-pack` when you have
material to add: a new resume, a LinkedIn export, a project writeup. It ingests
and reviews in one invocation and ends with a single batch of questions plus a
readiness statement. Answer as many or as few as you like; unanswered questions
leave a claim `unresolved` rather than blocking anything.

**Delivery, whenever you need a document.** Ask Claude to use `make-resume` with
a target role. It reads the pack, writes the draft, evaluates it for integrity,
screens it as a recruiter would, and hands it over with a verdict. It does not ask
questions. If evidence is thin it narrows or drops the claim and tells you
afterwards.

Every delivery run ends with `recruiter-screen`: a cold read of the finished
document by a senior technical recruiter and then the hiring manager, returning
`advance`, `borderline`, or `reject` and the three changes that would most move
that verdict. It separates what a rewrite can fix from what needs new evidence,
and routes the latter back to `build-career-pack`. A `reject` is a successful run.
It is cheaper here than in the market.

Run it on its own against anything, including material this workspace did not
generate: an existing CV, a LinkedIn About section, a cover letter.

The point of answering questions during setup is that delivery stays quiet. The
stage-by-stage skills below remain available for running one step on its own.

## Running a single stage

`build-career-pack` and `make-resume` cover the normal path. The four stage skills
below exist for when you want one step on its own, and each is what the
orchestrators call underneath.

`ingest-career-materials` takes source files or `data/sources/` and reports what it
found and what is missing before creating a datapack.

The files in `examples/` are fictional format references only. They are never an approved personal datapack. Real personal profiles that pre-date the schema live in `data/private/`, which is ignored by Git; treat them as self-asserted source material and confirm ownership and provenance before ingesting them.

## Review evidence

Ask Claude to use `review-evidence`. Answer questions one claim at a time. A response can clarify a claim, but it never promotes its status on its own: status follows the sources, not the answer. Keep unresolved questions in `reviews/`.

## Create a datapack

Approved packs belong in `data/packs/` and must validate against `schemas/career.schema.json`. Keep source references and stable evidence IDs intact when revising a pack.

## Generate an artefact

Provide the approved datapack, target role, job description, ATS constraints, persona, target length, and recruiter context. Ask Claude to use `generate-resume` or the relevant output workflow. Each substantive claim must retain its evidence ID.

## Evaluate before publication

Ask Claude to use `evaluate-output`. The result must identify factual, privacy, targeting, and style findings. A draft is not publishable until material findings are resolved and the evaluation explicitly passes.

## Privacy

The following directories are ignored by Git by default:

- `data/sources/`
- `data/packs/`
- `data/private/`
- `reviews/`
- `outputs/`

Do not paste secrets into the repository. Treat raw career material and PII as private even when the source is technically public.
## Evidence status

`self_asserted` is the default and the honest resting state for most career
claims. Promotion requires a source independent of you.

| Status | Means | Promotes when |
| --- | --- | --- |
| `self_asserted` | Appears only in material you wrote | A third party or public artefact supports it |
| `corroborated` | A person or public artefact supports it, no record captured | The URL or record is captured as a source |
| `externally_verified` | Backed by an independent source in `source_records` | n/a |
| `unresolved` | An open question | The question is answered |
| `declined` | You chose not to pursue it | You change your mind |

Your resume and your LinkedIn profile are both written by you. A claim in both is
`self_asserted`, not corroborated. This matters because a reference check tests
corroboration, not consistency.

Each atom also records `corroborators` (who would confirm it), `outcome_type`
(`activity`, `output`, or `business_outcome`), and `role_fit_notes` (where the
evidence counts against you). Generation prefers business outcomes and demotes
evidence that reads as a negative signal for the target role.

## Tooling and tests

The workspace splits work between the model and code on one line: anything
decidable from the pack alone is a script.

| Script | Does |
| --- | --- |
| `current_pack.py` | Resolves the current pack by supersedes chain, not by mtime |
| `select_evidence.py` | Emits only eligible evidence, so ineligible atoms never enter context |
| `render.py` | Markdown to HTML through one template, so the two cannot drift |
| `validate_pack.py` | Structural check on a pack |
| `validate_artifact.py` | An artefact against the pack it came from |
| `manifest.py` | Pack hash and skill hashes for an evaluation record |
| `extract_text.sh` | Source text plus provenance fields |

`make check` validates the packs and runs `tests/run_tests.py`. Behavioural claims
that need a model in the loop are listed in `tests/scenarios.md`; run them after a
material skill edit.

## Employment

Employers, titles, and dates live in the pack's `employment` records, not in the
prose of a draft. They carry no evidence ID of their own, so nothing else in the
system can see them, and they are exactly what a background check tests. A date or
employer in an artefact that traces to no record is an error, and a claim like
"N years of experience" is checked against the span the records support.

Record `employer_of_record` wherever the work was delivered for a client rather
than the paying entity. It never appears in an artefact; it exists so a reference
check does not surprise you.

## Targeting

`make fit` scores the pack against every profile in `data/roles/` and ranks them.
An unevidenced essential requirement makes a role unsupported however well the
rest scores, because it is the thing they are hiring for. Use it to choose where
to apply, rather than discovering the mismatch at the recruiter screen.

`make verdicts` appends screen verdicts to `reviews/verdicts.jsonl` and shows
whether artefacts are improving over time.

## LinkedIn

There is no LinkedIn connector, deliberately. See `docs/linkedin.md`.

## Capture and recall

`scripts/capture.py` appends a one-line note to `data/capture/notes.jsonl`. It
never writes to the pack: a thirty-second note that costs a pack version is a note
that does not get written. Notes are promoted into atoms later, which is work
worth doing when you are already remembering, such as while writing an annual
review.

`scripts/find.py` searches the pack by term, skill, tag, employer, date range,
outcome, or status. Skill matching goes through `skill_vocabulary`, so a query in
one spelling finds atoms recorded in another. Free-text skills fragment as a pack
grows, and a search that silently misses things is worse than no search.

`scripts/dedupe.py` compares a candidate claim against the pack. Run it before
importing an annual write-up: the second year of a continuing programme belongs in
the existing atom as a stronger Result, not in a new atom that splits the evidence
for one achievement across three entries.

`occurred` records when an atom happened. Where it was inherited from an
employment window it is marked `inferred: true`, because a nine-year span is
barely a date and should be narrowed while the detail is still recallable.
