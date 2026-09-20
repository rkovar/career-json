"""Career review operations shared by conversation and the local review page.

The existing pack review contract remains the authority for factual acceptance.
This module coordinates corrections, exact-state saves and the reading view.
"""
import copy
from datetime import date
import json
from pathlib import Path
import re
import uuid

import pack_review as review
from career_profile import digest
from pack_io import local, pin, pin_errors, read, write_new, write_view, workspace_lock

SOURCE_FIELDS = {'source_id', 'source_type', 'path', 'sha256', 'character_count', 'byte_size',
                 'extraction_method', 'retrieved', 'independent', 'saved_copy', 'saved_sha256'}


def source_annotations(proposed, base):
    """Separate new import commentary from verifiable source metadata.

    Existing sources and judgments of independence retain their exact review path.
    Unknown fields never become auto-registered authority.
    """
    old = {s['source_id'] for s in base.get('source_records', [])}
    annotations = {}
    for source in proposed.get('source_records', []):
        if (source['source_id'] not in old and source.get('independent') is False
                and not set(source) - SOURCE_FIELDS - {'notes'} and 'notes' in source):
            annotations[source['source_id']] = {'notes': source.pop('notes'), 'authority': 'import_commentary'}
    return annotations


def registered_sources(proposed, base):
    """New, locally verifiable citation metadata; never a person's approval."""
    old = review.units(base)
    result = {}
    for source in proposed.get('source_records', []):
        key = 'source_records/' + source['source_id']
        if (key in old and old[key] != source) or set(source) - SOURCE_FIELDS or source.get('independent') is not False:
            continue
        target = source.get('saved_copy') if source['source_type'] == 'url' else source['path']
        if not target:
            continue
        try:
            path = local(target)
            if not path.is_file():
                continue
            expected = source.get('saved_sha256') if source['source_type'] == 'url' else source.get('sha256')
            actual = pin(path)
            if expected and expected != actual['sha256']:
                continue
            if source['source_type'] not in ('person', 'url') and not expected:
                continue
            result[key] = actual
        except (ValueError, OSError):
            continue
    return result


def state_token(state):
    current = review.resolve()
    return digest({'session': state['session'], 'current': pin(current) if current else None,
                   'decisions': review.decisions(local('reviews/pack-reviews/' + state['session']['review_id'] + '/session.json'))})


def check_token(session, expected):
    if not expected or state_token(review.status(session)) != expected:
        raise ValueError('Your career record or review changed. Reload this page before saving; your choices have not been applied.')


def reading_page():
    from career_page import build
    current = review.resolve()
    if current is None:
        return None
    path = local('outputs/career-record.html')
    marker = '<!-- career-pack-sha256: ' + pin(current)['sha256'] + ' -->\n'
    write_view(path, marker + build(read(current), str(local(current).relative_to(review.ROOT.resolve()))))
    return str(path.relative_to(review.ROOT.resolve()))


def save(session, payload, expected=None, output=None):
    """Record actual choices, commit supported facts, and report both outcomes."""
    with workspace_lock():
        if expected is not None:
            check_token(session, expected)
        review._record(session, payload)
        saved, blocked = None, None
        output = output or 'data/packs/career-' + uuid.uuid4().hex[:12] + '.json'
        try:
            saved = review._publish(session, output)
        except ValueError as exc:
            if not str(exc).startswith('no new accepted changes or privacy restrictions'):
                blocked = str(exc)
        state = review.status(session)
        waiting = [row['key'] for row in state['items'] if row.get('decision', {}).get('action') == 'accept'
                   and row['review_status'] != 'accepted' and not row.get('source_registration')]
        if saved and waiting:
            blocked = 'Some selections still need their supporting records reviewed: ' + ', '.join(waiting)
        state['saved_pack'] = str(saved.relative_to(review.ROOT.resolve())) if saved else None
        state['save_blocked'] = blocked
        state['reading_page'] = None
        state['reading_page_error'] = None
        if saved:
            try:
                state['reading_page'] = reading_page()
            except (ValueError, OSError, KeyError) as exc:
                # Facts are already durable. Never imply they failed to save because a view failed.
                state['reading_page_error'] = str(exc)
        state['state_token'] = state_token(state)
        state['message'] = ('Saved to your career pack.' if saved else
                            'Review decisions saved. No career facts changed.')
        return state


def revise(session, candidate, review_id):
    """Rebase a corrected proposal while retaining exact unchanged decisions."""
    with workspace_lock():
        return _revise(session, candidate, review_id)


def revise_changes(session, changes_path, review_id):
    """Apply record fields to a pinned proposal, then use ordinary review staging.

    Fields replace their top-level value (including complete arrays/STAR objects).
    Omitted fields and records survive unchanged; metadata/receipts are not edits.
    """
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', review_id):
        raise ValueError('review id must use letters, numbers, hyphens or underscores')
    changes = read(changes_path)
    if not isinstance(changes, dict) or not changes:
        raise ValueError('Changes must map collection/ID keys to nonempty field objects.')
    with workspace_lock():
        _, proposed, _ = review.load_session(session)
        candidate = copy.deepcopy(proposed)
        items = review.units(candidate)
        changed = False
        for key, fields in changes.items():
            group, slash, ident = key.partition('/')
            id_field = review.COLLECTIONS.get(group)
            if not slash or not ident or '/' in ident or not id_field:
                raise ValueError('Change a named collection record, not metadata or approval receipts: ' + key)
            if not isinstance(fields, dict) or not fields:
                raise ValueError('Each record change needs nonempty fields: ' + key)
            if id_field in fields and fields[id_field] != ident:
                raise ValueError('Record ID must match its change key: ' + key)
            previous = items.get(key)
            value = copy.deepcopy(previous) if previous is not None else {id_field: ident}
            value.update(fields)
            if value == previous:
                continue
            if 'external_safe' in value:
                value['external_safe'] = False
            if group == 'strengths_profile' and value.get('status') == 'confirmed':
                value['status'] = 'proposed'
            if value == previous:
                continue
            if previous is None:
                candidate.setdefault(group, []).append(value)
            else:
                candidate[group] = [value if row[id_field] == ident else row for row in candidate[group]]
            changed = True
        if not changed:
            raise ValueError('No content changed; resume the existing review.')
        destination = local('data/candidates/' + review_id + '.json')
        if destination.exists() or local('reviews/pack-reviews/' + review_id).exists():
            raise ValueError('Review or candidate already exists; resume it or choose a new id.')
        review.validate_pack_object(candidate)
        write_new(destination, candidate)
        return _revise(session, destination, review_id)


def _revise(session, candidate, review_id):
    previous, previous_pack, _ = review.load_session(session)
    path = review._start(candidate, review_id, grouped=True)
    record = read(path)
    # Import commentary lives beside the proposal. Loading that proposal for a
    # small update must not silently discard notes about unchanged sources.
    old_sources = {s['source_id']: s for s in previous_pack.get('source_records', [])}
    new_sources = {s['source_id']: s for s in read(record['proposal']['path']).get('source_records', [])}
    for sid, annotation in previous.get('source_annotations', {}).items():
        if sid in new_sources and old_sources.get(sid) == new_sources[sid]:
            record.setdefault('source_annotations', {}).setdefault(sid, annotation)
    record['previous_review'] = pin(session)
    # _start just created this session under the same exclusive lock. Publish the
    # completed header atomically before exposing it to callers.
    temporary = path.with_suffix('.pending')
    try:
        temporary.write_text(json.dumps(record, indent=2) + '\n')
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return path


def editable_fields(key, value):
    if key.startswith('evidence_atoms/'):
        return {'title': value.get('title', ''), **{'star.' + field: (value.get('star') or {}).get(field, '')
                for field in ('situation', 'task', 'action', 'result')}}
    if key.startswith('employment/'):
        return {field: value.get(field) for field in ('employer', 'title', 'start', 'end')}
    return {}


def correct(session, payload, edits, expected=None):
    """Stage literal user edits as a new sourced proposal. Never accepts them."""
    if not isinstance(edits, list) or not edits:
        raise ValueError('Supply at least one edited item.')
    with workspace_lock():
        if expected is not None:
            check_token(session, expected)
        _, proposed, _ = review.load_session(session)
        candidate = copy.deepcopy(proposed)
        items = review.units(candidate)
        changed, seen = [], set()
        for edit in edits:
            if not isinstance(edit, dict) or set(edit) != {'key', 'fingerprint', 'fields'}:
                raise ValueError('Each edit needs its item, exact fingerprint and changed fields.')
            key = edit['key']
            if key in seen or key not in items or edit['fingerprint'] != review.fingerprint(key, proposed):
                raise ValueError('Edited content changed or was repeated. Reload the proposal.')
            seen.add(key)
            fields = edit['fields']
            allowed = editable_fields(key, items[key])
            if not isinstance(fields, dict) or not fields or not set(fields) <= set(allowed):
                raise ValueError('Edit only the displayed achievement wording or role details.')
            if any(not isinstance(v, str) and not (v is None and k in ('start', 'end')) for k, v in fields.items()):
                raise ValueError('Edited wording must be text; unknown dates may be null.')
            difference = {k: v for k, v in fields.items() if v != allowed[k]}
            if not difference:
                continue
            value = copy.deepcopy(items[key])
            for field, content in difference.items():
                if field.startswith('star.'):
                    value.setdefault('star', {})[field.split('.', 1)[1]] = content
                else:
                    value[field] = content
            if 'evidence_status' in value and value['evidence_status'] in ('corroborated', 'externally_verified'):
                value['evidence_status'] = 'self_asserted'
            if 'external_safe' in value:
                value['external_safe'] = False
            changed.append((key, value, difference))
        if not changed:
            raise ValueError('No wording changed. Your current proposal is still available.')
        # Validate choices before creating any correction source; the operator must
        # supply the person's name and actual choices, never inferred approvals.
        review._record(session, payload, dry_run=True)
        suffix = uuid.uuid4().hex[:12]
        answer_path = 'reviews/answers/correction-' + suffix + '.json'
        sid = 'SRC_CORRECTION_' + suffix.upper()
        answer = {'reviewed_by': payload['reviewed_by'], 'on': str(date.today()),
                  'question': 'What exact wording should replace the recorded career details?',
                  'answers': [{'item': key, 'fields': changes} for key, _, changes in changed]}
        source = {'source_id': sid, 'source_type': 'person', 'path': answer_path,
                  'retrieved': str(date.today()), 'independent': False}
        candidate.setdefault('source_records', []).append(source)
        for key, value, changes in changed:
            value.setdefault('source_refs', []).extend({'source_id': sid, 'excerpt': json.dumps({field: content}, ensure_ascii=False)}
                                                       for field, content in changes.items())
            review.put_unit(candidate, key, value, True)
        # An accept click beside an edited field cannot approve the old wording.
        # The new proposal deliberately needs a fresh choice after its preview.
        payload = copy.deepcopy(payload)
        payload['decisions'] = [row for row in payload['decisions']
                                if row['action'] != 'accept'
                                or review.fingerprint(row['key'], candidate) == row['fingerprint']]
        current = review.resolve()
        if current:
            candidate.setdefault('metadata', {})['supersedes'] = str(local(current).relative_to(review.ROOT.resolve()))
        candidate_path = 'data/candidates/correction-' + suffix + '.json'
        created = []
        try:
            created.append(write_new(answer_path, answer))
            review.validate_pack_object(candidate)
            created.append(write_new(candidate_path, candidate))
            review._record(session, payload)
            return _revise(session, candidate_path, 'correction-' + suffix)
        except BaseException:
            for path in reversed(created):
                path.unlink(missing_ok=True)
            raise
