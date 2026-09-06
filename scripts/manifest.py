#!/usr/bin/env python3
"""Emit the provenance block for a generation run.

The workspace demands that every career claim record where it came from, then
records nothing about where the artefact came from. Pin the pack by hash and the
skills by hash, so an artefact can be reproduced and so a stale evaluation is
detectable rather than silently wrong.

    python3 scripts/manifest.py "Head of AI Security"
"""
import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from current_pack import resolve, sha256, ROOT  # noqa: E402

SKILLS = ROOT / ".claude" / "skills"


def skill_versions():
    out = {}
    for skill in sorted(SKILLS.glob("*/SKILL.md")):
        out[skill.parent.name] = hashlib.sha256(skill.read_bytes()).hexdigest()[:12]
    return out


def manifest(target_role=None, artifact=None):
    pack = resolve()
    out = {
        "generated": date.today().isoformat(),
        "target_role": target_role,
        "pack": str(pack.relative_to(ROOT)) if pack else None,
        "pack_sha256": sha256(pack) if pack else None,
        "schema_version": json.loads(pack.read_text()).get("schema_version") if pack else None,
        "skill_versions": skill_versions(),
    }
    if artifact is not None:
        # Approval belongs to an exact document. Pinning the pack alone let an
        # edited artefact keep its evaluation.
        out["artifact_sha256"] = sha256(Path(artifact))
    return out


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("target_role", nargs="?", default=None)
    parser.add_argument("--artifact", type=Path, default=None,
                        help="the Markdown artefact this record evaluates; pins its sha256")
    args = parser.parse_args(argv[1:])
    print(json.dumps(manifest(args.target_role, args.artifact), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
