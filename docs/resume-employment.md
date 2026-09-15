# One employer, several positions

A reader should immediately understand the employer, the length of the tenure,
the positions held, and where the achievements belong. Repeating the employer
as a full heading for every position fragments that story and can make a
continuous tenure look like several unrelated jobs.

The safe resume view provides `resume_plan.employment_groups`, derived from
approved employment records. Each group retains every eligible title and its
dates. Definite breaks create separate tenures, even when the employer name is
the same. Unknown dates are not replaced with assumptions. Changes of position
do not by themselves prove promotion, increased seniority or a reporting line.

## Default: a compact progression, then achievements

For several positions in one tenure, use one employer heading and compact dated
position rows, newest first. This preserves early positions without empty role
sections. Put achievements spanning positions under an explicit Career highlights
subsection. The example is fictional:

```markdown
### Example Systems | January 2017 to December 2025 | London

**Principal Engineer** | March 2022 to December 2025

**Senior Engineer** | June 2019 to March 2022

**Engineer** | January 2017 to June 2019

#### Career highlights

- A supported achievement, preserving its contribution and timeframe. <!-- Evidence: E_EXAMPLE -->
```

Blank lines separate the position paragraphs in source Markdown; PDF, HTML and
DOCX styles keep the rendered rows compact. The visible hierarchy is:

```text
EMPLOYER                         Overall tenure
  Latest position                Its dates
  Previous position              Its dates
  Earlier position               Its dates

  Career highlights
    - Supported achievement
    - Supported achievement spanning positions
```

Do not repeat a promotion-count bullet merely to compensate for an unclear
layout. Keep such a claim only when its supported distinction adds value. Keep
location at employer level when it is shared; preserve role-level location
changes where they matter and are recorded.

## When achievements belong to distinct positions

Use an H4 role subsection instead of its compact timeline row:

```markdown
#### Principal Engineer | March 2022 to December 2025

- An achievement from this position, with its evidence citation.
```

This is useful when the positions represent substantially different work. Each
position still appears exactly once and in reverse chronology. A role without
dedicated content belongs in the compact timeline. Do not repeat both its timeline
row and its subsection. Single-position employers can retain the existing
`### Employer | Title | Dates | Location` convention.

A project spanning several positions must not be placed under just one title's
dates. Use Career highlights, or split it into genuinely supported role-specific
contributions without duplicating outcomes. Shared sections preserve the source
employment links; they do not authorize attributing another employer's work or
combining separate stints into one continuous period. Correct incorrect source
dates or links through Core review.

## Checks and export behavior

The process review validates employer tenure, every position/date pair, chronology,
achievement scope and the absence of empty role subsections. Repeated flat entries
for the same tenure are flagged for grouping. Both numeric dates and named months
are recognized, including headings with a fourth location field. A displayed year
can summarize a recorded month; a month cannot be invented from a year-only source.

H4 headings are supported in HTML, PDF and DOCX. Position rows use compact
paragraph styles; employer/subsection headings and the position progression are
kept with following content. The whole employer block is not forced onto one
page: inspect the final PDF for sensible breaks without creating large blank areas.
TXT retains the same title/date order and explicit Career highlights label.

This is a reusable authoring and validation rule. Existing resumes and career
records are not reformatted automatically. Regression tests use fictional careers:

```sh
python3 tests/test_employer_layout.py
CAREER_TEST_REAL_PDF=1 python3 tests/test_employer_layout.py
```
