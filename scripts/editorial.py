#!/usr/bin/env python3
"""Durable editorial context. Facts stay in the pack; outputs are projections.

All writes are explicit and create new files. No model, dependency, or live-data
mutation is needed to inspect, validate, shortlist, or detect stale context.
"""
import argparse
import json
import sys
from pathlib import Path

from current_pack import ROOT, resolve, sha256
from career_profile import digest, atoms_by_id, profile_state, source_errors, validate_profile, safe_strengths
import pack_io

def local(path):
    return pack_io.local(path, ROOT)

def read(path):
    return pack_io.read(path, ROOT)

def pin(path):
    return pack_io.pin(path, ROOT)

def pin_errors(record):
    return pack_io.pin_errors(record, ROOT)

def write_new(path, record):
    return pack_io.write_new(path, record, ROOT)


def role_pin_errors(brief, role_pin):
    """Pin exactly the role profile that the brief directs the writer to load."""
    role_id = brief.get('role_id')
    if not role_id:
        return ['role pin supplied for a brief without a role'] if role_pin else []
    expected = f'data/roles/{role_id}.json'
    if not role_pin or role_pin.get('path') != expected:
        return [f'brief requires role pin for {expected}']
    return pin_errors(role_pin)


def applies(decision, brief):
    scope = decision['scope']
    value = {'output': brief.get('output_id', brief['brief_id']), 'application': brief['application_id'],
             'role_family': brief.get('role_family'), 'person': 'person'}[scope['kind']]
    return scope['id'] == value


def decision_records(extra=None):
    records = []
    for path in sorted((ROOT / 'reviews' / 'decisions').glob('*.json')):
        record = read(path)
        from validate_records import load, walk
        schema = load('editorial-decision.schema.json')
        errors = []
        walk(record, schema, schema, str(path), errors)
        if errors:
            raise ValueError('; '.join(errors))
        records.append((path, record))
    if extra is not None:
        # A candidate outside the decisions directory must still be checked
        # against the graph that would exist after saving it.
        existing = [r for _, r in records if r['decision_id'] == extra['decision_id']]
        if existing and existing != [extra]:
            raise ValueError('decision_id already exists; use a new ID and supersedes')
        if not existing:
            records.append((Path('<candidate>'), extra))
    ids = [r['decision_id'] for _, r in records]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate decision_id')
    by_id = {r['decision_id']: r for _, r in records}
    for _, r in records:
        previous = r.get('supersedes')
        seen = {r['decision_id']}
        while previous:
            if previous in seen or previous not in by_id:
                raise ValueError('decision supersedes chain is missing or cyclic')
            seen.add(previous)
            old = by_id[previous]
            if old['scope'] != r['scope'] or old['subject'] != r['subject']:
                raise ValueError('superseding a decision cannot change its scope or subject')
            if old['made_by'] == 'user' and r['made_by'] != 'user':
                raise ValueError('system decision cannot supersede a user decision')
            previous = old.get('supersedes')
    superseded = {r['supersedes'] for _, r in records if r.get('supersedes')}
    return [(p, r) for p, r in records if r['decision_id'] not in superseded]


def applicable_decisions(brief):
    return [(p, r) for p, r in decision_records() if applies(r, brief)]


def decision_context(brief):
    return [pin(p) for p, _ in applicable_decisions(brief)]


def effective_decisions(brief):
    groups = {}
    specificity = {'person': 0, 'role_family': 1, 'application': 2, 'output': 3}
    for _, r in applicable_decisions(brief):
        if r['action'] == 'retract':
            continue
        key = (r['subject']['kind'], r['subject']['id'])
        priority = (r['made_by'] == 'user', specificity[r['scope']['kind']])
        groups.setdefault(key, []).append((priority, r))
    result = {}
    for key, rows in groups.items():
        highest = max(priority for priority, _ in rows)
        winners = [r for priority, r in rows if priority == highest]
        if len({r['action'] for r in winners}) > 1:
            raise ValueError(f'conflicting decisions for {key}; record an explicit supersession')
        result[key] = winners[0]['action']
    return result


def validate_record(kind, record, path=None):
    errors, warnings = [], []
    pack_path = resolve()
    pack = read(pack_path) if pack_path else {'evidence_atoms': []}
    if kind == 'selection':
        for p in [record['pack'], record['brief']] + record.get('decisions', []) + ([record['role']] if record.get('role') else []):
            errors.extend(pin_errors(p))
        if errors:
            return errors, warnings
        pack = read(record['pack']['path'])
        brief = read(record['brief']['path'])
        errors.extend(role_pin_errors(brief, record.get('role')))
        if record.get('supersedes'):
            errors.extend(pin_errors(record['supersedes']))
        ids = set(atoms_by_id(pack))
        from select_evidence import eligible
        eligible_ids = {a['id'] for a in pack['evidence_atoms'] if eligible(a)[0]}
        if not set(record['candidate_ids']) <= eligible_ids:
            errors.append('selection candidates include unknown or ineligible evidence')
        chosen = [r['evidence_id'] for r in record['recommendations']]
        if len(chosen) != len(set(chosen)):
            errors.append('duplicate recommendation')
        if set(chosen) != set(record['candidate_ids']):
            errors.append('every candidate needs exactly one recommendation or omission')
        for r in record['recommendations']:
            if not set(r['replaces']) <= set(record['candidate_ids']) - {r['evidence_id']}:
                errors.append('replacement references must name other candidates')
        errors.extend(source_errors(record['review_source_refs'], pack, record['review_status'] == 'accepted'))
        if pack_path and sha256(pack_path) != record['pack']['sha256']:
            warnings.append('selection uses an older pack; prepare a new selection before generation')
        try:
            if decision_context(brief) != record['decisions']:
                warnings.append('selection decisions changed; prepare a new selection')
        except ValueError as exc:
            errors.append(str(exc))
    elif kind == 'brief':
        for field, available in (
            ('strength_ids', {s['id'] for s in pack.get('strengths_profile', [])}),
            ('preference_ids', {s['id'] for s in pack.get('positioning_preferences', [])}),
            ('priority_evidence_ids', set(atoms_by_id(pack)))):
            if not set(record[field]) <= available:
                errors.append(f'{field} contains unknown references')
        if record['format'] == 'interview_brief' and record['audience'] != 'private':
            errors.append('interview briefs must be private')
        if record.get('role_id') and not (ROOT / 'data' / 'roles' / (record['role_id'] + '.json')).is_file():
            errors.append('brief role_id does not resolve')
        if record.get('supersedes'):
            errors.extend(pin_errors(record['supersedes']))
    elif kind == 'decision':
        target = record['subject']
        available = {'atom': set(atoms_by_id(pack)),
                     'strength': {s['id'] for s in pack.get('strengths_profile', [])},
                     'preference': {s['id'] for s in pack.get('positioning_preferences', [])}}
        if target['id'] not in available[target['kind']]:
            errors.append('decision subject does not resolve in current pack')
        if record['scope']['kind'] == 'person' and record['scope']['id'] != 'person':
            errors.append('person scope id must be person')
        if record['scope']['kind'] != 'person':
            field = {'output': 'brief_id', 'application': 'application_id', 'role_family': 'role_family'}[record['scope']['kind']]
            briefs = [read(p) for p in (ROOT / 'data/briefs').glob('*.json')]
            if not any((b.get('output_id', b.get('brief_id')) if field == 'brief_id' else b.get(field)) == record['scope']['id'] for b in briefs):
                errors.append('decision scope does not resolve to a saved brief; create the brief first')
        errors.extend(source_errors(record['source_refs'], pack, record['made_by'] == 'user'))
        try:
            decision_records(extra=record)
        except ValueError as exc:
            errors.append(str(exc))
    elif kind == 'representation':
        from manifest import editorial_staleness
        errors.extend(editorial_staleness(record['run']))
        if errors:
            return errors, warnings
        artifact = local(record['artifact'])
        if not artifact.exists():
            errors.append('representation artifact does not exist')
            return errors, warnings
        if sha256(artifact) != record['run'].get('artifact_sha256'):
            errors.append('representation is stale: artifact changed')
        run = record['run']
        if not run.get('editorial_inputs'):
            errors.append('representation needs pinned editorial inputs')
            return errors, warnings
        brief = read(run['editorial_inputs']['brief']['path'])
        pack = read(run['pack'])
        rows = record['strengths']
        if len({r['strength_id'] for r in rows}) != len(rows) or {r['strength_id'] for r in rows} != set(brief['strength_ids']):
            errors.append('representation must account for every intended strength exactly once')
        strengths = {s['id']: s for s in pack.get('strengths_profile', [])}
        md = artifact.read_text()
        from quantities import CITATION
        import re
        cited = set(re.findall(r'E_[A-Z0-9_]+', ' '.join(m.group(0) for m in CITATION.finditer(md))))
        for row in rows:
            support = set(strengths.get(row['strength_id'], {}).get('evidence_ids', []))
            if not set(row['evidence_ids']) <= support:
                errors.append('representation cites evidence outside the strength support')
            if row['status'] == 'clearly_represented':
                if brief['audience'] != 'private' and row['strength_id'] not in {s['id'] for s in safe_strengths(pack)}:
                    errors.append('clearly represented external strength is not eligible')
                if not row['evidence_ids'] or not set(row['evidence_ids']) <= cited:
                    errors.append('clearly represented strength needs cited supporting evidence')
                if not row['artifact_excerpt'] or row['artifact_excerpt'] not in md:
                    errors.append('representation excerpt is absent from the artifact')
            if row['status'] == 'inadequately_represented':
                warnings.append(f"{row['strength_id']}: inadequately represented; revise or document omission")
            if row['status'] == 'intentionally_omitted':
                actions = effective_decisions(brief)
                if actions.get(('strength', row['strength_id'])) != 'omit':
                    errors.append('intentional omission needs an applicable saved strength omission decision')
    return errors, warnings


def checked(path, kind):
    from validate_records import load, walk
    names = {'brief': 'output-brief', 'selection': 'selection-record', 'decision': 'editorial-decision'}
    record = read(path)
    schema = load(names[kind] + '.schema.json')
    errors = []
    walk(record, schema, schema, '', errors)
    if not errors:
        errors, _ = validate_record(kind, record, local(path))
    if errors:
        raise ValueError('; '.join(errors))
    return record


def context_for(pack, brief):
    """Only safe interpretations and explicit IDs reach a writing context."""
    actions = effective_decisions(brief)
    strengths = [s for s in safe_strengths(pack) if s['id'] in brief['strength_ids']
                 and actions.get(('strength', s['id'])) not in ('omit', 'reserve')]
    preferences = [{k: p[k] for k in ('id', 'kind', 'text')} for p in pack.get('positioning_preferences', [])
                   if p['id'] in brief['preference_ids'] and p['status'] == 'active'
                   and p.get('external_safe') is True
                   and actions.get(('preference', p['id'])) != 'omit']
    return {'brief_id': brief['brief_id'], 'format': brief['format'], 'length': brief['length'],
            'instructions': brief['instructions'] if brief['external_safe'] else '',
            'strengths': strengths, 'preferences': preferences}


def prepare(brief_path, selection_id, limit=12):
    from select_evidence import view, load_role
    brief = checked(brief_path, 'brief')
    pack_path = resolve()
    if not pack_path:
        raise ValueError('no career pack')
    pack = read(pack_path)
    for path, _ in applicable_decisions(brief):
        checked(path, 'decision')
    actions = effective_decisions(brief)
    profile = load_role(brief['role_id']) if brief['role_id'] else None
    # Retrieve before truncation: strength support must never disappear because
    # the job description did not happen to use its vocabulary.
    all_view = view(pack, audience='public' if brief['audience'] == 'public' else 'named_recipient',
                    profile=profile, limit=max(len(pack['evidence_atoms']), 1))
    available = {a['id']: a for a in all_view['atoms']}
    priority = set(brief['priority_evidence_ids'])
    contributions = {}
    for s in safe_strengths(pack):
        if s['id'] in brief['strength_ids'] and actions.get(('strength', s['id'])) != 'omit':
            priority.update(s['evidence_ids'])
            for aid in s['evidence_ids']:
                contributions.setdefault(aid, []).append(s['id'])
    priority.update(sid for (kind, sid), action in actions.items() if kind == 'atom' and action == 'include')
    candidate_ids = [a['id'] for a in all_view['atoms'][:limit]]
    candidate_ids += sorted((priority & available.keys()) - set(candidate_ids))
    recommendations = []
    for aid in candidate_ids:
        action = actions.get(('atom', aid))
        disposition = {'omit': 'omit', 'reserve': 'reserve'}.get(action, 'recommended')
        reasons = available[aid].get('why_selected', [])
        contribution = ('Supports intended strengths: ' + ', '.join(contributions[aid])
                        if aid in contributions else 'Candidate for role coverage; assess distinct contribution during editorial review.')
        recommendations.append({'evidence_id': aid, 'disposition': disposition,
                                'reason': 'Recorded selection decision.' if action else '; '.join(reasons) or 'Eligible career evidence.',
                                'contribution': contribution, 'limitations': available[aid].get('constraints', []), 'replaces': []})
    record = {'selection_id': selection_id, 'pack': pin(pack_path), 'brief': pin(brief_path),
              'decisions': decision_context(brief), 'candidate_ids': candidate_ids,
              'recommendations': recommendations, 'created_by': 'system',
              'review_status': 'proposed', 'review_source_refs': []}
    record['unavailable_priorities'] = sorted(priority - available.keys())
    safe_ids = {s['id'] for s in safe_strengths(pack)}
    record['strength_readiness'] = []
    for s in pack.get('strengths_profile', []):
        if s['id'] in brief['strength_ids']:
            state = profile_state(s, pack)
            record['strength_readiness'].append({'strength_id': s['id'],
                'state': 'available' if s['id'] in safe_ids else state if state in ('stale', 'rejected', 'unsupported') else 'withheld'})
    if profile:
        record['role'] = pin(ROOT / 'data' / 'roles' / (brief['role_id'] + '.json'))
    return record


def generation_view(selection_path):
    from select_evidence import view, load_role
    selection = checked(selection_path, 'selection')
    _, warnings = validate_record('selection', selection)
    if warnings:
        raise ValueError('; '.join(warnings))
    pack = read(selection['pack']['path'])
    brief = checked(selection['brief']['path'], 'brief')
    if brief['audience'] == 'private':
        raise ValueError('private interview preparation reads the pack; it is not a sendable selection view')
    profile = load_role(brief['role_id']) if brief['role_id'] else None
    result = view(pack, audience=brief['audience'], profile=profile, limit=max(len(pack['evidence_atoms']), 1))
    ordered_ids = [r['evidence_id'] for r in selection['recommendations'] if r['disposition'] == 'recommended']
    wanted = set(ordered_ids)
    actions = effective_decisions(brief)
    for (kind, sid), action in actions.items():
        if kind == 'atom' and ((action == 'include' and sid not in wanted and sid in {a['id'] for a in result['atoms']})
                               or (action in ('omit', 'reserve') and sid in wanted)):
            raise ValueError(f'selection contradicts applicable decision for {sid}')
    available = {a['id']: a for a in result['atoms']}
    result['atoms'] = [available[aid] for aid in ordered_ids]
    result['not_shortlisted'] = []
    result['summary']['eligible'] = len(result['atoms'])
    result['summary']['by_outcome'] = {k: sum(a['outcome_type'] == k for a in result['atoms'])
                                     for k in ('business_outcome', 'output', 'activity')}
    result['summary']['with_corroborator'] = sum(a['has_corroborator'] for a in result['atoms'])
    result['editorial'] = context_for(pack, brief)
    # Interpretations with evidence outside this selection stay in the private
    # representation review, not the generation view.
    result['editorial']['strengths'] = [s for s in result['editorial']['strengths'] if set(s['evidence_ids']) <= wanted]
    for req in result['requirement_coverage']:
        from select_evidence import linked_ids
        original = next(r for r in profile['requirements'] if r['text'] == req['text'])
        if req['status'] == 'covered' and not set(linked_ids(original)) & wanted:
            req['status'] = 'omitted'
    result['source'] = selection['pack']
    return result


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("status", "migrate", "bind-strength", "export"):
        from career_core import main as core_main
        return core_main(argv)
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                     epilog="Core commands status, migrate, bind-strength and export are provided by career_core.py; old invocations still work.")
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init-brief')
    init.add_argument('--id', required=True)
    init.add_argument('--application', required=True)
    init.add_argument('--output-id', help='stable logical output ID across brief revisions; defaults to --id')
    init.add_argument('--role')
    init.add_argument('--role-family')
    init.add_argument('--format', default='resume')
    init.add_argument('--audience', default='named_recipient')
    init.add_argument('--length', default='two A4 pages')
    init.add_argument('--strength', action='append', default=[])
    init.add_argument('--preference', action='append', default=[])
    init.add_argument('--output', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--brief', required=True)
    prep.add_argument('--id', required=True)
    prep.add_argument('--limit', type=int, default=12)
    prep.add_argument('--output', required=True)
    save = sub.add_parser('save', help='validate a candidate record and save a new immutable version')
    save.add_argument('--kind', choices=('brief', 'decision', 'selection'), required=True)
    save.add_argument('--input', required=True)
    save.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'init-brief':
            record = {'brief_id': args.id, 'output_id': args.output_id or args.id,
                      'application_id': args.application, 'role_id': args.role,
                      'role_family': args.role_family, 'format': args.format, 'audience': args.audience,
                      'length': args.length, 'strength_ids': args.strength, 'preference_ids': args.preference,
                      'priority_evidence_ids': [], 'instructions': '', 'external_safe': False, 'created_by': 'system'}
        elif args.command == 'prepare':
            if args.limit < 1:
                raise ValueError('limit must be positive')
            record = prepare(args.brief, args.id, args.limit)
        else:
            record = checked(args.input, args.kind)
        # Validate before writing; a failed save must not poison the workspace.
        from validate_records import load, walk
        kind = {'init-brief': 'brief', 'prepare': 'selection', 'save': getattr(args, 'kind', None)}.get(args.command)
        if kind:
            schema = load({'brief': 'output-brief', 'selection': 'selection-record', 'decision': 'editorial-decision'}[kind] + '.schema.json')
            errors = []
            walk(record, schema, schema, '', errors)
            if not errors:
                errors, _ = validate_record(kind, record)
            if errors:
                raise ValueError('; '.join(errors))
            folder, id_field = {'brief': ('data/briefs', 'brief_id'),
                                'selection': ('data/selections', 'selection_id'),
                                'decision': ('reviews/decisions', 'decision_id')}[kind]
            if local(args.output).parent != local(folder):
                raise ValueError(f'{kind} records must be saved directly in {folder}')
            for old in local(folder).glob('*.json'):
                if read(old).get(id_field) == record[id_field]:
                    raise ValueError(f'{id_field} already exists; save a new ID and explicit supersedes')
        written = write_new(args.output, record)
        print(written.relative_to(ROOT.resolve()))
        return 0
    except (ValueError, KeyError, OSError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
