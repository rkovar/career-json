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

## Preserve editorial context through delivery

Follow `docs/editorial-memory.md` for every new generation or material revision.
Reuse the applicable durable brief or create one autonomously, even for a legacy
pack with no strengths profile. Use only relevant supported strengths; do not
invent a career narrative to fill an empty profile. Record output-specific
instructions and length in the brief. Reuse only decisions whose scope applies.

Run `editorial.py prepare`, then curate its candidates using the whole-set
judgment described in `review-selection`. Do not invoke its interactive checkpoint
unless the user requested it. Save the final selection under `data/selections/`
and generate from `select_evidence.py --selection <path>`. A stale selection must
be rebuilt. Recommendations are editorial choices, not factual approval or
confirmed requirement links. Keep safe interpretation wording tied to its atoms;
preferences guide emphasis and cannot supply achievement claims.

The outcome ordering and bullet limits above are editing defaults. Allocate space
by contribution to this brief: preserve distinctive technical, people, creative,
or other relevant evidence when it supplies something the rest of the document
lacks. Do not mechanically prefer recent metrics over the sole proof of a strength.

Run `review-representation` during evaluation, then retain the cold recruiter
screen. Save scoped decisions for material inclusion/omission changes, especially
when a revision removes the sole example of an intended strength. If feedback
conflicts with a prior decision, resolve and record the tradeoff instead of
oscillating between reviewers. User decisions take precedence over system choices;
publication and evidence constraints always govern eligibility.

Use `manifest.py --selection <path> --artifact <path>` for the final evaluation,
representation review and screen. Record available generation settings without
credentials. Keep reviews aligned with the final brief, selection and artifact.
Report representation, integrity, role coverage and reader quality separately;
never collapse them into an overall career score. Normal delivery still asks no
questions and finishes even when it must report limitations.

## Run

```sh
python3 scripts/select_evidence.py --role <role_id>   # ranked shortlist for the role
python3 scripts/select_evidence.py                 # everything eligible, unranked
python3 scripts/select_evidence.py --excluded      # what was withheld, and why
python3 scripts/render.py outputs/<role_id>-draft.md        # HTML, never hand-written
python3 scripts/validate_artifact.py outputs/<role_id>-draft.md
python3 scripts/select_evidence.py --selection data/selections/<id>-selection.json
python3 scripts/manifest.py "<target role>" --selection data/selections/<id>-selection.json --artifact outputs/<role_id>-draft.md
```

**Name the file `outputs/<role_id>-draft.md`** (a cover letter:
`outputs/<role_id>-cover-letter.md`). The index, `make artifacts`, the question
queue and the evaluation record all find artefacts by that suffix; a draft named
anything else is invisible to every one of them. The first behavioural eval of
this skill produced `head-of-detection-resume.md` and nothing could see it.

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

Shape rules first, because the screens keep failing drafts on them:

- **Scope on the role line.** Select the `scope` facts that help prove this role,
  in one short line under the employment heading. Leadership applications usually
  benefit from remit and team scale; hands-on applications benefit from technical
  remit. Headcount and budget are not mandatory on every version. Preserve explicit
  publication choices. These are record facts and need no evidence comment.
- **Value opens the summary.** Lead with demonstrated capability and one or two
  relevant achievements. Treat `positioning` as context for selection, not a
  mandatory opening sentence. Explain a title or transition only when it helps
  the reader understand the application. The summary never invents intent; if
  intent is unknown, state what the evidence shows. Cite any personal motivation
  or level-story claim to its recorded person source.
- **Bullet economics.** At most five bullets on the current role, three on the
  previous one, one line for a role that ended more than twelve years ago, one
  principal achievement per bullet. Aim for 20–30 words per bullet and a summary
  of 35–55 words; approved wording may need more space. Never combine unrelated
  achievements to evade a bullet limit. Word counts are editing guides, not
  measurements of rendered lines or pages. Check the final layout separately.
- **Document header.** Use `# Name`, then `## Target role`, then the audience's
  contact paragraph and the summary. Reserve later H2 headings for sections.
- **Top third.** The target title in the headline, and a confirmed atom for an
  essential requirement cited in the summary or the first role block.
  `validate_artifact.py` warns when either is missing.
- **No cliches.** `validate_artifact.py` lists the phrases recruiters discount.
- Run `python3 scripts/keyword_coverage.py <draft> --role <role_id>` and phrase
  bullets with the missing terms only where a confirmed atom carries them.

1. Take the smallest set of evidence that answers the role. The view is ordered
   `business_outcome`, then `output`, then `activity`: use that as an initial
   retrieval order. Choose the final set by contribution to the brief. A recent
   outcome must not displace the sole proof of a relevant strength merely because
   it has a number; activity counts alone do not explain consequence.
2. Demote or drop evidence whose `role_fit_notes` mark it as a negative signal
   for this role, even where it is eligible and impressive.
3. Take every employer, job title, and date from the `employment` records in the
   view. Never write one from memory or from source text: they are the facts a
   background check tests, and an unsourced date breaks rule 1. Use `employer` as
   written; if `employer_of_record` differs, that is interview and reference
   material, not artefact text. Derive any span claim such as "N years of
   experience" from `career_span_years`, never by hand.
4. Use STAR as evidence, not a sentence template: write the decisive action and
   supported result, with only the context needed to understand them. Preserve
   the Result's meaning. Never add an outcome, metric, date, or scope the evidence lacks.
   Obey every entry in the atom's `constraints`: "prototype only" means the
   bullet says so, "do not imply sole ownership" means it does not.
   Check `occurred` when choosing tense: historical maintenance or research must
   not become a current activity in the summary. Use implied first person
   consistently. Name and link selected public work where a recorded public URL
   is available; do not infer a URL or expose private source references.
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
record through `scripts/save_review.py --kind evaluation`, passing the saved
manifest file and a review body without `run`; see `docs/editorial-memory.md`.

**The screen runs in a fresh context, never in this one.** This context wrote
the document and cannot read it cold. Delegate to a subagent whose prompt
contains only the artefact path, the role profile path if one exists, and an
instruction to follow `recruiter-screen`; pass nothing else, not the pack, not
the selection view, not this conversation. The subagent writes the screen and
its sidecar with `"context": "fresh"`. If delegation is impossible, run the
screen here and record `"context": "shared"`: an honest weaker verdict beats a
flattering one dressed as independent.

`publishable: true` requires a clean evaluation. It is a status, not a stop: a run
ending `publishable: false` completes normally and names the blockers.

## Revise before delivery

Resolve actionable editorial findings from the screen before handing over the
document. Revise wording, selection and layout within the existing evidence and
publication constraints, then re-render, re-evaluate and obtain a fresh screen
of the revised text. Normally one revision is enough; allow at most two editorial
cycles. Do not chase an `advance` verdict by inventing evidence or relaxing the
role's requirements. Record why any remaining suggestion was not applied,
distinguishing missing evidence, publication choices and reviewer assumptions.

For a requested page count, inspect a PDF from the final HTML and check extracted
text for reading order and internal IDs. Do not claim print layout or ATS parsing
has been verified from word counts or valid HTML. If export cannot be checked,
report that limitation explicitly. Keep evaluation and screen hashes aligned
with the final Markdown, and regenerate the artifact index.

## Final report

1. The `recruiter-screen` verdict, in its own words, and the reason. This leads
   even when the evaluation is clean.
2. Publishable or not, and the blockers.
3. Claims narrowed or omitted, with evidence IDs.
4. Inferences made about audience, length, format, and keywords.
5. What the document rests on: counts by `evidence_status`, and whether any claim
   is a business outcome. Do not editorialise about corroboration.
