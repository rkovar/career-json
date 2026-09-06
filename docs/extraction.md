# Extracting Text From Sources

Ingestion needs the text of a source plus the values that make its provenance
auditable. `scripts/extract_text.sh` does both and requires nothing beyond the
shell.

```sh
scripts/extract_text.sh data/sources/resume.pdf             # text to stdout
scripts/extract_text.sh --record data/sources/resume.pdf    # source record fields
```

`--record` prints the `sha256`, `character_count`, `byte_size`,
`extraction_method`, and `independent` fields for a `source_records` entry.

## What it uses

| Input | Extractor |
| --- | --- |
| PDF, any platform with poppler | `pdftotext -layout` |
| PDF, macOS without poppler | Swift PDFKit, no install required |
| Word `.docx`, with pandoc | `pandoc -t plain`, which keeps tab and column spacing |
| Word `.docx`, without pandoc | `word/document.xml` read with the standard library, no install required |
| Anything else | Direct UTF-8 read |

If neither PDF extractor is present the script says so and exits non-zero. Install
poppler (`brew install poppler`, `apt install poppler-utils`) or convert the file
to text by hand.

A `.docx` is a zip, and read as bytes it yields around 120,000 "characters" of
zip noise: a source record that is provenance for nothing. Both docx paths read
the document text; `--record` reports `source_type: "other"` for it, since the
schema has no Word type and "text" would misdescribe the file.

## Two things to get right

**`character_count` is extracted text, not file size.** A 275 KB resume PDF holds
about 11,000 characters of text. Recording the byte size makes a source look an
order of magnitude richer than it is. The script measures the text and records the
file size separately as `byte_size`.

**`independent` defaults to false, and usually stays false.** A source you wrote
is not independent, whatever it contains. Set it true only for third-party
material: a conference programme, an employer's public page, a published article
under someone else's masthead. Only atoms citing an independent source can reach
`externally_verified`.

## URL sources

Public pages are recorded with `source_type: "url"`, the URL in `path`, and a
`retrieved` date instead of a hash. Capture the URL at the moment you check it. A
check that leaves no record cannot support `externally_verified`, and the atom
stays `corroborated`.

## Validating afterwards

```sh
python3 scripts/validate_pack.py
```

Standard library only. It checks required fields, status and outcome enums,
source-reference integrity, duplicate IDs, the URL-versus-file source rules, that
`externally_verified` atoms actually cite an independent source, and that
`private_profile` exists. Superseded packs are skipped. Warnings flag atoms with
no corroborator and packs with no contact details.
