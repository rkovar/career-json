# Career quality benchmarks

The release gate includes both component checks and complete fictional user
journeys. A passing schema alone does not establish a useful career record.

## Deterministic journeys

```sh
python3 tests/run_journeys.py --output /tmp/career-journeys.json
```

Five fictional profiles cover early-career analysis, a deep technical specialist,
service operations, a career transition, and technical/people leadership. Their
examples include shared ownership, prevention, architectural judgment, coaching
and work without financial measurements. The benchmark exercises first import,
partial acceptance, backup/restore, resuming decisions, repeat import, factual
correction, strength reassessment, history and (when installed) generation selection.

Required invariants include retained factual wording, no duplicate achievements,
no changes to unrelated facts, preserved source excerpts and distinctive strengths,
and exclusion of private evidence from generation. Separate regression tests cover
merge/split/refresh, source mismatch rejection, privacy reconsideration and corrupt
archive recovery. Existing editorial tests exercise shortening and retargeting.

The JSON report identifies each check, elapsed time and retained achievement counts.
Human burden and prose-quality metrics remain null in deterministic runs. Counts
are observations, not career-completeness or hiring-success scores.

`make check` runs these tests locally; GitHub Actions runs the same checks on Linux
and macOS with fictional workspaces, plus clean core/add-on installation tests.
Model calls are never part of the automatic CI job.

The [expanded Jules walkthrough](../examples/first-pack/README.md) provides a
browsable example of partial acceptance, ownership corrections, duplicate accounts,
private work, strengths interpretation and later note promotion. Its sources,
proposals and decisions are authored fixtures. The builder runs the actual tools;
`tests/test_pack_review.py` checks the saved history and acceptance boundaries.
This demonstrates the process without measuring extraction or interview quality.

## Model-driven checks

From the developer checkout, after changes to onboarding or maintenance instructions, run bounded scenarios (the runner builds an isolated core installation when requested):

```sh
python3 tests/run_editorial_scenarios.py --scenario first-pack --installation core --budget 2 --report /tmp/first-pack.json
python3 tests/run_editorial_scenarios.py --scenario maintenance --installation core --budget 2 --report /tmp/maintenance.json
python3 tests/run_editorial_scenarios.py --scenario representation --budget 2 --report /tmp/representation.json
```

Reports retain model usage, cost, permission denials, elapsed time, question count,
checks, and the response for inspection. A question mark count is a rough diagnostic,
not a reliable measure of interview quality. A fixed source pack must remain
unchanged when the request asks only for a proposal or representation review.

For release review, inspect the actual documents against these questions and record
examples, expected behavior, observed behavior, and a pass/fail/needs-review verdict:

- Did any factual detail, ownership limit or source disappear or become stronger?
- Would a reader recognize the person's distinctive strengths? Which passage shows it?
- Did shortening or retargeting remove the only example supporting a key strength?
- Did the assistant ask for facts already available or invent a numerical outcome?
- Could a person identify what was saved, pause, and recover their work?
- How many questions, manual file moves and approval controls did the person need?

Use `tests/fixtures/journey-observation.template.json` to record observed human
burden and prose quality. Leave unmeasured fields null. Reviewers should assess the
source and final artifact before reading the generator's self-evaluation. Treat
subjective disagreements as findings to inspect, not numbers to average into a
claim that a resume will succeed. Automated preservation checks and observed prose
quality remain separate evidence.

## Resume planning and export comparisons

`tests/test_resume_workflow.py` exercises plan readiness, input staleness, private
view boundaries, wording decisions, revision loss, related results, semantic DOCX
structure, Unicode content, cross-format text equivalence and incomplete export
handling in fictional workspaces. PDF fault injection tests validate error paths;
they do not substitute for a real browser and PDF-extractor check.

For actual paired baseline/revised outputs from the same fictional pack and brief:

```sh
python3 tests/compare_resume_runs.py --pack /tmp/fixture/pack.json --baseline /tmp/fixture/baseline.md --revised /tmp/fixture/revised.md --output /tmp/resume-comparison
```

An independent reviewer reads A/B before seeing the pack, plan, or coordinator
mapping, records impressions with actual passages, then assesses accuracy and
representation against the evidence. `reader-review.json` leaves quality, burden,
time and cost unmeasured until observed. No model calls or scores are fabricated.
Use the existing five personas plus cases with promotions, gaps, older relevant
work, shared results and outcomes without financial metrics. A preferred wording
is not evidence that one document will obtain more interviews.

The bounded `resume` model scenario exercises the revised authoring workflow and
all exports in an isolated fictional workspace. It reports generation cost,
failures and actual outputs separately from human prose-quality observations:

Every delivered `*-draft.md` must have valid current evaluation and representation
sidecars, a publishable evaluation, a ready plan, verified exports matching that
draft and plan, and a valid screen for the same run. Empty records, stale inputs
and unrelated exports fail. A shared-context screen remains explicitly weaker
than a fresh screen; neither makes the automated test a judgment of prose quality.

```sh
python3 tests/run_editorial_scenarios.py --scenario resume --budget 4 --report /tmp/resume-scenario.json
```

## Concrete resume quality corpus

The five complete fictional packs in `tests/fixtures/resume-quality-cases.json`
can be installed with `tests/run_resume_quality.py prepare` from the developer
checkout or matching Resume Application installation. See the add-on's
`docs/resume-quality.md`, under "Repeatable fictional evaluation set", for
actual candidate generation, recorded reader judgments and comparison commands.
The deterministic tests leave unobserved prose quality unmeasured.
