#!/usr/bin/env python3
"""Score the pack against every role profile, so targeting is evidence-led.

The workflow makes you name a role, generate, and then discover at the screen that
the evidence never supported it. This asks the question in the other order: given
what is actually in the pack, which of these roles can it carry?

Scoring is transparent on purpose. Essential requirements dominate, an unevidenced
essential is close to fatal, and corroborated evidence counts for more than the
subject's own word.

    python3 scripts/role_fit.py                 # all profiles, ranked
    python3 scripts/role_fit.py --markdown
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from current_pack import resolve, ROOT  # noqa: E402

ROLES = ROOT / "data" / "roles"
WEIGHT = {"essential": 3.0, "important": 1.5, "nice_to_have": 0.5}
STATUS_CREDIT = {"externally_verified": 1.0, "corroborated": 0.85, "self_asserted": 0.6}
OUTCOME_CREDIT = {"business_outcome": 1.0, "output": 0.8, "activity": 0.6, None: 0.5}


def score(profile, atoms):
    total = earned = 0.0
    gaps, thin = [], []
    for req in profile["requirements"]:
        weight = WEIGHT[req["weight"]]
        total += weight
        ids = [i for i in req.get("evidenced_by", []) if i in atoms]
        if not ids:
            gaps.append(req)
            continue
        best = max(STATUS_CREDIT.get(atoms[i]["evidence_status"], 0.5)
                   * OUTCOME_CREDIT.get(atoms[i].get("outcome_type"))
                   for i in ids)
        earned += weight * best
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
    }


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

    results = sorted((score(p, atoms) for p in profiles), key=lambda r: -r["score"])
    if not args.markdown:
        print(json.dumps({"pack": str(pack_path.relative_to(ROOT)), "roles": results}, indent=2))
        return 0

    out = ["# Role Fit", "", f"Pack: `{pack_path.relative_to(ROOT)}`", "",
           "An unevidenced essential requirement makes a role unsupported however high",
           "the rest scores. That is the honest reading: it is the thing they are hiring for.", "",
           "| Role | Score | Verdict | Unevidenced essentials |", "| --- | --- | --- | --- |"]
    for r in results:
        gaps = "; ".join(r["essential_gaps"]) or "none"
        out.append(f"| {r['title']} | {r['score']}% | {r['verdict']} | {gaps} |")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
