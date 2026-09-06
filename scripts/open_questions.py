#!/usr/bin/env python3
"""Rank every outstanding question about the pack, and say what answering unlocks.

"What is still open?" used to be answered by reading the pack by hand: grepping
`open_questions`, scanning `known_conflicts`, eyeballing which metrics had no
basis. That is a pure function over the pack and the role profiles, so it belongs
here rather than in a conversation that has to be repeated every time.

The ordering is the point. A batch of twenty questions in pack order gets
abandoned at the fourth. The same twenty ordered by what each answer unlocks gets
answered, because the first few visibly move something. Ranking is value times
exposure, the same shape as corroboration_plan.py, and deliberately explainable:
an ordering nobody trusts is one nobody follows.

`review-evidence` consumes `--json` and asks these one at a time.

    python3 scripts/open_questions.py              # ranked queue
    python3 scripts/open_questions.py --markdown   # same, as a review record
    python3 scripts/open_questions.py --delta      # what the last pack version changed
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from current_pack import resolve, metric_basis, metric_text, ROOT  # noqa: E402
from select_evidence import eligible  # noqa: E402
from quantities import extract  # noqa: E402

ROLES = ROOT / "data" / "roles"

# What answering is worth. A question that changes a verdict outranks one that
# tidies a field, however tidy the field would be.
UNLOCK = {
    "role_verdict": 5.0,
    "publishability": 4.0,
    "provenance": 3.5,
    "background_check": 3.0,
    "metric_defensibility": 2.5,
    "status_promotion": 2.5,
    "recorded_conflict": 2.0,
    "classification": 2.0,
    "recency": 1.5,
    "recorded_question": 2.5,
}


def cited_ids():
    """A claim that reaches artefacts matters more than one that never does."""
    ids = set()
    for path in (ROOT / "outputs").glob("*-draft.md"):
        try:
            ids |= set(re.findall(r"E_[A-Z0-9_]+", path.read_text()))
        except OSError:
            continue
    return ids


def roles():
    out = []
    if ROLES.is_dir():
        for path in sorted(ROLES.glob("*.json")):
            try:
                out.append(json.loads(path.read_text()))
            except json.JSONDecodeError:
                continue
    return out


def collect(pack, profiles, cited):
    """Every open question the pack can derive about itself."""
    atoms = {a["id"]: a for a in pack.get("evidence_atoms", [])}
    found = []

    def add(kind, question, unlocks, subject=None, detail=None):
        score = UNLOCK[unlocks]
        if subject in cited:
            score *= 1.5
        found.append({"kind": kind, "question": question, "unlocks": unlocks,
                      "subject": subject, "detail": detail, "score": round(score, 2)})

    # A requirement nothing evidences is the thing a role hires for.
    for profile in profiles:
        for req in profile.get("requirements", []):
            live = [i for i in req.get("evidenced_by", []) if i in atoms]
            if live or req.get("weight") != "essential":
                continue
            add("role_gap",
                f"What evidences {profile['title']}'s essential requirement "
                f"\"{req['text']}\"? Nothing in the pack is linked to it.",
                "role_verdict", subject=profile["role_id"],
                detail="An unevidenced essential requirement makes the role unsupported "
                       "however high the rest scores.")

    # Withheld evidence looks identical to missing evidence in every score.
    for atom in atoms.values():
        ok, why = eligible(atom)
        if ok:
            continue
        add("withheld",
            f"Can any part of \"{atom['title']}\" be said in public? It is withheld "
            f"({why}), so no artefact can cite it however strong it is.",
            "publishability", subject=atom["id"],
            detail="Splitting a publishable general claim from the private specifics is "
                   "usually possible and is the only way this evidence ever counts.")

    for atom in atoms.values():
        aid = atom["id"]

        # Questions someone deliberately wrote down.
        for q in atom.get("open_questions") or []:
            add("recorded", q, "recorded_question", subject=aid)

        # An atom with no source at all. Conversation-derived evidence is legitimate
        # and must still say where it came from, or the pack cannot tell recall from
        # persuasion.
        if not atom.get("source_refs"):
            add("no_source",
                f"What is the source for \"{atom['title']}\"? It cites nothing, so it "
                f"rests entirely on an unrecorded conversation.",
                "provenance", subject=aid,
                detail="Record a person source for the conversation that produced it, "
                       "the way any other source is recorded.")

        # A figure whose basis nobody recorded is an unanswerable interview question.
        for metric in atom.get("metrics") or []:
            text = metric_text(metric)
            if metric_basis(metric) or not extract(text):
                continue
            add("metric_basis",
                f"What is the measurement basis for \"{text}\" in \"{atom['title']}\"? "
                f"Baseline, denominator, period, and who produced it.",
                "metric_defensibility", subject=aid)

        if atom.get("outcome_type") is None and atom.get("evidence_status") != "unresolved":
            add("classification",
                f"What changed for the organisation because of \"{atom['title']}\", "
                f"beyond the work being done? It has no outcome_type.",
                "classification", subject=aid)

        if not atom.get("occurred"):
            add("undated",
                f"When did \"{atom['title']}\" happen? It is undated, so recency ranking "
                f"and gap detection skip it entirely.",
                "recency", subject=aid)

        if atom.get("evidence_status") == "corroborated" and not any(
                r.get("source_id") for r in atom.get("source_refs") or []):
            add("status",
                f"Is there a capturable URL or record behind \"{atom['title']}\"? "
                f"It is corroborated with nothing recorded.",
                "status_promotion", subject=aid)

    # Employment is what a background check actually tests.
    for rec in pack.get("employment", []):
        if rec.get("end") is None:
            add("employment",
                f"When did {rec['employer']} / {rec['title']} end? An unknown end date "
                f"is a gap a background check will find.",
                "background_check", subject=rec["employment_id"])

    for conflict in pack.get("metadata", {}).get("known_conflicts", []):
        if conflict.startswith("RESOLVED"):
            continue
        add("conflict", f"Can this conflict be resolved? {conflict}",
            "recorded_conflict", subject=None)

    found.sort(key=lambda q: -q["score"])
    return found


def delta(pack, pack_path):
    """What the current pack version changed, and how much of it has no source.

    A questioning process that reliably improves a score is indistinguishable from
    a coaching one. This makes the difference visible: movement that rests on
    evidence citing nothing is recall at best and persuasion at worst.
    """
    previous = (pack.get("metadata") or {}).get("supersedes")
    prior = {}
    if previous:
        path = ROOT / previous
        if path.exists():
            try:
                prior = {a["id"]: a for a in json.loads(path.read_text())["evidence_atoms"]}
            except (json.JSONDecodeError, KeyError):
                prior = {}

    atoms = pack.get("evidence_atoms", [])
    added = [a for a in atoms if a["id"] not in prior]
    promoted = [a for a in atoms if a["id"] in prior
                and a.get("outcome_type") != prior[a["id"]].get("outcome_type")]
    unsourced = [a for a in (added + promoted) if not a.get("source_refs")]

    return {"pack": str(pack_path.relative_to(ROOT)), "supersedes": previous,
            "atoms_added": [a["id"] for a in added],
            "outcome_type_changed": [a["id"] for a in promoted],
            "added_or_promoted_with_no_source": [a["id"] for a in unsourced],
            "verdict": (
                "clean" if not unsourced else
                f"{len(unsourced)} of {len(added) + len(promoted)} added or re-typed atoms cite "
                f"no source. That movement rests on conversation alone; record a person source "
                f"for it or treat the improvement as unproven.")}


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--markdown", action="store_true")
    parser.add_argument("--delta", action="store_true",
                        help="what the current pack version changed, and what has no source")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv[1:])

    path = resolve()
    if path is None:
        print("no pack found", file=sys.stderr)
        return 1
    pack = json.loads(path.read_text())

    if args.delta:
        print(json.dumps(delta(pack, path), indent=2))
        return 0

    questions = collect(pack, roles(), cited_ids())
    if args.limit:
        questions = questions[: args.limit]

    if not args.markdown:
        print(json.dumps({"pack": str(path.relative_to(ROOT)),
                          "open": len(questions), "questions": questions}, indent=2))
        return 0

    out = ["# Open questions", "", f"Pack: `{path.relative_to(ROOT)}`", "",
           "Ordered by what answering each one unlocks, not by where it sits in the",
           "pack. Answer from the top: the first few are the ones that move something.", ""]
    if not questions:
        out.append("Nothing outstanding.")
    for i, q in enumerate(questions, 1):
        out.append(f"{i}. **{q['question']}**")
        out.append(f"   _unlocks {q['unlocks'].replace('_', ' ')}"
                   + (f" · `{q['subject']}`" if q["subject"] else "") + "_")
        if q.get("detail"):
            out.append(f"   {q['detail']}")
        out.append("")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
