# The career.json format

The canonical contract is
[`schemas/career.schema.json`](../schemas/career.schema.json).
A fictional worked example is
[`examples/career.example.json`](../examples/career.example.json).
Validate with `make check`.

## Why it is shaped this way

Most of these fields exist because something went wrong without them.

## Evidence atoms

One achievement, in STAR form.

```json
{
  "id": "E_PLATFORM_COST",
  "title": "Cut build-pipeline cost by consolidating duplicate runners",
  "star": { "situation": "...", "task": "...", "action": "...", "result": "..." },
  "metrics": ["~33% CI spend reduction"],
  "skills": ["platform engineering", "cost optimisation"],
  "tags": ["cost-reduction"],
  "occurred": { "start": "2023-04", "end": "2023-09", "inferred": false },
  "employment_id": "EMP_CURRENT",
  "evidence_status": "self_asserted",
  "external_safe": true,
  "outcome_type": "business_outcome",
  "role_fit_notes": null,
  "capture": { "method": "annual_review", "review_period": "FY2023" },
  "source_refs": [{ "source_id": "SRC_RESUME", "locator": "page 1" }]
}
```

**`evidence_status`** — how well supported the claim is.

| Status | Means |
| --- | --- |
| `self_asserted` | Appears only in material you wrote. **The normal resting state.** |
| `corroborated` | A third party or public artefact supports it, no record captured |
| `externally_verified` | Backed by an independent source recorded in `source_records` |
| `unresolved` | An open question, recorded in `open_questions` |
| `declined` | You chose not to pursue it |

Your resume and your LinkedIn profile are both written by you. A claim in both is
`self_asserted`, not corroborated. Repetition is not corroboration — an earlier
version of this workspace marked eighteen atoms `verified` on exactly that
mistake.

Corroboration is **optional**. Its absence is not a defect and nothing chases it.

**`metrics`** — a metric is a claim, so it may carry how it was measured:

```json
"metrics": [
  {"value": "~33% CI spend reduction",
   "basis": "monthly CI invoice, Q1 2023 against Q1 2024",
   "measured": true},
  "median build time unchanged"
]
```

A plain string is still valid and no pack needs migrating. The object form exists
because a figure whose baseline and denominator nobody recorded cannot be
defended: "67% throughput increase" is a strong bullet and an unanswerable
interview question. `basis: null` says the basis was not recorded, which is
honest; `measured: false` marks an estimate or a recollection rather than
something a system produced. `select_evidence.py` carries both through to
generation, so an unmeasured figure is visible before it reaches a page.

**`outcome_type`** — `activity` (work done: engagements, throughput), `output`
(things produced: patterns, courses), `business_outcome` (what changed for the
organisation). Generation prefers outcomes, because hiring managers discount
workload metrics.

**`external_safe`** — false means it never reaches any artefact. Ineligible atoms
are filtered out before generation sees anything, so the rule cannot be broken by
a lapse in judgement.

**`occurred`** — when it happened. `inferred: true` means the dates came from the
employment window rather than being recorded, which for a nine-year tenure is
barely a date. Without this the pack cannot do recency, ordering, or gap
detection, which is most of what a career memory is for.

**`role_fit_notes`** — where the evidence counts *against* you. Media reach reads
as strength for an advocacy role and as "communicator, not builder" for a
hands-on engineering one.

## Employment

Employers, titles, and dates. These carry no evidence ID of their own, so nothing
else in the system can see them — and they are exactly what a background check
tests. Before they existed, every date on a generated resume was supplied from
source text with no provenance at all.

```json
{
  "employment_id": "EMP_PRIOR",
  "employer": "Acme Retail Group",
  "employer_of_record": "Contoso Contracting Ltd",
  "title": "Senior Software Engineer",
  "start": "2018-06", "end": "2022-02",
  "parent_employment_id": null
}
```

`employer_of_record` is the entity that actually paid you, where it differs from
the name on your resume. A background check compares against that, not the client.
It never appears in an artefact; it exists so a reference check does not surprise
you.

`parent_employment_id` links a promotion to the role it grew out of, so a
progression can be collapsed to one line without losing the detail.

## Education

Qualifications, held to the same standard as employment and for the same reason:
a degree is not a STAR achievement, it is a fact a background check verifies.

```json
{
  "education_id": "EDU_MSC",
  "institution": "Example University",
  "qualification": "MSc",
  "field": "Information Security",
  "start": "2012-09", "end": "2013",
  "grade": "Distinction"
}
```

Absent from the schema until 2026-09-06, which meant a degree could not be
recorded at all and `export_resume_json.py` could never fill JSON Resume's
education section. `external_safe: false` withholds a qualification from every
artefact exactly as it does an atom.

## Source records

Where material came from. Files carry a `sha256` and the character count of
**extracted text**, not the file size. URLs carry a `retrieved` date instead.

A `person` source is a conversation: the subject's own answers during a review,
dated, pointing at the review record that holds them. It has no hash, so like a
URL its `retrieved` date is the only thing making it auditable. It exists because
an answer to a good question is evidence, and evidence with no provenance cannot
be told apart from evidence a persuasive question produced.

`independent: true` marks a source you did not write. Only atoms citing one can
reach `externally_verified`.

## Skill vocabulary

Canonical skill names mapped to aliases, so "threat modelling" and "threat
modeling" are one thing. Free-text skills fragment as a pack grows and quietly
break recall; a search that silently misses things is worse than no search.

## Private profile

Name, location, email, phone, LinkedIn. Included in full only on a document sent
to a named recipient; a public artefact gets name and location. `address` and
`photo_reference` never appear in any artefact and are stripped before generation
sees the pack.

## Capture notes

`data/capture/notes.jsonl` — an append-only log, deliberately **not** part of the
pack. A thirty-second note must not require a new pack version, because that
friction is what stops people capturing at all. Notes are promoted into atoms
later, ids are never reused.

## Relationship to JSON Resume

[JSON Resume](https://jsonresume.org/) (`resume.json`) is an established standard
with 14 top-level sections, ISO 8601 dates, and a theme ecosystem. Its schema has
**no fields for evidence, provenance, sources, or confidence** — it records what
you claim, not how you know it.

`career.json` is the layer above: it keeps the evidence, the sources, the
confidence, the dates you inferred rather than recorded, and the material you must
never publish. `scripts/export_resume_json.py` projects it down, dropping
everything JSON Resume cannot represent.

Project down for compatibility. Never treat the projection as the record: it has
thrown away the parts that make the record trustworthy.
