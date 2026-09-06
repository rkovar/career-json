#!/usr/bin/env bash
# Extract plain text from a source file for ingestion, and report the values a
# source record needs: sha256, extracted character count, and byte size.
#
#   scripts/extract_text.sh data/sources/resume.pdf            # text to stdout
#   scripts/extract_text.sh --record data/sources/resume.pdf   # source record fields
#
# PDF extraction uses the first available of: pdftotext (poppler, any platform),
# or Swift PDFKit (macOS, no install needed). Text-like files are read directly.
set -euo pipefail

RECORD=0
if [ "${1:-}" = "--record" ]; then RECORD=1; shift; fi
FILE="${1:?usage: extract_text.sh [--record] <file>}"
[ -f "$FILE" ] || { echo "no such file: $FILE" >&2; exit 1; }

extract_pdf() {
  if command -v pdftotext >/dev/null 2>&1; then
    pdftotext -layout "$1" -
  elif [ "$(uname)" = "Darwin" ] && command -v swift >/dev/null 2>&1; then
    local tmp; tmp="$(mktemp -t pdftext).swift"
    cat > "$tmp" <<'SWIFT'
import Foundation
import PDFKit
for path in CommandLine.arguments.dropFirst() {
    guard let doc = PDFDocument(url: URL(fileURLWithPath: path)), let text = doc.string else {
        FileHandle.standardError.write("could not read \(path)\n".data(using: .utf8)!)
        exit(1)
    }
    print(text)
}
SWIFT
    swift "$tmp" "$1"; rm -f "$tmp"
  else
    echo "No PDF extractor available. Install poppler (brew install poppler, apt install poppler-utils) or convert the file to text by hand." >&2
    exit 1
  fi
}

extract_docx() {
  # pandoc first, as the workspace docx skill recommends: it keeps tab and
  # column spacing. Otherwise a .docx is a zip holding word/document.xml and
  # the text is the w:t runs, one paragraph per w:p; that fallback needs
  # nothing installed. Read as bytes it produced 120,000 "characters" of zip
  # noise and a source record that was provenance for nothing.
  if command -v pandoc >/dev/null 2>&1; then
    pandoc -t plain --wrap=none "$1"
    return
  fi
  python3 - "$1" <<'PY'
import sys, zipfile, xml.etree.ElementTree as ET
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
with zipfile.ZipFile(sys.argv[1]) as z:
    root = ET.fromstring(z.read("word/document.xml"))
for para in root.iter(W + "p"):
    print("".join(t.text or "" for t in para.iter(W + "t")))
PY
}

case "${FILE##*.}" in
  pdf|PDF) METHOD="pdftotext or macOS PDFKit"; TEXT="$(extract_pdf "$FILE")" ;;
  docx|DOCX) METHOD="$(command -v pandoc >/dev/null 2>&1 && echo 'pandoc -t plain' || echo 'python zipfile, word/document.xml')"; TEXT="$(extract_docx "$FILE")" ;;
  txt|text|md|markdown|json|csv|tsv|html|htm|xml|yaml|yml|rtf|TXT|TEXT|MD|JSON|CSV|HTML|XML)
           METHOD="direct UTF-8 read";        TEXT="$(cat "$FILE")" ;;
  *)
    # The default branch used to cat anything, so a .pptx, .doc or image
    # "extracted" as zip noise and became provenance for nothing, the docx
    # failure over again for every other binary. Unknown types are refused.
    echo "unsupported file type .${FILE##*.}: convert it to PDF, DOCX or text first" >&2
    exit 1 ;;
esac

if [ "$RECORD" -eq 1 ]; then
  CHARS=$(printf '%s' "$TEXT" | wc -m | tr -d ' ')
  BYTES=$(wc -c < "$FILE" | tr -d ' ')
  SHA=$(shasum -a 256 "$FILE" | cut -d' ' -f1)
  case "${FILE##*.}" in pdf|PDF) STYPE=pdf ;; docx|DOCX) STYPE=other ;; md|markdown|MD) STYPE=markdown ;; json|JSON) STYPE=json ;; *) STYPE=text ;; esac
  printf '  "source_type": "%s",\n' "$STYPE"
  printf '  "path": "%s",\n  "sha256": "%s",\n  "character_count": %s,\n  "byte_size": %s,\n' "$FILE" "$SHA" "$CHARS" "$BYTES"
  printf '  "extraction_method": "%s",\n  "independent": false\n' "$METHOD"
else
  printf '%s\n' "$TEXT"
fi
