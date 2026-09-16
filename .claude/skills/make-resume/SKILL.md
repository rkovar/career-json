---
name: make-resume
description: "Create or tailor a resume, CV, or cover letter from the approved career pack. Plans evidence, supports optional person review, generates the document, evaluates it, and delivers PDF, TXT and DOCX for resumes."
---

# Create a resume

Read `docs/resume-authoring.md`, `docs/resume-process.md` and `docs/editorial-memory.md`. The former owns
resume planning, authoring policy and PDF/TXT/DOCX delivery; the latter owns
immutable briefs, selection, scoped decisions and review provenance. Existing
career facts remain in Core. Never create a stronger fact through resume editing.

## Guided start

Use **Create a resume** as the user-facing path label. The `make start` launcher
routes here. For a named saved setup, resolve its latest revision and reuse its
answers or completed handoff. At a pause/handoff, show what is saved, the next
step and the exact `continue_prompt` from the startup report with the summary link.

For a first resume request with unclear direction, or a requested wizard, follow
`docs/operators/resume-start.md`. Reuse supplied targets and applicable saved choices;
a complete request can proceed without a questionnaire. Save the target, desired
impression, inclusion/de-emphasis preferences, application constraints and review
mode. Offer suggestions grounded in the pack; support skip, pause and edits.

Keep the brief while routing someone without an accepted pack through Core.
Resume the same setup after acceptance. Use the handoff's exact brief for selection
and carry its private preferences into the plan. Desired qualities are not facts;
wizard completion grants no selection or publication approval.

## Establish context and plan

Use the target supplied by the user or the applicable saved role profile. Ask for
the role only if it cannot be established. Reuse applicable preferences and record
employer requirements, user choices and inferred defaults in the brief. A standard
UK or US resume is supported; specialized applications need verified, recorded
instructions rather than presumed portal rules. All resumes require PDF, TXT and
DOCX even if the employer accepts just one of them.

Create/update a version-2 brief, run `editorial.py prepare`, and curate candidates
using `review-selection`. Ranking is retrieval, not career value. Read candidates
and select a complementary set: requirement coverage, distinct strengths,
ownership, context, technical judgment, people development and supported results.
`business_outcome`, output, activity, recency and corroboration are contextual
signals; none justifies discarding the only proof of a relevant strength.

Use `resume_workflow.py prepare`, curate a ready plan and save an immutable
revision. Explain intended reader impressions, direct/transferable/gap evidence,
section allocation, overlapping achievements, alternatives and omissions. Account
for every intended strength and role requirement. Distinguish missing evidence
from a document that communicates existing evidence poorly.

Recommend selection and own-voice checkpoints for a first-time user. Honor the
brief's review mode and explicit user instructions: automatic delivery proceeds
without intermediate approval; interactive delivery waits for the requested
review. Do not label a proposed system selection accepted by the person. The
private HTML review page supports conversational feedback. Ask focused questions
only when answers materially change the document; never repeatedly ask for facts
already recorded or force a numerical result. Route new answers through Core.

## Draft from safe evidence

Generate from `resume_workflow.py view --plan <path>`, which uses the validated
selection view. Private plan explanations, operator notes and review reasons do
not become external prose. Read safe strengths and evidence to realize the plan.
For other artifact types, use `select_evidence.py --selection <path>`.

Name the Markdown `outputs/<role_id>-draft.md` (cover letters use
`outputs/<role_id>-cover-letter.md`) so indexing and existing tools find it.
Take employer, title, dates and scope from eligible `employment` records; use
`career_span_years` for span claims. Preserve promotions, actual titles, sourced
context and chronology. A target headline must not imply the person held that
title. Explain unfamiliar names only from approved facts. The resume never
invents intent or a reason for a career transition.

For multiple positions within one employer tenure, use the derived
`resume_plan.employment_groups` and the structure in `docs/resume-employment.md`.
Show the employer and overall tenure once, followed by compact title/date rows
in reverse chronology. Put shared achievements under an explicit Career highlights
subsection. Use dated role subsections only when they have dedicated content;
never leave empty role headings or give one title the whole employer tenure.
Preserve separate return stints. Position changes alone do not establish promotion.

Write experience first: personal action, concrete work, useful method/context,
and defensible result or scope. Respect `constraints`, metric basis, shared
ownership and `occurred`. Supported output, prevention, service and technical
judgment can be valuable without financial metrics. `role_fit_notes` describe
contextual concerns, not universal exclusion rules. Avoid double-counting one
project through several atoms or summing shared outcomes.

Allocate space by contribution to the brief. Preserve relevant older work; no
fixed bullet counts, age cutoff or required summary. Write the summary last if
it adds understanding, backed by evidence in the body. Retain enough context for
claims to be credible and interviewable. Use precise natural wording and safe
person-sourced voice preferences. Run `keyword_coverage.py` only as a diagnostic;
use terms where the selected evidence supports them.

Use `# Name` (or neutral applicant label for an anonymous application), optional
clearly labeled target headline, contact paragraph when appropriate, and ordinary
sections. Standard contact details are for a named recipient; public and anonymous
instructions change the contact block. Do not place draft status, gaps, private
notes or publication warnings inside the artifact. Draft status never appears
inside the artefact. Missing contact is a delivery problem only when the actual
submission context requires it.

Keep `<!-- Evidence: E_X -->` at the end of the claim's own line or directly on
an **indented continuation line** without a blank line. An unindented comment
after a bullet is an orphan citation and must be fixed in the Markdown. Never add unsupported causation, comparisons,
motives, negative assertions, metrics or scope. Cite recorded URLs for public
work; do not infer URLs. STAR is evidence, not a sentence template.

## Review, revise and export

Run `evaluate-output` and `review-representation`, then `recruiter-screen` in a
fresh context when available. Pass only artifact, role and safe application
constraints to the screen, without the plan's intended impressions. If a fresh
context is unavailable, label the screen `"context": "shared"`. The cold reader
first states what they understood; then compare this with the plan.

Resolve actionable findings within existing facts and publication choices. Track cycles and categorized findings in the pinned process record. Use the
default limit of two editorial revision cycles unless the user explicitly changes it; never manufacture evidence
to obtain a favorable verdict. After shortening or retargeting, run
`resume_workflow.py compare`, inspect changed claims for loss of ownership,
context, method, timeframe and strength support, and save material tradeoffs.
Rebuild stale selections/plans and re-review the final text.

Render internal HTML with `render.py`, validate with `validate_artifact.py --plan`,
and export all three formats with `export_resume.py --plan`; read
`docs/resume-exports.md`. Inspect final PDF page breaks, typography and recovered
text. Report Word pagination or accessibility checks as unverified unless actually
performed. Export failures complete with explicit limitations, never false success.

Use `manifest.py --selection --plan --artifact --exports --process` with actual paths.
Save representation and evaluation through `save_review.py` with the same exact
manifest. A planned resume cannot be marked publishable without all three verified
exports. Changed input or export bytes invalidate prior approval. Regenerate the
artifact index, and return links to PDF, TXT and DOCX plus separate integrity,
representation, relevance, reader-quality and delivery findings. Explain material
omissions, inferences and remaining questions privately. No hiring probability or
ATS-pass claim is supported by these checks.

## Preserve the review across drafts

Follow `docs/resume-process.md`. Before drafting, record each impression's intended
prominence and compare it with restricted strengths, including impressions with
empty `strength_ids`. Review the exact guidance fingerprint after those checks.

For each version, use `resume_process.py prepare` and `packet`; complete the
per-claim ownership, chronology and individual source-constraint checks. Capture
reader observations before comparing with the plan, then assess prominence. These
are assistant review tasks, not a mandatory person questionnaire. Never auto-pass
a generated checklist or treat mechanical coverage as proof of meaning.

When shortening is requested or length remains a finding, attempt and measure an
equivalent-content compression before proposing evidence removal. Record the
candidate and semantic preservation review. Carry outstanding findings through
`--previous` and preserve immutable draft snapshots. Use the derived cycle count;
never claim the budget is exhausted while cycles remain. An unresolved editing
finding prevents publication even after the budget is spent.

Pin the completed process in the final manifest. Import actionable screen findings
into its next revision and re-evaluate changed text. Generate continuation notes
with `resume_process.py handoff`, linking the matching evaluation when available.
Do not author mandatory career claims, timeline gaps or remaining-cycle totals
from memory. Explain optional decisions as decisions, not policy.

## Other formats

**Cover letter:** three or four concise paragraphs addressing `central_requirement`,
with evidence references and accurate motivation. Avoid repeating the resume.
**LinkedIn:** first person with public audience constraints. These formats reuse
durable selection and review, but do not require a resume plan or three exports.
**Interview preparation:** use `make-interview-brief`, whose private view includes
evidence unavailable for publication. It is a separate workflow.

## Editorial quality and omitted evidence

Follow `docs/resume-quality.md`. Rank examples for their contribution to this role,
then inspect the combined set and the eligible alternatives in the process packet.
Complete version 2 opening, language, focus, contribution and metric-value reviews
with reasons and located passages. Inspect recent work without imposing a recency
quota. Distinguish unselected evidence from an actual evidence gap before asking
optional questions; respect saved omissions and keep new facts in Core review.

After export, use `resume_process.py layout` to attach the exact bundle. Inspect
the PDF, record actual visual observations, and resolve or explain each page
diagnostic. Pin the completed process for publication. Preparation and successful
export never substitute for editorial or visual judgment.
