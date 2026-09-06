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

case "${FILE##*.}" in
  pdf|PDF) METHOD="pdftotext or macOS PDFKit"; TEXT="$(extract_pdf "$FILE")" ;;
  *)       METHOD="direct UTF-8 read";        TEXT="$(cat "$FILE")" ;;
esac

if [ "$RECORD" -eq 1 ]; then
  CHARS=$(printf '%s' "$TEXT" | wc -m | tr -d ' ')
  BYTES=$(wc -c < "$FILE" | tr -d ' ')
  SHA=$(shasum -a 256 "$FILE" | cut -d' ' -f1)
  printf '  "source_type": "%s",\n' "$([ "${FILE##*.}" = "pdf" ] && echo pdf || echo text)"
  printf '  "path": "%s",\n  "sha256": "%s",\n  "character_count": %s,\n  "byte_size": %s,\n' "$FILE" "$SHA" "$CHARS" "$BYTES"
  printf '  "extraction_method": "%s",\n  "independent": false\n' "$METHOD"
else
  printf '%s\n' "$TEXT"
fi
