#!/usr/bin/env python3
"""Emit the provenance block for a generation run.

The workspace demands that every career claim record where it came from, then
records nothing about where the artefact came from. Pin the pack by hash and the
skills by hash, so an artefact can be reproduced and so a stale evaluation is
detectable rather than silently wrong.

    python3 scripts/manifest.py "Head of AI Security"
"""
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


def manifest(target_role=None):
    pack = resolve()
    return {
        "generated": date.today().isoformat(),
        "target_role": target_role,
        "pack": str(pack.relative_to(ROOT)) if pack else None,
        "pack_sha256": sha256(pack) if pack else None,
        "schema_version": json.loads(pack.read_text()).get("schema_version") if pack else None,
        "skill_versions": skill_versions(),
    }


def main(argv):
    print(json.dumps(manifest(argv[1] if len(argv) > 1 else None), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
