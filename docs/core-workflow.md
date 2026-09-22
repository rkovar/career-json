# Career Evidence Core workflow

The core works without a target role or a resume application. Its deliverable is
a useful, traceable career record. Start with `build-career-pack` on source
material, then use `review-evidence` and the optional `review-strengths` interview.
Capture subsequent work with `capture-work`. Python commands require no model;
the conversational skills run in Claude Code.

For a first pack, use [your first session](getting-started.md): one source, a readable
overview, a few accepted achievements and a recall example. Returning users can
say “Continue my career-pack review”; `career_core.py review resume` finds the
saved sessions. “Apply my saved review decisions” uses the supplied file through
`review apply` and returns a stopping-point summary.

## Maintain the record

Keep unreviewed proposals under `data/candidates/`. Use the readable
[human review checkpoint](pack-review.md) before making proposed changes current.
Keep sources under `data/sources/`, accepted versioned packs under `data/packs/`, and answers
under `reviews/`. Preserve employment and evidence IDs across revisions. New
versions set `metadata.supersedes`; never overwrite an earlier pack. Conflicting
values remain visible. Generated prose can suggest a question but cannot answer it
or promote evidence status.

```sh
python3 scripts/validate_pack.py
python3 scripts/current_pack.py
python3 scripts/open_questions.py --json
python3 scripts/coverage.py
python3 scripts/career_core.py status
```

Before first acceptance, add `--pack <candidate-path>` to the question and
strengths-status commands and validate that explicit candidate path. Coverage
reports and exports use the accepted pack.

Readiness means the person can find their history, see its sources, correct it,
and understand its gaps. It does not certify resume quality. Role and screen
records, when an application supplies them, may suggest questions; they carry no
factual authority and are not required for onboarding.

The default review groups achievements by role and registers verifiable source
metadata separately from human approval. Use `review open` for a temporary local
browser connection with direct saving; `review render` remains the offline option.
Corrections produce revised wording for confirmation and retain unchanged decisions.
A partial private pack needs no contact profile or strengths interview.
`open_questions.py` defaults to factual uncertainties; `--optional` adds enrichment
and `--application` includes role/screen/publication questions.

## Strengths and direction

Schema 1.4 stores `strengths_profile` and `positioning_preferences`. A strength
records an interpretation, supporting evidence IDs and fingerprints, timeframe,
limitations, status, disclosure constraints, and interview state. It remains an
interpretation even after confirmation. Preferences record what the person wants;
they are never past achievements. Confirmed or rejected interpretations and
preferences require person-source references, including explicit intent in a
user-written account. A Markdown account can be a person source; its file format
is not its provenance. Never manufacture confirmation or reclassify third-party
material to satisfy this requirement.

Ask one answerable question and wait. Reuse existing answers; allow corrections,
rejection, a skipped question, or no particular career narrative. Recurring
patterns need multiple supporting achievements. Preserve declined questions and
rejected interpretations. Changed supporting facts make an interpretation stale.

```sh
python3 scripts/career_core.py migrate --output data/candidates/career-v2.json
python3 scripts/career_core.py bind-strength --pack data/candidates/career-v2.json --strength S_DEPTH --assessment data/private/strength-assessment.json --output data/candidates/career-v3.json
```

Record scoped questions and answers and prepare the assessment as described in
[Questions and dependable updates](questions-and-updates.md). Use actual IDs and
the person’s exact answer. `bind-strength` updates the named interpretation and
its assessed limitations and fingerprints; it never changes its confirmation status. Preserve an explicit
supersedes link to the actual previous pack in a working candidate. Recheck the
pack and chain before finishing. Schema 1.3 remains readable without migration.

## Export and portability

`make career-page` creates a private reading page from the recorded pack at
`outputs/career-record.html` and a complete private Markdown snapshot at
`outputs/career.md`. The HTML view includes withheld work, preserves unknown dates
and marks strengths whose support changed. `make pack-html` provides a searchable
overview. Neither view adds facts from raw sources or records approval; use the
human review workflow for changes. Both the Markdown snapshot and the JSON
export contain the complete saved pack. The HTML page omits the profile contact
block. See [your files and exports](files-and-exports.md) for scope and regeneration
rules; generated-file edits never update the pack.

```sh
python3 scripts/career_core.py export --output data/private/career-export.json
```

This is a lossless **private** JSON export of the current pack, including withheld
facts and private contact details. It preserves IDs, sources, strengths,
preferences and metadata. It never overwrites an existing export or creates a new
chain head. Source files and earlier pack versions are not embedded: back up
`data/` and `reviews/` together to preserve the full history and relative source
paths. A public projection is a separate application operation.

## Optional Resume Application

The add-on consumes the same schema and workspace. Use `make-resume` only after
installing it. It owns briefs, selections, role profiles and scoped editorial
decisions; those survive deleting generated outputs. Factual corrections discovered
while writing return through core evidence review. See its `docs/resume-workflow.md`
when installed. Building a career pack does not require installing the add-on.

See [workspace maintenance](workspace-maintenance.md) for connected achievement
review, a save preview, explicit evidence reassessment, health, readable history,
merge/split/refresh and portable private backup/restore.

## Question state and strength reassessment

Use [Questions and dependable updates](questions-and-updates.md) for new scoped
answers, previewable legacy imports, and `bind-strength --assessment`. Bare hash
refresh is rejected. `health --summary --json` gives fast current-work state;
`status` remains the compatible strengths view. Packs still use schema 1.4 and
read 1.3; immutable question revisions have their own version 1 contract.
