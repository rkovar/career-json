#!/usr/bin/env python3
"""Deterministic career lifecycle benchmark; fictional people and explicit fixture choices.

Measures retained facts, sources, resumability and selected strengths. Does not
claim to measure model prose or human effort; those require the bounded model run
and the recorded human-review rubric in docs/quality-benchmarks.md.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from editorial_fixture import ROOT, personas, pack_for, brief_for
sys.path.insert(0, str(ROOT / 'scripts'))
from pack_review import units, fingerprint
from workspace_backup import backup_workspace, restore_workspace


def journey(person):
    started = time.monotonic()
    checks = []
    def check(name, value): checks.append({'check': name, 'passed': bool(value)})
    with tempfile.TemporaryDirectory(prefix='career-journey-') as folder:
        root = Path(folder).resolve()
        shutil.copytree(ROOT / 'schemas', root / 'schemas')
        def put(path, record):
            p = root / path; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(record, indent=2) + '\n')
        def cli(*args, script='career_core.py'):
            result = subprocess.run([sys.executable, str(ROOT / 'scripts' / script), *args], cwd=root,
                                    env={**os.environ, 'CAREER_WORKSPACE': str(root)}, capture_output=True, text=True)
            if result.returncode: raise RuntimeError(result.stdout + result.stderr)
            return result.stdout
        def stage(pack, name):
            put('data/candidates/' + name + '.json', pack)
            cli('review', 'start', '--candidate', 'data/candidates/' + name + '.json', '--id', name)
            return 'reviews/pack-reviews/' + name + '/session.json'
        def apply(pack, session, name, keys):
            s = json.loads((root / session).read_text())
            # Decisions are explicitly authored fixture inputs, never model-inferred approvals.
            payload = {'review_id': s['review_id'], 'proposal_sha256': s['proposal']['sha256'], 'reviewed_by': person['name'],
                       'decisions': [{'key': key, 'fingerprint': fingerprint(key, pack), 'action': 'accept', 'note': '',
                                      'publication': 'external' if isinstance(units(pack)[key], dict) and units(pack)[key].get('external_safe') is True else 'unchanged'} for key in keys], 'omissions': []}
            put('data/private/' + name + '-choices.json', payload)
            cli('review', 'apply', '--input', 'data/private/' + name + '-choices.json', '--output', 'data/packs/' + name + '.json')
            return json.loads((root / ('data/packs/' + name + '.json')).read_text())
        original = pack_for(person)
        (root / 'reviews').mkdir()
        (root / 'reviews/onboarding.md').write_text(original['evidence_atoms'][0]['source_refs'][0]['excerpt'])
        session = stage(original, 'first')
        check('first_import_stays_proposed', not list((root / 'data/packs').glob('*.json')))
        # Pause with one achievement and the shared supporting records accepted.
        keys = [k for k in units(original) if not k.startswith(('strengths_profile/', 'positioning_preferences/')) and k != 'evidence_atoms/E_STORY_2']
        partial = apply(original, session, 'partial', keys)
        archive = backup_workspace('backups/portable.zip', root)
        restored = restore_workspace(archive, root / 'restored', root)
        check('backup_preserves_pending_session', (restored / session).read_bytes() == (root / session).read_bytes())
        # Continue in the restored workspace, without recreating the session.
        root = restored
        remaining = [k for k in units(original) if k not in keys]
        accepted = apply(original, session, 'accepted', remaining)
        check('resume_retains_all_factual_wording', {a['id']: a['star'] for a in accepted['evidence_atoms']} == {a['id']: a['star'] for a in original['evidence_atoms']})
        repeated = stage(accepted, 'repeat-import')
        state = json.loads(cli('review', 'status', '--session', repeated))
        check('repeat_import_does_not_duplicate_atoms', len(accepted['evidence_atoms']) == len(original['evidence_atoms']) and all(r['change'] == 'unchanged' for r in state['items']))
        correction = copy.deepcopy(accepted)
        correction['evidence_atoms'][0]['star']['action'] += ' I clarified this account with the colleagues involved.'
        correction['source_records'].append({'source_id': 'SRC_CLARIFY', 'source_type': 'person', 'path': 'reviews/clarify.md', 'retrieved': '2026-09-11', 'independent': False})
        (root / 'reviews/clarify.md').write_text('I clarified this account with the colleagues involved.')
        correction['evidence_atoms'][0]['source_refs'] = copy.deepcopy(correction['evidence_atoms'][0]['source_refs']) + [{'source_id': 'SRC_CLARIFY', 'excerpt': 'I clarified this account with the colleagues involved.'}]
        corrected = apply(correction, stage(correction, 'correction'), 'corrected', ['source_records/SRC_CLARIFY', 'evidence_atoms/E_STORY_1'])
        check('correction_preserves_unrelated_achievements', corrected['evidence_atoms'][1:] == accepted['evidence_atoms'][1:])
        from editorial_fixture import strength_assessment
        (root/'data/private/assessment.json').write_text(json.dumps(strength_assessment(corrected)))
        cli('bind-strength', '--pack', 'data/packs/corrected.json', '--strength', 'S_DISTINCTIVE', '--output', 'data/candidates/reassessed.json', '--assessment', 'data/private/assessment.json')
        reassessed = json.loads((root / 'data/candidates/reassessed.json').read_text())
        final = apply(reassessed, stage(reassessed, 'strength'), 'final', ['strengths_profile/S_DISTINCTIVE'])
        check('strength_interpretation_survives_reassessment', final['strengths_profile'][0]['interpretation'] == original['strengths_profile'][0]['interpretation'])
        check('source_excerpts_still_verify', json.loads(cli('--json', script='verify_excerpts.py'))['counts']['mismatch'] == 0)
        history = json.loads(cli('history', 'E_STORY_1'))
        check('history_explains_correction', any(c['before'] and c['value']['star'] != c['before']['star'] for c in history['changes']))
        if (ROOT / 'scripts/editorial.py').exists():
            put('data/briefs/resume.json', brief_for(person))
            cli('prepare', '--brief', 'data/briefs/resume.json', '--id', 'after-revisions', '--output', 'data/selections/resume.json', script='editorial.py')
            view = json.loads(cli('--selection', 'data/selections/resume.json', script='select_evidence.py'))
            check('generation_retains_distinctive_strength', any(s['id'] == 'S_DISTINCTIVE' for s in view['editorial']['strengths']))
            check('generation_excludes_private_evidence', all(a['id'] != 'E_PRIVATE' for a in view['atoms']))
        return {'persona': person['id'], 'checks': checks, 'metrics': {'elapsed_seconds': round(time.monotonic() - started, 3),
            'source_achievements': len(original['evidence_atoms']), 'retained_achievements': len(final['evidence_atoms']),
            'human_review_burden': None, 'unnecessary_model_questions': None, 'prose_representation_quality': None}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    results = []
    for person in personas():
        try: result = journey(person)
        except Exception as exc: result = {'persona': person['id'], 'checks': [{'check': 'journey_completed', 'passed': False}], 'error': str(exc)}
        results.append(result)
        print(person['id'] + ': ' + ('PASS' if all(c['passed'] for c in result['checks']) else 'FAIL'))
    report = {'benchmark': 'career-lifecycle-v1', 'kind': 'deterministic', 'results': results,
              'limitations': 'Fixture choices simulate people. Human burden and prose quality require separate observation.'}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    failed = [r for r in results if not all(c['passed'] for c in r['checks'])]
    for result in failed: print(json.dumps(result, indent=2))
    return int(bool(failed))


if __name__ == '__main__': sys.exit(main())
