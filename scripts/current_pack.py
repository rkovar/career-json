#!/usr/bin/env python3
"""Resolve the pack a generation run should use, deterministically.

"Newest file in data/packs" is a guess: it breaks on same-day filenames and on a
pack retained as history. This walks the supersedes chain instead, so there is
exactly one answer and it is reproducible.

    python3 scripts/current_pack.py          # path
    python3 scripts/current_pack.py --json   # path, sha256, atom counts
"""
import hashlib
import json
import os
import sys
from datetime import date
from pathlib import Path

# CAREER_WORKSPACE lets tests and alternate checkouts point at another tree.
# Without it every test had to mutate the user's live data to run.
ROOT = Path(os.environ.get("CAREER_WORKSPACE", Path(__file__).resolve().parent.parent))
PACKS = ROOT / "data" / "packs"


def metric_text(metric):
    """A metric is either a plain string or an object carrying its measurement
    basis. Every consumer joins metrics into text, so each one needed this and
    would otherwise have crashed on the object form."""
    if isinstance(metric, dict):
        return metric.get("value") or ""
    return metric or ""


def metric_basis(metric):
    """How the figure was measured, or None when nobody recorded it."""
    return metric.get("basis") if isinstance(metric, dict) else None


def this_year():
    """A current role ends today, not in whatever year this was written."""
    return date.today().year


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve(directory=PACKS):
    packs = sorted(p for p in directory.glob("*.json"))
    if not packs:
        return None
    superseded = set()
    for path in packs:
        try:
            meta = json.loads(path.read_text()).get("metadata") or {}
        except json.JSONDecodeError:
            continue
        if meta.get("supersedes"):
            superseded.add((ROOT / meta["supersedes"]).resolve())
    live = [p for p in packs if p.resolve() not in superseded]
    if len(live) > 1:
        # Ambiguity is a bug in pack hygiene, not something to paper over.
        names = ", ".join(p.name for p in live)
        raise SystemExit(
            f"ambiguous: {len(live)} packs claim to be current ({names}).\n"
            "Set metadata.supersedes on the newer pack so the chain has one head."
        )
    return live[0] if live else None


def main(argv):
    path = resolve()
    if path is None:
        print("no pack found in data/packs", file=sys.stderr)
        return 1
    if "--json" in argv:
        pack = json.loads(path.read_text())
        atoms = pack.get("evidence_atoms", [])
        eligible = [a for a in atoms
                    if a.get("external_safe") and a.get("evidence_status") not in ("unresolved", "declined")]
        print(json.dumps({
            "path": str(path.relative_to(ROOT)),
            "sha256": sha256(path),
            "schema_version": pack.get("schema_version"),
            "atoms": len(atoms),
            "eligible": len(eligible),
            "has_private_profile": bool(pack.get("private_profile")),
        }, indent=2))
    else:
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
