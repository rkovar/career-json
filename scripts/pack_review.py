#!/usr/bin/env python3
"""Stage career changes, record human decisions and publish only accepted content."""
import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

from current_pack import ROOT, resolve, sha256
from career_profile import digest
from pack_io import local, read, pin, pin_errors, write_new
from schema_tools import walk

COLLECTIONS = {'evidence_atoms': 'id', 'employment': 'employment_id', 'education': 'education_id',
               'source_records': 'source_id', 'strengths_profile': 'id', 'positioning_preferences': 'id'}
ACTIONS = ('accept', 'correct', 'unsure', 'later')
PUBLICATION = ('unchanged', 'private', 'external')
PROMPTS = ('What important work is missing?', 'Where does this understate your contribution?',
           'Which achievement are you proudest of?', 'Does this record reflect the work you actually did?')


def now():
    return datetime.now(timezone.utc).isoformat()


def units(pack):
    result = {}
    for field, value in pack.items():
        if field == 'schema_version':
            continue
        if field == 'metadata':
            value = {k: v for k, v in value.items() if k not in ('supersedes', 'human_review')}
            if not value:
                continue
        if field in COLLECTIONS:
            for row in value:
                key = field + '/' + row[COLLECTIONS[field]]
                if key in result:
                    raise ValueError('duplicate review item: ' + key)
                result[key] = row
        else:
            result['field/' + field] = value
    return result


def dependencies(key, pack):
    """Snapshot source records and cited support, not just polished claim text."""
    items = units(pack)
    value = items.get(key)
    refs = {}
    if isinstance(value, dict):
        for ref in value.get('source_refs', []):
            sid = 'source_records/' + ref['source_id']
            refs[sid] = items.get(sid)
        for aid in value.get('evidence_ids', []):
            atom_key = 'evidence_atoms/' + aid
            refs[atom_key] = items.get(atom_key)
            refs.update(dependencies(atom_key, pack))
        if value.get('employment_id') and not key.startswith('employment/'):
            eid = 'employment/' + value['employment_id']
            refs[eid] = items.get(eid)
    for dep_key, dep_value in list(refs.items()):
        if isinstance(dep_value, dict):
            refs[dep_key] = {k: v for k, v in dep_value.items() if k not in ('external_safe', 'evidence_status')}
    return refs


def fingerprint(key, pack):
    value = copy.deepcopy(units(pack).get(key))
    # Wording review cannot authorize publication or raise evidence confidence.
    if isinstance(value, dict):
        value.pop('external_safe', None)
        value.pop('evidence_status', None)
    return digest({'key': key, 'present': key in units(pack), 'value': value,
                   'dependencies': dependencies(key, pack)})


def records(pack):
    review = (pack.get('metadata') or {}).get('human_review') or {}
    return review.get('items', {})


def review_status(key, pack):
    receipt = records(pack).get(key)
    if receipt and receipt.get('fingerprint') == fingerprint(key, pack) and receipt.get('batch') and not pin_errors(receipt['batch']):
        return 'accepted'
    return 'changed_since_review' if receipt else 'not_reviewed'


def validate_pack_object(pack, allow_schema_errors=False):
    # Structural validator also checks source references and strength support.
    from career_core import validate_candidate
    import tempfile
    with tempfile.TemporaryDirectory(prefix='career-review-validation-', dir=ROOT) as folder:
        validate_candidate(pack, Path(folder) / 'candidate.json')
    schema_path = ROOT / 'schemas' / ('archive/career-1.3.schema.json' if pack.get('schema_version') == '1.3' else 'career.schema.json')
    schema = json.loads(schema_path.read_text())
    errors = []
    walk(pack, schema, schema, '', errors)
    if errors and not allow_schema_errors:
        raise ValueError('; '.join(errors))
    return errors


def start(candidate_path, review_id):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', review_id):
        raise ValueError('review id must use letters, numbers, hyphens or underscores')
    candidate_path = local(candidate_path)
    base_path = resolve()
    if local('data/packs') in candidate_path.parents and (base_path is None or candidate_path != local(base_path)):
        raise ValueError('stage proposed packs outside data/packs; that directory is for current/history only')
    proposed = read(candidate_path)
    warnings = validate_pack_object(proposed, allow_schema_errors=bool(base_path and candidate_path == local(base_path)))
    folder = local('reviews/pack-reviews/' + review_id)
    if folder.exists():
        raise ValueError('review id already exists; resume it or choose a new id')
    proposal = write_new(folder / 'proposal.json', proposed)
    session = {'review_id': review_id, 'created': now(), 'proposal': pin(proposal),
               'base': pin(base_path) if base_path else None, 'validation_warnings': warnings}
    return write_new(folder / 'session.json', session)


def load_session(path):
    path = local(path)
    session = read(path)
    if path != local('reviews/pack-reviews/' + session['review_id'] + '/session.json'):
        raise ValueError('review sessions must use their canonical private directory')
    errors = pin_errors(session['proposal'])
    if session['base']:
        errors.extend(pin_errors(session['base']))
    if errors:
        raise ValueError('; '.join(errors))
    return session, read(session['proposal']['path']), read(session['base']['path']) if session['base'] else {}


def change_rows(proposed, base):
    old, new = units(base), units(proposed)
    rows = []
    for key in sorted(set(old) | set(new)):
        before, after = old.get(key), new.get(key)
        change = 'added' if key not in old else 'removed' if key not in new else 'changed' if (
            before != after or fingerprint(key, base) != fingerprint(key, proposed)) else 'unchanged'
        rows.append({'key': key, 'change': change, 'before': before, 'after': after,
                     'fingerprint': fingerprint(key, proposed),
                     'review_status': review_status(key, base) if change == 'unchanged' else 'awaiting_review'})
    return rows


def batches(path):
    return sorted(local(path).parent.glob('decisions/*.json'))


def decisions(path):
    result = {}
    for batch_path in batches(path):
        batch = read(batch_path)
        for row in batch['decisions']:
            result[row['key']] = dict(row, reviewed_by=batch['reviewed_by'], recorded=batch['recorded'], batch=pin(batch_path))
    return result


def record(path, payload):
    session, proposed, base = load_session(path)
    schema = read('schemas/pack-review-decisions.schema.json')
    errors = []
    walk(payload, schema, schema, '', errors)
    if errors:
        raise ValueError('; '.join(errors))
    if payload['review_id'] != session['review_id'] or payload['proposal_sha256'] != session['proposal']['sha256']:
        raise ValueError('decisions do not belong to this exact proposal')
    keys = {row['key']: row for row in change_rows(proposed, base)}
    seen = set()
    for row in payload['decisions']:
        key = row['key']
        if key in seen or key not in keys:
            raise ValueError('duplicate or unknown review item: ' + key)
        seen.add(key)
        if row['fingerprint'] != keys[key]['fingerprint']:
            raise ValueError('reviewed content changed: ' + key)
        if row['action'] == 'correct' and not row['note'].strip():
            raise ValueError('a correction needs the person’s explanation')
        if row['publication'] != 'unchanged' and not (
            isinstance(keys[key]['after'] or keys[key]['before'], dict) and
            'external_safe' in (keys[key]['after'] or keys[key]['before'])):
            raise ValueError('this item has no publication permission: ' + key)
    if not payload['reviewed_by'].strip():
        raise ValueError('a reviewer name is required')
    for previous in batches(path)[-1:]:
        if {k:v for k,v in read(previous).items() if k != 'recorded'} == payload:
            return previous
    value = dict(payload, recorded=now())
    index = max([int(p.stem) for p in batches(path)] or [0]) + 1
    return write_new(local(path).parent / 'decisions' / f'{index:06d}.json', value)


def put_unit(pack, key, value, present):
    field, identifier = key.split('/', 1)
    if field == 'field':
        if present:
            pack[identifier] = copy.deepcopy(value)
        else:
            pack.pop(identifier, None)
        return
    rows = pack.setdefault(field, [])
    index = next((n for n, r in enumerate(rows) if r[COLLECTIONS[field]] == identifier), None)
    if not present:
        if index is not None:
            rows.pop(index)
    elif index is None:
        rows.append(copy.deepcopy(value))
    else:
        rows[index] = copy.deepcopy(value)


def publish(path, output):
    session, proposed, base = load_session(path)
    current = resolve()
    current_pin = pin(current) if current else None
    # Further batches can be committed to this same review after an earlier
    # partial commit; other pack changes require a fresh comparison.
    checkpoint = (read(current).get('metadata', {}).get('human_review', {}) if current else {})
    if current_pin != session['base'] and checkpoint.get('session') != pin(path):
        raise ValueError('current pack changed; start a new review against it')
    output = local(output)
    if output.parent != local('data/packs'):
        raise ValueError('accepted pack versions belong in data/packs')
    latest = read(current) if current else {}
    result = copy.deepcopy(latest)
    result['schema_version'] = proposed['schema_version']
    all_decisions = decisions(path)
    old_units, proposed_units = units(base), units(proposed)
    accepted = {}
    applied_before = checkpoint.get('applied_batches', []) if checkpoint.get('session') == pin(path) else []
    for batch in applied_before:
        if pin_errors(batch):
            raise ValueError('previously accepted decisions changed; restore the original review record')
    applied_keys = []
    for key, choice in all_decisions.items():
        if choice['batch'] in applied_before:
            continue
        if choice['fingerprint'] != fingerprint(key, proposed):
            raise ValueError('stale acceptance: ' + key)
        if choice['action'] == 'accept':
            present = key in proposed_units
            value = copy.deepcopy(proposed_units.get(key))
            if isinstance(value, dict) and 'evidence_status' in value:
                # Preserve or lower confidence. Wording acceptance is not
                # corroboration, irrespective of what a candidate claims.
                rank = {'declined': 0, 'unresolved': 1, 'self_asserted': 2, 'corroborated': 3, 'externally_verified': 4}
                prior = (old_units.get(key) or {}).get('evidence_status', 'self_asserted')
                if rank[value['evidence_status']] > rank[prior]:
                    value['evidence_status'] = prior
            if isinstance(value, dict) and 'external_safe' in value:
                unchanged = key in old_units and fingerprint(key, proposed) == fingerprint(key, base)
                value['external_safe'] = bool(unchanged and old_units[key].get('external_safe'))
                if choice['publication'] != 'unchanged':
                    value['external_safe'] = choice['publication'] == 'external'
            put_unit(result, key, value, present)
            accepted[key] = choice
            applied_keys.append(key)
        elif choice['publication'] == 'private' and key in units(result):
            value = copy.deepcopy(units(result)[key])
            value['external_safe'] = False
            put_unit(result, key, value, True)
            applied_keys.append(key)
        elif choice['publication'] == 'external':
            raise ValueError('external use requires acceptance of the exact proposed content')
    if not applied_keys:
        raise ValueError('no new accepted changes or privacy restrictions; review progress is already saved')
    # Never associate an accepted claim with different supporting records as a
    # side effect of partially accepting a batch.
    for key in accepted:
        if dependencies(key, proposed) != dependencies(key, result):
            raise ValueError('accept the supporting sources/roles/evidence in the same batch first: ' + key)
    for key in units(latest):
        if not key.startswith('strengths_profile/') and key in units(result) and key not in accepted and dependencies(key, latest) != dependencies(key, result):
            raise ValueError('support changed; review the affected item before accepting its source: ' + key)
    metadata = result.setdefault('metadata', {})
    if current:
        metadata['supersedes'] = str(local(current).relative_to(ROOT.resolve()))
    else:
        metadata.pop('supersedes', None)
    receipts = copy.deepcopy(records(latest))
    for key, choice in accepted.items():
        receipts[key] = {'fingerprint': fingerprint(key, result), 'reviewed_fingerprint': choice['fingerprint'],
                         'reviewed_by': choice['reviewed_by'], 'recorded': choice['recorded'], 'batch': choice['batch']}
    metadata['human_review'] = {'session': pin(path), 'items': receipts,
                                'applied_batches': [pin(p) for p in batches(path)], 'accepted_at': now()}
    validate_pack_object(result)
    return write_new(output, result)


def status(path):
    session, proposed, base = load_session(path)
    choices = decisions(path)
    rows = change_rows(proposed, base)
    current = resolve()
    checkpoint = (read(current).get('metadata', {}).get('human_review', {}) if current else {})
    applied = checkpoint.get('applied_batches', []) if checkpoint.get('session') == pin(path) else []
    for row in rows:
        if row['key'] in choices:
            choice = choices[row['key']]
            row['decision'] = choice
            if choice['action'] == 'accept' and choice['batch'] in applied:
                row['review_status'] = review_status(row['key'], read(current))
    feedback = [item for p in batches(path) for item in read(p)['omissions']]
    return {'session': session, 'items': rows, 'omissions': feedback}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    begin = commands.add_parser('start')
    begin.add_argument('--candidate', required=True)
    begin.add_argument('--id', required=True)
    for name in ('status', 'record', 'publish', 'render'):
        sub = commands.add_parser(name)
        sub.add_argument('--session', required=True)
        if name == 'record':
            sub.add_argument('--input', required=True, help='decisions explicitly supplied by the person; never infer approval')
        if name in ('publish', 'render'):
            sub.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'start':
            result = start(args.candidate, args.id)
        elif args.command == 'record':
            result = record(args.session, read(args.input))
        elif args.command == 'publish':
            result = publish(args.session, args.output)
        elif args.command == 'render':
            from review_html import render_review
            result = local(args.output)
            result.parent.mkdir(parents=True, exist_ok=True)
            result.write_text(render_review(status(args.session)), encoding='utf-8')
        else:
            print(json.dumps(status(args.session), indent=2))
            return 0
        print(str(result.relative_to(ROOT.resolve())))
        return 0
    except (ValueError, KeyError, OSError) as exc:
        print('error: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
