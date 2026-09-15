# Repeatable resume quality review

The career pack holds facts and reviewed strengths. A resume chooses how to
communicate them. This process records the checks and decisions that would
otherwise disappear between drafts. It applies to any career, without fixed talk
counts, compulsory metrics, or a universal two-page limit.

The assistant performs these editorial checks. They are not a questionnaire for
the person. Ask only for missing facts or a consequential preference that the
existing brief cannot settle. Honor automatic or interactive delivery as recorded.

```text
Approved pack + brief
          |
Selection + plan -- privacy comparison + intended prominence
          |
Versioned draft --> reader observations (before viewing the plan)
          |                    |
          +------ claim and prominence review
                               |
                   compress / revise when needed
                               |
                    PDF + TXT + DOCX verification
                               |
                    final reviews + generated handoff

New facts --> Core review --> new approved pack
```

## Before drafting: privacy and emphasis

Choose `prominence: leading|supporting` for each plan impression. The first
prepared impression defaults to leading and the others to supporting; curate that
choice for the application. Leading means a reader should notice and remember it,
not merely find it after searching. No strength must lead every application.

Compare each impression with each restricted strength in `privacy_reviews`, even
when the impression has `strength_ids: []`. Use `excluded_interpretation` when
the restricted interpretation is absent, or `independent_evidence` when the new
message follows from eligible facts without carrying the restricted interpretation.
Give a substantive reason referencing the facts and the distinction in meaning.
Do not replace a private interpretation with a synonym and call it independent.
If uncertain, narrow the statement to the approved action or request a Core
strength/publication review. This record cannot grant publication permission.

`resume_workflow.py guidance` supplies the restricted context privately. Add a
comparison row for each new impression/restricted-strength pair when curating the
plan. A ready plan rejects missing or pending comparisons and verbatim reuse of a
restricted interpretation. The guidance fingerprint binds both the comparison
and the exact restricted context. Semantic paraphrases still need reviewer judgment.
Neither private comparisons nor their reasons enter the writer's safe view.

## Review the exact draft

Keep versioned draft snapshots. Never overwrite a draft referenced by an earlier
process record. Start one process chain for the application; preserve it through
changes to selections and plans. Do not restart the chain to reset its budget.

```sh
python3 scripts/resume_process.py prepare --artifact outputs/example-v1-draft.md --plan data/plans/example-v2-plan.json --output outputs/example-v1-pending-process.json
python3 scripts/resume_process.py packet --artifact outputs/example-v1-draft.md --plan data/plans/example-v2-plan.json
```

Preparation leaves all checks pending. The private packet locates blocks, shows
word counts/positions, and includes the selected safe evidence and employment
records. Copy the pending record to `data/private/` to complete the review; save a
new version with `resume_process.py save`. Do not hand-edit hashes or auto-fill
every status with pass.

Each cited block gets ownership and chronology checks, plus a separate check for
**every source constraint**. Headings and uncited paragraphs also get a chronology
and scope check. Preserve generated IDs, source text and evidence lists. For each
check, record `pass` or `issue`, an exact visible excerpt from that block, and a
reason explaining how the passage satisfies or violates the source.

Assess the subject, action and object of each claim separately. “Created the
program and co-authored its dataset” does not preserve co-creation of the program.
Crediting one talk's co-presenter does not credit a different talk's collaborators.
Check metric basis, qualifiers, prototype/production distinctions and individual
versus team contribution. A citation or a matching word cannot prove entailment.

Use the [employer-level hierarchy](resume-employment.md) for multiple positions
in one tenure. Compare event dates with the role actually heading the passage. A promotion chain
does not give its latest title the whole employer tenure. Put work spanning roles
in an explicit `### Employer | Career highlights | Dates` section, alongside
literal role headings, or distribute it accurately. Definite date conflicts block
completion; year-only and inferred dates retain their uncertainty and need review.
An atom's incorrect employment link requires a Core correction. Adjacent end/start
months are not evidence of an employment gap. A valid career-span number is
optional unless the brief explicitly requires it.

## Presence is not prominence

Record `cold_read.impressions` before comparing with the plan. Use `context: fresh`
only if the reader had the artifact and safe application context alone. Otherwise
record `shared`; staged reading in the writer's context is not independence.

For each planned impression, locate the blocks, record observed prominence and
explain the result. `reader_impression_indexes` are zero-based references to those
initial observations. A leading impression must emerge in the reader observations;
an atom hidden in a dense bullet is insufficient. Assess space, placement,
distinctness and surrounding competition. Word positions aid inspection without
imposing a universal top-third cutoff. Cite the exact passage in the separate
representation record as well.

## Compression and revision accounting

When shortening is requested or a length finding remains, prepare the next review
with `--compression-target "<actual target>"` and `--previous <prior-process.json>`.
First remove repetition, simplify phrasing, split overloaded claims and rebalance
space. Try an equivalent-content candidate before recommending removal of sole
evidence. Do not weaken ownership or remove context just to satisfy a word count.

Record `compression.status: attempted`, exact `baseline` and `candidate` pins,
and an assessment of the measured result. The candidate must be the reviewed
draft. Review all six `meaning_review` dimensions: ownership, context, method,
timeframe, scope and strengths. A no-op is not an attempt. Keep rejected candidates
and their issues as separate process records; continue the same revision chain.
The generated handoff computes before/after word counts. Actual page counts come
from the PDF export report; word reduction does not establish pagination.

If a shorter candidate still fails the actual target, report that result and the
remaining tradeoff. Do not claim all possible compression is exhausted or that
deletion is the only solution. Optional alternative emphases can be shown to the
person with reasons; their choice stays application-scoped unless they say otherwise.

The initial draft uses zero editorial revision cycles. Each changed draft in the
`supersedes` chain uses one; re-reviewing identical bytes uses none. The default
limit is two, with a different budget allowed only for an explicit user instruction
recorded in `budget_origin` and `budget_reason`. History and previous draft hashes
are checked. Outstanding findings carry forward until resolved or explicitly
deferred; they cannot silently disappear.

Classify each finding as `editing`, `user_choice`, or `new_evidence`, with its
disposition and reason. Import actionable evaluation and screen findings into this
ledger before the next cycle. `prepare --previous` automatically imports the prior
draft's screen sidecar when present; repeat `--feedback <review.json>` to import
other evaluations, representation reviews or a same-draft screen. Imported work
lists keep exact source keys and descriptions. Their source pins and ledger
coverage are checked, so deleting an unresolved item cannot silently clear it.
Keep immutable feedback snapshots; do not overwrite a pinned review to refresh
its manifest. Final delivery sidecars can be assembled separately from those
snapshots. Classify imported integrity/representation findings more specifically
when appropriate, retaining their source keys. Routine writing issues remain editing work. Missing
facts go to Core. `budget_exhausted` is invalid while cycles remain, and does not
waive editorial failures. Open user choices and evidence questions also require
resolution or explicit deferral as a limitation before publication. Stop honestly
with an incomplete draft if necessary.

```sh
python3 scripts/resume_process.py prepare --artifact outputs/example-v2-draft.md --plan data/plans/example-v2-plan.json --previous outputs/example-v1-process.json --compression-target "Meet the brief's page target" --output outputs/example-v2-pending-process.json
python3 scripts/resume_process.py save --input data/private/example-v2-reviewed-process.json --output outputs/example-v2-process.json
python3 scripts/resume_process.py check --process outputs/example-v2-process.json
```

`check --allow-incomplete` and `save` accept a consistent unfinished record.
Ordinary `check` enforces completed claim/prominence reviews, compression evidence
when requested, and no unresolved editing findings. Mechanical checks establish
coverage and consistency; they do not replace a competent semantic review.

## Final records and handoff

Export the final draft, inspect its PDF, and save one exact manifest with selection,
plan, artifact, exports **and `--process`**. Use it for the representation and
evaluation records. A planned resume cannot be marked publishable without a valid
completed process review and all three verified exports. A later screen may expose
new issues: record them, revise within budget and regenerate the final records.
Keep reviewer context honest; fresh readers are useful when available and allowed.

```sh
python3 scripts/manifest.py --artifact outputs/example-v2-draft.md --selection data/selections/example-v1-selection.json --plan data/plans/example-v2-plan.json --exports outputs/example-v2-export/review/export-report.json --process outputs/example-v2-process.json
python3 scripts/resume_process.py handoff --process outputs/example-v2-process.json --evaluation outputs/example-v2-draft-evaluation.json --output outputs/example-v2-HANDOFF.md
```

Use the actual matching selection and save the emitted manifest; do not retype it.
The handoff starts with remaining work, links to the records, derives cycle counts
and content measurements, and labels reviewer judgments separately. Delivery claims
come only from a matching validated evaluation/export report. Without an evaluation,
the handoff explicitly says delivery and publishability are unverified. It does not
invent timeline gaps, mandatory career claims, or ATS success.

These records and packets are private working material. Submit only the exported
files. Existing drafts and reviews are never rewritten automatically. Older ready
plans need a newly reviewed guidance fingerprint; older publishable evaluations
without a process record do not satisfy the strengthened workflow.

## Editorial quality and page review

Follow [resume-quality.md](resume-quality.md) for role-sensitive selection, explicit
editorial questions, review of omitted eligible evidence, PDF geometry diagnostics
and the visual review required for the exact exported bundle. These extend existing
process records; they never promote application judgments into career facts.
