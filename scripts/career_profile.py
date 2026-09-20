"""Evidence-backed strengths and preferences, independent of output applications."""
import hashlib
import json

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False).encode()).hexdigest()


def atoms_by_id(pack):
    return {a['id']: a for a in pack.get('evidence_atoms', [])}


def reassess_strength(strength, pack, assessment):
    """Require a concrete narrative reassessment, not a fingerprint-only refresh.

    This records the operator's reasoning; it does not prove prose entailment or
    confer human approval. The resulting proposal still needs ordinary review.
    """
    atoms = atoms_by_id(pack)
    support = {i: digest(atoms[i]) for i in strength['evidence_ids']}
    if assessment.get('strength_sha256') != digest(strength) or assessment.get('support') != support:
        raise ValueError('reassessment does not match the current strength and supporting facts')
    if not isinstance(assessment.get('interpretation'), str) or not assessment['interpretation'].strip() or not assessment.get('reason', '').strip():
        raise ValueError('reassessment needs the resulting interpretation and its reason')
    originals = strength.get('limitations', [])
    covered, limitations = set(), []
    for row in assessment.get('limitations', []):
        index, action = row.get('index'), row.get('action')
        if not row.get('reason', '').strip() or action not in ('retain', 'remove', 'replace', 'add'):
            raise ValueError('explain whether each limitation is retained, removed, replaced or added')
        if action != 'add':
            if type(index) is not int or not 0 <= index < len(originals) or index in covered:
                raise ValueError('reassessment has a missing, repeated or invalid limitation index')
            covered.add(index)
        elif index is not None:
            raise ValueError('new limitations have no previous index')
        if action == 'retain': limitations.append(originals[index])
        elif action in ('replace', 'add'):
            if not isinstance(row.get('text'), str) or not row['text'].strip():
                raise ValueError('supply the resulting limitation wording')
            limitations.append(row['text'])
    if covered != set(range(len(originals))):
        raise ValueError('reassess every prior limitation; do not silently drop one')
    strength.update(interpretation=assessment['interpretation'], limitations=limitations, evidence_fingerprints=support)
    return {'result_sha256': digest(strength), 'support': support, 'reason': assessment['reason']}


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
