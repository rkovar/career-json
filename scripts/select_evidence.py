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
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from current_pack import resolve, sha256, this_year, metric_text, metric_basis, ROOT  # noqa: E402

from evidence_rules import links, linked_ids, eligible, canonical, contains_term, atom_prose

ROLES = ROOT / "data" / "roles"

# Outcome type and corroboration describe evidence; neither is a universal ranking.


def role_score(atom, profile, canon):
    """How much this atom answers this role. Explainable on purpose: a curation
    the user cannot understand is one they will not trust."""
    reasons = []
    score = 0.0

    for req in profile.get("requirements", []):
        # Selection is curation, not a verdict, so a proposed link still ranks.
        if atom["id"] in linked_ids(req):
            weight = {"essential": 5.0, "important": 2.5, "nice_to_have": 1.0}[req["weight"]]
            score += weight
            status = "confirmed link" if atom["id"] in linked_ids(req, confirmed_only=True) else "proposed link; inspect support"
            reasons.append(f"candidate for {req['weight']} {req.get('kind', 'other')} requirement ({status}): {req['text']}")

    have = {canon.get(s.lower(), s.lower()) for s in atom.get("skills", [])}
    wanted = {canon.get(k.lower(), k.lower()) for k in profile.get("ats_keywords", [])}
    overlap = {w for w in wanted for h in have if w == h or contains_term(h, w) or contains_term(w, h)}
    if overlap:
        score += min(len(overlap), 3) * 0.75
        reasons.append("matches role keywords: " + ", ".join(sorted(overlap)[:3]))

    hits = [k for k in profile.get("ats_keywords", []) if contains_term(atom_prose(atom), k)]
    if hits and not overlap:
        score += min(len(hits), 3) * 0.4
        reasons.append("mentions " + ", ".join(hits[:3]))

    # Date and outcome category remain visible context, without a blanket bonus
    # that can displace older technical work or work with no financial measure.
    if atom.get("occurred"):
        reasons.append("timeframe: " + str(atom["occurred"].get("end") or atom["occurred"].get("start") or "unknown"))
    reasons.append("outcome category: " + str(atom.get("outcome_type") or "unspecified") + "; assess value for this role")

    if atom.get("role_fit_notes"):
        # Whether a note counts against THIS role is judgement, so it is carried
        # rather than scored. A blanket penalty demoted "strong for a head-of
        # role" on head-of roles.
        reasons.append("carries role_fit_notes; read them before citing")

    return round(score, 2), reasons


def load_role(role_id):
    path = ROLES / f"{role_id}.json"
    if not path.exists():
        available = sorted(p.stem for p in ROLES.glob("*.json"))
        raise SystemExit(f"no role profile {role_id!r}. Available: {', '.join(available) or 'none'}")
    return json.loads(path.read_text())


def recency(atom):
    """Sort key for how current an atom is.

    Two subtleties, both found by a pack that finally had a precise recent date
    alongside ongoing work. `end` falls back to `start`, because a point-in-time
    atom (a course release, an award) has a start and no end and is not undated.
    And ongoing sorts above any dated month in the same year: work still running is
    more current than something finished mid-year, and returning the bare year put
    it below a YYYY-MM value from that same year on a string compare.
    """
    occurred = atom.get("occurred") or {}
    end = occurred.get("end") or occurred.get("start") or "0000"
    return f"{this_year()}-99" if end == "ongoing" else end


DIMENSIONS = {"build": "technical delivery", "lead": "leadership and influence",
              "domain": "domain expertise", "communicate": "communication and knowledge sharing",
              "govern": "governance and risk", "other": "role-specific contribution"}


def contributions(atom, profile):
    return [{"requirement": req["text"], "dimension": DIMENSIONS.get(req.get("kind"), DIMENSIONS["other"]),
             "link_status": "confirmed" if atom["id"] in linked_ids(req, True) else "proposed"}
            for req in (profile or {}).get("requirements", []) if atom["id"] in linked_ids(req)]


def complementary_shortlist(atoms, profile, limit):
    """Preserve essential coverage; then prefer complementary requirement links.

    Proposed links support retrieval, not a qualification verdict. Essential
    coverage may exceed a requested shortlist size, as in the previous selector.
    """
    if limit < 1:
        raise ValueError("shortlist limit must be positive")
    requirements = (profile or {}).get("requirements", [])
    kept, covered = [], set()
    def coverage(atom):
        return {i for i, req in enumerate(requirements) if atom["id"] in linked_ids(req)}
    for index, req in enumerate(requirements):
        if req.get("weight") == "essential" and index not in covered:
            best = next((a for a in atoms if index in coverage(a)), None)
            if best:
                kept.append(best); covered.update(coverage(best))
    while len(kept) < limit:
        remaining = [a for a in atoms if a not in kept]
        if not remaining: break
        def gain(atom):
            return sum({"essential": 5, "important": 2.5, "nice_to_have": 1}[requirements[i]["weight"]]
                       for i in coverage(atom) - covered)
        best = max(remaining, key=gain)  # stable tie: existing role ranking
        kept.append(best); covered.update(coverage(best))
    return kept


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
            "metrics": [metric_text(m) for m in atom.get("metrics", [])],
            # Carried so a bullet can be written against a figure whose basis is
            # known, and so an unmeasured one is visible before it reaches a page.
            "metric_basis": {metric_text(m): metric_basis(m)
                             for m in atom.get("metrics", []) if metric_basis(m)},
            "unmeasured_metrics": [metric_text(m) for m in atom.get("metrics", [])
                                   if isinstance(m, dict) and m.get("measured") is False],
            "skills": atom.get("skills", []),
            "evidence_status": atom["evidence_status"],
            "occurred": atom.get("occurred"),
            "tags": atom.get("tags", []),
            "outcome_type": atom.get("outcome_type"),
            "role_fit_notes": atom.get("role_fit_notes"),
            # An identifier, not private. Without it overlapping roles and undated
            # work had to be attributed to an employer by guesswork.
            "employment_id": atom.get("employment_id"),
            # Reviewed handling constraints the bullet must respect. Operator
            # `notes` stay out of the view on purpose: that is where internal
            # names live.
            "constraints": atom.get("constraints", []),
            "has_corroborator": bool(atom.get("corroborators")),
        })
    # Stable recency order is a browsing default, never a career-value score.
    atoms.sort(key=recency, reverse=True)

    dropped, coverage = [], []
    if profile:
        # Rank against the role before generation sees anything. Sending the whole
        # pack and asking a model to curate does not survive a pack of 500 atoms.
        canon = canonical(pack)
        scored = []
        for atom in atoms:
            score, reasons = role_score(atom, profile, canon)
            atom["role_score"] = score
            atom["why_selected"] = reasons
            atom["role_contributions"] = contributions(atom, profile)
            scored.append(atom)
        scored.sort(key=lambda a: -a["role_score"])
        cap = limit or 30
        keep = complementary_shortlist(scored, profile, cap)
        keep.sort(key=lambda a: -a["role_score"])
        dropped = [{"id": a["id"], "title": a["title"], "role_score": a["role_score"]}
                   for a in scored if a not in keep]
        atoms = keep
        # Per requirement: covered by the shortlist, omitted by the limit, withheld
        # from every artefact, or missing from the pack. A single percentage could
        # not tell the last two apart.
        kept_ids = {a["id"] for a in keep}
        eligible_ids = {a["id"] for a in scored}
        all_ids = {a["id"] for a in pack.get("evidence_atoms", [])}
        for req in profile.get("requirements", []):
            linked = linked_ids(req)
            if any(i in kept_ids for i in linked):
                status = "covered"
            elif any(i in eligible_ids for i in linked):
                status = "omitted"
            elif any(i in all_ids for i in linked):
                status = "withheld"
            else:
                status = "missing"
            coverage.append({"text": req["text"], "weight": req["weight"], "status": status})

    # Named `contact`, not `profile`: this function already takes a role profile,
    # and the collision silently overwrote it.
    profile_fields = pack.get("private_profile") or {}
    contact_fields = ('name', 'location', 'linkedin')
    if audience == 'named_recipient':
        contact_fields += ('email', 'phone', 'personal_website')
    # Profile extensions are private unless deliberately added to this allowlist.
    contact = {key: profile_fields[key] for key in contact_fields if key in profile_fields}
    contact.setdefault('name', pack.get('name'))

    # Projected through an allowlist. The whole record used to pass through,
    # carrying employer_of_record and operator notes that data-model.md says
    # never appear in an artefact.
    employment = [{k: r.get(k) for k in ("employment_id", "employer", "title", "start",
                                         "end", "location", "parent_employment_id", "scope")}
                  for r in pack.get("employment", [])
                  if r.get("external_safe") and r.get("evidence_status") not in ("unresolved", "declined")]
    employment.sort(key=lambda r: r["start"], reverse=True)
    years = [int(r["start"][:4]) for r in employment]
    ends = [this_year() if r.get("end") == "present" else int((r.get("end") or r["start"])[:4]) for r in employment]

    # Same eligibility rule as employment: withheld or unresolved never reaches
    # generation.
    education = [{k: r.get(k) for k in ("education_id", "institution", "qualification",
                                        "field", "start", "end", "grade", "location")}
                 for r in pack.get("education", [])
                 if r.get("external_safe") and r.get("evidence_status") not in ("unresolved", "declined")]
    education.sort(key=lambda r: r.get("end") or r.get("start") or "", reverse=True)

    return {
        "audience": audience,
        "role": profile["role_id"] if profile else None,
        "central_requirement": profile.get("central_requirement") if profile else None,
        # The subject's own level story, or null. Generation may open with it and
        # must not invent one when it is null.
        "positioning": (profile.get("positioning") if profile else None),
        "not_shortlisted": dropped,
        "requirement_coverage": coverage,
        "contact": contact,
        "employment": employment,
        "education": education,
        "career_span_years": (max(ends) - min(years)) if employment else None,
        "atoms": atoms,
        "summary": {
            "employment_records": len(employment),
            "education_records": len(education),
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
    parser.add_argument("--selection", help="durable selection record; applies its brief, audience and decisions")
    parser.add_argument("--limit", type=int, default=30, help="shortlist size when --role is given")
    parser.add_argument("--excluded", action="store_true",
                        help="list what was withheld and why, instead of the view")
    args = parser.parse_args(argv[1:])

    if args.selection:
        if args.role or args.excluded or '--audience' in argv or '--limit' in argv:
            parser.error('--selection determines role, audience and candidates; do not combine these options')
        from editorial import generation_view
        try:
            print(json.dumps(generation_view(args.selection), indent=2))
            return 0
        except (ValueError, KeyError, OSError) as exc:
            print(f'error: {exc}', file=sys.stderr)
            return 1

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
