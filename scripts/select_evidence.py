#!/usr/bin/env python3
"""Emit the evidence a generation run is allowed to use, and nothing else.

Generation previously read the whole pack and was instructed not to cite
ineligible atoms. This inverts that: ineligible atoms never enter context, so the
guarantee is structural rather than instructional. You cannot cite what you were
never shown.

Also drops fields generation has no use for, which matters once a pack holds a
hundred atoms rather than twenty.

    python3 scripts/select_evidence.py                    # eligible atoms, ranked
    python3 scripts/select_evidence.py --audience public  # contact block trimmed
    python3 scripts/select_evidence.py --excluded         # what was withheld, and why
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from current_pack import resolve, sha256, this_year, ROOT  # noqa: E402

ROLES = ROOT / "data" / "roles"

# Hiring managers discount workload metrics, so outcomes sort first.
OUTCOME_RANK = {"business_outcome": 0, "output": 1, "activity": 2, None: 3}
STATUS_RANK = {"externally_verified": 0, "corroborated": 1, "self_asserted": 2}


def eligible(atom):
    if not atom.get("external_safe"):
        return False, "external_safe is false"
    if atom.get("evidence_status") in ("unresolved", "declined"):
        return False, f"evidence_status is {atom['evidence_status']}"
    return True, None


def canonical(pack):
    out = {}
    for canon, aliases in (pack.get("skill_vocabulary") or {}).items():
        out[canon.lower()] = canon
        for alias in aliases:
            out[alias.lower()] = canon
    return out


def role_score(atom, profile, canon):
    """How much this atom answers this role. Explainable on purpose: a curation
    the user cannot understand is one they will not trust."""
    reasons = []
    score = 0.0

    for req in profile.get("requirements", []):
        if atom["id"] in req.get("evidenced_by", []):
            weight = {"essential": 5.0, "important": 2.5, "nice_to_have": 1.0}[req["weight"]]
            score += weight
            reasons.append(f"answers {req['weight']} requirement: {req['text'][:60]}")

    have = {canon.get(s.lower(), s.lower()) for s in atom.get("skills", [])}
    wanted = {canon.get(k.lower(), k.lower()) for k in profile.get("ats_keywords", [])}
    overlap = {w for w in wanted for h in have if w == h or w in h or h in w}
    if overlap:
        score += min(len(overlap), 3) * 0.75
        reasons.append("matches role keywords: " + ", ".join(sorted(overlap)[:3]))

    blob = json.dumps(atom).lower()
    hits = [k for k in profile.get("ats_keywords", []) if k.lower() in blob]
    if hits and not overlap:
        score += min(len(hits), 3) * 0.4
        reasons.append("mentions " + ", ".join(hits[:3]))

    score += {"business_outcome": 2.0, "output": 1.0, "activity": 0.25, None: 0}[atom.get("outcome_type")]

    occurred = atom.get("occurred") or {}
    end = occurred.get("end") or occurred.get("start")
    if end:
        year = this_year() if end == "ongoing" else int(end[:4])
        age = this_year() - year
        if age <= 3:
            score += 1.5
            reasons.append("recent")
        elif age <= 8:
            score += 0.5
        elif age > 15:
            score -= 0.75
            reasons.append(f"{age} years old")

    if atom.get("role_fit_notes"):
        score -= 1.5
        reasons.append("flagged as a negative signal for some roles")

    return round(score, 2), reasons


def load_role(role_id):
    path = ROLES / f"{role_id}.json"
    if not path.exists():
        available = sorted(p.stem for p in ROLES.glob("*.json"))
        raise SystemExit(f"no role profile {role_id!r}. Available: {', '.join(available) or 'none'}")
    return json.loads(path.read_text())


def view(pack, audience="named_recipient", profile=None, limit=None):
    atoms = []
    for atom in pack.get("evidence_atoms", []):
        ok, _ = eligible(atom)
        if not ok:
            continue
        atoms.append({
            "id": atom["id"],
            "title": atom["title"],
            "star": atom.get("star", {}),
            "metrics": atom.get("metrics", []),
            "skills": atom.get("skills", []),
            "evidence_status": atom["evidence_status"],
            "occurred": atom.get("occurred"),
            "tags": atom.get("tags", []),
            "outcome_type": atom.get("outcome_type"),
            "role_fit_notes": atom.get("role_fit_notes"),
            "has_corroborator": bool(atom.get("corroborators")),
        })
    def recency(atom):
        occurred = atom.get("occurred") or {}
        end = occurred.get("end") or occurred.get("start") or "0000"
        return str(this_year()) if end == "ongoing" else end

    # Outcomes first, then recent work: a hiring manager discounts both workload
    # metrics and things you did twelve years ago.
    atoms.sort(key=lambda a: (OUTCOME_RANK[a["outcome_type"]],
                              STATUS_RANK.get(a["evidence_status"], 9)))
    atoms.sort(key=recency, reverse=True)
    atoms.sort(key=lambda a: OUTCOME_RANK[a["outcome_type"]])

    dropped = []
    if profile:
        # Rank against the role before generation sees anything. Sending the whole
        # pack and asking a model to curate does not survive a pack of 500 atoms.
        canon = canonical(pack)
        scored = []
        for atom in atoms:
            score, reasons = role_score(atom, profile, canon)
            atom["role_score"] = score
            atom["why_selected"] = reasons
            scored.append(atom)
        scored.sort(key=lambda a: -a["role_score"])
        keep = scored[: (limit or 30)]
        dropped = [{"id": a["id"], "title": a["title"], "role_score": a["role_score"]}
                   for a in scored[len(keep):]]
        atoms = keep

    # Named `contact`, not `profile`: this function already takes a role profile,
    # and the collision silently overwrote it.
    contact = dict(pack.get("private_profile") or {})
    contact.pop("source_refs", None)
    # Never in any artefact, so never in context either.
    contact.pop("address", None)
    contact.pop("photo_reference", None)
    if audience == "public":
        for field in ("email", "phone", "personal_website"):
            contact.pop(field, None)

    employment = [r for r in pack.get("employment", [])
                  if r.get("external_safe") and r.get("evidence_status") not in ("unresolved", "declined")]
    employment.sort(key=lambda r: r["start"], reverse=True)
    years = [int(r["start"][:4]) for r in employment]
    ends = [this_year() if r.get("end") == "present" else int((r.get("end") or r["start"])[:4]) for r in employment]

    return {
        "audience": audience,
        "role": profile["role_id"] if profile else None,
        "central_requirement": profile.get("central_requirement") if profile else None,
        "not_shortlisted": dropped,
        "contact": contact,
        "employment": employment,
        "career_span_years": (max(ends) - min(years)) if employment else None,
        "atoms": atoms,
        "summary": {
            "employment_records": len(employment),
            "eligible": len(atoms),
            "shortlisted_from": len(atoms) + len(dropped),
            "by_outcome": {k: sum(1 for a in atoms if a["outcome_type"] == k)
                           for k in ("business_outcome", "output", "activity")},
            "with_corroborator": sum(1 for a in atoms if a["has_corroborator"]),
        },
    }


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--audience", choices=("named_recipient", "public"),
                        default="named_recipient",
                        help="public trims the contact block to name and location")
    parser.add_argument("--role", help="role_id from data/roles/; ranks and shortlists for it")
    parser.add_argument("--limit", type=int, default=30, help="shortlist size when --role is given")
    parser.add_argument("--excluded", action="store_true",
                        help="list what was withheld and why, instead of the view")
    args = parser.parse_args(argv[1:])

    path = resolve()
    if path is None:
        print("no pack found", file=sys.stderr)
        return 1
    pack = json.loads(path.read_text())

    if args.excluded:
        rows = []
        for atom in pack.get("evidence_atoms", []):
            ok, why = eligible(atom)
            if not ok:
                rows.append({"id": atom["id"], "title": atom["title"], "withheld_because": why})
        print(json.dumps({"excluded": rows}, indent=2))
        return 0

    profile = load_role(args.role) if args.role else None
    out = view(pack, args.audience, profile=profile, limit=args.limit)
    out["source"] = {"pack": str(path.relative_to(ROOT)), "sha256": sha256(path)}
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
