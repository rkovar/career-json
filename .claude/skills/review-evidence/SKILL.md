---
name: review-evidence
description: "Called by `build-career-pack`, which is the normal entry point. Use directly only to run evidence review alone, or when reviewing a single new claim, achievement, metric, or datapack that may be weak, vague, inflated, or consequential."
---

# Review Evidence Socratically

## Goal

Improve the truth and the commercial usefulness of a claim without supplying
invented answers. A claim that is true but unpersuasive has failed, and so has a
claim that is persuasive but cannot be defended in an interview.

## Questions

Ask only the questions needed to resolve the claim.

### Grounding

- Situation: What was happening, and why did it matter?
- Task: What were you personally responsible for?
- Action: What did you personally do, rather than what did the team do?
- Result: What changed, and how do you know?
- Scope: How many people, systems, teams, regions, or users were affected?
- Timeframe: When did this happen?
- Measurement: Is the result measured, observed, estimated, or still unknown?

### Corroboration, only when asked for

Corroboration is **not a requirement** of this workspace. Do not ask these
questions in a normal review, and never treat an empty `corroborators` array as a
finding. Most claims will stay `self_asserted`, and that is the expected resting
state, not a deficiency.

Ask only when the user requests a corroboration pass, or when a claim is both
consequential and cheap to check:

- Is there a public artefact, record, or system that already shows this?
- Who, by role, would confirm it, if you happen to know?

Record answers in `corroborators` when they arrive. Never chase them.

### Commercial consequence

- What changed for the organisation, beyond the work being done?
- Did this reduce risk, cost, or time, or enable revenue or delivery? By how much?
- If the honest answer is that the outcome was never measured, say so and set
  `outcome_type` accordingly. Do not reach for a number.
- Where does this claim count against the subject? A metric that proves reach can
  read as a negative signal for a hands-on role. Record that in `role_fit_notes`.

## Evidence status

Assign against what the sources actually are, not how confident the subject is.

- `self_asserted`: appears only in material the subject wrote. A claim repeated in
  a resume and a LinkedIn profile is still `self_asserted`. Repetition is not
  corroboration, and treating it as such is the most common failure in this
  workflow.
- `corroborated`: a named third party or public artefact supports it, but no
  auditable record has been captured.
- `externally_verified`: supported by an independent source recorded in
  `source_records` with `independent: true`. For a public page, capture the URL
  and the date retrieved. Without a recorded source it is `corroborated`, not
  this.
- `unresolved`: an open question. Record the question.
- `declined`: the subject chose not to pursue it. Record that they declined.

## Rules

- Do not turn a vague assertion into a precise metric.
- Do not treat team activity as individual ownership without clarification.
- Do not convert throughput into business impact. Throughput is `activity`.
- Do not promote status because the subject answered confidently. Status is a
  property of the sources, not of the answer.
- Record unanswered questions as `unresolved` and declined answers as `declined`.
- Approval requires complete STAR fields and provenance. Publication safety is a
  separate decision.

## Corroboration backlog, on request only

If the user asks for a corroboration pass, `python3 scripts/corroboration_plan.py`
ranks what is worth chasing and states the specific ask. Prefer the wins that cost
minutes rather than a phone call: an atom already `corroborated` needs only its URL
recorded. Do not run this unprompted.

## Output

Write a review record containing the evidence ID, questions, answers, status,
corroborators identified, conflicts, and approval decision. Include a concise
recommendation for the next action.
