#!/usr/bin/env python3
"""Score the pack against every role profile, so targeting is evidence-led.

The workflow makes you name a role, generate, and then discover at the screen that
the evidence never supported it. This asks the question in the other order: given
what is actually in the pack, which of these roles can it carry?

Scoring is transparent on purpose. Essential requirements dominate and an
unevidenced essential is close to fatal. Coverage drives the verdict: self-asserted
evidence is the normal resting state of a career record and earns full credit, and
how much of the coverage is corroborated is reported beside the score rather than
gating it. A declined atom is a decision and earns nothing. An unresolved atom is
an open question: it earns reduced credit on an important or nice-to-have
requirement and can never by itself clear an essential one, because "we do not
know" must not become "supported" on the thing the role hires for.

    python3 scripts/role_fit.py                 # all profiles, ranked
    python3 scripts/role_fit.py --markdown
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from current_pack import resolve, ROOT  # noqa: E402
from select_evidence import eligible  # noqa: E402

ROLES = ROOT / "data" / "roles"
WEIGHT = {"essential": 3.0, "important": 1.5, "nice_to_have": 0.5}
OUTCOME_CREDIT = {"business_outcome": 1.0, "output": 0.8, "activity": 0.6, None: 0.5}
# An open question earns half credit where it is allowed to earn any.
UNRESOLVED_CREDIT = 0.5
CORROBORATED = ("corroborated", "externally_verified")


def usable(atom, deliverable):
    """Whether an atom may count at all. Declined never does: it is a recorded
    decision, not evidence. In deliverable mode only what an artefact may cite
    counts, which also excludes unresolved and withheld atoms."""
    if atom.get("evidence_status") == "declined":
        return False
    if deliverable and not eligible(atom)[0]:
        return False
    return True


def score(profile, atoms, deliverable=False):
    """Fit against the pack. deliverable=True counts only evidence an artefact may
    cite, which is not the same question.

    Without the distinction this scored ineligible evidence as if a resume could
    show it, so a role could read "supported" on material no document may carry.
    Left unlinked in the profile instead, the same atom made the role read "not
    supported" when the capability exists. Neither number was the truth, and the
    gap between the two is what a publication constraint costs.
    """
    total = earned = 0.0
    gaps, thin, unresolved_essentials, unresolved_credited = [], [], [], []
    evidenced = corroborated = 0
    for req in profile["requirements"]:
        weight = WEIGHT[req["weight"]]
        total += weight
        linked = [atoms[i] for i in req.get("evidenced_by", []) if i in atoms]
        linked = [a for a in linked if usable(a, deliverable)]
        firm = [a for a in linked if a.get("evidence_status") != "unresolved"]
        open_ = [a for a in linked if a.get("evidence_status") == "unresolved"]
        if firm:
            best = max(OUTCOME_CREDIT.get(a.get("outcome_type")) for a in firm)
        elif open_ and req["weight"] != "essential":
            best = max(OUTCOME_CREDIT.get(a.get("outcome_type")) for a in open_) * UNRESOLVED_CREDIT
            unresolved_credited.append(req)
        else:
            gaps.append(req)
            if open_:
                unresolved_essentials.append(req)
            continue
        earned += weight * best
        evidenced += 1
        if any(a.get("evidence_status") in CORROBORATED for a in firm):
            corroborated += 1
        if best < 0.55:
            thin.append(req)
    pct = round(100 * earned / total) if total else 0

    essential_gaps = [g for g in gaps if g["weight"] == "essential"]
    if essential_gaps:
        verdict = "not supported"
    elif pct >= 70:
        verdict = "well supported"
    elif pct >= 50:
        verdict = "partly supported"
    else:
        verdict = "thin"
    return {
        "role_id": profile["role_id"],
        "title": profile["title"],
        "score": pct,
        "verdict": verdict,
        "central_requirement": profile["central_requirement"],
        "essential_gaps": [g["text"] for g in essential_gaps],
        "other_gaps": [g["text"] for g in gaps if g["weight"] != "essential"],
        "thin_evidence": [t["text"] for t in thin],
        # Reported beside the score, never gating it: corroboration is optional.
        "corroborated_share": round(100 * corroborated / evidenced) if evidenced else 0,
        # Open questions that touched the score, and the essentials they could not clear.
        "unresolved_credited": [r["text"] for r in unresolved_credited],
        "unresolved_essentials": [r["text"] for r in unresolved_essentials],
    }


def unresolved_linked(profiles, atoms):
    """Unresolved atoms linked to any requirement. Listed beside the verdict for
    the same reason withheld atoms are: in the score they look like weak evidence
    or a gap, and they are neither. They are questions."""
    rows = []
    for profile in profiles:
        for req in profile.get("requirements", []):
            for i in req.get("evidenced_by", []):
                atom = atoms.get(i)
                if atom and atom.get("evidence_status") == "unresolved":
                    rows.append({"id": i, "title": atom["title"], "role_id": profile["role_id"],
                                 "requirement": req["text"], "weight": req["weight"]})
    return rows


def withheld(atoms):
    """Atoms no artefact may ever cite. Reported next to the verdict because an
    unevidenced essential requirement and a withheld one look identical in the
    score and are completely different problems. Finding this took reading a
    whole pack by hand; it is decidable, so it belongs here."""
    rows = []
    for atom in atoms.values():
        ok, why = eligible(atom)
        if not ok:
            rows.append({"id": atom["id"], "title": atom["title"], "withheld_because": why})
    return rows


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--markdown", action="store_true")
    args = parser.parse_args(argv[1:])

    pack_path = resolve()
    if pack_path is None:
        print("no pack found", file=sys.stderr)
        return 1
    atoms = {a["id"]: a for a in json.loads(pack_path.read_text())["evidence_atoms"]}

    profiles = []
    for path in sorted(ROLES.glob("*.json")):
        profiles.append(json.loads(path.read_text()))
    if not profiles:
        print(f"no role profiles in {ROLES.relative_to(ROOT)}; write one before scoring fit",
              file=sys.stderr)
        return 1

    results = []
    for profile in profiles:
        row = score(profile, atoms)
        shown = score(profile, atoms, deliverable=True)
        row["deliverable_score"] = shown["score"]
        row["deliverable_verdict"] = shown["verdict"]
        row["withheld_essentials"] = [g for g in shown["essential_gaps"]
                                      if g not in row["essential_gaps"]]
        results.append(row)
    results.sort(key=lambda r: -r["score"])
    unpublishable = withheld(atoms)
    open_questions = unresolved_linked(profiles, atoms)
    if not args.markdown:
        print(json.dumps({"pack": str(pack_path.relative_to(ROOT)),
                          "withheld_from_every_artefact": unpublishable,
                          "unresolved_linked_to_requirements": open_questions,
                          "roles": results}, indent=2))
        return 0

    out = ["# Role Fit", "", f"Pack: `{pack_path.relative_to(ROOT)}`", "",
           "An unevidenced essential requirement makes a role unsupported however high",
           "the rest scores. That is the honest reading: it is the thing they are hiring for.", "",
           "Coverage drives the verdict; corroboration is reported beside it and gates nothing.", "",
           "| Role | Coverage | Verdict | Corroborated | Unevidenced essentials |",
           "| --- | --- | --- | --- | --- |"]
    for r in results:
        gaps = "; ".join(r["essential_gaps"]) or "none"
        shown = ("" if r["deliverable_score"] == r["score"]
                 else f" (deliverable {r['deliverable_score']}%)")
        out.append(f"| {r['title']} | {r['score']}%{shown} | {r['verdict']} | "
                   f"{r['corroborated_share']}% | {gaps} |")
    if open_questions:
        out += ["", "## Unresolved evidence linked to requirements", "",
                "An open question, not weak evidence. It earns half credit on an important or",
                "nice-to-have requirement and can never clear an essential one on its own.", ""]
        for row in open_questions:
            out.append(f"- `{row['id']}` {row['title']} — {row['weight']} requirement "
                       f"\"{row['requirement']}\" ({row['role_id']})")
    if unpublishable:
        out += ["", "## Withheld from every artefact", "",
                "These cannot appear in any document. Check whether any of them answers",
                "a requirement listed above as a gap: the score cannot tell the two apart.",
                ""]
        for row in unpublishable:
            out.append(f"- `{row['id']}` {row['title']} — {row['withheld_because']}")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
