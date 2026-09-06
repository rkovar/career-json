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
- Conflicting source values are not silently resolved.

### Safety and privacy

- No `external_safe: false` evidence appears in public text.
- Internal names, systems, identifiers, and confidential details are scrubbed.
- The contact block matches the stated audience: full details for a named
  recipient, name and location only for a public artefact. A missing contact
  block on a document meant to be sent is a blocker, not a nicety.
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
- The document is not carried by `activity` metrics. If the strongest claims all
  measure workload rather than consequence, say so: hiring managers discount them.
- No evidence flagged in `role_fit_notes` as a negative signal for this role is
  given prominence.
- Where the target role's central requirement has no eligible evidence behind it,
  that is a blocker, not a warning. Name it as the likely reason for rejection.

### Background-check exposure

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

## Decision

Write a machine-readable evaluation record with `publishable: true` only when
there are no material failures. `publishable: true` means fit to send, not likely
to succeed. Hand the artefact to `recruiter-screen` before telling the user it is
ready. Each finding must include severity, category, affected evidence ID or output section, and remediation.