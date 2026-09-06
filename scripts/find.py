#!/usr/bin/env python3
"""Search the pack. The point of a career memory is getting things back out.

At twenty atoms you can read the file. At two hundred, which is where a pack
lands after a few years of annual write-ups, you cannot, and the whole thing
quietly stops being used.

Skill matching goes through skill_vocabulary, so "threat modelling" also finds
"threat modeling" and "threat models" rather than silently missing them.

    scripts/find.py kubernetes
    scripts/find.py --skill "threat modelling"
    scripts/find.py --since 2020 --outcome business_outcome
    scripts/find.py --employer Splunk --tag scaling
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from current_pack import resolve, this_year, ROOT  # noqa: E402


def canonical_map(pack):
    """alias -> canonical, so a query in any spelling lands on the same skill."""
    out = {}
    for canon, aliases in (pack.get("skill_vocabulary") or {}).items():
        out[canon.lower()] = canon
        for alias in aliases:
            out[alias.lower()] = canon
    return out


def atom_years(atom, employment):
    occurred = atom.get("occurred")
    if occurred:
        start = occurred["start"][:4]
        end = (occurred.get("end") or occurred["start"])
        return start, (str(this_year()) if end == "ongoing" else end[:4])
    rec = employment.get(atom.get("employment_id"))
    if rec:
        end = rec.get("end")
        return rec["start"][:4], (str(this_year()) if end == "present" else (end or rec["start"])[:4])
    return None, None


def matches(atom, args, canon, employment):
    if args.terms:
        blob = json.dumps(atom).lower()
        if not all(t.lower() in blob for t in args.terms):
            return False
    if args.skill:
        wanted = {canon.get(s.lower(), s.lower()) for s in args.skill}
        have = {canon.get(s.lower(), s.lower()) for s in atom.get("skills", [])}
        # Exact canonical match, or one name contained in the other: a pack will
        # always hold "AI threat modelling" alongside "threat modelling", and a
        # search that misses the first is a search nobody trusts.
        def within(a, b):
            return re.search(r"(?<![a-z0-9])" + re.escape(a) + r"(?![a-z0-9])", b) is not None
        if not (wanted & have or any(within(w, h) or within(h, w) for w in wanted for h in have)):
            return False
    if args.tag and not set(args.tag) & set(atom.get("tags", [])):
        return False
    if args.outcome and atom.get("outcome_type") != args.outcome:
        return False
    if args.status and atom.get("evidence_status") != args.status:
        return False
    if args.employer:
        rec = employment.get(atom.get("employment_id"))
        if not rec or args.employer.lower() not in rec["employer"].lower():
            return False
    start, end = atom_years(atom, employment)
    if args.since and (end is None or end < args.since[:4]):
        return False
    if args.until and (start is None or start > args.until[:4]):
        return False
    return True


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("terms", nargs="*", help="free-text terms, all must match")
    parser.add_argument("--skill", action="append", default=[])
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--employer")
    parser.add_argument("--since", help="YYYY")
    parser.add_argument("--until", help="YYYY")
    parser.add_argument("--outcome", choices=("business_outcome", "output", "activity"))
    parser.add_argument("--status", choices=("self_asserted", "corroborated",
                                             "externally_verified", "unresolved", "declined"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv[1:])

    path = resolve()
    if path is None:
        print("no pack found", file=sys.stderr)
        return 1
    pack = json.loads(path.read_text())
    employment = {e["employment_id"]: e for e in pack.get("employment", [])}
    canon = canonical_map(pack)

    hits = [a for a in pack["evidence_atoms"] if matches(a, args, canon, employment)]
    hits.sort(key=lambda a: atom_years(a, employment)[1] or "0000", reverse=True)

    if args.json:
        print(json.dumps(hits, indent=2))
        return 0
    if not hits:
        print("nothing matched")
        return 1
    print(f"{len(hits)} of {len(pack['evidence_atoms'])} atoms\n")
    for atom in hits:
        start, end = atom_years(atom, employment)
        when = f"{start}-{end}" if start and start != end else (start or "undated")
        rec = employment.get(atom.get("employment_id"))
        where = rec["employer"] if rec else "-"
        print(f"  {atom['id']}")
        print(f"    {atom['title']}")
        print(f"    {when} | {where} | {atom.get('outcome_type') or 'unclassified'}")
        result = (atom.get("star") or {}).get("result")
        if result:
            print(f"    {result[:110]}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
