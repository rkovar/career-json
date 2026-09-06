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
2. Prefer external-safe evidence with the strongest `outcome_type`:
   `business_outcome`, then `output`, then `activity`. Prefer
   `externally_verified` and `corroborated` evidence over `self_asserted` where
   both would serve. Flag any requested evidence that is not eligible.
3. Demote or drop evidence whose `role_fit_notes` mark it as a negative signal
   for this role, even when it is eligible and impressive.
4. Build each substantive bullet from STAR fields.
5. Preserve the meaning of the Result. Never add an outcome, metric, date, or scope that is absent from the evidence.
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