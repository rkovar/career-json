#!/usr/bin/env python3
"""Ask, cold, whether each bullet says more than its cited evidence does.

quantities.py checks magnitudes and nothing else, because whether a bullet
preserves the meaning of a Result is entailment and is not decidable from the
pack. It is decidable by a model that has seen nothing but the atom and the
bullet, which is a different thing from the model that wrote the bullet judging
its own work. This script runs that cold judgement, one call per cited block,
through the Claude Code CLI (`claude -p`, structured output, no tools, no
session). No new Python dependency: the CLI is the workspace's own runtime.

Each judge sees only the atom's title, STAR and metrics, and the bullet. Not the
pack, not the role, not the conversation. It answers supported, overstated or
unsupported, and quotes the clause that overreaches.

Reporting mode by default, like quantities.py, and for the same reason: a noisy
check teaches generation to flatten claims rather than go back to the atom. Run
it on real drafts, measure, then decide whether it may block.

    scripts/entailment.py outputs/draft.md
    scripts/entailment.py outputs/draft.md --json
    scripts/entailment.py outputs/draft.md --strict        # exit 1 on unsupported
    scripts/entailment.py --text "Halved spend." --atom E_X

Tests replace the CLI with CLAUDE_CMD, so the suite never spends tokens.
"""
import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from current_pack import resolve, metric_text, metric_basis, this_year, ROOT  # noqa: E402
from quantities import cited_blocks  # noqa: E402

VERDICTS = ("supported", "overstated", "unsupported")
SCHEMA = {
    "type": "object",
    "required": ["verdict", "reason"],
    "properties": {
        "verdict": {"type": "string", "enum": list(VERDICTS)},
        "reason": {"type": "string"},
        "overreach": {"type": ["string", "null"],
                      "description": "The clause of the bullet the evidence does not support, quoted; null if supported."},
    },
    "additionalProperties": False,
}
SYSTEM = """You judge whether a resume bullet is entailed by the evidence it cites. You see only the evidence and the bullet.

supported: every claim in the bullet is stated in or follows directly from the evidence. Rewording, compression and omission are fine.
overstated: the bullet is about the same work but strengthens it: a larger scope, a firmer causal claim, ownership the evidence gives to a team, a result the evidence gives as an estimate stated as fact, or a consequence the evidence does not mention.
unsupported: the bullet makes a claim the evidence does not contain at all.

Judge the bullet's claims, not its style. A bullet that says less than the evidence is supported. Quote the overreaching clause exactly."""
DEFAULT_CMD = "claude -p --output-format json --no-session-persistence --tools \"\" --model sonnet"


def atom_text(atom):
    star = atom.get("star") or {}
    lines = [f"Title: {atom.get('title', '')}"]
    for field in ("situation", "task", "action", "result"):
        if star.get(field):
            lines.append(f"{field.capitalize()}: {star[field]}")
    metrics = [metric_text(m) + (f" (basis: {metric_basis(m)})" if metric_basis(m) else "")
               for m in atom.get("metrics") or []]
    if metrics:
        lines.append("Metrics: " + "; ".join(metrics))
    return "\n".join(lines)


def context(atoms, pack):
    """What a bullet may say that no atom says: the employer, title and dates
    from the employment record each atom is linked to, and the career span.
    make-resume takes those from the records, so the judge must see them or it
    reports the employer's name as invented. Nothing else is added."""
    records = {r["employment_id"]: r for r in pack.get("employment", [])}
    safe = [r for r in records.values() if r.get("external_safe")]
    lines = []
    # A summary paragraph cites several atoms and surveys the whole career, so
    # it may name every employer; a bullet under one role may name only its own.
    linked = safe if len(atoms) >= 3 else [records[a["employment_id"]] for a in atoms
                                            if a.get("employment_id") in records]
    for rec in linked:
        lines.append(f"{rec['employer']}, {rec['title']}, {rec['start']} to {rec.get('end') or 'unknown'}")
    if safe:
        first = min(int(r["start"][:4]) for r in safe)
        last = max(this_year() if r.get("end") == "present" else int((r.get("end") or r["start"])[:4]) for r in safe)
        lines.append(f"Career span across all employment records: {last - first} years, {first} to {last}")
    return "\n".join(dict.fromkeys(lines))


def prompt(atoms, bullet, pack=None):
    evidence = "\n\n".join(atom_text(a) for a in atoms)
    extra = context(atoms, pack) if pack else ""
    if extra:
        evidence += f"\n\nEMPLOYMENT CONTEXT (the bullet may state these facts)\n\n{extra}"
    return f"EVIDENCE\n\n{evidence}\n\nBULLET\n\n{bullet}\n\nIs the bullet entailed by the evidence?"


def ask(text):
    """One cold call. CLAUDE_CMD overrides the CLI so tests can fake it."""
    cmd = shlex.split(os.environ.get("CLAUDE_CMD", DEFAULT_CMD))
    if "CLAUDE_CMD" not in os.environ:
        cmd += ["--system-prompt", SYSTEM, "--json-schema", json.dumps(SCHEMA)]
    proc = subprocess.run(cmd + [text], capture_output=True, text=True, timeout=180)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip()[:300] or "judge call failed")
    payload = json.loads(proc.stdout)
    # The CLI wraps structured output; a fake runner may return the object bare.
    verdict = payload.get("structured_output") or payload.get("result") or payload
    if isinstance(verdict, str):
        verdict = json.loads(verdict)
    if verdict.get("verdict") not in VERDICTS:
        raise RuntimeError(f"judge returned no verdict: {str(payload)[:200]}")
    return verdict


def check(markdown, pack, limit=None):
    atoms = {a["id"]: a for a in pack.get("evidence_atoms", [])}
    rows = []
    for text, ids in cited_blocks(markdown):
        cited = [atoms[i] for i in ids if i in atoms]
        if not cited:
            continue
        if limit is not None and len(rows) >= limit:
            break
        try:
            verdict = ask(prompt(cited, text, pack))
        except (RuntimeError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
            verdict = {"verdict": "error", "reason": str(exc)[:200], "overreach": None}
        rows.append({"bullet": text, "cites": ids, **verdict})
    return rows


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("markdown", type=Path, nargs="?")
    parser.add_argument("--text", help="judge one bullet directly")
    parser.add_argument("--atom", action="append", default=[], help="with --text; repeatable")
    parser.add_argument("--limit", type=int, default=None, help="judge at most this many blocks")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="exit 1 on overstated or unsupported")
    args = parser.parse_args(argv[1:])
    if not args.markdown and not args.text:
        parser.error("give an artefact, or --text with --atom")

    path = resolve()
    if path is None:
        print("no pack found", file=sys.stderr)
        return 1
    pack = json.loads(path.read_text())
    if args.text:
        markdown = f"- {args.text} " + " ".join(f"<!-- Evidence: {a} -->" for a in args.atom) + "\n"
        label = "--text"
    else:
        markdown = args.markdown.read_text()
        label = str(args.markdown)

    rows = check(markdown, pack, args.limit)
    flagged = [r for r in rows if r["verdict"] in ("overstated", "unsupported")]
    if args.json:
        print(json.dumps({"artefact": label, "judged": len(rows), "findings": rows}, indent=2))
    else:
        counts = {v: sum(1 for r in rows if r["verdict"] == v) for v in VERDICTS + ("error",)}
        print(f"{'FLAG' if flagged else 'ok'}  {label}  ({len(rows)} blocks judged cold: "
              + ", ".join(f"{k} {v}" for k, v in counts.items() if v) + ")")
        for row in rows:
            if row["verdict"] == "supported":
                continue
            print(f"      {row['verdict'].upper()}  {row['bullet'][:90]}")
            if row.get("overreach"):
                print(f"        overreach: {row['overreach']!r}")
            print(f"        {row['reason'][:200]}")
    return 1 if (flagged and args.strict) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
