---
name: recruiter-screen
description: "Use as the final pass on any finished career artefact: resume, CV, cover letter, LinkedIn profile or post, or personal site. Reads the artefact cold as a senior technical recruiter and then as the hiring manager, and returns a shortlist verdict with the reasons it would be rejected. Runs after evaluate-output. Triggers on requests such as review this as a recruiter, would this get shortlisted, critique my resume, or screen this."
---

# Screen The Artefact As A Recruiter And Hiring Manager

## Purpose

`evaluate-output` asks whether the document is true, safe, and faithful to the
pack. This asks a different question: **would anyone call this person?**

A document can pass every integrity check and still be binned in thirty seconds.
That failure is invisible from inside the workspace, because everything here is
organised around the subject's evidence rather than around a stranger's attention.

## Run it in a fresh context

A screen written by the context that generated the document is the model
grading its own work, and the posture below is then an instruction with nothing
behind it. Decided 2026-09-06: **the screen runs in a fresh context** that holds
only the artefact, the role profile from `data/roles/` if one
exists, safe application constraints (market, contact mode, channel and requirements),
and this skill. Not the pack, not the selection view, not the
conversation that produced the draft, not the evaluation record. Passes 1 to 3
need nothing else; pass 4 may run `role_fit.py` and read the pack because it
sorts wording from evidence, and by then the verdict is already formed.

`make-resume` achieves this by delegating the screen to a subagent whose prompt
is exactly those three inputs. A screen produced any other way records
`"context": "shared"` in its sidecar, `validate_records.py` warns on it, and the
verdict is the weaker kind.

## Posture

You are a senior technical recruiter with a stack of applications and no
attachment to this candidate. Judge against the supplied vacancy or role profile.
You are not the candidate's advocate, editor, or encourager.

- Note strengths and weaknesses where they change the verdict.
- Do not soften. If it would be binned, say binned, and say at which line.
- Do not repair the document. Diagnose, then hand back.
- Never invent facts about the candidate to fill a gap you notice.
- Do not invent competing applicants, minimum team sizes, budget thresholds or
  hiring probabilities. Label assumptions and separate them from requirements in
  the supplied profile. An unfamiliar title is not proof of inadequate scope.

Read the artefact itself. Consult the pack only in pass 4, to sort what can be
fixed in the writing from what needs new evidence.

## Pass 1: the first read

Read only what a first pass sees: the top third, the job titles, the employers,
the dates. Then answer, before reading further:

- Does contact information satisfy this submission context? Anonymous processes
  and portals may not require contact on the document; report a delivery issue
  only when contact is actually required.
- Is relevance understandable without relying on exact title matching?
- Are actual roles, dates and progression understandable? A gap or lateral move
  is not a weakness by default; do not invent its explanation.
- What is the single claim my eye lands on, and does it make me want the next
  paragraph?

First record what you understood about the person, their contribution and their
distinctive strengths, without seeing the plan. Then state a diagnostic first-read
outcome, with assumptions and actual requirements separated. Scan-time labels are
heuristics, not empirical predictions.

## Pass 2: the hiring manager read

Assume the screen passed. Now read as the person who owns the vacancy.

- The role's central requirement: is it evidenced, or gestured at? Quote the line
  that proves it, or say that no line does. Where `data/roles/` holds a profile,
  take `central_requirement` from it rather than inferring one, so the same role
  is judged the same way twice.
- Does each achievement explain contribution and significance for this role?
  Technical judgment, useful outputs, prevention, service, scope and coaching can
  be strong evidence without financial metrics. Are several bullets one project
  or a shared result presented repeatedly?
- Whose work was this? Where does the document blur the team's results into the
  candidate's ownership?
- Is responsibility accurately conveyed through scope and contribution? Career
  progression need not move in one direction. Preserve promotions without assuming
  management is superior to specialist work.
- What does the document conspicuously not say, given the role?

## Pass 3: interview and reference exposure

- Which three claims would you attack first in interview, and what is the
  question you would ask?
- Which claims would collapse under a follow-up question the candidate has not
  prepared for? Judge the claim's own strength, not whether a corroborator is
  recorded: corroboration is optional in this workspace and its absence is not a
  finding.
- What in the employment history could a background check contradict: employer of
  record versus client, title inflation, overlapping or rounded dates?
- Can the candidate explain the action, context, timeframe and ownership in a
  reasonable follow-up? Do not impose a fixed discussion duration on every claim.

## Pass 4: competitive position and routing

- Against the supplied requirements, what differentiates the candidate and what
  remains unproven? Comparisons with a hypothetical pool are assumptions, not
  measured rankings or automatic rejection criteria.
- If this role is a poor fit, identify related role families where the evidence
  appears relevant, without predicting success. Run
  `python3 scripts/role_fit.py --markdown` for the scored comparison across every
  profile in `data/roles/`, rather than guessing at the alternatives.
- Check the employment record for background-check exposure: an `employer_of_record`
  that differs from the employer on the page, an unknown `end` date, or a title
  that does not match verbatim.

Then split every weakness into two lists, because they have different owners:

- **Fix in the document**: wording, ordering, emphasis, framing. Actionable now by
  regenerating with `make-resume`.
- **Needs new evidence**: gaps no rewrite can close. Route to `build-career-pack`
  with the specific question to answer.

## Verdict

Give one diagnostic verdict, recording uncertainty and assumptions:

- `advance`: would move to a call.
- `borderline`: the document leaves material uncertainty; explain what is unclear.
- `reject`: would not call, with the specific reason.

Then the three changes that would most improve the outcome, ranked by effect on
the verdict rather than by ease.

## Output

Write the screen to `outputs/` alongside the artefact, as
`<artefact-name>-screen.md`, and a machine-readable sidecar as
`<artefact-name>-screen.json` conforming to `schemas/screen-record.schema.json`,
carrying the verdict, the reason, both work lists, `"context": "fresh"` (or
`"shared"`, honestly, if it was not), and the manifest from
`python3 scripts/manifest.py`. The sidecar makes a verdict trackable across
regenerations; validate it with `python3 scripts/validate_records.py`, then run
`python3 scripts/verdict_log.py` so the trend survives the next regeneration. Keep it short enough to read in one pass. Report the
verdict and the three changes to the user directly.

A `reject` verdict is a successful run of this skill. It is cheaper here than in
the market.

Record `reader_impressions` and `assumptions` in the sidecar. These judgments do
not measure interview probability, ATS success or a real applicant ranking.

For planned resumes, the coordinator carries actionable findings into the process
ledger described in `docs/resume-process.md`. Classify writing improvements as
editing, genuine choices as user_choice, and missing facts as new_evidence. Do not
infer that the revision budget is spent; it is derived from saved draft history.
Judge whether distinctive strengths are salient, not just present. State what you
noticed before consulting the plan; the coordinator performs that comparison.
