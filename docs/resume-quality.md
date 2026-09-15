# Resume editorial quality

Career facts remain in the approved pack. Role-specific judgments, selection,
prose review and visual observations belong to the Resume Application. A completed
review records what a reviewer assessed; it is not independent proof of quality or
an ATS/hiring prediction. Preparation never fills in reviewer answers.

## Selection and consequential omissions

`select_evidence.py` ranks by requirement links and supported terminology. Each
linked requirement explains the candidate contribution (technical delivery,
influence, domain expertise, communication, governance or another contribution),
and distinguishes proposed from confirmed links. Outcome type, financial magnitude,
corroboration and age receive no universal ranking bonus. A general view uses
recency for browsing, without penalising older evidence in role scoring.

Both the shortlist and brief builder preserve essential coverage, then prefer
examples linked to requirements not yet represented. Essential coverage may exceed
a requested candidate limit. The result is a retrieval proposal: the editor still
judges technical depth, adoption, scope, prevention and complementary value. Links
alone cannot establish fit, and an outcome label cannot establish causality.

`resume_process.py packet` includes a private `quality` section. It provides a safe
eligible evidence pool and up to three alternatives per uncovered requirement,
unrepresented planned impression, and latest employment record (including
concurrent roles). It examines the pack, including evidence never selected for the
current draft. Explicit omit/reserve decisions suppress alternatives; unsafe and
unresolved evidence is excluded. Requirements may remain *unmapped*: missing links
are not proof that the person lacks experience. Manually inspect the pool before
recording a new-evidence need. Sparse recent experience is a prompt for inspection,
not a requirement to invent outcomes or remove useful older work.

For each omission question, record `retain`, `revise_selection`, or `needs_evidence`
with a reason. `revise_selection` remains unfinished until a revised selection,
plan and draft resolve it. `needs_evidence` is allowed only for unmapped questions,
not as a substitute for inspecting surfaced evidence or respecting existing choices.
It records a private limitation; it does not automatically interrupt delivery.
Ask an optional focused question only if the answer would materially improve the
result. New facts must pass through Core review.

## Explicit editorial review

Version 2 process records extend the existing review with:

- Opening: what distinct contribution does it establish, and what does a summary
  add beyond the body? A summary is optional.
- Language: are actions clear without generic praise, unnecessary biography or
  unexplained jargon? Respect the person's explicitly saved voice preferences.
- Focus: identify the main achievement in each substantive block and inspect
  competing stories, repeated results and supporting detail.
- Contribution: locate personal work, useful context or method, and supported
  change, output or scope; flag responsibility-only writing when better evidence
  exists. No financial metric is required.
- Metric value: explain what a visible number establishes for this role and its
  measurement basis. Effort, visibility, adoption and impact are different.

Each passed editorial assessment needs a reason and exact visible passages from
its assigned blocks. The validator checks review coverage and passage locations;
it cannot decide whether praise is generic or a reviewer reason is persuasive.
Record genuine issues rather than marking every prepared row as passed.

The existing cold read and prominence review remain separate. Record reader
impressions before consulting the plan. These are assistant tasks, not a new list
of questions the person must answer. Version 1 records remain readable history;
prepare a new version with `--previous` for the new checks. Nothing automatically
upgrades an older approval or overwrites an existing resume.

## Page diagnostics and final visual review

Export version 3 records PDF geometry from PDFKit or Poppler and locates document
blocks on actual pages. It flags split prose, headings or position lines separated
from following content, a sparse final page following dense pages, and planned
leading evidence first appearing after page one. The geometry reports observed
text-band fractions, not whitespace targets. Unmatched text is explicitly partial;
unavailable geometry is not a clean layout result. Content and hyperlink validation
remain separate. DOCX pagination is not inferred from PDF geometry.

After exporting, attach pending visual review to the content review:

```sh
python3 scripts/resume_process.py layout --input outputs/example-content-process.json --exports outputs/example-export/review/export-report.json --output outputs/example-layout-process.json
```

Inspect the actual PDF. Record `quality.layout.status: reviewed`, concrete
`observations`, and an `accepted` disposition plus reason for each diagnostic whose
layout is acceptable. An `issue` requires revision and re-export; it cannot be
waived by filling a generic observation. Use `save --input ... --output ...` to save
the completed record, and pin it with `manifest.py --process`. Publication checks
require this review to match the exact submitted export bundle. No diagnostic or
export success automatically counts as a visual inspection.

Do not shrink text to satisfy an invented page limit, or keep every employer group
on one page. Inspect and adjust the actual layout within the brief's instructions.

## Repeatable fictional evaluation set

`tests/fixtures/resume-quality-cases.json` contains five complete fictional packs
and role profiles: promotion progression, older specialist evidence, sparse recent
work, shared ownership and cumulative metrics, and nonfinancial prevention impact.

```sh
python3 tests/run_resume_quality.py prepare --output /tmp/resume-quality-run-1
```

The runner installs allowlisted Core and Resume files into separate workspaces,
with a `TASK.md` for each case. Generate real candidates there using the normal
workflow; keep `outputs/candidate-draft.md` as the final cited Markdown. It does not
call a model, generate a purported improvement, or copy live career data.

A reviewer reads the candidate and role before the coordinator expectations,
records initial observations, then assesses each criterion in `reader-review.json`.
Record the reviewer, fresh/shared context, exact candidate SHA-256, reasons and
visible passages. Leave unobserved criteria `unmeasured`. Export reviews stay in
the normal process and evaluation records; this runner does not approve exports.

```sh
python3 tests/run_resume_quality.py check --suite /tmp/resume-quality-run-1 --output /tmp/resume-quality-results-1.json
```

The report separates deterministic integrity/chronology/central-evidence checks
from recorded reader judgments. Changed fixture inputs, a different candidate hash,
missing observations or invented passages prevent a completed result. Use a new
suite directory for another generator version and compare the saved artifacts with
`tests/compare_resume_runs.py`. No hiring outcome or quality gain is inferred from
passing schemas. `make check` runs deterministic regressions, not paid model calls
or automatically completed subjective reviews.
