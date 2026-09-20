#!/usr/bin/env python3
"""Private career workspace health, readable history and reviewed maintenance."""
import argparse
import copy
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import sys

from current_pack import ROOT, resolve
from pack_io import local, read, write_new
from career_profile import profile_state


def health(root=ROOT):
    root = Path(root).resolve()
    from validate_pack import check
    from verify_excerpts import verify
    from schema_tools import walk
    errors, attention, steps = [], [], []
    pack, path = {}, None
    try:
        path = resolve(root / 'data/packs', root)
        if path:
            pack = json.loads(path.read_text())
            schema = json.loads((root / 'schemas/career.schema.json').read_text())
            issues, warnings = check(path, schema, root=root)
            errors.extend(issues)
            attention.extend(warnings)
            if pack.get('schema_version') == '1.3':
                schema = json.loads((root / 'schemas/archive/career-1.3.schema.json').read_text())
            walk(pack, schema, schema, '', errors)
    except (SystemExit, ValueError, KeyError, TypeError, OSError) as exc:
        errors.append(str(exc))
    verification = {'counts': {}, 'records_without_excerpt': []}
    if pack and not errors:
        verification = verify(pack, root)
        for row in verification['excerpts']:
            if row['status'] == 'mismatch':
                errors.append(row['record'] + ': ' + row['detail'])
            elif row['status'] == 'unverifiable':
                attention.append(row['record'] + ': source unavailable: ' + row['detail'])
        attention.extend(key + ': no source excerpt recorded' for key in verification['records_without_excerpt'])
        attention.extend(s['id'] + ': reassess changed supporting evidence' for s in pack.get('strengths_profile', []) if profile_state(s, pack) in ('stale', 'unsupported'))
    sessions = []
    for p in sorted((root / 'reviews/pack-reviews').glob('*/session.json')):
        try:
            session = json.loads(p.read_text())
            from pack_io import pin_errors
            for field in ('proposal', 'base'):
                if session.get(field):
                    errors.extend(pin_errors(session[field], root))
            saved = {'path': str(p.relative_to(root))}
            if root == ROOT.resolve() and not errors:
                from pack_review import status
                saved['summary'] = status(p)['summary']
            sessions.append(saved)
        except (ValueError, KeyError, TypeError, OSError) as exc:
            errors.append(str(p.relative_to(root)) + ': ' + str(exc))
    from workspace_backup import reference_audit
    audit = reference_audit(root)
    errors.extend(audit['errors'])
    attention.extend(audit['warnings'])
    from career_state import summary
    current_state = summary(root)
    errors.extend(current_state['errors'])
    # Audit every historical session above; navigation shows only current work.
    sessions = current_state['reviews']
    question_state = current_state['questions']
    questions = [q for q in question_state['items'] if q.get('state', 'open') == 'open' and not q.get('optional')]
    if errors:
        steps.append('Resolve the reported integrity problems before accepting another version.')
    if any(s['actionable'] for s in sessions):
        steps.append('Continue a saved review; your recorded decisions remain available.')
    if questions:
        steps.append('Answer one open question when you have useful information to add.')
    if not path and not errors:
        steps.append('Bring one source to build your first proposed career record.')
    elif pack.get('evidence_atoms'):
        steps.append('Recall a recorded achievement and inspect its original source.')
    from coverage import analyse
    coverage = analyse(pack) if pack.get('evidence_atoms') else None
    return {'coverage': coverage, 'integrity': 'needs_repair' if errors else 'ok',
            'current_pack': str(path.relative_to(root)) if path else None,
            'saved': {'roles': len(pack.get('employment', [])), 'achievements': sum(a.get('evidence_status') != 'declined' for a in pack.get('evidence_atoms', []))},
            'errors': list(dict.fromkeys(errors)), 'attention': list(dict.fromkeys(attention)),
            'open_questions': questions, 'question_state': question_state, 'review_sessions': sessions, 'verification': verification['counts'],
            'next_steps': steps, 'readiness': 'Integrity and career completeness are separate. There is no completeness score or minimum achievement count.'}


def health_text(state):
    lines = ['Career workspace health', '', 'Integrity: ' + state['integrity'],
             f"Saved: {state['saved']['roles']} roles; {state['saved']['achievements']} achievements."]
    for session in state['review_sessions']:
        summary = session.get('summary')
        if summary:
            lines.append(session['path'] + ': ' + str(summary['pending_items']) + ' pending items; ' + str(summary['corrections']) + ' correction requests.')
    if state.get('coverage'):
        gaps = state['coverage']['gaps']
        if gaps:
            lines.append('Periods with no recorded achievements: ' + ', '.join(str(a) + '–' + str(b) for a, b in gaps) + '. These may be intentional; they are not evidence of missing work.')
    for label, field in [('Needs repair', 'errors'), ('Needs attention', 'attention'), ('Useful next steps', 'next_steps')]:
        lines.extend(['', label + ':'])
        lines.extend('- ' + value for value in state[field])
        if not state[field]:
            lines.append('- None recorded.')
    lines.extend(['', state['readiness']])
    return '\n'.join(lines) + '\n'


def history(identifier, root=ROOT):
    root = Path(root).resolve()
    from pack_review import units
    path = resolve(root / 'data/packs', root)
    versions, dependencies, relationships, gaps = [], [], [], []
    latest = json.loads(path.read_text()) if path else {}
    key = identifier if '/' in identifier else 'evidence_atoms/' + identifier
    visited = set()
    while path:
        if path.resolve() in visited:
            gaps.append('Cycle in historical references; run health.')
            break
        visited.add(path.resolve())
        if not path.is_file():
            gaps.append('Missing historical version: ' + str(path.relative_to(root)))
            break
        pack = json.loads(path.read_text())
        value = units(pack).get(key)
        receipt = ((pack.get('metadata') or {}).get('human_review') or {}).get('items', {}).get(key)
        decision = None
        if receipt:
            try:
                batch = json.loads(local(receipt['batch']['path'], root).read_text())
                decision = next((r for r in batch['decisions'] if r['key'] == key), None)
            except (ValueError, OSError, KeyError):
                decision = {'note': 'Review record is unavailable; run health.'}
        sources = {s['source_id']: s for s in pack.get('source_records', [])}
        versions.append({'pack': str(path.relative_to(root)), 'value': value, 'review': receipt, 'decision': decision,
                         'sources': [{'reference': r, 'source': sources.get(r['source_id'])} for r in (value or {}).get('source_refs', [])] if isinstance(value, dict) else []})
        previous = (pack.get('metadata') or {}).get('supersedes')
        path = local(previous, root) if previous else None
    versions.reverse()
    changes, before, prior_review = [], None, None
    for version in versions:
        if version['value'] != before or version['review'] != prior_review or not changes:
            version['before'] = before
            changes.append(version)
        before = version['value']
        prior_review = version['review']
    aid = key.split('/', 1)[1]
    for strength in latest.get('strengths_profile', []):
        if aid in strength['evidence_ids']:
            dependencies.append({'kind': 'strength', 'id': strength['id'], 'state': profile_state(strength, latest)})
    for folder in ('data/briefs', 'data/selections'):
        for file in sorted((root / folder).glob('*.json')):
            record = json.loads(file.read_text())
            def has(value):
                return value == aid if isinstance(value, str) else any(has(v) for v in value.values()) if isinstance(value, dict) else any(has(v) for v in value) if isinstance(value, list) else False
            if has(record):
                dependencies.append({'kind': 'saved application input', 'path': str(file.relative_to(root)), 'state': 'pinned to its original inputs; regenerate after relevant changes'})
    for event in (latest.get('metadata') or {}).get('evidence_maintenance', []):
        if aid in event['from_ids'] + event['to_ids']:
            relationships.append(event)
    return {'key': key, 'changes': changes, 'dependencies': dependencies, 'relationships': relationships, 'gaps': gaps}


def history_html(state):
    from review_html import show
    esc = html.escape
    blocks = ['<h1>History of ' + esc(state['key']) + '</h1><p>Private career history. Original versions remain available.</p>']
    if state.get('gaps'):
        blocks.append('<h2>History needs attention</h2>' + show(state['gaps']))
    for change in state['changes']:
        blocks.append('<section><h2>' + esc(change['pack']) + '</h2>')
        if change['review']:
            blocks.append('<p>Accepted by ' + esc(change['review']['reviewed_by']) + ' on ' + esc(change['review']['recorded']) + '</p>')
        else:
            blocks.append('<p>No wording acceptance recorded for this version.</p>')
        blocks.append('<h3>Recorded content</h3>' + show(change['value']))
        blocks.append('<details><summary>Previous content</summary>' + show(change['before']) + '</details>')
        blocks.append('<h3>Original sources and answers</h3>' + show(change['sources']))
        if change['decision']:
            blocks.append('<h3>Review explanation</h3>' + show(change['decision']))
        blocks.append('</section>')
    blocks.append('<h2>Used by</h2>' + show(state['dependencies']))
    blocks.append('<h2>Merge, split and refresh history</h2>' + show(state['relationships']))
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Private achievement history</title><style>body{max-width:960px;margin:32px auto;padding:20px;font:16px/1.6 system-ui}section{border-top:1px solid #ccc}dt{font-weight:bold}dd{overflow-wrap:anywhere}details{padding:12px}</style><main>' + ''.join(blocks) + '</main></html>'


def maintain(operation, input_path, ids, reason, output):
    """Author supplied replacement wording as a candidate; never merge prose automatically."""
    from career_core import validate_candidate
    current = resolve()
    if not current:
        raise ValueError('maintenance needs an accepted career pack')
    destination = local(output)
    if destination.parent != local('data/candidates'):
        raise ValueError('maintenance creates a candidate; review it before acceptance')
    if not reason.strip():
        raise ValueError('explain why these records should change')
    pack = copy.deepcopy(read(current))
    original = {a['id']: a for a in pack['evidence_atoms']}
    if len(set(ids)) != len(ids) or not ids or not set(ids) <= set(original):
        raise ValueError('from IDs must identify distinct existing achievements')
    payload = read(input_path)
    atoms = payload['atoms']
    targets = [a['id'] for a in atoms]
    if len(set(targets)) != len(targets):
        raise ValueError('replacement IDs must be unique')
    if operation == 'merge' and (len(ids) < 2 or len(targets) != 1):
        raise ValueError('merge needs multiple original IDs and one new achievement')
    if operation == 'split' and (len(ids) != 1 or len(targets) < 2):
        raise ValueError('split needs one original ID and multiple new achievements')
    if operation == 'refresh' and (len(ids) != 1 or targets != ids):
        raise ValueError('refresh preserves one existing achievement ID')
    if operation != 'refresh' and set(targets) & set(original):
        raise ValueError('merge and split need new IDs; historical IDs are never reused')
    sources = {s['source_id']: s for s in pack.get('source_records', [])}
    for source in payload.get('source_records', []):
        if source['source_id'] in sources and source != sources[source['source_id']]:
            raise ValueError('new source versions need new source IDs')
        sources[source['source_id']] = source
    pack['source_records'] = list(sources.values())
    for aid in ids:
        if operation != 'refresh':
            original[aid]['evidence_status'] = 'declined'
            original[aid]['external_safe'] = False
            original[aid].setdefault('constraints', []).append('Replaced through reviewed ' + operation + ': ' + ', '.join(targets))
    for atom in atoms:
        atom['external_safe'] = False
        original[atom['id']] = atom
    pack['evidence_atoms'] = list(original.values())
    metadata = pack.setdefault('metadata', {})
    metadata['supersedes'] = str(local(current).relative_to(ROOT.resolve()))
    metadata.setdefault('evidence_maintenance', []).append({'operation': operation, 'from_ids': ids, 'to_ids': targets,
        'reason': reason, 'created': datetime.now(timezone.utc).isoformat()})
    # Dependent strengths stay attached to historical evidence and become stale.
    # Reinterpreting their support requires a separate explicit reassessment.
    validate_candidate(pack, destination)
    return write_new(destination, pack)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    h = sub.add_parser('health'); h.add_argument('--json', action='store_true'); h.add_argument('--output')
    hist = sub.add_parser('history'); hist.add_argument('id'); hist.add_argument('--output')
    maintenance = sub.add_parser('maintain'); maintenance.add_argument('operation', choices=('merge', 'split', 'refresh'))
    maintenance.add_argument('--input', required=True); maintenance.add_argument('--from', dest='ids', nargs='+', required=True)
    maintenance.add_argument('--reason', required=True); maintenance.add_argument('--output', required=True)
    backup = sub.add_parser('backup'); backup.add_argument('--output', required=True)
    restore = sub.add_parser('restore'); restore.add_argument('--input', required=True); restore.add_argument('--destination', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'health':
            state = health()
            text = json.dumps(state, indent=2) + '\n' if args.json else health_text(state)
            if args.output:
                dest = local(args.output)
                if dest.parent != local('outputs'):
                    raise ValueError('health reports belong in outputs')
                dest.parent.mkdir(parents=True, exist_ok=True); dest.write_text(text)
            print(text, end='')
            return 1 if state['errors'] else 0
        if args.command == 'history':
            state = history(args.id)
            if args.output:
                dest = local(args.output)
                if dest.parent != local('outputs'):
                    raise ValueError('private history pages belong in outputs')
                dest.parent.mkdir(parents=True, exist_ok=True); dest.write_text(history_html(state))
                print(dest)
            else:
                print(json.dumps(state, indent=2))
        elif args.command == 'maintain':
            print(maintain(args.operation, args.input, args.ids, args.reason, args.output))
        else:
            from workspace_backup import backup_workspace, restore_workspace
            print(backup_workspace(args.output) if args.command == 'backup' else restore_workspace(args.input, args.destination))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print('error: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
