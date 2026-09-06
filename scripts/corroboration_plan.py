#!/usr/bin/env python3
"""Rank the evidence worth getting corroborated, and say what to ask for.

The workspace records whether a claim is corroborated and does nothing to help
close the gap. Left alone that produces a pack where everything is technically
honest and almost nothing survives a reference check.

Ranking is deliberately simple and explainable: value to a resume, multiplied by
how exposed the claim currently is. No cleverness, because the user has to trust
the ordering enough to act on it.

    python3 scripts/corroboration_plan.py            # ranked work list
    python3 scripts/corroboration_plan.py --markdown # same, as a review record
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from current_pack import resolve, ROOT  # noqa: E402

# How much a corroborated version of this claim is worth on a resume.
VALUE = {"business_outcome": 3.0, "output": 2.0, "activity": 1.0, None: 0.5}
# How exposed the claim is today. externally_verified needs no work.
EXPOSURE = {"self_asserted": 2.0, "corroborated": 1.0, "externally_verified": 0.0,
            "unresolved": 1.5, "declined": 0.0}

URL_HINT = re.compile(r"page|programme|archive|listing|site|url|http", re.I)


def cited_ids():
    """Claims that actually reach artefacts matter more than ones that never do."""
    ids = set()
    for path in (ROOT / "outputs").glob("*-draft.md"):
        ids |= set(re.findall(r"E_[A-Z0-9_]+", path.read_text()))
    return ids


def ask_for(atom):
    """The specific request, not a generic nudge."""
    status = atom["evidence_status"]
    if status == "unresolved":
        first = (atom.get("open_questions") or ["Answer the open question recorded on this atom."])[0]
        return f"Answer it or retire it: {first}"
    if status == "corroborated":
        for c in atom.get("corroborators") or []:
            if c.get("kind") == "public_artefact" or URL_HINT.search(str(c.get("reference", ""))):
                return (f"Capture the URL and today's date for: {c.get('reference')}. "
                        "Add it as a url source record with independent: true.")
        return "Record the corroborating artefact as a url source so this reaches externally_verified."
    employer = any(k in atom["id"] for k in ("JPMC", "SPLUNK", "DARPA", "NAVY", "EARLY"))
    if employer:
        return ("Name, by role, one person who saw this and would confirm your part: "
                "the manager who approved it, or a peer who delivered alongside you.")
    return "Identify a public artefact or a named third party who would confirm this."


def plan(pack):
    rows = []
    cited = cited_ids()
    for atom in pack["evidence_atoms"]:
        status = atom["evidence_status"]
        exposure = EXPOSURE.get(status, 1.0)
        if exposure == 0.0:
            continue
        if atom.get("corroborators") and status != "unresolved":
            exposure *= 0.5  # someone is identified, just not recorded
        score = VALUE[atom.get("outcome_type")] * exposure
        if atom["id"] in cited:
            score *= 1.5  # already load-bearing in a real document
        if not atom.get("external_safe"):
            score *= 0.4  # cannot be published, so worth less until that changes
        rows.append({
            "id": atom["id"],
            "title": atom["title"],
            "evidence_status": status,
            "outcome_type": atom.get("outcome_type"),
            "cited_in_an_artefact": atom["id"] in cited,
            "external_safe": atom["external_safe"],
            "score": round(score, 2),
            "ask": ask_for(atom),
        })
    rows.sort(key=lambda r: (-r["score"], r["id"]))
    return rows


def summarise(pack, rows):
    atoms = pack["evidence_atoms"]
    counts = {}
    for atom in atoms:
        counts[atom["evidence_status"]] = counts.get(atom["evidence_status"], 0) + 1
    return {
        "atoms": len(atoms),
        "by_status": counts,
        "with_corroborator": sum(1 for a in atoms if a.get("corroborators")),
        "needing_work": len(rows),
        "quickest_wins": [r["id"] for r in rows if r["evidence_status"] == "corroborated"],
    }


def as_markdown(pack_path, rows, summary):
    out = [f"# Corroboration Plan: {date.today().isoformat()}", "",
           f"Pack: `{pack_path}`", "",
           "Ranked by what a corroborated version of the claim is worth, multiplied by",
           "how exposed it is today. Claims already carrying a document rank higher.", "",
           "## Where the pack stands", ""]
    for status, count in sorted(summary["by_status"].items()):
        out.append(f"- `{status}`: {count}")
    out += [f"- atoms with any corroborator: {summary['with_corroborator']} of {summary['atoms']}", ""]
    if summary["quickest_wins"]:
        out += ["## Quickest wins", "",
                "Already corroborated, needing only a recorded source to reach "
                "`externally_verified`:", ""]
        out += [f"- `{i}`" for i in summary["quickest_wins"]] + [""]
    out += ["## Work list", "", "| # | Atom | Status | Ask |", "| --- | --- | --- | --- |"]
    for i, row in enumerate(rows, 1):
        out.append(f"| {i} | `{row['id']}` | {row['evidence_status']} | {row['ask']} |")
    out += ["", "Answers are user assertions. Recording one does not promote an atom past",
            "`self_asserted` unless it names a third party, and not past `corroborated`",
            "unless that source is recorded. See `review-evidence`."]
    return "\n".join(out) + "\n"


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--markdown", action="store_true", help="emit a review record")
    parser.add_argument("--top", type=int, default=None, help="limit the work list")
    args = parser.parse_args(argv[1:])

    path = resolve()
    if path is None:
        print("no pack found", file=sys.stderr)
        return 1
    pack = json.loads(path.read_text())
    rows = plan(pack)
    if args.top:
        rows = rows[: args.top]
    summary = summarise(pack, plan(pack))

    if args.markdown:
        print(as_markdown(path.relative_to(ROOT), rows, summary))
    else:
        print(json.dumps({"pack": str(path.relative_to(ROOT)), "summary": summary, "plan": rows}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
