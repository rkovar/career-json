# Behavioural scenarios

`tests/run_tests.py` covers everything decidable without a model. These are the
claims that need one, so they are run by invoking the skill and checking the
result against the expectation. Run them after any material skill edit.

Record outcomes in this file, with the date and the skill hashes from
`python3 scripts/manifest.py`.

## make-resume

| # | Scenario | Expected |
| --- | --- | --- |
| 1 | `make-resume` with a role title and nothing else | Produces a document. Asks no question at any point. |
| 2 | Same, with no target role identifiable anywhere | Asks for the role and nothing else. The one permitted question. |
| 3 | Pack whose only on-target evidence is `external_safe: false` | Produces a draft on weaker evidence and reports a role-fit blocker. Never cites the excluded atom. |
| 4 | Pack with no `private_profile` | Produces the draft and opens the report by saying it is unsendable. |
| 5 | Role for which an atom carries negative `role_fit_notes` | That evidence is demoted or dropped, and the choice is recorded. |
| 6 | Any run | Ends with a `recruiter-screen` verdict, even when the evaluation is clean. |

## build-career-pack

| # | Scenario | Expected |
| --- | --- | --- |
| 7 | Fresh workspace, one resume PDF, no existing pack | Ingests and reviews without stopping. Contact details appear in the question batch. |
| 8 | Re-run with an unchanged source | Source skipped as unchanged by hash, and said so. |
| 9 | A confident answer to a corroboration question | Recorded `self_asserted`. Never promoted for confidence. |
| 10 | A claim in both resume and LinkedIn | Stays `self_asserted`. Not promoted for appearing twice. |
| 11 | Any run | New pack file written; previous pack untouched; `metadata.supersedes` set. |

## recruiter-screen

| # | Scenario | Expected |
| --- | --- | --- |
| 12 | A weak artefact | Verdict `reject`, with the line it fails at. No praise. |
| 13 | An artefact with no contact route | Binned at pass 1 for that reason alone. |
| 14 | Any run | Weaknesses split into fix-in-document and needs-new-evidence. |

## Cross-cutting

| # | Scenario | Expected |
| --- | --- | --- |
| 15 | Any generated artefact | `scripts/validate_artifact.py` passes. |
| 16 | Any evaluation record | Carries a `run` block pinning the pack hash. |
