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


def editorial_staleness(run):
    """Changed or newly applicable inputs invalidate an editorial review."""
    from editorial import pin_errors, read, decision_context, digest, role_pin_errors
    inputs = run.get('editorial_inputs')
    if not inputs:
        return []
    errors = []
    pins = [inputs['selection'], inputs['brief']] + inputs.get('decisions', [])
    if inputs.get('role'):
        pins.append(inputs['role'])
    for p in pins:
        errors.extend(pin_errors(p))
    errors.extend(pin_errors({'path': run['pack'], 'sha256': run['pack_sha256']}))
    if not errors:
        try:
            selection = read(inputs['selection']['path'])
            if (selection['pack'] != {'path': run['pack'], 'sha256': run['pack_sha256']}
                    or selection['brief'] != inputs['brief'] or selection['decisions'] != inputs['decisions']
                    or selection.get('role') != inputs.get('role')):
                errors.append('manifest does not match its pinned selection')
            brief = read(inputs['brief']['path'])
            errors.extend(role_pin_errors(brief, inputs.get('role')))
            if digest(decision_context(brief)) != inputs['decision_context_sha256']:
                errors.append('applicable editorial decisions changed')
            if run.get('skill_versions') != skill_versions():
                errors.append('workflow versions changed')
            current = resolve()
            if current and sha256(current) != run['pack_sha256']:
                errors.append('current career pack changed')
        except (ValueError, OSError) as exc:
            errors.append(str(exc))
    return errors


def manifest(target_role=None, artifact=None, selection=None, settings=None):
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
    if selection is not None:
        from editorial import checked, pin, read, digest, decision_context, validate_record
        record = checked(selection, 'selection')
        _, warnings = validate_record('selection', record)
        if warnings:
            raise ValueError('; '.join(warnings))
        brief = read(record['brief']['path'])
        out['pack'] = record['pack']['path']
        out['pack_sha256'] = record['pack']['sha256']
        out['schema_version'] = read(out['pack'])['schema_version']
        out['editorial_inputs'] = {'selection': pin(selection), 'brief': record['brief'],
                                  'decisions': record['decisions'],
                                  'decision_context_sha256': digest(record['decisions'])}
        if record.get('role'):
            out['editorial_inputs']['role'] = record['role']
        if decision_context(brief) != record['decisions']:
            raise ValueError('selection decisions are stale')
    if settings is not None:
        out['generation_settings'] = settings
    return out


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("target_role", nargs="?", default=None)
    parser.add_argument("--artifact", type=Path, default=None,
                        help="the Markdown artefact this record evaluates; pins its sha256")
    parser.add_argument('--selection', help='durable selection used to produce the artifact')
    parser.add_argument('--settings', type=Path, help='JSON object of generation settings; no credentials')
    args = parser.parse_args(argv[1:])
    try:
        settings = json.loads(args.settings.read_text()) if args.settings else None
        if settings is not None and not isinstance(settings, dict):
            raise ValueError('settings must be a JSON object')
        print(json.dumps(manifest(args.target_role, args.artifact, args.selection, settings), indent=2))
    except (ValueError, KeyError, OSError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
