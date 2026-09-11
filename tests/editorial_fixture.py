"""Create complete fictional packs for diverse editorial journeys."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def personas():
    return json.loads((ROOT / 'tests/fixtures/editorial-personas.json').read_text())


def pack_for(person):
    ref = {'source_id': 'SRC_SUBJECT', 'excerpt': 'These examples describe my contribution. ' + person['direction']}
    atoms = []
    for n, (title, action, result, when) in enumerate(person['examples'], 1):
        atoms.append({'id': f'E_STORY_{n}', 'title': title,
                      'star': {'situation': title, 'task': 'Improve this work within my role', 'action': action, 'result': result},
                      'metrics': [], 'skills': [], 'source_refs': [ref], 'evidence_status': 'self_asserted',
                      'external_safe': True, 'outcome_type': 'output', 'corroborators': [],
                      'employment_id': 'EMP_CURRENT', 'occurred': {'start': when, 'end': when, 'inferred': False}, 'constraints': []})
    atoms.append({'id': 'E_PRIVATE', 'title': 'PRIVATE_CANARY investigation',
                  'star': {'situation': 'Confidential work', 'task': 'Private', 'action': 'PRIVATE_CANARY system investigation', 'result': None},
                  'metrics': [], 'skills': [], 'source_refs': [ref], 'evidence_status': 'self_asserted',
                  'external_safe': False, 'outcome_type': 'activity', 'corroborators': [], 'employment_id': 'EMP_CURRENT',
                  'occurred': {'start': '2026-01', 'end': '2026-01', 'inferred': False}})
    ids = ['E_STORY_1', 'E_STORY_2'] if person['basis'] == 'recurring_pattern' else ['E_STORY_1']
    pack = {'schema_version': '1.4', 'name': person['name'], 'purpose': 'Entirely fictional editorial regression fixture',
            'source_records': [{'source_id': 'SRC_SUBJECT', 'source_type': 'person', 'path': 'reviews/onboarding.md',
                                'retrieved': '2026-09-08', 'independent': False}],
            'evidence_atoms': atoms,
            'employment': [{'employment_id': 'EMP_CURRENT', 'employer': 'Fictional Fieldwork Ltd',
                            'employer_of_record': 'Fictional Fieldwork Ltd', 'title': person['title'], 'start': person['start'],
                            'end': 'present', 'location': 'London', 'parent_employment_id': None, 'source_refs': [ref],
                            'evidence_status': 'self_asserted', 'external_safe': True, 'corroborators': []}],
            'private_profile': {'name': person['name'], 'email': person['id'] + '@example.invalid', 'location': 'London, UK'},
            'strengths_profile': [{'id': 'S_DISTINCTIVE', 'interpretation': person['strength'], 'evidence_ids': ids,
                                   'evidence_fingerprints': {a['id']: fingerprint(a) for a in atoms if a['id'] in ids},
                                   'status': 'confirmed', 'basis': person['basis'], 'limitations': ['Only the recorded examples are established'],
                                   'timeframe': 'Dates of the supporting achievements', 'external_safe': True, 'source_refs': [ref],
                                   'question_status': 'answered'}],
            'positioning_preferences': [{'id': 'P_DIRECTION', 'kind': 'direction', 'text': person['direction'],
                                        'status': 'active', 'external_safe': True, 'source_refs': [ref]}]}
    return pack


def brief_for(person, fmt='resume', version='v1'):
    return {'brief_id': person['id'] + '-' + fmt + '-' + version, 'output_id': person['id'] + '-' + fmt,
            'application_id': person['id'] + '-application',
            'role_id': None, 'role_family': None, 'format': fmt,
            'audience': {'biography': 'public', 'interview_brief': 'private'}.get(fmt, 'named_recipient'),
            'length': 'one page' if fmt == 'resume' else '150 words' if fmt == 'biography' else 'concise private preparation',
            'strength_ids': ['S_DISTINCTIVE'], 'preference_ids': ['P_DIRECTION'], 'priority_evidence_ids': [],
            'instructions': '', 'external_safe': False, 'created_by': 'system'}
