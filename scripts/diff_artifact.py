#!/usr/bin/env python3
"""Compare two artefacts by what they claim, not by their words.

A text diff of two resumes is mostly noise. What matters between regenerations is
which evidence entered or left the document, and whether the claim mix improved.

    python3 scripts/diff_artifact.py outputs/a-draft.md outputs/b-draft.md
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from current_pack import resolve  # noqa: E402

EVIDENCE_ID = re.compile(r"E_[A-Z0-9_]+")


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    args = parser.parse_args(argv[1:])

    pack_path = resolve()
    atoms = {a["id"]: a for a in json.loads(pack_path.read_text())["evidence_atoms"]} if pack_path else {}

    before = set(EVIDENCE_ID.findall(args.before.read_text()))
    after = set(EVIDENCE_ID.findall(args.after.read_text()))

    def describe(ids):
        for i in sorted(ids):
            atom = atoms.get(i)
            extra = f" ({atom['outcome_type']}, {atom['evidence_status']})" if atom else ""
            print(f"    {i}{extra}")

    print(f"before: {args.before}  ({len(before)} claims)")
    print(f"after:  {args.after}  ({len(after)} claims)")
    if after - before:
        print("\n  added:")
        describe(after - before)
    if before - after:
        print("\n  removed:")
        describe(before - after)
    if not (after - before) and not (before - after):
        print("\n  same evidence set")

    def mix(ids):
        kinds = [atoms[i].get("outcome_type") for i in ids if i in atoms]
        return {k: kinds.count(k) for k in ("business_outcome", "output", "activity")}
    if atoms:
        print(f"\n  outcome mix before: {mix(before)}")
        print(f"  outcome mix after:  {mix(after)}")
    words_before = len(args.before.read_text().split())
    words_after = len(args.after.read_text().split())
    print(f"\n  words: {words_before} -> {words_after}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
