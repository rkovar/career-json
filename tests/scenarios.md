# Behavioural scenarios

`tests/run_tests.py` covers everything decidable without a model. These are the
claims that need one, so they are run by invoking the skill and checking the
result against the expectation. Run them after any material skill edit.

`python3 tests/run_scenarios.py` (or `make evals`) runs the scenarios marked
with a runner below through the Claude Code CLI against a throwaway fixture
workspace and asserts on the result with the deterministic scripts. It spends
tokens and is never part of `make check`. Paste its summary line into the log at
the end of this file, with the skill hashes from `python3 scripts/manifest.py`.
Scenarios without a runner are still checked by hand.

Runner coverage: #1, #2, #13, #17.

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

## review-evidence, iterative mode

| # | Scenario | Expected |
| --- | --- | --- |
| 17 | A pack with several open questions | Asks one question, waits, then asks the next. Never a numbered list. |
| 18 | Any question | Carries a genuine null option, phrased as neutrally as the others. |
| 19 | An answer that contradicts a recorded source | Challenged, not recorded. The source's version is stated. |
| 20 | A question nothing can ever resolve | Closed with the reason, removed from `open_questions`, not left open. |
| 21 | An atom created by an answer | Cites a `source_type: "person"` record dated to the conversation. |
| 22 | A re-typing whose change cannot be written into `star.result` | Refused. The atom keeps the type it had. |
| 23 | End of a session | `open_questions.py --delta` reported; movement resting on no source is named. |
| 24 | User asks to stop mid-session | Stops immediately, states that everything answered is recorded and the queue is resumable. |

## Cross-cutting

| # | Scenario | Expected |
| --- | --- | --- |
| 15 | Any generated artefact | `scripts/validate_artifact.py` passes. |
| 16 | Any evaluation record | Carries a `run` block pinning the pack hash. |

## Run log

| Date | Result |
| --- | --- |
