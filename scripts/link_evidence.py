#!/usr/bin/env python3
"""Propose, confirm and reject the links between requirements and evidence.

role_fit.py scores whatever a role profile's evidenced_by lists name, and those
lists were edited by hand by whoever wanted the score. The fix is provenance:
a link is proposed by this script (deterministically, from word and skill
overlap) or by a model, and it earns nothing until the subject confirms it, one
link at a time, with "no, that does not evidence it" as a real answer. Rejected
links are remembered so they are never proposed again.

    scripts/link_evidence.py --status                       # confirmed and proposed, per role
    scripts/link_evidence.py --propose [--role R] [--apply] # candidates; --apply writes them as proposed
    scripts/link_evidence.py --confirm R "<requirement text prefix>" E_X [--note "..."]
    scripts/link_evidence.py --reject  R "<requirement text prefix>" E_X --why "..."
    scripts/link_evidence.py --migrate                      # bare ids -> proposed links, once
"""
import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from current_pack import resolve, ROOT  # noqa: E402
from select_evidence import links, canonical, atom_prose  # noqa: E402
from dedupe import tokens  # noqa: E402

ROLES = ROOT / "data" / "roles"


def profiles(role_id=None):
    paths = sorted(ROLES.glob("*.json")) if ROLES.is_dir() else []
    if role_id:
        paths = [p for p in paths if p.stem == role_id]
        if not paths:
            raise SystemExit(f"no role profile {role_id!r} in {ROLES.relative_to(ROOT)}")
    return [(p, json.loads(p.read_text())) for p in paths]


def save(path, profile):
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w") as handle:
        handle.write(json.dumps(profile, indent=2, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def find_requirement(profile, prefix):
    hits = [r for r in profile["requirements"] if r["text"].lower().startswith(prefix.lower())]
    if len(hits) != 1:
        raise SystemExit(f"{len(hits)} requirements start with {prefix!r}; be more specific")
    return hits[0]


def candidates(req, profile, atoms, canon):
    """Deterministic proposals: word overlap between the requirement and the
    atom's prose, plus skill overlap with the role's keywords. Crude and
    explainable, like dedupe.py: a prompt to decide, not a decision."""
    want = tokens(req["text"])
    keywords = {canon.get(k.lower(), k.lower()) for k in profile.get("ats_keywords", [])}
    already = {l["id"] for l in links(req)} | {r["id"] for r in req.get("rejected_links") or []}
    rows = []
    for atom in atoms.values():
        if atom["id"] in already or atom.get("evidence_status") == "declined":
            continue
        have = tokens(atom_prose(atom))
        overlap = want & have
        skills = {canon.get(s.lower(), s.lower()) for s in atom.get("skills", [])} & keywords
        score = len(overlap) * 1.0 + len(skills) * 0.5
        if score >= 2:
            rows.append({"id": atom["id"], "title": atom["title"], "score": round(score, 1),
                         "because": sorted(overlap)[:5] + [f"skill:{s}" for s in sorted(skills)][:3]})
    rows.sort(key=lambda r: -r["score"])
    return rows[:5]


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--propose", action="store_true")
    parser.add_argument("--apply", action="store_true", help="with --propose: write candidates as proposed links")
    parser.add_argument("--confirm", nargs=3, metavar=("ROLE", "REQUIREMENT", "ATOM"))
    parser.add_argument("--reject", nargs=3, metavar=("ROLE", "REQUIREMENT", "ATOM"))
    parser.add_argument("--why", help="with --reject: the subject's reason, in their words")
    parser.add_argument("--note", help="with --confirm: why it evidences the requirement, in the subject's words")
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--role")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv[1:])
    today = date.today().isoformat()

    pack_path = resolve()
    atoms = {a["id"]: a for a in json.loads(pack_path.read_text())["evidence_atoms"]} if pack_path else {}

    if args.confirm or args.reject:
        role_id, prefix, aid = args.confirm or args.reject
        if aid not in atoms:
            raise SystemExit(f"{aid} is not in the current pack")
        (path, profile), = profiles(role_id)
        req = find_requirement(profile, prefix)
        existing = [l for l in req.get("evidenced_by") or []]
        existing = [l for l in existing if (l if isinstance(l, str) else l.get("id")) != aid]
        if args.confirm:
            link = {"id": aid, "linked_by": "subject", "on": today}
            if args.note:
                link["note"] = args.note
            existing.append(link)
            req["evidenced_by"] = existing
            print(f"confirmed {aid} -> {profile['role_id']} / {req['text'][:50]!r}")
        else:
            req["evidenced_by"] = existing
            req.setdefault("rejected_links", []).append({"id": aid, "on": today, "why": args.why})
            print(f"rejected {aid} for {profile['role_id']} / {req['text'][:50]!r}; it will not be proposed again")
        save(path, profile)
        return 0

    if args.migrate:
        changed = 0
        for path, profile in profiles(args.role):
            for req in profile["requirements"]:
                new = []
                for item in req.get("evidenced_by") or []:
                    if isinstance(item, str):
                        new.append({"id": item, "linked_by": "proposed", "on": today,
                                    "note": "migrated from a bare id; provenance unknown, so unconfirmed"})
                        changed += 1
                    else:
                        new.append(item)
                req["evidenced_by"] = new
            save(path, profile)
        print(f"migrated {changed} bare id(s) to proposed links; confirm each with --confirm")
        return 0

    if args.propose:
        canon = canonical(json.loads(pack_path.read_text())) if pack_path else {}
        report = []
        for path, profile in profiles(args.role):
            for req in profile["requirements"]:
                rows = candidates(req, profile, atoms, canon)
                report.append({"role_id": profile["role_id"], "requirement": req["text"],
                               "weight": req["weight"], "candidates": rows})
                if args.apply:
                    req.setdefault("evidenced_by", [])
                    for row in rows:
                        req["evidenced_by"].append({"id": row["id"], "linked_by": "proposed", "on": today,
                                                    "note": "proposed by link_evidence.py: " + ", ".join(row["because"])})
            if args.apply:
                save(path, profile)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            for block in report:
                print(f"{block['role_id']} / {block['weight']}: {block['requirement'][:70]}")
                for row in block["candidates"] or [{"id": "(no candidate)", "title": "", "score": 0, "because": []}]:
                    print(f"    {row['score']:>4}  {row['id']}  {row['title'][:50]}  {' '.join(row['because'])}")
            if args.apply:
                print("\nwritten as proposed links; they earn nothing until confirmed")
        return 0

    # --status, the default
    for path, profile in profiles(args.role):
        confirmed = proposed = 0
        for req in profile["requirements"]:
            for link in links(req):
                if link["linked_by"] == "subject":
                    confirmed += 1
                else:
                    proposed += 1
        print(f"{profile['role_id']}: {confirmed} confirmed, {proposed} proposed"
              + (" (nothing counts towards the verdict yet)" if confirmed == 0 and proposed else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
