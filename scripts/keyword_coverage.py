#!/usr/bin/env python3
"""Which of a role's ATS keywords the artefact carries, and where the missing ones could come from.

ATS screens and first-pass readers look for the role's own vocabulary. Stuffing
it in is the wrong fix; the right one is knowing which confirmed atoms already
carry the missing terms so the bullet built from them can use the words.
Report only.

    scripts/keyword_coverage.py outputs/head-of-ai-security-draft.md --role head-of-ai-security
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from current_pack import resolve, ROOT  # noqa: E402
from select_evidence import load_role, contains_term, atom_prose, canonical, linked_ids  # noqa: E402


def coverage(markdown, profile, pack):
    visible = re.sub(r"<!--.*?-->", "", markdown)
    canon = canonical(pack)
    atoms = {a["id"]: a for a in pack.get("evidence_atoms", [])}
    confirmed = {i for req in profile.get("requirements", []) for i in linked_ids(req, confirmed_only=True)}
    present, missing = [], []
    for keyword in profile.get("ats_keywords", []):
        forms = {keyword} | {a for c, aliases in (pack.get("skill_vocabulary") or {}).items()
                             if c.lower() == canon.get(keyword.lower(), "").lower() for a in aliases}
        if any(contains_term(visible, f) for f in forms):
            present.append(keyword)
        else:
            carriers = [i for i in confirmed if i in atoms and any(
                contains_term(atom_prose(atoms[i]), f) or
                any(contains_term(s, f) for s in atoms[i].get("skills", [])) for f in forms)]
            missing.append({"keyword": keyword, "confirmed_atoms_carrying_it": sorted(carriers)})
    total = len(profile.get("ats_keywords", []))
    return {"role_id": profile["role_id"], "present": present, "missing": missing,
            "coverage": round(100 * len(present) / total) if total else None}


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("markdown", type=Path)
    parser.add_argument("--role", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv[1:])
    path = resolve()
    if path is None:
        print("no pack found", file=sys.stderr)
        return 1
    report = coverage(args.markdown.read_text(), load_role(args.role), json.loads(path.read_text()))
    if args.json:
        print(json.dumps(report, indent=2))
        return 0
    print(f"{report['coverage']}% of {report['role_id']} keywords on the page "
          f"({len(report['present'])} present, {len(report['missing'])} missing)")
    for row in report["missing"]:
        via = ", ".join(row["confirmed_atoms_carrying_it"]) or "no confirmed atom carries it: do not add it"
        print(f"  missing {row['keyword']!r}: {via}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
