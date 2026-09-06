---
name: make-resume
description: "Use when the user asks for a resume, CV, or cover letter for a specific role from the existing career datapack. Triggers on requests such as I need a resume for this job, build me a CV for this role, tailor my resume to this job description, or make a one-pager for X. Runs generation, evaluation, and a recruiter screen in one invocation and asks no questions."
---

# Make A Resume From The Existing Pack

The delivery phase. Answer a resume request from the pack `build-career-pack`
produced, and return a finished document with a verdict on it.

## The rule that defines this skill

**Ask no questions.** Not about missing evidence, not about format, not to
confirm an intermediate result. Resolve every ambiguity by inference or by
narrowing the claim, and state the inferences in the report. A question that
genuinely needs answering goes in the report, after the draft, never in place of
one.

The user came here for a document. Produce the document.

The single exception: if no target role can be found in the request, in
`data/sources/`, or in the most recent artefact, ask for the role and nothing
else. Without it there is no work to do.

## Run

```sh
python3 scripts/select_evidence.py --role <role_id>   # ranked shortlist for the role
python3 scripts/select_evidence.py                 # everything eligible, unranked
python3 scripts/select_evidence.py --excluded      # what was withheld, and why
python3 scripts/render.py outputs/<name>.md        # HTML, never hand-written
python3 scripts/validate_artifact.py outputs/<name>.md
python3 scripts/manifest.py "<target role>" --artifact outputs/<name>.md   # provenance for the record
```

Generate from the selection view, not from the raw pack. Pass `--role` whenever a
profile exists in `data/roles/`: it ranks and shortlists against that role's
requirements and explains each choice in `why_selected`, which keeps curation
sharp as the pack grows past what anyone can read. Without a profile you get the
whole eligible pack and must curate it yourself. Ineligible atoms are
absent from it by construction, so the exclusion rule needs no policing. Use
`--audience public` for a website or published CV; the default is a document sent
to a named recipient.

## Artefact types

The same evidence, selection, and evaluation path serves several documents. Say
which was produced, and apply its shape.

- **Resume or CV**, the default. Bullets from STAR, outcomes first.
- **Cover letter.** Three or four short paragraphs against the role profile's
  `central_requirement`. One claim per paragraph, each still carrying an evidence
  ID. No restating the resume, and no enthusiasm the evidence does not support.
- **LinkedIn About or headline.** First person, `--audience public`, so the
  contact block is name and location only. Nothing `external_safe: false`, and no
  employer-internal framing.

Interview preparation is `make-interview-brief`, which reads the whole pack
rather than the selection view because a brief must cover what the artefacts hide.

## Role profile

If `data/roles/` holds a profile for this role, use it: `central_requirement`
drives selection, `negative_signals` drive demotion, and `ats_keywords` drive
phrasing. A requirement with an empty `evidenced_by` is a gap to report, not one
to write around.

## Writing the document

1. Take the smallest set of evidence that answers the role. The view is ordered
   `business_outcome`, then `output`, then `activity`: prefer that order. Never
   let activity metrics such as engagement counts or throughput percentages carry
   the document, because hiring managers discount them.
2. Demote or drop evidence whose `role_fit_notes` mark it as a negative signal
   for this role, even where it is eligible and impressive.
3. Take every employer, job title, and date from the `employment` records in the
   view. Never write one from memory or from source text: they are the facts a
   background check tests, and an unsourced date breaks rule 1. Use `employer` as
   written; if `employer_of_record` differs, that is interview and reference
   material, not artefact text. Derive any span claim such as "N years of
   experience" from `career_span_years`, never by hand.
4. Build each substantive bullet from STAR fields, preserving the Result's
   meaning. Never add an outcome, metric, date, or scope the evidence lacks.
   Obey every entry in the atom's `constraints`: "prototype only" means the
   bullet says so, "do not imply sole ownership" means it does not.
5. Carry claim-to-evidence IDs as `<!-- Evidence: E_X -->` comments. The renderer
   turns them into hidden spans so both formats stay in step. Put the comment
   **at the end of the claim's own line**, or on the line directly after it. Both
   placements are supported and nothing else is: a comment separated from its
   claim by a blank line binds to nothing, and `scripts/quantities.py` will then
   compare that claim against no evidence at all.
6. Draft status never appears inside the artefact: no banner, no "not
   publishable" notice, no bracketed note about withheld or pending evidence.
   That language reaches a hiring manager the first time the file is forwarded.
   Status belongs in the evaluation record and the report.
7. Open with the contact block from the view. If it carries no email and no
   phone, still produce the draft, then open the report by saying it is
   unsendable until `build-career-pack` collects contact details.

When evidence is thin: make the narrower claim, then drop the claim and record
the omission. Never substitute a different metric to fill the space, and never
return questions instead of a document.

## Then evaluate and screen

Run `evaluate-output` for integrity, then `recruiter-screen` for shortlistability.
Never skip the screen because the evaluation passed: a document can be faithful,
safe, and unshortlistable, and only the screen will say so. Write the evaluation
record with the manifest as its `run` block.

`publishable: true` requires a clean evaluation. It is a status, not a stop: a run
ending `publishable: false` completes normally and names the blockers.

## Final report

1. The `recruiter-screen` verdict, in its own words, and the reason. This leads
   even when the evaluation is clean.
2. Publishable or not, and the blockers.
3. Claims narrowed or omitted, with evidence IDs.
4. Inferences made about audience, length, format, and keywords.
5. What the document rests on: counts by `evidence_status`, and whether any claim
   is a business outcome. Do not editorialise about corroboration.
