# Architecture

## The dividing line

**Anything decidable from the pack alone is a script. Everything requiring
judgement is a skill.**

Eligibility filtering, rendering, date arithmetic, and artefact checks are pure
functions over data. Written as instructions to a model they get re-derived on
every run, inconsistently, and cannot be tested. Written as code they are checked
once and hold.

Writing a bullet that preserves the meaning of a Result, deciding whether a claim
reads as ownership or team credit, judging whether a document would be shortlisted
— those are judgement, and they belong in skills.

The strongest version of this shows up in selection. Generation reads a
**selection view**, not the pack: ineligible evidence never enters context, so the
rule "do not cite `external_safe: false` atoms" cannot be broken by a lapse in
attention. You cannot cite what you were never shown. That is strictly stronger
than any instruction.

## Layout

```
.claude/skills/     judgement: the nine skills
scripts/            decidable work, standard library only
schemas/            contracts: datapack, role profile, evaluation, screen record
tests/              456 assertions plus a skill-invariant lint
data/               your material. Git ignored, never leaves the machine
  sources/            raw input
  packs/career.json   the current record
  packs/archive/      superseded versions
  roles/              structured role profiles
  capture/            the append-only note log
  private/            pre-schema profiles
outputs/            generated artefacts, evaluations, screens. Git ignored
reviews/            review records and decisions. Git ignored
```

## Scripts

| Script | Role |
| --- | --- |
| `current_pack.py` | Resolves the current pack by supersedes chain, not by mtime. Refuses when ambiguous |
| `select_evidence.py` | Emits only eligible evidence; `--role` ranks and shortlists against a profile |
| `render.py` | Markdown to HTML through one template, so the two cannot drift |
| `validate_pack.py` | Structural check on a pack |
| `validate_artifact.py` | An artefact against the pack that produced it |
| `validate_records.py` | Evaluation, screen, and role-profile records |
| `quantities.py` | Magnitudes a bullet asserts that its cited atom does not carry. Warns through `validate_artifact.py`; never blocks |
| `manifest.py` | Pack hash and skill hashes, pinned into an evaluation record |
| `capture.py` | The note log. Never writes to the pack |
| `find.py` | Recall by term, skill, tag, employer, date, outcome, status |
| `dedupe.py` | Is this claim already in the pack? |
| `coverage.py` | Timeline, gaps, undated atoms, stale skills |
| `role_fit.py` | Score the pack against every role profile, and name what no artefact may cite |
| `pack_html.py` | Browsable private view of the whole pack, withheld atoms included. Never sendable |
| `open_questions.py` | Every outstanding question, ranked by what answering unlocks. `--delta` reports movement resting on no source |
| `corroboration_plan.py` | Optional: what is worth corroborating |
| `verdict_log.py` | Screen verdicts over time |
| `artifact_index.py`, `diff_artifact.py` | What exists, and what changed between versions |
| `extract_text.sh` | Source text plus provenance fields |
| `export_resume_json.py` | Lossy projection to JSON Resume (`resume.json`) |

Every script honours `CAREER_WORKSPACE` so tests never touch live data.

## Versioning and provenance

Packs are never edited in place. A new pack sets `metadata.supersedes`, and
`current_pack.py` walks that chain, so "which pack is current" has exactly one
answer rather than depending on file timestamps.

Every evaluation record carries a `run` block pinning the pack sha256 and a hash
per skill. `validate_artifact.py` reads that pin and validates against the pack
that *produced* the artefact, reporting staleness when the pack has moved on.
Provenance that nothing consumes is worse than none, because it looks like the
problem is solved.

## Testing

`make check` runs 456 assertions: real tests over the scripts, plus a lint
asserting each skill still states its load-bearing rules. That lint exists because
prose regressions are invisible — during one refactor it caught a rewrite that had
silently dropped two rules from a skill file.

Tests run against **two** fictional fixtures, and the second one matters.
`career.example.json` is small and readable. `career.complex.example.json` has the
shape of a real pack: a promotion chain, withheld and unresolved evidence, undated
atoms, and an independent source. Everything used to run against the small one
only, and three defects shipped behind that gap — a leak scan that failed the
private brief on the words it exists to state, a magnitude check that emitted
eighty warnings on one document, and a fit score with no eligibility filter. None
were visible to three hundred passing assertions; all three appeared within one
run against real data.

Behavioural claims that need a model in the loop are listed in
`tests/scenarios.md` and run by hand after a material skill edit.
