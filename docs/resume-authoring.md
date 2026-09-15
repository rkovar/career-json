# Resume authoring workflow

The approved career pack remains the factual source. A resume plan, selection,
wording preference, and rendered document are application records. None can
promote an inferred claim into the pack. The versioned policy is
[resume-authoring.json](policies/resume-authoring.json). Its sources are supplied
research memos, with their population and system limitations preserved. Standard
UK and US modes are implemented; specialized portal requirements must be verified
and recorded as employer instructions before being enforced.

```text
Pack + application brief -> selection -> resume plan
                                             |
                                optional person review
                                             |
                                  draft -> shared document
                                             |
                                 PDF + TXT + DOCX exports
                                             |
                       integrity / representation / reader / file checks
                                             |
                              delivery + durable decisions

New facts -> Core candidate review -> new approved pack
```

## Application and evidence planning

`editorial.py init-brief` creates a version-2 resume brief. Supply `--market UK`
or `--market US` when known and `--review-mode interactive` when the person wants
checkpoints. Each application setting has an origin and reason. Edit a candidate
brief to record explicit employer/user instructions, then save with `editorial.py
save`. Page limits are positive integers or null; never infer a precise limit
from a country's convention. A4/Letter are contextual defaults. All three exports
are required regardless of which one the employer accepts for submission.

First-time users should be offered a selection review and an own-voice review.
Respect explicit automatic delivery and previously saved preferences. Ask focused
questions only when answers materially change the document; otherwise draft
narrowly and disclose gaps privately. Never wait for an optional review the person
has declined. An interactive checkpoint requires an actual reply before recording
acceptance. Proposed system choices are usable in automatic mode and are never
labelled user-approved.

Interactive selections can be prepared and shown for review while proposed, but
generation, ready-plan validation, manifests and planned exports require an
accepted selection with valid person source references. Automatic mode continues
to allow proposed system selections.

```sh
python3 scripts/editorial.py init-brief --id example-v1 --application example --market UK --output data/briefs/example-v1-brief.json
python3 scripts/editorial.py prepare --brief data/briefs/example-v1-brief.json --id example-v1 --output data/selections/example-v1-selection.json
python3 scripts/resume_workflow.py prepare --selection data/selections/example-v1-selection.json --id example-v1 --output data/plans/example-v1-plan.json
```

The prepared selection and plan are starting proposals. Inspect every candidate,
curate the selection and save immutable revisions. Judge the combined set:
requirements, distinctive strengths, ownership, relevant older work, technical
judgment, prevention, service and people development. Outcomes, recency and
keyword scores are retrieval aids, not universal measures of value. Record what
each example adds and explain useful alternatives. Overlap detection flags likely
shared projects/results; an editor decides whether to combine, distinguish or
omit them. Never total a shared result twice.

Edit the plan as JSON in `data/private/`, then save with:

```sh
python3 scripts/resume_workflow.py guidance --plan data/private/curated-plan.json
python3 scripts/resume_workflow.py save --input data/private/curated-plan.json --output data/plans/example-v2-plan.json
python3 scripts/resume_workflow.py review --plan data/plans/example-v2-plan.json --output reviews/example-v2-selection.html
python3 scripts/resume_workflow.py check --plan data/plans/example-v2-plan.json
python3 scripts/resume_workflow.py view --plan data/plans/example-v2-plan.json
```

Before saving a ready plan, inspect the private `guidance` preview: intended
impressions, direct/transferable/gap qualifications, requirement assessments,
employer instructions, section allocation and submission channel. Remove private
details from these drafting fields, retaining private rationale in tradeoffs and
section/summary reasons. Complete the private strength comparisons and intended
prominence described in [resume-process.md](resume-process.md). The fingerprint
also binds those comparisons and their restricted source context. After inspecting
the exact preview, copy its
`drafting_review_sha256` into the candidate plan. This is an editorial check the
assistant can perform in automatic mode, not acceptance on behalf of the person.
The command only previews; it does not record approval. Changed guidance requires
another review. Older ready plans without this fingerprint need a reviewed new
revision before generation or export; their saved history remains intact.

A ready plan has a new ID, `status: ready`, and an explicit `supersedes` pin when
revising. Obtain exact references with `resume_workflow.py pin --path <path>`;
do not reconstruct hashes manually. It pins its selection and policy, accounts for intended strengths,
allocates selected evidence to sections and assesses every saved role requirement.
Direct/transferable impressions need selected support; transferable evidence needs
its limitation stated; gaps cannot pretend to have support. These checks verify
references, not semantic truth. The author must still inspect every claim.

The review page is a readable private document, not an approval form. The person
can respond conversationally. Save selection acceptance with person source refs,
and inclusion/omission decisions with explicit scope through `editorial.py save`.
Rebuild selection and plan after a decision changes. The safe generation view
excludes private rationales and review reasons. It retains the exact reviewed
guidance, approved strengths, underlying evidence and safe formatting settings.
Guidance constrains writing; it cannot establish new career facts.

## Writing and revision

Explain the setting when it helps the reader understand an achievement, using
only approved employer/scope facts or selected evidence. Translate internal jargon
without adding claims. Preserve promotions and distinguish actual job titles
from the application target. For multiple positions within one employer tenure,
use the [grouped employment structure](resume-employment.md): one employer heading,
compact dated position rows and explicitly scoped achievements. Do not invent reasons for transitions or conceal
gaps. Describe ownership, concrete work, useful method/context and defensible
result or scope. No requirement exists to fabricate a business metric.

Draft experience first. Write a summary last only if it adds understanding;
corroborate its claims in the body. Avoid generic adjectives, repeated achievements
and stale claims of current technical work. Allocate space by the relevance and
distinct contribution of evidence; no fixed number of bullets or age cutoff.
Public links must be recorded URLs. All export formats show the same URL text.

After shortening or retargeting, save the old draft and run:

```sh
python3 scripts/resume_workflow.py compare --before outputs/example-v1-draft.md --after outputs/example-draft.md --plan data/plans/example-v2-plan.json
```

The report surfaces removed evidence, lost strength support and rewritten claims,
including removed ownership/timeframe qualifiers. It is a review queue, not a
semantic entailment verdict. Review contribution, technical method, ownership,
timeframe, metric boundaries and scope. Resolve loss or record a scoped tradeoff.
Existing representation review still requires passage-level proof. Each quoted
passage must be visible in a block containing the evidence cited by that review;
an evidence reference elsewhere in the document or text inside a hidden comment
does not establish representation.

## Learning from feedback

New facts and corrections go through Core candidate review. Strength changes go
through strengths review. Application inclusion choices stay editorial. Wording
preferences use existing editorial decisions with `subject.kind: wording`, a stable
subject ID, `wording: {text, external_safe}`, and person source refs. `include`
means prefer this wording; `omit` means avoid it; `retract` withdraws the preference.
Only a user decision may record a wording preference. The private `reason` explains
why. The safe view includes only explicitly external-safe examples and prefer/avoid
instructions; examples cannot supply career facts. Scope and supersession work
as for other decisions. Recheck evidence when reusing previously approved wording.

## Delivery and review

See [resume-exports.md](resume-exports.md) for required PDF/TXT/DOCX delivery.
Use one exact manifest for representation and integrity reviews:

```sh
python3 scripts/manifest.py "Target role" --selection data/selections/example-v2-selection.json --plan data/plans/example-v2-plan.json --artifact outputs/example-draft.md --exports outputs/example-v2-export/review/export-report.json --process outputs/example-v2-process.json
```

Review accuracy, representation, relevance, readability and delivery separately.
A fresh reader first records what they understood, then the representation review
compares that impression with the plan. A fresh screen receives only the artifact,
role and safe application constraints; no pack, selection rationale or desired
impressions. If a fresh context is unavailable, label the screen shared. No fixed
scan-time claim, career-gap penalty, linear-promotion requirement, financial-metric
quota, title matching requirement or hiring-probability prediction is justified.

A ready resume requires final content review plus verified exports. Export checks
alone do not approve facts or visual quality. Record manual PDF inspection and
own-voice feedback honestly; unknown observations stay unmeasured. A changed plan,
policy, selection, brief, applicable decision, draft or submitted file invalidates
previous approval. Preserve the existing bounded editorial revision cycle.

## Durable process review

Follow [resume-process.md](resume-process.md) for exact-draft constraint checks,
reader prominence, compression attempts, revision accounting and generated
handoffs. These assistant checks are required before planned-resume publication;
they do not create additional mandatory user checkpoints.

## Editorial quality and page review

Follow [resume-quality.md](resume-quality.md) for role-sensitive selection, explicit
editorial questions, review of omitted eligible evidence, PDF geometry diagnostics
and the visual review required for the exact exported bundle. These extend existing
process records; they never promote application judgments into career facts.
