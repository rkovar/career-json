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

Preserve original markdown logs as history. Resolve short/bulk answers using the
actual displayed proposal, never the final reference pack as extraction input.

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
