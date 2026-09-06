# Parody packs

Three datapacks built for fun, and for showing the format on careers everyone
already knows. None of them is a real record. Nothing here should ever be cited
in a real artefact, which is why every pack carries
`metadata.status: example_only` and a warning field saying so.

| Pack | Why it is here |
| --- | --- |
| [`picard.career.json`](picard.career.json) | Fictional character, so nothing is constrained. Forty years of logs and the same two-page problem as everyone else |
| [`jobs.career.json`](jobs.career.json) | A career with a famous public setback in the middle of it |
| [`clinton.career.json`](clinton.career.json) | A career where the hardest problem is shared credit and a matter of record you cannot omit |

## The rules these were built under

Two of the three are real people, so the packs are deliberately narrow:

- **Public record only.** No invented achievements, no invented metrics.
- **Contact details are obviously fake.** `example.com` addresses, no phone
  numbers, no addresses. The `private_profile` block exists to show the shape.
- **No named corroborators.** Real private individuals are not listed as people
  who would confirm a claim. Where a corroborator appears at all it is a role.
- **Every source is a placeholder URL** on `example.org`, not a real citation.
  These packs demonstrate the format, not the provenance.

## What they actually demonstrate

The interesting fields are the ones that record what works *against* you, and a
famous career exercises them harder than a normal one.

**`role_fit_notes`** carries the same evidence pointing both ways. Jobs leaving
Apple in 1985 reads as a governance failure to a board and as conviction to
everyone else. NAFTA is a strength or a liability depending entirely on who is
reading. The pack does not resolve this; it records it and lets selection decide
per role.

**A matter of public record cannot be omitted.** Clinton's impeachment and
acquittal is in the pack, external-safe, with a note explaining that a document
which appears to hide it is worse than one that does not. The interview brief is
the place that gets used.

**Shared credit gets recorded as shared.** The Good Friday Agreement atom says
*supported*, not *delivered*, in the atom itself, so no generated document can
quietly upgrade it.

**`unresolved` is where reputation goes.** Jobs' management style is widely
reported, entirely second-hand, and therefore `external_safe: false`. It never
reaches an artefact. Second-hand characterisation is not evidence, however much
of it there is.

**Picard has the only genuinely unanswerable one.** Forty years of memory
implanted in twenty-five minutes by an alien probe. It is unresolved, ineligible,
and the open questions are recorded rather than smoothed over: does subjective
experience with no external record count as experience, and who would confirm it?

## Using one

```sh
python3 scripts/validate_pack.py examples/fun/picard.career.json
```

To generate against one, point the workspace at a copy rather than your own pack:

```sh
WS=$(mktemp -d) && mkdir -p "$WS/data/packs" "$WS/outputs"
cp examples/fun/picard.career.json "$WS/data/packs/pack.json"
CAREER_WORKSPACE="$WS" python3 scripts/select_evidence.py
```
