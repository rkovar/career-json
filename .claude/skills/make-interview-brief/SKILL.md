---
name: make-interview-brief
description: "Use when preparing for an interview, screening call, or reference check for a specific role. Builds a private brief from the datapack: the STAR answers behind each claim, the questions a hostile interviewer will ask, where the evidence is thin, and what must not be discussed. Triggers on requests such as prep me for this interview, what will they ask, or interview brief for X."
---

# Build A Private Interview Brief

## Purpose

Every other artefact skill produces something a stranger reads, so all of them
exclude weak and unpublishable evidence. **This one inverts that rule.** A brief is
private preparation, and the claims most likely to be attacked are precisely the
ones the artefacts had to hide.

Never publish this. Never send it. It is `external_safe: false` by nature.

## Inputs

- the target role, and its profile in `data/roles/` if one exists
- the artefact that was actually sent, so the brief covers what they will read
- the current pack, in full, including atoms no artefact may cite

## What to include, that an artefact may not

Read the **whole pack** here, not the selection view. Run
`python3 scripts/private_facts.py` for recorded dates and explicit measurement
states. Use absolute dates at their recorded precision; do not estimate how many
years ago an event happened. Empty metrics or absent/null `measured` or `basis`
mean the information is not recorded, not that the result was never measured.
Only `measured: false` supports calling that specific metric unmeasured.
Use nearby evidence citations for measurement statements so they can be checked.

- Atoms that are `unresolved` or `external_safe: false`. The candidate must know
  what they cannot discuss, and have a prepared way to decline that does not read
  as evasion.
- Every `open_questions` entry, because an interviewer will find the same gap.
- Any recorded reference-check concern; absent corroboration alone is not a defect.

## Structure

1. **What they have read.** The claims in the artefact sent, with the evidence ID
   behind each, so the candidate can trace any question back to its source.
2. **STAR answers.** For each substantive claim, the full Situation, Task, Action,
   Result from the pack. Not the compressed bullet: the version that survives
   follow-up questions.
3. **Where the numbers came from.** For every metric in the artefact, the
   measurement basis recorded in the pack, and plainly "not measured" where that
   is the truth. Rehearsing a number whose denominator the candidate cannot
   explain is how an interview is lost.
4. **The attacks.** Pull `interview_attacks` from the screen record if one exists,
   and add any claim where ownership is ambiguous or the result is unmeasured.
   Give the question as an interviewer would ask it.
5. **Do not discuss.** Atoms that are `external_safe: false`, with a one-line way
   to decline that stays professional and does not invent a reason.
6. **Reference preparation.** Recorded employment or reference-check issues, if
   any. Do not initiate corroboration chasing unless the user requests it.
7. **Their gaps, not yours.** Requirements in the role profile with an empty
   `evidenced_by`. The candidate should decide in advance how to address the gap
   honestly rather than improvising under pressure.

## Rules that still hold

- Never invent an answer, a metric, or a corroborator. A brief that rehearses a
  fabrication is worse than no brief.
- Where the pack says a result was never measured, the brief says so, and offers
  the honest framing rather than a number.
- Preserve conflicting values. The candidate needs to know a conflict exists
  before an interviewer finds it.

## Output

Write to `outputs/<role>-interview-brief.md`. State at the top that it is private
and must not be sent. Report to the user the three questions most likely to be
asked and the single weakest answer.

## Shared career context

Read `docs/editorial-memory.md`. Create or reuse an output brief with
`format: interview_brief` and `audience: private`; prepare a durable selection
for provenance and story priorities. Read the full pack for private preparation,
including strengths and preferences, and use application-scoped decisions to
understand omissions in the sent resume. Output-scoped resume omissions do not
ban those stories from private preparation. Facts still come from the atoms;
never turn an aspiration or a polished resume sentence into an achievement.

Use `review-representation` to assess the intended strengths, accounting privately
for withheld evidence without suggesting disclosure. Pin the selection using
`manifest.py --selection` and validate with `validate_artifact.py --private`.
The filtered external selection view is intentionally unavailable for private
briefs. Regeneration must remain possible from the pack and saved context.
