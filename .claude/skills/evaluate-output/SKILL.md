---
name: evaluate-output
description: "Called by `make-resume`, which is the normal entry point. Use directly only to run the integrity review alone on a resume, CV, cover letter, website, or LinkedIn content. Shortlistability is `recruiter-screen`, not this."
---

# Evaluate Generated Output

## Scope

This skill checks integrity: whether the artefact is true to the pack, safe to
send, and free of internal leakage. It does not judge whether the document would
win an interview. That is `recruiter-screen`, which runs after this one and reads
the artefact cold as a stranger. Passing here is necessary and not sufficient.

## Required checks

### Factual grounding

- Every substantive claim maps to evidence IDs.
- Every employer, job title, and date traces to an `employment` record. These
  carry no evidence ID, so nothing else catches them, and they are exactly what a
  background check tests. Any span claim such as "N years of experience" must
  match `career_span_years`.
- `employer_of_record`, where it differs from `employer`, is interview and
  reference material and never artefact text.
- Every metric, date, title, employer, and outcome is supported.
- STAR meaning has not changed during compression or tailoring.
- Review connecting prose and contrasts as factual claims too. Unsupported
  causes, motives, comparisons and negative assertions are integrity failures
  requiring revision, even when described as "interpretive framing". Adoption
  does not prove voluntary uptake or absence of a mandate; absent metric
  records do not prove that measurement never happened. For each such clause,
  identify direct support or remove it before marking publishable.
- Current-tense claims agree with `occurred`; historical work is not presented
  as current maintenance, production use, or recent domain experience.
- Conflicting source values are not silently resolved.

### Safety and privacy

- No `external_safe: false` evidence appears in public text.
- Internal names, systems, identifiers, and confidential details are scrubbed.
- The contact block matches the stated audience: full details for a named
  recipient, name and location only for a public artefact. Apply the brief
  contact mode and submission instructions. Anonymous applications suppress identity;
  a portal may already carry contact details. Missing required contact is a delivery
  blocker, not a judgment of capability.
- No street address or photo reference in either case.

### Sendability

- No draft status, publication warning, or note about withheld or pending
  evidence appears anywhere in the artefact.
- No internal vocabulary leaks into candidate-facing prose: no evidence IDs in
  visible text, no `self_asserted`, no "pending confirmation", no "withheld".
- The document can be forwarded as-is without embarrassing the subject.

### Target fit

- Relevant job requirements are addressed with evidence, not keyword stuffing.
- ATS terms are used naturally.
- Requested persona, length, and format are satisfied.
- Evaluate contribution and significance in context. Technical judgment, prevention,
  service, scope and people development can provide strong evidence without a
  numerical business outcome.
- No evidence flagged in `role_fit_notes` as a negative signal for this role is
  given prominence.
- Where a central requirement lacks eligible support, report a role-coverage gap.
  Do not invent rejection probabilities or conflate missing fit with factual error.
- Assess each component of a compound essential requirement separately. A linked
  atom or a high `role_fit.py` score does not establish every component: team
  leadership does not imply budget ownership, and output does not imply adoption.
  Record material unmet essential components as relevance findings. Distinguish absent
  evidence from evidence deliberately withheld under publication constraints.

### Background-check exposure

For multiple positions at one employer, check the hierarchy in
`docs/resume-employment.md`: one heading per tenure, actual titles with their own
dates, no omitted/duplicated positions in a grouped tenure, no empty role
subsections, and an explicit scope for achievements spanning positions. Check
the PDF keeps employer headings and title/date progressions with their content.
Do not describe the whole employer tenure as time spent in the latest title.

Corroboration of achievements is **not** checked here: `self_asserted` evidence is
normal and is not a finding. What is checked is the material a background check
actually touches.

- Every employer, title, and date matches an `employment` record.
- An `employer_of_record` that differs from the employer on the page is recorded
  in the pack, so it cannot surprise the subject at offer stage.
- No employment record cited by the artefact has an unknown `end` date.

### Artefact kind

The checks above assume a document sent to a named recipient. Apply the extra
rules for what was actually produced.

**Cover letter.** One claim per paragraph, each carrying an evidence ID. It must
not restate the resume, and must not express enthusiasm, cultural fit, or
motivation the evidence does not support. Address the role profile's
`central_requirement` directly or say why it cannot.

**LinkedIn About, headline, or post.** First person. Audience is `public`, so the
contact block is name and location only and an email or phone in the text is a
blocker. No employer-internal framing, no team-scale or budget detail that reads
as internal, and nothing whose `external_safe` is false. Remember it is
permanently indexed and read by the current employer.

**Personal site or public CV.** As above, plus: no `employer_of_record` detail, and
no date precision beyond what the employment records support.

### Human quality

- The writing is specific, credible, and natural.
- No generic AI phrasing, inflated claims, repetition, or empty adjectives remain.
- Missing outcomes are visible rather than invented.
- The opening states relevant value, each bullet has one principal achievement,
  and scope supports the requested role. Public-work references identify the work.
- Verify requested page count and heading/bullet placement from the final PDF,
  and inspect extracted text. Record the actual checks and any unverified export
  limitations; HTML validity and word counts do not establish print quality or
  compatibility with a specific ATS.

## Representation and input freshness

For a generation with a durable brief, run `review-representation` and save its
sidecar with the same final manifest `run`. Every intended strength needs a
representation disposition. Resolve inadequate representation by revision or a
saved, justified omission before marking publishable. Withheld or unsupported
strengths remain explicit report limitations; they do not authorize a stronger
claim. Keep this assessment separate from integrity, role coverage and reader
quality. A cited atom alone does not prove successful representation.

Validate the evaluation and representation records with `validate_records.py`.
Use `manifest.py --selection` so changed briefs, roles, decisions and selections
invalidate prior reviews. Re-evaluate after editing; old positive reviews do not
approve new text. See `docs/editorial-memory.md`.

## Decision

Write the evaluation body without `run` in `data/private/` and assemble it with
`scripts/save_review.py --kind evaluation`, using the same saved manifest as the
representation sidecar (see `docs/editorial-memory.md`). Do not copy provenance
fields by hand. Set `publishable: true` only when
there are no material failures. `publishable: true` means fit to send, not likely
to succeed. Hand the artefact to `recruiter-screen` before telling the user it is
ready. Each finding must include severity, category, affected evidence ID or output section, and remediation.

## Planned resumes and exports

Read `docs/resume-authoring.md` and `docs/resume-exports.md`. Compare the final
artifact to the ready resume plan, including intended impressions and section
allocation. Review overlap groups and repeated outcomes, jargon/context, accurate
progression, summary support and person-sourced voice preferences. After shortening,
inspect `resume_workflow.py compare` findings; it cannot establish semantic equivalence.

Keep accuracy, representation, relevance, readability and delivery findings separate.
A factual error or confidentiality leak blocks integrity; missing role evidence
is a relevance limitation; a failed export blocks delivery. A planned resume needs
PDF, TXT, DOCX and Markdown, with matching recovered content and export hashes. Manually inspect
PDF layout; distinguish that observation from DOCX structure and unverified Word
pagination. Use `manifest.py --plan --exports --process` along with selection and artifact.

For planned resumes, read `docs/resume-process.md` and complete the exact-draft
process checks. Review each source constraint separately, checking the action's
object: credit for co-authoring a dataset does not preserve co-creation of its
program. Verify named collaborators for each named work. Inspect literal title
tenure and event dates, including company-wide work crossing promotions.

Require the process's claim and prominence checks, compression review when
shortening was requested, and consistent revision accounting. Record actionable
findings in its categorized ledger. Use `manifest.py --process` with the final
review record. Passing reference, schema and excerpt checks is not semantic proof.
Do not change truthful prose to conceal an export extraction problem; PDF physical
wrap reconciliation is bounded and separate from TXT/DOCX verification.

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
