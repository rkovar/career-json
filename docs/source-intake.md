# Source Intake

Add copies of the materials you want Claude to use under `data/sources/`. Keep raw files local; that directory is ignored by Git.

## Useful inputs

- Existing resumes and CVs
- LinkedIn export
- End-of-year reviews and work writeups
- Awards and recognition
- Presentations and conference material
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

That runs ingestion and evidence review in one go and ends with a single batch of
questions plus a readiness statement. It does not stop between stages, and it does
not generate a resume: that is `make-resume`, run separately once the pack exists.

On a first run the batch will include your contact details, because a pack without
them cannot produce a sendable document.

## Extraction

PDFs are the most common input. `scripts/extract_text.sh` handles them without any
install on macOS, and with poppler elsewhere. See [extraction.md](extraction.md).
You do not need to run it yourself; `build-career-pack` uses it.