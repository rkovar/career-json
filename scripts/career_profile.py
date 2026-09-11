"""Evidence-backed strengths and preferences, independent of output applications."""
import hashlib
import json

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False).encode()).hexdigest()


def atoms_by_id(pack):
    return {a['id']: a for a in pack.get('evidence_atoms', [])}


def profile_state(strength, pack):
    atoms = atoms_by_id(pack)
    ids = strength.get('evidence_ids', [])
    if not ids or any(i not in atoms for i in ids):
        return 'unsupported'
    if any(strength.get('evidence_fingerprints', {}).get(i) != digest(atoms[i]) for i in ids):
        return 'stale'
    return strength['status']


def source_errors(refs, pack, require_person=False):
    sources = {s['source_id']: s for s in pack.get('source_records', [])}
    errors = []
    for ref in refs:
        source = sources.get(ref['source_id'])
        if source is None:
            errors.append(f"unknown source {ref['source_id']}")
        elif require_person and source['source_type'] != 'person':
            errors.append(f"user confirmation needs a person source: {ref['source_id']}")
        if require_person and not ref.get('excerpt'):
            errors.append('user confirmation needs the recorded answer excerpt')
    if require_person and not refs:
        errors.append('user confirmation needs a recorded answer source')
    return errors


def validate_profile(pack):
    errors, warnings = [], []
    atoms = atoms_by_id(pack)
    all_ids = set()
    for item in pack.get('strengths_profile', []) + pack.get('positioning_preferences', []):
        sid = item['id']
        if sid in all_ids:
            errors.append(f'duplicate profile id: {sid}')
        all_ids.add(sid)
        is_strength = 'interpretation' in item
        errors.extend(source_errors(item['source_refs'], pack,
                                   not is_strength or item['status'] in ('confirmed', 'rejected')))
        if is_strength:
            if set(item['evidence_fingerprints']) != set(item['evidence_ids']):
                errors.append(f'{sid}: fingerprint keys must match evidence_ids')
            for aid in item['evidence_ids']:
                if aid not in atoms:
                    errors.append(f'{sid}: unknown evidence {aid}')
            if profile_state(item, pack) == 'stale':
                warnings.append(f'{sid}: supporting evidence changed; reassess before reuse')
            if item['basis'] == 'recurring_pattern' and len(item['evidence_ids']) < 2:
                errors.append(f'{sid}: a recurring pattern needs multiple achievements')
            if item['status'] == 'rejected' and item['question_status'] == 'open':
                errors.append(f'{sid}: rejected interpretations must close the question')
    return errors, warnings


def safe_strengths(pack):
    from evidence_rules import eligible
    atoms = atoms_by_id(pack)
    result = []
    for s in pack.get('strengths_profile', []):
        # Requiring ALL supporting atoms prevents a private inference being
        # laundered through one harmless supporting example.
        if (s.get('external_safe') is True and profile_state(s, pack) in ('proposed', 'confirmed')
                and all(eligible(atoms[i])[0] for i in s['evidence_ids'])):
            result.append({k: s[k] for k in ('id', 'interpretation', 'evidence_ids',
                                           'status', 'basis', 'limitations', 'timeframe')})
    return result
