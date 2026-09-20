# Source Intake

Add copies of the materials you want Claude to use under `data/sources/`. Keep raw files local; that directory is ignored by Git.

## Useful inputs

- Existing resumes and CVs
- LinkedIn export
- End-of-year reviews and work writeups
- Awards and recognition
- Presentations and conference material, and any catalogue of talks, publications, podcasts and courses (each item becomes a `publications` record)
- Project notes and architecture documents
- GitHub repository exports or selected repository files
- Education, certifications, and training records
- Optional private profile information such as name, location, address, and photo

## Before ingestion

1. Remove material you do not want Claude to see.
2. Keep the original filename and source context where possible.
3. Separate public, internal, and private material if that distinction matters.
4. Do not add passwords, API keys, or unrelated personal information.

## Start the workflow

After adding the files, ask Claude:

> Use `build-career-pack` on everything in `data/sources/`.

Claude inspects the requested scope, separates career evidence from job
descriptions and writing advice, and prepares a proposed pack and readable review.
Evidence questions are queued for review; they are not a giant questionnaire to
answer at once. Contact details beyond name/location can wait until delivery.

For help deciding what to bring, say **“Help me start a career pack”**. The
[guided start](guided-starts.md) offers a checklist or conversational account,
saves deferrals, and works with one source. Resume generation is separate.

## Extraction

PDFs are the most common input. `scripts/extract_text.sh` handles them without any
install on macOS, and with poppler elsewhere. See [extraction.md](extraction.md).
You do not need to run it yourself; `build-career-pack` uses it.
For large archives, the report includes `reading_batches` of roughly 60,000
extracted characters. These are suggested reading boundaries, not a token budget
or a completeness score. Oversized individual sources are flagged for reading in
sections. The operator saves a valid partial proposal after each useful batch,
then resumes from that proposal and the remaining paths. Every authorized source
remains in the inventory; batching never grants permission to omit material.

Intake's `purpose_hint` is a keyword suggestion, not a final classification.
The operator inspects the content before excluding it as a job description or
writing advice. A relevant interview can contain a hiring quote or careers link.
Only an explicitly supplied classification changes the source's purpose; an
unreviewed hint cannot make new material disappear from the intake summary.

## Preserve coverage across batches

Evidence can add a record **or support an existing one**. A customer account of a
programme, project report or interview can strengthen an achievement without
becoming a publication. Attach its source and excerpt to the existing record.
Do not exclude it because the current batch is about talks or it adds no new work.

When staging an extraction, pass the original report returned by intake:

```sh
python3 scripts/career_core.py review start --candidate data/candidates/proposal.json --id first --intake reviews/intake/intake-example.json
```

Use the actual generated intake path in place of `intake-example.json`. The review
retains the whole inventory across `review revise` and `review correct`. Its status
and page show sources linked to claims, sources still to process and explicit
deferrals. Registering a source without attaching its excerpt to a career record
does not complete its coverage. Partial proposals can still be saved.

For material that should wait or is unrelated, optionally supply
`--dispositions data/private/source-dispositions.json`:

```json
{
  "data/sources/project-report.md": {
    "outcome": "defer",
    "reason": "Read this during the achievements batch."
  },
  "data/sources/job-description.md": {
    "outcome": "exclude",
    "purpose": "job_context",
    "reason": "Requirements for a target role, not the person's history."
  }
}
```

Exclusion purposes are `job_context`, `writing_reference` or
`not_career_evidence`. Material classified as career evidence needs a record link
or deferral. If the initial classification was wrong, inspect it and create a
corrected intake report. `not_relevant` to one batch is not a whole-career
exclusion. Revisions retain dispositions unless replacements are supplied; a newly
linked source supersedes its deferral automatically.

Check coverage without editing anything:

```sh
python3 scripts/career_core.py intake --report reviews/intake/intake-example.json --candidate data/candidates/proposal.json
```

Add `--dispositions` to include exclusions or deferrals. Exit status is nonzero
while sources remain pending, deferred or changed since intake. This is a
completeness check, not a prerequisite for saving reviewed facts. Links do not
establish that every important fact in a long document was preserved; the final
source-to-pack review still checks meaning, contribution and scope.

## Catalogue coverage

For a large publication archive, the assistant saves a compact coverage note beside
the review. Each catalogue entry or author-page card maps to a publication ID, an
existing achievement, a collection/profile, or an explicit unresolved item. Count
only individually identified works; a series or archive is not another authored
item. Summaries of programmes and team founding remain achievements.

Preserve the stated contribution: author, co-author, foreword contributor, host,
guest, speaker and committee member are different roles. A shared archive URL
does not make two talks the same work. Use titles, dates, venues and contributor
context to reconcile duplicates; preserve conflicting titles when unresolved.
Missing dates stay unknown. Unidentified decks or episodes stay listed as coverage
gaps, without inventing titles or requiring another interview before saving.

Publications carry an absolute HTTP(S) URL or `null`. Local captures belong in
source references. Copy an actual source link or the saved page's canonical URL;
never construct a likely address from its title. Compare existing URLs when
merging duplicate items: preserving richer metadata must not preserve a wrong
address. Format validation does not establish provenance or live availability.
A title-only video capture supports its title, not the complete
description; a saved 404 supports no career claim. Text extraction failure for an
image should lead to direct image inspection when the assistant supports it, with
the visual check and any automated-verification limitation stated separately.

The coverage note makes omissions visible; it is not factual approval or proof
that every description is correct. Only the ordinary review accepts new content.
