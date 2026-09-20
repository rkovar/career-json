"""Immutable, scoped career questions. Answers are evidence, never approval."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
import sys

from current_pack import ROOT
from pack_io import local, pin, pin_errors, read, write_new, workspace_lock

STATES = ('open', 'answered', 'deferred', 'declined', 'superseded')
KINDS = ('factual_ambiguity', 'factual_correction', 'enrichment', 'preference')


def identity(question, targets):
    value = json.dumps([' '.join(question.split()).casefold(), sorted(targets)], ensure_ascii=False)
    return 'q-' + hashlib.sha256(value.encode()).hexdigest()[:20]


def folder(identifier, root=ROOT):
    if not re.fullmatch(r'q-[a-f0-9]{20}', identifier):
        raise ValueError('invalid question id')
    return local('reviews/questions/' + identifier, root)


def load(identifier, revision=None, root=ROOT):
    paths = sorted(folder(identifier, root).glob('[0-9][0-9][0-9][0-9][0-9][0-9].json'))
    if not paths:
        raise ValueError('unknown question: ' + identifier)
    path = folder(identifier, root) / ('%06d.json' % revision) if revision else paths[-1]
    record = read(path, root)
    if (record.get('version') != 1 or record.get('id') != identifier or record.get('state') not in STATES
            or path.stem != '%06d' % record.get('revision', 0)):
        raise ValueError('invalid question revision: ' + str(path))
    if record.get('context', {}).get('pack'):
        errors = pin_errors(record['context']['pack'], root)
        if errors:
            raise ValueError('; '.join(errors))
    # A broken earlier revision is not hidden by a good latest file.
    cursor, expected = record, record['revision']
    while cursor.get('previous'):
        previous = cursor['previous']
        expected -= 1
        if previous.get('path') != str((folder(identifier, root) / ('%06d.json' % expected)).relative_to(root.resolve())):
            raise ValueError('invalid question history')
        errors = pin_errors(previous, root)
        if errors:
            raise ValueError('; '.join(errors))
        cursor = read(previous['path'], root)
    if expected != 1:
        raise ValueError('incomplete question history')
    return record, path


def catalogue(root=ROOT):
    rows = []
    for directory in sorted(local('reviews/questions', root).glob('q-*')):
        row, path = load(directory.name, root=root)
        rows.append(dict(row, record=pin(path, root)))
    return rows


def question_fields(payload, pack_path=None, root=ROOT):
    question, targets = payload.get('question'), payload.get('targets')
    if not isinstance(question, str) or not question.strip():
        raise ValueError('Supply the exact question.')
    if not isinstance(targets, list) or not targets or any(not isinstance(k, str) or not re.fullmatch(r'(?:evidence_atoms|employment|education|publications|strengths_profile|positioning_preferences|field)/[^/\s]+', k) for k in targets):
        raise ValueError('Supply affected record keys, including their group.')
    targets = sorted(set(targets))
    kind = payload.get('kind', 'factual_ambiguity')
    required = payload.get('required', kind.startswith('factual_'))
    if kind not in KINDS or type(required) is not bool or (kind in ('enrichment', 'preference') and required):
        raise ValueError('Choose a factual question or optional enrichment/preference.')
    if not isinstance(payload.get('reason', ''), str):
        raise ValueError('The question reason must be text.')
    context = {}
    if pack_path:
        from pack_review import units, fingerprint
        pack = read(pack_path, root)
        if any(k not in units(pack) for k in targets):
            raise ValueError('A question target is absent from the supplied proposal.')
        context = {'pack': pin(pack_path, root), 'fingerprints': {k: fingerprint(k, pack) for k in targets}}
    return question, targets, kind, required, context


def ask(payload, pack_path=None, root=ROOT):
    question, targets, kind, required, context = question_fields(payload, pack_path, root)
    identifier = identity(question, targets)
    with workspace_lock(root):
        if folder(identifier, root).exists():
            current, path = load(identifier, root=root)
            # Repeated prompting is not permission to reopen an answered question.
            return dict(current, record=pin(path, root))
        if pack_path:
            # Candidates may be edited later; preserve the exact displayed context.
            snapshot = write_new(folder(identifier, root) / 'context.json', read(pack_path, root), root)
            context['original_pack_path'] = context['pack']['path']
            context['pack'] = pin(snapshot, root)
        row = {'version': 1, 'id': identifier, 'revision': 1, 'previous': None,
               'question': question.strip(), 'targets': targets, 'kind': kind, 'required': required,
               'state': 'open', 'context': context, 'answer': None, 'by': None,
               'reason': payload.get('reason', ''), 'revisit_when': None,
               'recorded_at': datetime.now(timezone.utc).isoformat()}
        path = write_new(folder(identifier, root) / '000001.json', row, root)
        return dict(row, record=pin(path, root))


def respond(identifier, revision, state, answer=None, by=None, reason='', revisit_when=None, root=ROOT):
    if state not in STATES or not isinstance(by, str) or not by.strip():
        raise ValueError('Supply a valid state and the person who made the decision.')
    if state == 'answered' and (not isinstance(answer, str) or not answer.strip()):
        raise ValueError('An answered question needs the exact answer.')
    if state != 'answered' and answer is not None:
        raise ValueError('Only an answered revision may contain an answer.')
    if not isinstance(reason, str) or (revisit_when is not None and not isinstance(revisit_when, str)):
        raise ValueError('Reasons and revisit conditions must be text.')
    with workspace_lock(root):
        previous, path = load(identifier, root=root)
        if previous['revision'] != revision:
            raise ValueError('Question changed; read the current question before answering.')
        if state == 'open' and not reason.strip():
            raise ValueError('Reopening a question requires a reason; do not repeat settled questions.')
        row = {**previous, 'revision': revision + 1, 'previous': pin(path, root), 'state': state,
               'answer': answer, 'by': by.strip(), 'reason': reason, 'revisit_when': revisit_when,
               'recorded_at': datetime.now(timezone.utc).isoformat()}
        path = write_new(folder(identifier, root) / ('%06d.json' % row['revision']), row, root)
    result = dict(row, record=pin(path, root))
    if state == 'answered':
        sid = 'SRC_ANSWER_' + identifier[2:].upper() + '_R' + str(row['revision'])
        result['source_record'] = {'source_id': sid, 'source_type': 'person', 'path': result['record']['path'],
                                   'sha256': result['record']['sha256'], 'retrieved': row['recorded_at'][:10], 'independent': False}
        result['source_ref'] = {'source_id': sid, 'locator': 'Question ' + identifier + ', revision ' + str(row['revision']),
                                'excerpt': json.dumps(answer, ensure_ascii=False)}
    return result


def answer_scope_error(source, key, root=ROOT):
    """Normal person sources stay compatible; new answers have verifiable scope."""
    path = source.get('path', '')
    if not path.startswith('reviews/questions/'):
        return None
    try:
        target = local(path, root)
        row, canonical = load(target.parent.name, int(target.stem), root)
        if canonical != target or row['state'] != 'answered' or key not in row['targets']:
            return 'answer does not resolve a question about this record'
        if not source.get('sha256') or pin_errors({'path': path, 'sha256': source['sha256']}, root):
            return 'answer revision is unpinned or changed'
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return 'invalid scoped answer: ' + str(exc)
    return None


def target_key(subject, pack):
    groups = {'evidence_atoms': 'id', 'employment': 'employment_id', 'education': 'education_id',
              'publications': 'publication_id', 'strengths_profile': 'id', 'positioning_preferences': 'id'}
    for group, field in groups.items():
        if any(r[field] == subject for r in pack.get(group, [])):
            return group + '/' + subject
    return 'field/' + str(subject or 'career')


def queue(pack, generated=(), optional=False, include_closed=False, root=ROOT):
    """Merge legacy derived questions with durable decisions without editing packs."""
    durable = {r['id']: r for r in catalogue(root)}
    rows = {}
    for original in generated:
        row = dict(original)
        targets = [target_key(row.get('subject'), pack)]
        identifier = identity(row['question'], targets)
        row.update(id=identifier, targets=targets, state='open', origin='legacy',
                   required=not row.get('optional', False))
        if re.search(r'\bdeferred by (?:the )?(?:subject|user)\b', row['question'], re.I):
            row['state'] = 'deferred'
        rows[identifier] = row
    for identifier, row in durable.items():
        # An explicit target/question match, not a generic subject-level 'yes'.
        rows[identifier] = {**row, 'subject': row['targets'][0].split('/', 1)[1], 'unlocks': 'recorded_question',
                            'optional': not row['required'], 'origin': 'recorded'}
    return sorted((r for r in rows.values() if (include_closed or r['state'] == 'open')
                   and (optional or r['required'])), key=lambda r: (not r['required'], r['id']))


def legacy_pair_present(raw, question, answer):
    """Decode JSON escapes and keep structured questions paired with their answers."""
    try:
        value = json.loads(raw)
    except ValueError:
        # Plain-text historical logs still require an explicit scope mapping.
        return question in raw and answer in raw

    def contains(node):
        if isinstance(node, dict):
            if node.get('question') == question and node.get('answer') == answer:
                return True
            return any(contains(child) for child in node.values())
        if isinstance(node, list):
            return any(contains(child) for child in node)
        return False

    return contains(value)


def import_answers(path, apply=False, root=ROOT):
    """Preview explicit mappings from a legacy ledger. Never guess target scope."""
    payload = read(path, root)
    entries = payload.get('answers') if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        raise ValueError('Import an answers list with explicit question, answer, targets, by and source pin.')
    result = []
    for entry in entries:
        try:
            if not isinstance(entry, dict):
                raise ValueError('each mapping must be an object')
            if any(not isinstance(entry.get(k), str) or not entry[k].strip() for k in ('question', 'answer', 'by')):
                raise ValueError('exact question, answer and author required')
            if pin_errors(entry['source'], root):
                raise ValueError('legacy source changed or missing')
            raw = local(entry['source']['path'], root).read_text()
            if not legacy_pair_present(raw, entry['question'], entry['answer']):
                raise ValueError('exact legacy question/answer is not present in the pinned source')
            if not entry.get('by') or not entry.get('targets'):
                raise ValueError('explicit author and target mapping required')
            row = {'question': entry['question'], 'targets': entry['targets'], 'kind': entry.get('kind', 'factual_ambiguity'),
                   'required': entry.get('required', entry.get('kind', 'factual_ambiguity').startswith('factual_')), 'reason': 'Imported from ' + json.dumps(entry['source'])}
            question_fields(row, entry.get('pack'), root)
            identifier = identity(row['question'], row['targets'])
            def check_existing(current):
                if current['state'] != 'open' and not (current['state'] == 'answered' and current['answer'] == entry['answer']):
                    raise ValueError('Question already has a different answer or decision. Review its current revision and context before recording the supplied change with respond.')
            if folder(identifier, root).exists():
                check_existing(load(identifier, root=root)[0])
            if apply:
                created = ask(row, entry.get('pack'), root)
                check_existing(created)
                if created['state'] == 'open':
                    respond(created['id'], created['revision'], 'answered', entry['answer'], entry['by'], row['reason'], root=root)
            result.append({'id': identifier, 'status': 'imported' if apply else 'ready'})
        except (KeyError, ValueError, OSError, TypeError, AttributeError) as exc:
            result.append({'status': 'needs_mapping', 'reason': str(exc)})
    return {'applied': apply, 'entries': result}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    a = sub.add_parser('ask'); a.add_argument('--input', required=True); a.add_argument('--pack')
    a = sub.add_parser('respond'); a.add_argument('--id', required=True); a.add_argument('--revision', required=True, type=int)
    a.add_argument('--state', required=True, choices=STATES); a.add_argument('--answer'); a.add_argument('--by', required=True)
    a.add_argument('--reason', default=''); a.add_argument('--revisit-when')
    a = sub.add_parser('list'); a.add_argument('--all', action='store_true')
    a = sub.add_parser('import'); a.add_argument('--input', required=True); a.add_argument('--apply', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.command == 'ask': result = ask(read(args.input), args.pack)
        elif args.command == 'respond': result = respond(args.id, args.revision, args.state, args.answer, args.by, args.reason, args.revisit_when)
        elif args.command == 'import': result = import_answers(args.input, args.apply)
        else: result = [r for r in catalogue() if args.all or r['state'] == 'open']
        print(json.dumps(result, indent=2, ensure_ascii=False)); return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, 'questions: ' + str(exc) + '\n')


if __name__ == '__main__':
    sys.exit(main())
