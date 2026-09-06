#!/usr/bin/env python3
"""Show where the record is thin, because gaps are where forgetting already won.

A career memory cannot tell you what you have forgotten. It can tell you which
periods hold nothing, which is the same information from the other side, and which
skills have not appeared in years.

    scripts/coverage.py               # timeline and gaps
    scripts/coverage.py --markdown
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from current_pack import resolve, this_year, ROOT  # noqa: E402


def atom_year(atom, employment):
    occurred = atom.get("occurred") or {}
    end = occurred.get("end") or occurred.get("start")
    if end:
        return this_year() if end == "ongoing" else int(end[:4])
    rec = employment.get(atom.get("employment_id"))
    if rec:
        end = rec.get("end")
        return this_year() if end == "present" else int((end or rec["start"])[:4])
    return None


def analyse(pack):
    employment = {e["employment_id"]: e for e in pack.get("employment", [])}
    atoms = pack["evidence_atoms"]

    years = Counter()
    undated = []
    inferred = []
    for atom in atoms:
        year = atom_year(atom, employment)
        if year is None:
            undated.append(atom["id"])
            continue
        years[year] += 1
        if (atom.get("occurred") or {}).get("inferred"):
            inferred.append(atom["id"])

    if employment:
        first = min(int(e["start"][:4]) for e in employment.values())
    else:
        first = min(years) if years else this_year()
    span = list(range(first, this_year() + 1))
    gaps, run = [], []
    for year in span:
        if years.get(year):
            if len(run) >= 2:
                gaps.append((run[0], run[-1]))
            run = []
        else:
            run.append(year)
    if len(run) >= 2:
        gaps.append((run[0], run[-1]))

    recent_cutoff = this_year() - 5
    skill_last = {}
    for atom in atoms:
        year = atom_year(atom, employment)
        for skill in atom.get("skills", []):
            if year and year > skill_last.get(skill, 0):
                skill_last[skill] = year
    stale = sorted((s, y) for s, y in skill_last.items() if y < recent_cutoff)

    return {"span": span, "by_year": dict(years), "gaps": gaps, "undated": undated,
            "inferred": inferred, "stale_skills": stale,
            "recent_atoms": sum(v for k, v in years.items() if k >= recent_cutoff),
            "total": len(atoms)}


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--markdown", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv[1:])

    path = resolve()
    if path is None:
        print("no pack found", file=sys.stderr)
        return 1
    data = analyse(json.loads(path.read_text()))
    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    lines = []
    if args.markdown:
        lines.append(f"# Coverage\n\nPack: `{path.relative_to(ROOT)}`\n")
    peak = max(data["by_year"].values()) if data["by_year"] else 1
    lines.append("Timeline (atoms recorded per year):\n")
    for year in data["span"]:
        count = data["by_year"].get(year, 0)
        bar = "#" * int(round(count / peak * 28)) if count else ""
        lines.append(f"  {year}  {count:>2}  {bar}")
    lines.append("")
    if data["gaps"]:
        lines.append("Gaps of two years or more with nothing recorded:")
        for start, end in data["gaps"]:
            lines.append(f"  {start}-{end}: nothing. If work happened here, it is already being forgotten.")
        lines.append("")
    if data["undated"]:
        lines.append(f"Undated atoms ({len(data['undated'])}): {', '.join(data['undated'])}")
        lines.append("  These cannot be placed in time, so recency and gap detection skip them.\n")
    if data["inferred"]:
        lines.append(f"Atoms dated only by employment window ({len(data['inferred'])}):")
        lines.append("  Narrow these while the detail is still recallable; a nine-year span is barely a date.\n")
    if data["stale_skills"]:
        lines.append(f"Skills not seen in {this_year() - 5} or later:")
        for skill, year in data["stale_skills"][:12]:
            lines.append(f"  {skill} (last {year})")
        lines.append("")
    lines.append(f"{data['recent_atoms']} of {data['total']} atoms are from the last five years.")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
