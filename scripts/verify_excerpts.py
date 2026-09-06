#!/usr/bin/env python3
"""Check that every recorded excerpt is really in the source it cites.

An atom's source_ref may carry an excerpt: the words in the source that the atom
was built from. Until now nothing read it back. A review of this workspace showed
a claim could be rewritten with its old citation intact and every check stayed
green, because the checks compared atoms to the pack, never atoms to the source.

This is the source-to-atom hop. It re-extracts each cited file through
extract_text.sh, compares letters and digits only (so layout, quotes, dashes and hyphenation cannot differ)
and reports every excerpt that is not a substring of its source. An ellipsis
(... or …) in an excerpt elides text: each fragment must appear, in order. It
also checks the file still matches the sha256 the source record captured, so a
replaced source cannot vouch for an excerpt taken from its predecessor.

A URL source with no saved copy cannot be checked and is reported as
unverifiable, not failed. A person source is checked against the review record
its path names. Atoms with no excerpt on any ref are counted as uncovered.

    python3 scripts/verify_excerpts.py            # current pack
    python3 scripts/verify_excerpts.py --json
    python3 scripts/verify_excerpts.py --quiet    # summary and failures only
"""
import argparse
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from current_pack import resolve, sha256, ROOT  # noqa: E402

EXTRACT = Path(__file__).resolve().parent / "extract_text.sh"
FILE_TYPES = ("pdf", "text", "markdown", "json", "other")
def normalise(text):
    """Letters and digits only. Extractors disagree about everything else: pdftotext
    and PDFKit lay out whitespace differently, a hyphen at a line end may or may
    not be a real hyphen, and quotes come curly or straight. Comparing on the
    characters that carry meaning makes a verified pack stay verified on another
    machine, at the cost of not noticing punctuation-only edits, which is the
    right trade."""
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def fragments(excerpt):
    """Split on the ellipsis before normalising, since normalising removes it."""
    return [normalise(f) for f in re.split(r"\.\.\.|…", excerpt) if normalise(f)]


def contains(source_text, excerpt):
    """Every fragment of the excerpt, in order, somewhere in the source."""
    position = 0
    for fragment in fragments(excerpt):
        found = source_text.find(fragment, position)
        if found < 0:
            return False, fragment
        position = found + len(fragment)
    return True, None


def html_text(html):
    """Visible text of a saved page: scripts, styles and tags removed."""
    html = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?s)<!--.*?-->", " ", html)
    text = re.sub(r"<[^>]+>", " ", html)
    import html as htmllib
    return htmllib.unescape(text)


def extract(path):
    result = subprocess.run([str(EXTRACT), str(path)], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "extraction failed")
    return result.stdout


def verify(pack, root=ROOT):
    sources = {s["source_id"]: s for s in pack.get("source_records", [])}
    texts, results, uncovered = {}, [], []

    def source_text(source):
        sid = source["source_id"]
        if sid in texts:
            return texts[sid]
        kind = source.get("source_type")
        path = root / source["path"] if source.get("path") else None
        if kind == "url" and source.get("saved_copy"):
            # A saved copy makes a url source checkable. HTML is reduced to its
            # text so an excerpt from the rendered page matches.
            copy = root / source["saved_copy"]
            if not copy.exists():
                texts[sid] = ("unverifiable", f"saved copy missing: {source['saved_copy']}")
            elif source.get("saved_sha256") and sha256(copy) != source["saved_sha256"]:
                texts[sid] = ("changed", "saved copy no longer matches saved_sha256")
            else:
                try:
                    raw = extract(copy) if copy.suffix.lower() == ".pdf" else html_text(copy.read_text(errors="replace"))
                    texts[sid] = ("ok", normalise(raw))
                except RuntimeError as exc:
                    texts[sid] = ("unverifiable", str(exc))
        elif kind == "url":
            texts[sid] = ("unverifiable", "url source with no saved copy")
        elif path is None or not path.exists():
            texts[sid] = ("unverifiable", f"file not found: {source.get('path')}")
        elif kind == "person":
            texts[sid] = ("ok", normalise(path.read_text()))
        elif kind in FILE_TYPES:
            recorded = source.get("sha256")
            if recorded and sha256(path) != recorded:
                texts[sid] = ("changed", "file no longer matches the sha256 the source record captured")
            else:
                try:
                    texts[sid] = ("ok", normalise(extract(path)))
                except RuntimeError as exc:
                    texts[sid] = ("unverifiable", str(exc))
        else:
            texts[sid] = ("unverifiable", f"source_type {kind!r}")
        return texts[sid]

    for atom in pack.get("evidence_atoms", []):
        refs = [r for r in atom.get("source_refs") or [] if r.get("excerpt")]
        if not refs:
            uncovered.append(atom["id"])
        for ref in refs:
            source = sources.get(ref.get("source_id"))
            row = {"atom": atom["id"], "source": ref.get("source_id"), "excerpt": ref["excerpt"]}
            if source is None:
                row.update(status="mismatch", detail="unknown source")
            else:
                state, payload = source_text(source)
                if state == "ok":
                    ok, missing = contains(payload, ref["excerpt"])
                    if ok:
                        row.update(status="verified", detail=None)
                    else:
                        row.update(status="mismatch", detail=f"not found in source: {missing!r}")
                elif state == "changed":
                    row.update(status="mismatch", detail=payload)
                else:
                    row.update(status="unverifiable", detail=payload)
            results.append(row)

    counts = {k: sum(1 for r in results if r["status"] == k) for k in ("verified", "mismatch", "unverifiable")}
    return {"excerpts": results, "counts": counts, "atoms_without_excerpt": uncovered,
            "atoms": len(pack.get("evidence_atoms", []))}


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--quiet", action="store_true", help="summary and failures only")
    args = parser.parse_args(argv[1:])

    path = resolve()
    if path is None:
        print("no pack found; nothing to verify")
        return 0
    report = verify(json.loads(path.read_text()))
    if args.json:
        print(json.dumps(report, indent=2))
        return 1 if report["counts"]["mismatch"] else 0

    for row in report["excerpts"]:
        if args.quiet and row["status"] == "verified":
            continue
        mark = {"verified": "ok  ", "mismatch": "FAIL", "unverifiable": "??  "}[row["status"]]
        line = f"{mark}  {row['atom']} <- {row['source']}: {row['excerpt'][:70]!r}"
        if row["detail"]:
            line += f"\n        {row['detail']}"
        print(line)
    c = report["counts"]
    covered = report["atoms"] - len(report["atoms_without_excerpt"])
    print(f"\n{c['verified']} verified, {c['mismatch']} mismatched, {c['unverifiable']} unverifiable; "
          f"{covered} of {report['atoms']} atoms carry an excerpt")
    if report["atoms_without_excerpt"] and not args.quiet:
        print("no excerpt: " + ", ".join(report["atoms_without_excerpt"]))
    return 1 if c["mismatch"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
