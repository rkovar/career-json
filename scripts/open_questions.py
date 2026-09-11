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
from evidence_rules import eligible, links, linked_ids  # noqa: E402
from quantities import extract  # noqa: E402

ROLES = ROOT / "data" / "roles"

# What answering is worth. A question that changes a verdict outranks one that
# tidies a field, however tidy the field would be.
UNLOCK = {
    "role_verdict": 5.0,
    "empty_role": 4.5,
    "publishability": 4.0,
    "provenance": 3.5,
    "background_check": 3.0,
    "metric_defensibility": 2.5,
    "status_promotion": 2.5,
    "recorded_conflict": 2.0,
    "classification": 2.0,
    "recency": 1.5,
    "recorded_question": 2.5,
    "link_confirmation": 4.0,
    "screen_gap": 3.5,
}


def screen_gaps():
    """What the latest cold screen of each artefact said needs new evidence.
    Sidecars are overwritten on regeneration, so a gap that was closed stops
    being asked without anyone editing the queue."""
    rows = []
    for path in sorted((ROOT / "outputs").glob("*-screen.json")):
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        for gap in data.get("needs_new_evidence") or []:
            rows.append((data.get("target_role") or path.name, data.get("verdict"), gap))
    return rows


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
            # A proposed link is a question with a real null answer: does this
            # atom evidence that requirement, or not? Until the subject says,
            # role_fit counts nothing for it.
            for link in links(req):
                if link["linked_by"] != "subject" and link["id"] in atoms:
                    add("proposed_link",
                        f"Does \"{atoms[link['id']]['title']}\" evidence {profile['title']}'s "
                        f"{req['weight']} requirement \"{req['text']}\"? The link is proposed, "
                        f"not confirmed, so it earns nothing yet.",
                        "link_confirmation", subject=link["id"],
                        detail=f"scripts/link_evidence.py --confirm {profile['role_id']} "
                               f"\"{req['text'][:40]}\" {link['id']}, or --reject with why.")
            live = [i for i in linked_ids(req) if i in atoms]
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
        # declined is a recorded decision, not a gap; asking again overrides it.
        # unresolved carries its own recorded questions, which are the real ones,
        # and "can it be published" is premature until they are answered.
        if ok or atom.get("evidence_status") in ("declined", "unresolved"):
            continue
        # A constraint beginning "Do not publish" is a recorded decision that the
        # answer is no. Without it the queue asked the same question every run.
        if any(c.lower().startswith("do not publish") for c in atom.get("constraints") or []):
            continue
        add("withheld",
            f"Can any part of \"{atom['title']}\" be said in public? It is withheld "
            f"({why}), so no artefact can cite it however strong it is.",
            "publishability", subject=atom["id"],
            detail="Splitting a publishable general claim from the private specifics is "
                   "usually possible and is the only way this evidence ever counts.")

    for atom in atoms.values():
        aid = atom["id"]
        # A declined atom produces no questions at all. The fixture that says
        # "do not re-ask" received three, which is the queue overruling the owner.
        if atom.get("evidence_status") == "declined":
            continue

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

    # An employer with no evidence at all. This is a hole in every document
    # generated from the pack, and it shows: the role heading renders with an
    # employer, a title, dates and nothing underneath, which reads worse than
    # omitting the role. Found by the subject noticing a blank block on a draft,
    # not by this script, which is why it is here now.
    with_atoms = {a.get("employment_id") for a in atoms.values()}
    for rec in pack.get("employment", []):
        eid = rec["employment_id"]
        if eid in with_atoms:
            continue
        # A promotion with no atoms of its own is not a hole: generation collapses a
        # progression into its parent, so the achievements render under the parent's
        # heading. Only ask when the whole chain is empty, which is a real gap.
        parent = rec.get("parent_employment_id")
        if parent:
            chain = {parent} | {r["employment_id"] for r in pack.get("employment", [])
                                if r.get("parent_employment_id") == parent}
            if chain & with_atoms:
                continue
        add("empty_role",
            f"What did you actually do at {rec['employer']} as {rec['title']}? "
            f"No evidence atom is linked to this role at all "
            f"({rec.get('start')} to {rec.get('end')}).",
            "empty_role", subject=eid,
            detail="Every resume from this pack renders the heading with nothing under it.")

    # Employment is what a background check actually tests.
    for rec in pack.get("employment", []):
        if rec.get("end") is None:
            add("employment",
                f"When did {rec['employer']} / {rec['title']} end? An unknown end date "
                f"is a gap a background check will find.",
                "background_check", subject=rec["employment_id"])

    # A screen's "needs new evidence" list used to go nowhere. Each entry is a
    # question the recruiter effectively asked; it is answered in the pack, not
    # the document, so it belongs in this queue.
    for role, verdict, gap in screen_gaps():
        add("screen_gap",
            f"The cold screen for {role} ({verdict}) says this needs new evidence: {gap}",
            "screen_gap", subject=role,
            detail="Answer it in the pack as an atom, a scope fact on the employment record, or a "
                   "positioning line on the role profile; a rewrite cannot close it.")

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

    # A rewritten Result that kept its old citation. The review found a changed
    # claim returned "clean" because only additions and re-typings were compared;
    # what the atom *says* is the thing most worth watching. A rewrite whose
    # sources did not change is legitimate (a wording fix) and is listed, not
    # flagged: this is a report, and a report that cries wolf gets skipped.
    def claim(a):
        return json.dumps({"title": a.get("title"), "star": a.get("star"),
                           "metrics": a.get("metrics")}, sort_keys=True)
    def sources(a):
        return sorted(r.get("source_id", "") for r in a.get("source_refs") or [])
    rewritten = [a for a in atoms if a["id"] in prior and claim(a) != claim(prior[a["id"]])]
    rewritten_same_sources = [a["id"] for a in rewritten if sources(a) == sources(prior[a["id"]])]

    return {"pack": str(pack_path.resolve().relative_to(ROOT.resolve())), "supersedes": previous,
            "atoms_added": [a["id"] for a in added],
            "outcome_type_changed": [a["id"] for a in promoted],
            "claims_rewritten": [a["id"] for a in rewritten],
            "rewritten_with_no_new_source": rewritten_same_sources,
            "added_or_promoted_with_no_source": [a["id"] for a in unsourced],
            "verdict": (
                (f"{len(unsourced)} of {len(added) + len(promoted)} added or re-typed atoms cite "
                 f"no source. That movement rests on conversation alone; record a person source "
                 f"for it or treat the improvement as unproven.") if unsourced else
                ("clean" + (f"; {len(rewritten_same_sources)} claim(s) rewritten with no new "
                            f"source, listed above for review" if rewritten_same_sources else "")))}


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--markdown", action="store_true")
    output.add_argument("--json", action="store_true", help="explicit JSON output (the default)")
    parser.add_argument("--delta", action="store_true",
                        help="what the current pack version changed, and what has no source")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--pack", help="inspect a staged candidate before acceptance")
    args = parser.parse_args(argv[1:])

    from pack_io import local
    path = local(args.pack) if args.pack else resolve()
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
        print(json.dumps({"pack": str(path.resolve().relative_to(ROOT.resolve())),
                          "open": len(questions), "questions": questions}, indent=2))
        return 0

    out = ["# Open questions", "", f"Pack: `{path.resolve().relative_to(ROOT.resolve())}`", "",
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
