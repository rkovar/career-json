# Architecture

## Components and release boundaries

Career Evidence Core is an independently runnable early-access toolkit; Resume
Application is a beta add-on. See [releases](releases.md) for ownership, compatibility
and quality gates. `components/*/component.json` declares independent versions and
explicit release file lists. `build_release.py` checks dependencies and builds
separate archives; the add-on cannot replace core files or include private data.

`career_core.py`, `career_profile.py`, `pack_io.py`, `schema_tools.py` and
`evidence_rules.py` own shared maintenance and validation primitives. Resume
modules consume them. `editorial.py` retains output decisions and selection while
forwarding its historical core commands for compatibility. Core pack validation
no longer imports the application. Clean-install tests exercise this boundary.

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
.claude/skills/     judgement: the twelve skills
scripts/            decidable work, standard library only
schemas/            contracts: datapack, role profile, evaluation, screen record
tests/              regression, human-review and clean-install checks
data/               your private material, excluded from Git and release archives
  sources/            raw input
  candidates/         proposed changes awaiting human review
  packs/              current and previous versions linked by metadata.supersedes
  roles/              structured role profiles
  briefs/             durable output briefs
  selections/         immutable evidence selections and alternatives
  capture/            the append-only note log
  private/            pre-schema profiles
outputs/            generated artefacts, evaluations, screens. Git ignored.
                    A screen records its context: "fresh" means it was produced
                    by a context holding only the artefact, the role profile and
                    the skill, never by the context that wrote the document.
reviews/            source answers and review records. Git ignored
  pack-reviews/       proposal snapshots, sessions and immutable decision batches
  decisions/          scoped editorial decisions
```

## Scripts

| Script | Role |
| --- | --- |
| `career_core.py` | Core maintenance, candidate strengths queues, private export and review commands |
| `pack_review.py` | Stages proposals, records human decisions and saves accepted local versions |
| `review_html.py` / `pack_html.py` | Offline guided proposal review and read-only current-pack overview |
| `current_pack.py` | Resolves the current pack by supersedes chain, not by mtime. Refuses when ambiguous |
| `select_evidence.py` | Emits only eligible evidence; `--role` ranks and shortlists against a profile |
| `render.py` | Markdown to HTML through one template, so the two cannot drift |
| `answer.py` | Records a review answer verbatim, at the moment it is given, where the atom can cite it |
| `keyword_coverage.py` | Which ATS keywords a draft carries, and which confirmed atoms could carry the missing ones |
| `link_evidence.py` | Proposes, confirms, rejects and migrates requirement-to-evidence links; only subject-confirmed links count in role_fit |
| `entailment.py` | A cold model judges each bullet against only its cited atom: supported, overstated, unsupported. Reporting only; spends tokens |
| `verify_excerpts.py` | Re-extracts each cited source and fails on an excerpt it does not contain: the source-to-atom hop |
| `validate_pack.py` | Structural check on a pack |
| `validate_artifact.py` | An artefact against the pack that produced it |
| `validate_records.py` | Evaluation, screen, and role-profile records |
| `quantities.py` | Magnitudes a bullet asserts that its cited atom does not carry. Warns through `validate_artifact.py`; never blocks |
| `manifest.py` | Pack hash and skill hashes, pinned into an evaluation record |
| `save_review.py` | Attach the exact saved manifest and validate a review before atomic publication |
| `private_facts.py` | Recorded dates and explicit measurement states for private briefs |
| `capture.py` | The note log. Never writes to the pack |
| `find.py` | Recall by term, skill, tag, employer, date, outcome, status |
| `dedupe.py` | Is this claim already in the pack? |
| `coverage.py` | Timeline, gaps, undated atoms, stale skills |
| `role_fit.py` | Coverage against every role profile; corroboration beside it, never gating; names withheld and unresolved evidence |
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

`make check` runs 585 assertions in the original suite and 35 editorial tests, 8 core tests, 25 human-review tests and 6 release installation tests: real tests over the scripts, plus a lint
asserting each skill still states its load-bearing rules. That lint exists because
prose regressions are invisible — during one refactor it caught a rewrite that had
silently dropped two rules from a skill file.

The original suite runs against **two** fictional fixtures, and the second one matters.
`career.example.json` is small and readable. `career.complex.example.json` has the
shape of a real pack: a promotion chain, withheld and unresolved evidence, undated
atoms, and an independent source. Everything used to run against the small one
only, and three defects shipped behind that gap — a leak scan that failed the
private brief on the words it exists to state, a magnitude check that emitted
eighty warnings on one document, and a fit score with no eligibility filter. None
were visible to the passing checks; all three appeared within one
run against real data.

Behavioural claims that need a model in the loop are listed in
`tests/scenarios.md` and run by hand after a material skill edit.


## Editorial memory

See [editorial-memory.md](editorial-memory.md) for the contracts and full workflow.
`editorial.py` validates references, resolves scoped decisions, builds durable
selections, filters profile context and detects changed support. Schema 1.4 adds
optional strengths and preferences; archived schema 1.3 keeps older packs usable.
The three new skills interview for strengths, review selection when requested,
and assess representation. Selection reasons and briefs survive deletion of outputs.

The editorial tests additionally cover five fictional career profiles and sequences
of shortening, retargeting, correction and regeneration. Model-driven checks in
`tests/run_editorial_scenarios.py` test actual interpretation and writing in an
isolated fixture workspace; they are separate from `make check`.

## Human review of career data

See [pack review](pack-review.md). Proposed packs stay outside the current-pack
chain. An offline document presents exact values, sources and before/after changes.
Immutable decision batches bind a person’s choices to the proposal fingerprint;
only explicitly accepted content and privacy restrictions enter a new pack.
Human wording review is separate from evidence confidence and publication rights.
Corrections and omissions remain follow-up notes until reviewed as new proposals.
