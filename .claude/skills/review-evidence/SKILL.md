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
- **A re-typing only holds if the specific change can be written into
  `star.result`.** If the sentence cannot be written from what the subject
  actually said, the atom keeps the type it had. This single test is what stands
  between a review and an inflation engine: applied honestly it rejects most
  candidates, and a review that promotes everything has stopped being a review.
- An answer is a source. Record it as one: a `source_type: "person"` record dated
  to the conversation, pointing at the review record, cited by every atom the
  answer created or changed. An atom that cites nothing cannot be told apart from
  one invented by a persuasive question.

## Running an iterative review session

Batch the questions during ingestion, because a run that blocks leaves the pack
half-written. **Reviewing evidence is the opposite and must not be batched.** A
numbered list of twenty questions gets abandoned at the fourth; the same twenty
asked one at a time get answered, because each answer visibly moves something and
because the interesting questions only exist once an earlier one is answered.

Run `python3 scripts/open_questions.py --json` for the queue. It ranks by what
answering unlocks rather than by pack order, so work from the top.

1. **Ask one question. Wait. Then ask the next.** Never present a list. The
   follow-up is usually worth more than the original: "is there a budget?" answered
   "no" is a dead end, and "no separate line" followed by "is there any budget
   dimension at all?" found spend influence that moved a verdict.
2. **Give every option its consequence**, not just its label: what would be
   recorded, what it would unlock, and what it would cost. The subject is deciding
   about their own record and needs to see what each answer does to it.
3. **Every question must carry a genuine null option** — "not measured", "I cannot
   recall", "reach was the outcome", "narrow the title instead". Phrase it as
   neutrally as the others. Without it the questions lead, and a review that only
   ever ratchets upwards is producing claims the subject cannot defend.
4. **Apply each answer immediately and show the movement.** Re-run
   `scripts/role_fit.py` and say what changed. That feedback is what makes the
   twentieth question worth answering.
5. **Challenge an answer that does not match the evidence.** Where a repository
   names three authors, "I led it" is a claim about the artefact that the artefact
   does not support. Say so, and record what the source shows.
6. **Record a publication decision as a constraint.** When the answer to "can
   any of this be said in public?" is no, write `Do not publish: <reason>` into
   the atom's `constraints`. `open_questions.py` treats that as decided and stops
   asking; without it the same question returns every run.
7. **Close an unanswerable question rather than leaving it open.** A prize with no
   public record can never reach `externally_verified`. Record why, and remove it
   from `open_questions`: a question nothing can ever resolve is noise that teaches
   the subject to skim the list.
8. **Stop whenever asked.** Everything answered is already recorded and the queue
   lives in the pack, so a session is resumable by construction. Say so, so that
   stopping does not feel like abandoning.

## Corroboration backlog, on request only

If the user asks for a corroboration pass, `python3 scripts/corroboration_plan.py`
ranks what is worth chasing and states the specific ask. Prefer the wins that cost
minutes rather than a phone call: an atom already `corroborated` needs only its URL
recorded. Do not run this unprompted.

## Output

Write a review record containing the evidence ID, questions, answers, status,
corroborators identified, conflicts, and approval decision. Include a concise
recommendation for the next action.

End an iterative session with `python3 scripts/open_questions.py --delta`. It
reports what the pack version changed and how much of that movement rests on
atoms citing no source. **A questioning process that reliably improves a score is
indistinguishable from a coaching one**, and this is what makes the difference
visible. If the delta is not clean, either record the person source behind the
movement or say plainly that the improvement is unproven.
