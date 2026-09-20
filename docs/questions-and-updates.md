# Questions and dependable updates

The accepted career pack is the factual record. Questions and their exact answers
live separately in private review history. A saved answer supports a proposed
change; it does not approve wording the person has not seen.

Use `make start` to build, update, view or continue. For a quick summary the
operator can run `python3 scripts/career_core.py health --summary --json`.
Full `health` also verifies sources and backup references; it is deliberately
separate from fast navigation.

## Record questions before asking

Create `data/private/question.json` with the exact question and affected keys:

```json
{
  "question": "Did you personally build the tool, or lead the team that built it?",
  "targets": ["evidence_atoms/E_TOOL"],
  "kind": "factual_ambiguity",
  "required": true
}
```

```sh
python3 scripts/career_core.py questions ask --pack data/candidates/proposal.json --input data/private/question.json
```

This returns the stable ID and revision. Supply both when recording the actual
answer, so an old response cannot accidentally answer a changed question:

```sh
python3 scripts/career_core.py questions respond --id q-0123456789abcdef0123 --revision 1 --state answered --answer "I designed it; two colleagues and I built it together." --by "Career owner"
```

Use the returned `source_record` and `source_ref` in the candidate. The person
source is an immutable, hashed question/answer revision, and excerpt verification
also checks the target record. A matching “yes” elsewhere cannot validate it.

States are `open`, `answered`, `deferred`, `declined`, and `superseded`. Deferral
can record `--revisit-when`. Reopening needs an explicit `--reason`; repeated
intake does not reopen an answered question. Enrichment and preferences must be
optional. Unknown impact, missing corroboration and incomplete publication lists
do not prevent a useful first private record.

Use `questions list --all` to inspect history. The default accuracy queue combines
legacy pack questions with this history and removes answered/deferred/declined
items from required work. Startup choices still belong to the startup wizard.

The question file format has its own `version: 1`. Existing person source fields
carry its references, so career schema 1.3/1.4 and old receipts need no migration.
Do not edit old packs or append to a pinned answer revision.

## Import existing answers without another interview

`questions import --input data/private/answer-mapping.json` previews an `answers`
array. Each entry supplies `question`, `answer`, explicit `targets`, `by`, and a
`source` path/SHA256 pin. `pack` can bind the historical proposal. Use `--apply`
only after inspecting the mapping. Exact legacy text must exist in the pinned
source. Missing mappings are reported; the tool does not infer what a bare yes
approved. Reapplying the same mapping leaves the existing answer in place.
For JSON ledgers, `question` and `answer` must belong to the same object; escaped
quotes, Unicode and newlines are decoded before exact comparison. An answer from
another question is not a match, even if both strings appear elsewhere in the file.
If that question already has a different answer or a deferred/declined decision,
the import reports a conflict. Inspect the current revision and its context, then
use `respond` for an explicitly supplied change; importing does not overwrite it
or pretend the conflicting answer was saved.

Preserve original markdown logs as history. Resolve short/bulk answers using the
actual displayed proposal, never the final reference pack as extraction input.

## Reconcile answers before handoff

After each answer-driven update, inspect the affected records together. Before
the final handoff, review the complete candidate against the supplied answers
and sources once more. Excerpt verification establishes that quoted text exists;
it does not establish that the resulting claim means the same thing.

- Apply a correction everywhere it appears: title, STAR wording, metric value
  and basis, dates, constraints, notes, linked achievements and strengths. A
  corrected measurement basis does not repair a contradictory result sentence.
- Recheck inherited achievement dates when a role's dates change. Preserve
  explicit event dates and their precision; do not replace them with a whole
  employment window. Split or relink work that spans roles when the sources
  support it. Validator warnings identify some inferred date conflicts, not
  every chronology problem.
- Treat a clear answer to the exact disputed claim as its correction. Preserve
  the old source and explain the decision, but remove the resolved question.
  Keep a conflict open only when the answer leaves a real ambiguity. Declined
  details and optional corroboration are not unresolved factual obligations.
- Keep preferences within the question's scope. A choice about one publication
  count is not permission to impose the same presentation choice on all metrics.
  Store explicit career direction in `positioning_preferences`.
- Preserve the positive contribution when narrowing ownership, scope or impact.
  A warning against overclaiming is not a replacement for the supported work.
  Do not add expansions, causality or STAR details absent from the evidence.
- Keep historical approvals tied to their exact displayed content. If that
  context is unavailable, record the gap; never approve reconstructed wording.
  A newly worded strength stays `proposed` when the originally confirmed wording
  is unavailable, even if the person previously agreed with its general theme.

Save a compact reconciliation note beside the review: answer/question revision,
affected record keys, correction applied, and any remaining ambiguity or missing
context. Work through small groups of related records and save each correction
before moving on. For a numerical claim, compare the positive wording in the
result and metric value with its type, unit, period, population and attribution;
a correct caveat cannot cancel an incorrect claim. Record the concrete before/after
change, or explain why the potentially conflicting fields are consistent. A broad
"checked all answers" statement is not a substitute for this inspection.
Review only changed records at each checkpoint; the final pass also
checks their dependencies. This is an operator assessment, not a new approval
layer or proof of correctness. Show unresolved accuracy issues in the ordinary
human review; do not ask the person to repeat answers already available.

## Reassess strengths after evidence changes

`bind-strength` still writes a candidate and never approves it. It now requires
`--assessment data/private/strength-assessment.json`. The assessment has:

- `strength_sha256`: canonical digest of the original strength.
- `support`: current canonical digest of each supporting atom, by ID.
- `interpretation`: the resulting wording and `reason` for it.
- `limitations`: an entry for every original limitation, with its zero-based
  `index`, `action` (`retain`, `remove`, `replace`), and `reason`. Replacements
  also supply `text`; new limits use `action: add`, `index: null` and `text`.

Generate canonical digests using `career_profile.digest`, not file-byte hashes.
Use already recorded answers to remove stale “unrecorded” caveats while retaining
the remaining uncertainty. Do not turn a recorded measurement basis into
independent verification. The assessment explains an operator decision; it does
not prove the prose is correct. Changed wording still needs normal human review.

## Save, pause and recover

`career_core.py view` atomically regenerates the reading page from the accepted
pack. A failed render keeps the last good page; the summary reports it as stale.
`career_core.py recover` finds valid saved reviews and writes a usable
`outputs/career-handoff.md` even if the model stopped without a final response.
Recovery never accepts a proposal or claims a stopped generation completed.

The launcher hides completed setup and review sessions from normal continuation.
Use `python3 scripts/start.py --history` to inspect completed work. Independent
unfinished reviews remain distinguishable. A broken current-pack chain requires
repair rather than starting a replacement career record.
