# Career Evidence Core workflow

The core works without a target role or a resume application. Its deliverable is
a useful, traceable career record. Start with `build-career-pack` on source
material, then use `review-evidence` and the optional `review-strengths` interview.
Capture subsequent work with `capture-work`. Python commands require no model;
the conversational skills run in Claude Code.

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

## Strengths and direction

Schema 1.4 stores `strengths_profile` and `positioning_preferences`. A strength
records an interpretation, supporting evidence IDs and fingerprints, timeframe,
limitations, status, disclosure constraints, and interview state. It remains an
interpretation even after confirmation. Preferences record what the person wants;
they are never past achievements. Confirmed or rejected interpretations and
preferences require person-source answer references.

Ask one answerable question and wait. Reuse existing answers; allow corrections,
rejection, a skipped question, or no particular career narrative. Recurring
patterns need multiple supporting achievements. Preserve declined questions and
rejected interpretations. Changed supporting facts make an interpretation stale.

```sh
python3 scripts/career_core.py migrate --output data/candidates/career-v2.json
python3 scripts/answer.py reviews/onboarding.md --subject S_DEPTH --source SRC_ONBOARDING --question 'Does this describe your contribution?' --answer 'I designed the format; colleagues built the runner.'
python3 scripts/career_core.py bind-strength --pack data/candidates/career-v2.json --strength S_DEPTH --output data/candidates/career-v3.json
```

Use actual IDs and the person's actual answer. Register its person source and
excerpt in the new pack. `bind-strength` refreshes only the named, reassessed
interpretation's fingerprints; it never changes its status. Preserve an explicit
supersedes link to the actual previous pack in a working candidate. Recheck the
pack and chain before finishing. Schema 1.3 remains readable without migration.

## Export and portability

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
