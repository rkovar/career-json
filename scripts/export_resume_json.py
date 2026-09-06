#!/usr/bin/env python3
"""Project career.json down into a JSON Resume (resume.json) document.

The two formats are not competitors, they are layers. career.json is the private
superset: evidence with STAR fields, provenance, confidence, unresolved claims,
and material marked never-publish. JSON Resume is a presentation format with no
notion of evidence, provenance, or confidence at all.

So this is a deliberately lossy projection: everything that cannot be published
is dropped, and what survives is the external-safe view. In exchange you get the
whole JSON Resume theme and renderer ecosystem for free.

    scripts/export_resume_json.py                          # to stdout
    scripts/export_resume_json.py --role head-of-ai-security -o outputs/resume.json
    scripts/export_resume_json.py --audience public
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from current_pack import resolve, this_year, ROOT  # noqa: E402
from select_evidence import eligible, load_role, role_score, canonical  # noqa: E402


def iso(value, end=False):
    """JSON Resume wants ISO 8601. Our dates are YYYY or YYYY-MM."""
    if not value or value in ("present", "ongoing"):
        return None
    parts = value.split("-")
    if len(parts) == 1:
        return f"{parts[0]}-12-31" if end else f"{parts[0]}-01-01"
    return f"{parts[0]}-{parts[1]}-01"


def export(pack, audience="named_recipient", profile=None, limit=None):
    contact = pack.get("private_profile") or {}
    basics = {"name": contact.get("name"), "label": profile["title"] if profile else None,
              "summary": None, "location": {}, "profiles": []}
    if contact.get("location"):
        basics["location"] = {"city": contact["location"]}
    if audience != "public":
        basics["email"] = contact.get("email")
        basics["phone"] = contact.get("phone")
    if contact.get("personal_website") and audience != "public":
        basics["url"] = contact["personal_website"]
    if contact.get("linkedin"):
        basics["profiles"].append({"network": "LinkedIn", "url": contact["linkedin"],
                                   "username": contact["linkedin"].rstrip("/").split("/")[-1]})
    basics = {k: v for k, v in basics.items() if v not in (None, {}, [])}

    atoms = [a for a in pack["evidence_atoms"] if eligible(a)[0]]
    if profile:
        canon = canonical(pack)
        for atom in atoms:
            atom["_score"] = role_score(atom, profile, canon)[0]
        atoms.sort(key=lambda a: -a["_score"])
        atoms = atoms[: (limit or 30)]
    kept = {a["id"] for a in atoms}

    work = []
    for rec in sorted((r for r in pack.get("employment", [])
                       if r.get("external_safe") and r.get("evidence_status") not in ("unresolved", "declined")),
                      key=lambda r: r["start"], reverse=True):
        if rec.get("parent_employment_id"):
            continue  # promotions collapse into the role they grew from
        highlights = []
        for atom in pack["evidence_atoms"]:
            if atom["id"] not in kept:
                continue
            if atom.get("employment_id") == rec["employment_id"] or \
               any(e.get("parent_employment_id") == rec["employment_id"] and
                   e["employment_id"] == atom.get("employment_id")
                   for e in pack.get("employment", [])):
                result = (atom.get("star") or {}).get("result")
                highlights.append(result or atom["title"])
        entry = {"name": rec["employer"], "position": rec["title"],
                 "startDate": iso(rec["start"]),
                 "endDate": iso(rec.get("end"), end=True),
                 "highlights": highlights}
        if rec.get("location"):
            entry["location"] = rec["location"]
        work.append({k: v for k, v in entry.items() if v not in (None, [], "")})

    # JSON Resume has carried an education section since v1; this pack could not
    # fill it until education records existed.
    education = []
    for rec in sorted((r for r in pack.get("education", [])
                       if r.get("external_safe") and r.get("evidence_status") not in ("unresolved", "declined")),
                      key=lambda r: r.get("end") or r.get("start") or "", reverse=True):
        entry = {"institution": rec["institution"], "studyType": rec["qualification"],
                 "area": rec.get("field"), "score": rec.get("grade"),
                 "startDate": iso(rec.get("start")), "endDate": iso(rec.get("end"), end=True)}
        education.append({k: v for k, v in entry.items() if v not in (None, [], "")})

    vocab = pack.get("skill_vocabulary") or {}
    canon_names = list(vocab) or sorted({s for a in atoms for s in a.get("skills", [])})
    skills = []
    for name in canon_names:
        keywords = sorted({s for a in atoms for s in a.get("skills", [])
                           if s.lower() == name.lower()
                           or s.lower() in [x.lower() for x in vocab.get(name, [])]
                           or name.lower() in s.lower()})
        if keywords:
            skills.append({"name": name, "keywords": keywords})

    resume = {"$schema": "https://raw.githubusercontent.com/jsonresume/resume-schema/v1.0.0/schema.json",
              "basics": basics, "work": work, "education": education, "skills": skills,
              "meta": {"canonical": "career.json",
                       "generated_from": {"pack": "career.json",
                                          "note": "Lossy projection. Evidence, provenance, confidence, "
                                                  "and non-publishable material are not representable in "
                                                  "JSON Resume and were dropped."},
                       "role": profile["role_id"] if profile else None,
                       "audience": audience,
                       "version": "v1.0.0"}}
    return resume


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--role", help="role_id from data/roles/, to shortlist highlights")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--audience", choices=("named_recipient", "public"), default="named_recipient")
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv[1:])

    path = resolve()
    if path is None:
        print("no pack found", file=sys.stderr)
        return 1
    pack = json.loads(path.read_text())
    profile = load_role(args.role) if args.role else None
    resume = export(pack, args.audience, profile, args.limit)
    text = json.dumps(resume, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(text)
        print(args.output)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
