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
    errors = []
    if run.get('process'):
        errors.extend(pin_errors(run['process']))
        if not errors:
            from resume_process import process_errors
            process = read(run['process']['path'])
            errors.extend(process_errors(process, final=False))
            if not errors and (process['artifact']['sha256'] != run.get('artifact_sha256')
                    or process['plan'] != (inputs or {}).get('plan')):
                errors.append('process review does not match the manifest artifact and plan')
    if run.get('exports'):
        errors.extend(pin_errors(run['exports']))
        if not errors:
            from export_resume import validate_export_report
            errors.extend(validate_export_report(run['exports']['path']))
    if not inputs:
        return errors
    pins = [inputs['selection'], inputs['brief']] + inputs.get('decisions', [])
    pins += [inputs[key] for key in ('plan', 'policy') if inputs.get(key)]
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
            from editorial import require_selection_review
            require_selection_review(selection, brief)
            if brief.get('application') and brief['format'] == 'resume' and not inputs.get('plan'):
                errors.append('planned resume workflow is missing its ready plan pin')
            if inputs.get('plan'):
                from resume_workflow import checked_plan
                plan = checked_plan(inputs['plan']['path'])
                if plan['selection'] != inputs['selection'] or plan['policy'] != inputs.get('policy'):
                    errors.append('manifest plan does not match its selection or policy')
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


def manifest(target_role=None, artifact=None, selection=None, settings=None, plan=None, exports=None, process=None):
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
        from editorial import require_selection_review
        require_selection_review(record, brief)
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
        if brief.get('application') and brief['format'] == 'resume' and plan is None:
            raise ValueError('this resume brief requires a ready resume plan')
    if plan is not None:
        from resume_workflow import checked_plan
        from editorial import pin
        planned = checked_plan(plan)
        if selection is None or planned['selection'] != pin(selection):
            raise ValueError('manifest plan must refer to the supplied selection')
        out['editorial_inputs']['plan'] = pin(plan)
        out['editorial_inputs']['policy'] = planned['policy']
    if exports is not None:
        from export_resume import validate_export_report
        from editorial import pin, read
        errors = validate_export_report(exports)
        exported = read(exports)
        if errors: raise ValueError('; '.join(errors))
        if artifact is None or exported['artifact'] != pin(artifact):
            raise ValueError('exports do not match this artifact')
        if plan is not None and exported.get('plan') != pin(plan):
            raise ValueError('exports do not match this plan')
        out['exports'] = pin(exports)
    if settings is not None:
        out['generation_settings'] = settings
    if process is not None:
        from editorial import pin, read
        from resume_process import process_errors
        reviewed = read(process)
        errors = process_errors(reviewed, final=False)
        if errors:
            raise ValueError('; '.join(errors))
        if artifact is None or plan is None or reviewed['artifact'] != pin(artifact) or reviewed['plan'] != pin(plan):
            raise ValueError('process review must match the supplied artifact and plan')
        out['process'] = pin(process)
    return out


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("target_role", nargs="?", default=None)
    parser.add_argument("--artifact", type=Path, default=None,
                        help="the Markdown artefact this record evaluates; pins its sha256")
    parser.add_argument('--selection', help='durable selection used to produce the artifact')
    parser.add_argument('--plan', help='ready resume plan for this selection')
    parser.add_argument('--exports', help='verified PDF/TXT/DOCX/Markdown export report')
    parser.add_argument('--process', help='private exact-draft process review')
    parser.add_argument('--settings', type=Path, help='JSON object of generation settings; no credentials')
    args = parser.parse_args(argv[1:])
    try:
        settings = json.loads(args.settings.read_text()) if args.settings else None
        if settings is not None and not isinstance(settings, dict):
            raise ValueError('settings must be a JSON object')
        print(json.dumps(manifest(args.target_role, args.artifact, args.selection, settings, args.plan, args.exports, args.process), indent=2))
    except (ValueError, KeyError, OSError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
