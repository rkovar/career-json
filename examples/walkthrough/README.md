# A complete run, end to end

Everything here is fictional. Alex Rivera does not exist, and neither does the
role. This is what one `make-resume` run produces, committed so you can see the
output before installing anything.

The pack is [`../career.example.json`](../career.example.json): five evidence
atoms, two employment records, one of each `evidence_status`.

| File | What it is |
| --- | --- |
| [`roles/head-of-platform-engineering.json`](roles/head-of-platform-engineering.json) | The role, structured. `central_requirement` is the field that decides everything |
| [`resume.md`](resume.md) | The draft. Evidence comments are hidden in the rendered HTML |
| [`head-of-platform-engineering-evaluation.json`](head-of-platform-engineering-evaluation.json) | The integrity check, pinned to the pack hash that produced it |
| [`head-of-platform-engineering-screen.json`](head-of-platform-engineering-screen.json) | The recruiter and hiring-manager read, with a verdict |

## What the run decided

**Three of five atoms reached the document.** `E_EXAMPLE_REVENUE_CLAIM` is an
open question and `E_EXAMPLE_PRIOR_EMPLOYER_DETAIL` was withheld under a
confidentiality obligation. Both are marked ineligible in the pack, so selection
never showed them to generation. That is the architecture working: you cannot
cite what you were never shown.

**The Acme Retail Group role has dates, a title, and no achievements.** Both of
its atoms were the ineligible ones. The evaluation records this as a warning
rather than hiding it, and the screen turns it into an interview question the
candidate should expect.

**The verdict is `borderline`, and the document is not the problem.** The role
hires for ownership of a team, a roadmap and a budget. Alex has strong delivery
evidence and none of that, so no rewrite fixes it. The screen splits the five
weaknesses accordingly: two a rewrite can fix, three that need new evidence.

An unflattering verdict on a clean document is the normal outcome, and it is the
cheapest place to discover a mismatch.

## Reproducing it

The files are regression-tested rather than decorative. `make check` validates
all three records, confirms the evaluation still pins the current hash of the
example pack, renders the draft, and validates it against the pack.

```sh
python3 scripts/validate_records.py examples/walkthrough/*.json examples/walkthrough/roles/*.json
```
