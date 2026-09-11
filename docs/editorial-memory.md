# Durable editorial memory

The career pack is the source of truth. Strengths are evidence-backed
interpretations; preferences describe intent. An output is a disposable projection.
Deleting `outputs/` must never delete factual corrections, preferences, briefs,
selections or the reasons behind important editorial decisions. Regeneration
preserves those inputs, not necessarily identical model wording.

## Storage and authority

| Record | Location | Authority |
| --- | --- | --- |
| Proposed career changes | `data/candidates/*.json` | Pending content; never selected as the current pack |
| Human wording review | `reviews/pack-reviews/<id>/` and accepted pack receipts | Exact-content decisions, corrections, deferrals and omission notes |
| Achievements, employment, education, sources | Versioned `data/packs/*.json` | Recorded facts with evidence status and disclosure constraints |
| `strengths_profile` | Career pack, schema 1.4 | Proposed, confirmed or rejected interpretations; never a new evidence status |
| `positioning_preferences` | Career pack, schema 1.4 | Subject-sourced direction and presentation preferences |
| Output brief | `data/briefs/<id>-brief.json` | Audience, format, application, relevant strengths and priorities |
| Evidence selection | `data/selections/<id>-selection.json` | Ranked editorial choices and alternatives, pinned to their inputs |
| Scoped decisions | `reviews/decisions/<id>-decision.json` | Who decided what, why, scope, and supersession history |
| Representation review | `outputs/<artifact-stem>-representation.json` | Assessment of this exact artifact against this exact brief |

Everything in data/briefs, data/selections and reviews is private and gitignored.
Only fully fictional examples belong in examples/ and tests/. A generated document
is not a source merely because the system previously wrote it. Corrections flow
to atoms, interpretations or preferences according to what was corrected.

All record shapes are in schemas/. Scripts handle eligibility, references, hashes,
scopes and persistence; skills handle interpretation, marginal contribution and
writing. Stored reasons explain decisions without pretending to be facts.

## Upgrade and onboarding

Schema 1.3 packs remain readable and validate against their archived schema.
Optional 1.4 fields default to empty; there is no compulsory new interview.

```sh
python3 scripts/career_core.py migrate --output data/candidates/career-v2.json
python3 scripts/validate_pack.py data/candidates/career-v2.json
python3 scripts/career_core.py status --pack data/candidates/career-v2.json
```

Migration writes a new version and sets metadata.supersedes. It does not alter
atoms or populate speculative strengths. Keep the previous pack at its existing
path. To change evidence or profile records, author a candidate pack preserving
all original fields and IDs, then use the [human review checkpoint](pack-review.md)
to accept exact changes into a new version with a supersedes link. Never edit a
historical pack in place. Wording review, interpretation confirmation, evidence
confidence and external-use permission each retain their own meaning.

`review-strengths` proposes interpretations and asks one question at a time.
For each strength, store supporting evidence IDs, `evidence_fingerprints`, basis,
timeframe, limitations, status, safe-publication flag, answer sources and question
state. `proposed` means model interpretation, not subject approval. Confirmed and
rejected interpretations need a person source. A recurring pattern requires
multiple achievements, whereas a single achievement may still establish a strength.

```sh
python3 scripts/answer.py reviews/onboarding.md --subject S_TECHNICAL_DEPTH \
  --source SRC_ONBOARDING --question 'Does this describe your contribution?' \
  --answer 'I designed the format; two colleagues built the integration.'
python3 scripts/career_core.py bind-strength --pack data/candidates/career-v2.json \
  --strength S_TECHNICAL_DEPTH --output data/candidates/career-v3.json
```

Register the answer as a person source in the new pack and cite its excerpt.
`bind-strength` hashes only the named strength's supporting atoms; it never changes
its status. Use it after reassessment, not to suppress a stale warning. Ensure the
new version supersedes the actual previous pack, not a detached working copy;
the command preserves an explicit candidate metadata.supersedes when provided.
The `status` command exposes open questions and changed support without reopening
rejected interpretations or declined questions. A material change can be revisited
when the user explicitly resumes it.

Preferences require person-source answers and remain separate from evidence.
Role-specific motivation can remain in the existing role profile; do not copy it
into a general preference without the person's instruction. Pending interviews
never block generation from usable evidence.

## Prepare an output

Use a distinct brief ID per revision and preserve a stable `output_id` across
revisions of the same document. Use an application ID shared only by
outputs for that application, and an optional explicitly chosen role family.
Supported formats are resume, cover_letter, biography, linkedin, interview_brief,
and promotion_case. A role profile is optional for non-application formats.

```sh
python3 scripts/editorial.py init-brief --id platform-resume-v1 \
  --output-id platform-resume --application northwind-platform --role head-of-platform-engineering \
  --format resume --audience named_recipient --length 'two A4 pages' \
  --strength S_TECHNICAL_DEPTH --output data/briefs/platform-resume-v1-brief.json
python3 scripts/editorial.py prepare --brief data/briefs/platform-resume-v1-brief.json \
  --id platform-v1 --limit 12 --output data/selections/platform-v1-selection.json
```

Use the person's actual IDs; these command examples are placeholders. With legacy
packs omit `--strength`. `--preference` is repeatable. `instructions` is empty and
private by default; review it before setting the brief's `external_safe: true`.
This flag permits the instruction text into generation context, not factual claims.

Preparation retrieves role candidates plus eligible supporting evidence for the
brief's strengths and explicit priorities. Strength support can expand the limit;
the limit is a retrieval budget, not a mandate to lose sole evidence. The private `unavailable_priorities` and `strength_readiness` fields explain
why requested evidence or interpretations cannot enter the external view. Scores remain
retrieval aids. The workflow must curate this baseline into a useful small set,
recording recommended/reserve/omit, why, distinct contribution, limitations and
replacements. No script pretends to measure narrative quality.

Author a candidate selection in data/private, preserving its input pins, then
validate and save it with a new ID and optional supersedes pin:

```sh
python3 scripts/editorial.py save --kind selection --input data/private/curated.json \
  --output data/selections/platform-v2-selection.json
python3 scripts/select_evidence.py --selection data/selections/platform-v2-selection.json
```

Normal `make-resume` curates autonomously. `review-selection` is a separate optional
interactive preview. Acceptance requires a recorded answer and sets review_status,
but does not confirm requirement links or promote evidence. Unaccepted proposals
can still produce a document from the current career pack: these are editorial
selection proposals, not unreviewed career facts. The private interview format reads the full pack;
its selection record supplies provenance and priorities, not a sendable view.

## Scope feedback and preserve history

A decision names a subject (atom, strength or preference), action (include,
reserve, omit or retract), author, reason, date, source references and scope:

- output: stable output_id (older records fall back to brief_id);
- application: exact application_id;
- role_family: explicitly assigned family;
- person: literal ID `person`, only when a general preference was explicitly given.

User decisions require person sources. System decisions record autonomous editorial
judgments and cannot supersede user decisions. Among applicable decisions, user
choices take precedence, then the more specific scope. Conflicting choices at the
same precedence must be resolved with explicit supersession; timestamps never
silently choose a winner. Scopes must resolve to a saved brief; create the brief before saving its decisions.
A retraction supersedes the original decision in its
original scope. Do not broaden scope while superseding. Ineligible evidence always
stays ineligible, even if an old decision says include it.

```sh
python3 scripts/editorial.py save --kind decision --input data/private/decision.json \
  --output reviews/decisions/choice-v1-decision.json
```

Re-prepare selection after saving an applicable decision. Keep generation-facing
instructions separate from private reasons. Selection omissions do not change an
atom's evidence status. Publication changes belong on the atom; factual corrections
belong in evidence review. Saved general preferences remain editable rather than
permanently typecasting the person.

## Generate and review

Generation reads `select_evidence.py --selection`. This projects safe profile
interpretations and preferences using allowlists. A strength is excluded if
rejected, stale, unsafe, or any supporting atom is ineligible. It reaches the writer
only when all its support is selected. Raw answers, private reasoning, source
paths, and omitted confidential interpretations are absent. The writer still cites
atoms; preferences do not authorize achievement claims.

```sh
python3 scripts/manifest.py 'Head of Platform Engineering' \
  --selection data/selections/platform-v2-selection.json \
  --artifact outputs/platform-draft.md
python3 scripts/validate_records.py outputs/platform-draft-representation.json
python3 scripts/validate_records.py outputs/platform-evaluation.json
```

The manifest pins pack, artifact, skills, brief, selection, role and applicable
decisions. Optional `--settings <json>` records known model/runtime settings; never
put credentials there. New applicable decisions also invalidate the old context.
Do not rehash a changed input to make an old review look current.

`review-representation` records reader impressions before comparing the artifact
with the brief and eligible alternatives. Every intended strength receives a
status: clearly_represented, inadequately_represented, intentionally_omitted,
withheld, or unsupported. Clear representation requires an exact artifact excerpt
and supporting citations, plus human/model judgment that the meaning survives.
Presence of an ID or keyword alone is insufficient. An inadequate representation
must be revised or intentionally omitted with a saved rationale before publishable
can be true. Missing and withheld support remain reported limitations.

Keep integrity, role coverage, representation and reader quality separate. Preserve
the existing cold recruiter screen for application documents. Revise within the
existing cycle limits, reconcile conflicting advice against saved decisions, and
review the final text again. Publication restrictions cannot be negotiated away by
editorial feedback. Private briefs do not receive a sendability verdict.

## Validation

`make check` includes pack and record validation plus deterministic tests. The
editorial regression suite exercises fictional early-career, specialist, operator,
career-changer and technical-leader packs across shortening, retargeting,
corrections and regeneration. Model-driven scenarios separately assess whether
these records lead to good writing. Deterministic coverage is not a substitute
for that judgment; retain explicit unverified limitations when a model run cannot
be completed.


Run the bounded model checks explicitly (they use the configured Claude CLI login):

```sh
python3 tests/run_editorial_scenarios.py --scenario representation --budget 2 --report /tmp/representation-eval.json
python3 tests/run_editorial_scenarios.py --scenario formats --budget 4 --report /tmp/formats-eval.json
python3 tests/run_editorial_scenarios.py --scenario interview --budget 2 --report /tmp/interview-eval.json
```

Reports retain the temporary workspace path for inspecting the fictional artifacts.
No real career pack is read or changed by these scenarios.

Initial validation results, limits and exact tested skill hashes are recorded in
[the fictional evaluation report](../tests/results/editorial-2026-09-08.json).


## Save reviews without copying provenance

Create the final manifest once after the artifact is final, redirecting the exact
JSON from `manifest.py --selection <selection> --artifact <artifact>` to a file
under `data/private/`. Reuse that file for representation and integrity reviews.
The model writes only review content, without a `run` property, to a separate
body file under `data/private/`. Then assemble and validate it:

```sh
python3 scripts/save_review.py --kind representation --body data/private/representation-body.json --run data/private/run.json --output outputs/example-draft-representation.json
python3 scripts/save_review.py --kind evaluation --body data/private/evaluation-body.json --run data/private/run.json --output outputs/example-evaluation.json
```

Save representation first. Use `--replace` to refresh a disposable sidecar after
reviewing a changed artifact and generating a new manifest. The helper preserves
the exact run object and refuses stale inputs, mismatched artifact hashes, schema
errors and invalid publishability before publishing the complete file atomically.
One Markdown artifact is reviewed per manifest; HTML/PDF exports can accompany it.
A review that finds inadequate representation may be saved; its integrity record
cannot claim publishability until that finding is resolved.

Generation preserves the recommendation array order and applies scoped strength
omissions to writer context. Supporting atoms remain eligible for other claims.
Role-targeted briefs require the exact role file pin, including in archived run
freshness checks. Private briefs use `private_facts.py` for recorded dates and
measurement status; `validate_artifact.py --private` catches relative-age prose
and negative measurement statements without local explicit support. Name the
specific metric using its recorded text beside the evidence citation; a false
measurement flag for one metric does not describe every outcome in that atom. These
conservative checks supplement semantic review; they do not prove every sentence.
