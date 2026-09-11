---
name: generate-resume
description: "Called by `make-resume`, which is the normal entry point. Use directly only to run generation alone, without evaluation or the recruiter screen."
---

# Generate Resume Or CV

## Inputs

- approved career datapack
- target role and job description
- ATS keywords or requirements
- requested persona and length
- recruiter context, if available

## Workflow

1. Identify the target role and select the smallest set of relevant evidence IDs.
2. Retrieve eligible evidence using `outcome_type` as one signal:
   `business_outcome`, then `output`, then `activity`. Select for the distinct
   contribution each example makes to the brief. `self_asserted` evidence is
   normal; corroboration is not a gate or a substitute for relevance. Flag any
   requested evidence that is not eligible.
3. Demote or drop evidence whose `role_fit_notes` mark it as a negative signal
   for this role, even when it is eligible and impressive.
4. Use STAR fields to write one principal achievement per bullet: decisive action,
   supported result, and only the context needed to understand them. Cut secondary
   claims instead of combining them to meet a bullet limit.
5. Preserve the meaning of the Result. Never add an outcome, metric, date, or scope that is absent from the evidence.
   Apply this to connecting prose too: comparisons, causes, motives and claims
   that something did not happen need their own support. Adoption alone does
   not establish voluntary uptake or absence of a mandate. Missing measurement
   records do not establish that no measurement happened.
6. Keep claim-to-evidence IDs in the draft metadata.
7. Optimise for the requested length and ATS terms without keyword stuffing.
8. State evidence gaps instead of smoothing them over.
9. Run `evaluate-output` before presenting the artefact as publishable.

## Contact details and status

Include a contact block appropriate to the audience: full contact details for a
document sent to a named recipient, name and location only for a public artefact.
A resume with no route to the candidate cannot be actioned.

Never place draft status, publication warnings, or notes about withheld evidence
inside the artefact. Those belong in the evaluation record. State gaps to the
user, not to the hiring manager.

## Style

Use specific verbs, concrete scope, honest metrics, and natural language. Avoid generic claims such as “results-driven professional”, “proven track record”, and “dynamic team player”.

Open with demonstrated value for the target role. Personal positioning informs
selection; title explanations and career transitions do not automatically belong
in the opening sentence. Choose scope appropriate to the target: organisational
remit for leadership, personal technical contribution for hands-on work. Preserve
explicit publication choices. Use implied first person consistently, and check
`occurred` so past work does not become a current activity through tailoring.
Name and link the most relevant public work using recorded public URLs.

Use `# Name`, `## Target role`, contact paragraph, then summary. Aim for a
35–55-word summary and 20–30-word bullets, allowing space for required approved
wording. Page count must be checked in the rendered document.

## Constraints

Each atom in the selection view may carry `constraints`: reviewed handling rules
such as "prototype only, did not reach production" or "team contribution, do not
imply sole ownership". A bullet must respect every one of them. They are the
generation-facing half of a review; the operator's `notes` never reach this view.

## Generation from durable context

Follow the editorial preparation steps in `make-resume` and
`docs/editorial-memory.md`, including when this skill is used directly. Consume
`select_evidence.py --selection`, not raw profile interpretations or private
selection reasons. Candidate ordering is a retrieval aid; select for what each
example adds to the document, using the saved brief and scoped decisions.
Corroboration, outcome class and recency are contextual signals, never reasons
to discard the only supported example of an intended strength. Claims still cite
the underlying evidence IDs; a preference is not an accomplishment. Save material
tradeoffs so shortening and later retargeting can account for them.
