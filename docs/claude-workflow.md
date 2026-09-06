# Claude Workflow

How to operate the workspace once it exists. For the shape of the system see the
[README](../README.md), for the schema see [data-model.md](data-model.md), and for
what is code versus what is a skill see [architecture.md](architecture.md). This
document does not repeat those.

The repository is the durable memory. Claude is the conversational operator.

## The normal path

`build-career-pack` when you have material to add, `make-resume` when you need a
document. Both are described in the [README](../README.md#skills). Two operating
rules matter and are easy to miss:

**Answer what you like during setup.** Unanswered questions leave a claim
`unresolved` rather than blocking anything. The claim is simply left out of
documents until you come back to it.

**Delivery never asks.** That is the point of answering during setup. If evidence
is thin, `make-resume` narrows or drops the claim and tells you afterwards.

## Running a single stage

The four stage skills exist for when you want one step on its own. Each is what
the orchestrators call underneath.

**`ingest-career-materials`** takes source files or `data/sources/` and reports
what it found and what is missing before creating a datapack.

**`review-evidence`** works one claim at a time. A response can clarify a claim but
never promotes its status on its own: status follows the sources, not the answer.
Keep unresolved questions in `reviews/`.

**`generate-resume`** needs the approved datapack, target role, job description,
ATS constraints, persona, target length, and recruiter context. Every substantive
claim keeps its evidence ID, carried as an `<!-- Evidence: ... -->` comment that
the renderer hides.

**`evaluate-output`** must identify factual, privacy, targeting, and style
findings. A draft is not publishable until material findings are resolved and the
evaluation explicitly passes.

Approved packs belong in `data/packs/` and must validate against
`schemas/career.schema.json`. Keep source references and stable evidence IDs
intact when revising a pack.

The files in `examples/` are fictional format references, never an approved
personal datapack. Real profiles that pre-date the schema live in `data/private/`;
treat them as self-asserted source material and confirm provenance before
ingesting them.

## Choosing where to apply

`make fit` scores the pack against every profile in `data/roles/` and ranks them.
An unevidenced essential requirement makes a role unsupported however well the
rest scores, because it is the thing they are hiring for. Use it to choose where
to apply rather than discovering the mismatch at the recruiter screen.

`make verdicts` appends screen verdicts to `reviews/verdicts.jsonl` and shows
whether artefacts are improving over time.

## Capture and recall

`scripts/capture.py` appends a one-line note to `data/capture/notes.jsonl`. It
never writes to the pack: a thirty-second note that costs a pack version is a note
that does not get written. Promote notes into atoms later, which is work worth
doing while you are already remembering, such as during an annual review.

`scripts/find.py` searches by term, skill, tag, employer, date range, outcome, or
status. Skill matching goes through `skill_vocabulary`, so a query in one spelling
finds atoms recorded in another. A search that silently misses things is worse
than no search.

`scripts/dedupe.py` compares a candidate claim against the pack. Run it before
importing an annual write-up: the second year of a continuing programme belongs in
the existing atom as a stronger Result, not in a new atom that splits one
achievement across three entries.

`occurred` records when an atom happened. Where it was inherited from an
employment window it is marked `inferred: true`, because a nine-year span is
barely a date and should be narrowed while the detail is still recallable.

## LinkedIn

There is no LinkedIn connector, deliberately. See [linkedin.md](linkedin.md).
