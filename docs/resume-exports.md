# PDF, TXT and DOCX export

All three formats are required in the first release of the revised workflow.
They share a derived document (`resume_document.py`) built from the final cited
Markdown. Supported source syntax is H1–H4 headings, paragraphs, ordinary bullets,
inline emphasis and recorded HTTP(S)/mailto links. Unsupported tables, images,
raw HTML, code and other structures fail explicitly instead of silently dropping
content. URLs are visible in every format; headings, chronology and wording stay
identical. Exporting never rewrites facts or edits the career pack.

```sh
python3 scripts/export_resume.py outputs/example-draft.md --plan data/plans/example-v2-plan.json --output outputs/example-v2-export
python3 scripts/export_resume.py --check outputs/example-v2-export/review/export-report.json
```

The output directory must be new. `files/` contains only `resume.pdf`, `resume.txt`
and `resume.docx`. `review/` holds the clean HTML preview, internal derived document
with claim references, and export report. Send only the required files from
`files/`, never the review directory. The report pins the draft, plan and actual
submission bytes. Re-export to a new directory after editing. A standalone legacy
draft may omit `--plan` and supply `--paper-size A4|Letter` and `--page-limit N`;
this compatibility path does not confer planned-resume approval.

- **PDF:** real selectable text, correct recovered order, actual page count and
  compliance with the recorded limit. Source URLs are embedded as clickable
  hyperlinks, including each fragment when a link wraps across lines.
  Chrome/Chromium renders the document using
  an isolated temporary profile, with browser headers/footers disabled. No network
  assets are loaded. Visual inspection of final page breaks is still required.
- **TXT:** UTF-8, ordinary heading text, blank-line separation and `-` list markers.
- **DOCX:** editable WordprocessingML with native paragraph styles, heading outline
  levels and true list numbering. No layout tables, floating boxes, hidden review
  data or macros. Word may paginate differently from the PDF renderer; inspect
  DOCX in the intended word processor when a DOCX page limit is consequential.

TXT and DOCX need only standard-library Python. PDF requires Chrome or Chromium
and either Poppler (`pdftotext`, `pdfinfo` and `pdftohtml`) or macOS Swift/PDFKit
for text, page-count and hyperlink checks. `export_resume.py` reports missing prerequisites or tool
failures per format and exits nonzero. It retains successful formats and a failure
report but does not label a partial bundle complete. Do not claim accessibility
or employer ATS certification from text recovery. Report those checks separately.

The automated check compares recovered text against the shared document, allowing
Unicode compatibility normalization, whitespace wrapping and list markers.
For PDF only, a physical newline after an existing hyphen or inside an expected
URL can be reconciled with the exact source token. Ordinary within-word spaces,
missing word boundaries and changed URL characters still fail. The report records
when this bounded reconciliation was needed. TXT and DOCX remain strict.
Word boundaries are preserved: `SQL pipelines` and `SQLpipelines` are different.
Missing, added or reordered content fails. Native DOCX content and styles are
also covered by regression tests. The export report records PDF tools, page count,
content checks, hashes, and unperformed visual/accessibility/Word layout checks.

An orphan evidence comment is an authored Markdown error. Attach citations to
the claim line or an indented continuation line. Keep accurate hyphenated words
and recorded URLs when troubleshooting extraction; do not rewrite the candidate
to accommodate an exporter defect.

## Clickable PDF links

The shared document retains source URL targets and their visible text spans.
Explicit Markdown links and full bare HTTP(S)/mailto URLs become HTML anchors
before PDF generation. Balanced parentheses, query strings, fragments and encoded
characters stay attached to the original destination. Use `[label](URL)` to
disambiguate URLs ending in sentence punctuation. Bare hostnames do not acquire
an invented protocol. TXT and DOCX retain the same visible URL text; this change
verifies PDF hyperlinks, not word-processor automatic link detection.

After rendering, the exporter extracts PDF hyperlinks and their clickable text.
Every logical source link must match its destination and all of its text, allowing
multiple annotations for a wrapped link. Missing, incorrect, unexpected or partly
clickable links fail the PDF export even if text extraction passes. Repeated
destinations are checked as separate occurrences. Normal browser serialization
of hostnames, Unicode and percent-encoding is allowed; changed paths, query values
and fragments are not. The Poppler branch uses `pdftohtml` XML without its `-p`
option, which would rewrite PDF link destinations; see the
[upstream utility manual](https://cgit.freedesktop.org/poppler/poppler/tree/utils/pdftohtml.1).

Version-2 export reports retain annotation targets/text, verification results and
file hashes. `--check` compares that recorded inspection with the pinned Markdown
and checks the exported file hashes. It does not rerun the PDF extractor. Older
reports cannot claim this verification; create a new export bundle when needed.
Existing files are never regenerated automatically.

These checks do not visit destinations or establish website availability. A
correct clickable URL can still lead to a removed page or require authentication.
Copying wrapped URL text may retain a line break in some viewers; clicking the
embedded hyperlink uses the complete destination independently of that text.

Run the real regression with Chrome and either supported extraction toolchain:

```sh
CAREER_TEST_REAL_PDF=1 python3 tests/test_pdf_links.py
```

This uses fictional data in temporary directories. The normal test suite runs
the deterministic link and failure-path tests without launching a browser.

For multiple positions at one employer, [employment grouping](resume-employment.md)
uses compact title/date paragraphs and H4 subsections in HTML, PDF and DOCX.

## Editorial quality and page review

Follow [resume-quality.md](resume-quality.md) for role-sensitive selection, explicit
editorial questions, review of omitted eligible evidence, PDF geometry diagnostics
and the visual review required for the exact exported bundle. These extend existing
process records; they never promote application judgments into career facts.
