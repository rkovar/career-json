"""Creation journeys use fictional careers, real sources and explicit decisions."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from editorial_fixture import personas, pack_for
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from pack_review import fingerprint


class CreationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='career-creation-')
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / 'schemas', self.root / 'schemas')
        self.pack = pack_for(personas()[0])
        self.pack['metadata'] = {}
        self.write('reviews/onboarding.md', self.pack['evidence_atoms'][0]['source_refs'][0]['excerpt'])
        self.session = 'reviews/pack-reviews/first/session.json'
        self.put('data/candidates/first.json', self.pack)
        self.cli('review', 'start', '--candidate', 'data/candidates/first.json', '--id', 'first', '--grouped')

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, text):
        path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text)
        return path

    def put(self, name, value):
        return self.write(name, json.dumps(value, indent=2))

    def cli(self, *args, ok=True):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/career_core.py'), *args],
                                cwd=self.root, env={**os.environ, 'CAREER_WORKSPACE': str(self.root)},
                                text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def state(self):
        return json.loads(self.cli('review', 'status', '--session', self.session).stdout)

    def test_staging_reports_excerpt_warning_and_keeps_machine_readable_path(self):
        self.pack['evidence_atoms'][0]['source_refs'][0]['excerpt'] = 'This claim does not occur in the supplied source.'
        self.put('data/candidates/warning.json', self.pack)
        result = self.cli('review', 'revise', '--session', self.session,
                          '--candidate', 'data/candidates/warning.json', '--id', 'warning')
        self.assertEqual(result.stdout.strip(), 'reviews/pack-reviews/warning/session.json')
        self.assertIn('mismatch', result.stderr)
        self.assertIn('Human review is still required', result.stderr)
        session = json.loads((self.root / result.stdout.strip()).read_text())
        self.assertTrue(session['validation_warnings'])
        self.assertFalse(list((self.root / 'data/packs').glob('*.json')))

    def choices(self, actions, pack=None):
        pack = pack or self.pack
        state = self.state()
        return {'review_id': state['session']['review_id'], 'proposal_sha256': state['session']['proposal']['sha256'],
                'reviewed_by': 'Fictional Reviewer', 'decisions': [{'key': key, 'fingerprint': fingerprint(key, pack),
                 'action': action, 'publication': 'unchanged', 'note': 'Please correct this wording.' if action == 'correct' else ''}
                 for key, action in actions.items()], 'omissions': []}

    def apply(self, payload):
        self.put('data/private/choices.json', payload)
        return json.loads(self.cli('review', 'apply', '--input', 'data/private/choices.json').stdout)

    def first_save(self):
        return self.apply(self.choices({'employment/EMP_CURRENT': 'accept', 'evidence_atoms/E_STORY_1': 'accept'}))

    def test_a_role_can_start_a_private_pack_without_an_achievement(self):
        result=self.apply(self.choices({'employment/EMP_CURRENT':'accept'}))
        saved=json.loads((self.root/result['saved_pack']).read_text())
        self.assertEqual(len(saved['employment']),1)
        self.assertEqual(saved['evidence_atoms'],[])
        self.assertNotIn('private_profile',saved)
        self.assertTrue((self.root/'outputs/career-record.html').is_file())

    def test_recovery_finds_staged_review_without_approving_it(self):
        result = json.loads(self.cli('recover').stdout)
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['reviews'][0]['review'], self.session)
        self.assertTrue((self.root / result['reviews'][0]['page']).is_file())
        self.assertFalse(list((self.root / 'data/packs').glob('*.json')))
        page = result['reviews'][0]['page']
        offline = self.cli('review', 'handover', '--session', self.session, '--page', page).stdout
        connected = self.cli('review', 'handover', '--session', self.session, '--page', page, '--connected').stdout
        self.assertIn('offline review', offline)
        self.assertIn('Save reviewed changes', connected)
        self.assertNotIn('download decisions', connected)

    def test_completed_review_moves_to_history_and_saved_page_is_current(self):
        from start import saved_work
        actions = {r['key']: 'accept' for r in self.state()['items'] if not r.get('source_registration')}
        self.apply(self.choices(actions))
        state = json.loads(self.cli('health', '--summary', '--json').stdout)
        self.assertEqual(state['state'], 'saved')
        self.assertEqual(state['reading_page']['state'], 'current')
        self.assertFalse(state['reviews'][0]['actionable'])
        self.assertEqual(saved_work(self.root, False)[0], [])
        self.assertEqual(len(saved_work(self.root, False, history=True)[0]), 1)

    def test_question_cli_and_review_summary_share_exact_answer_state(self):
        self.put('data/private/question.json', {'question': 'Who built the rehearsal runner?',
            'targets': ['evidence_atoms/E_STORY_1'], 'kind': 'factual_ambiguity', 'required': True})
        question = json.loads(self.cli('questions', 'ask', '--input', 'data/private/question.json',
                                      '--pack', 'data/candidates/first.json').stdout)
        before = self.state()['summary']['questions']
        answer = json.loads(self.cli('questions', 'respond', '--id', question['id'], '--revision', '1',
             '--state', 'answered', '--answer', 'I designed it and co-built it with colleagues.', '--by', 'Jules').stdout)
        self.assertEqual(self.state()['summary']['questions'], before - 1)
        self.assertIn('source_ref', answer)
        proposal = copy.deepcopy(self.pack)
        proposal['source_records'].append(answer['source_record'])
        proposal['evidence_atoms'][0]['source_refs'].append(answer['source_ref'])
        self.put('data/candidates/answered.json', proposal)
        self.cli('review', 'start', '--candidate', 'data/candidates/answered.json', '--id', 'answered')
        self.assertEqual(self.state()['summary']['question_state']['answered'], 1)
        self.assertFalse(list((self.root / 'data/packs').glob('*.json')))

    def test_first_save_registers_sources_without_fabricating_source_approval(self):
        state = self.first_save()
        saved = json.loads((self.root / state['saved_pack']).read_text())
        self.assertEqual(len(saved['source_records']), 1)
        self.assertEqual(len(saved['evidence_atoms']), 1)
        self.assertFalse(saved['evidence_atoms'][0]['external_safe'])
        source_key = 'source_records/' + saved['source_records'][0]['source_id']
        self.assertNotIn(source_key, saved['metadata']['human_review']['items'])
        self.assertEqual(saved['metadata']['source_imports'][source_key]['kind'], 'source_registration')
        self.assertTrue((self.root / 'outputs/career-record.html').is_file())
        self.assertEqual(state['message'], 'Saved to your career pack.')
        self.assertFalse(list((self.root / 'scripts').glob('*')))  # no resume/runtime needed in data fixture

    def test_achievement_cannot_implicitly_approve_its_role(self):
        payload = self.choices({'evidence_atoms/E_STORY_1': 'accept'})
        self.put('data/private/choices.json', payload)
        result = json.loads(self.cli('review', 'apply', '--input', 'data/private/choices.json', ok=False).stdout)
        self.assertIn('supporting sources/roles', result['save_blocked'])
        self.assertFalse(list((self.root / 'data/packs').glob('*.json')))

    def test_changed_source_file_blocks_save(self):
        self.write('reviews/onboarding.md', 'A different account.')
        self.put('data/private/choices.json', self.choices({'employment/EMP_CURRENT': 'accept', 'evidence_atoms/E_STORY_1': 'accept'}))
        result = json.loads(self.cli('review', 'apply', '--input', 'data/private/choices.json', ok=False).stdout)
        self.assertIn('changed input', result['save_blocked'])
        self.assertFalse(list((self.root / 'data/packs').glob('*.json')))

    def test_correction_is_pending_then_saved_without_reapproving_role(self):
        initial = self.first_save()
        original = (self.root / initial['saved_pack']).read_bytes()
        payload = self.choices({'evidence_atoms/E_STORY_1': 'correct'})
        wording = 'I helped design the procedure with the operations team.'
        self.put('data/private/edit.json', {'decisions': payload, 'edits': [{'key': 'evidence_atoms/E_STORY_1',
                 'fingerprint': fingerprint('evidence_atoms/E_STORY_1', self.pack), 'fields': {'star.action': wording}}]})
        self.session = self.cli('review', 'correct', '--session', self.session, '--input', 'data/private/edit.json').stdout.strip()
        state = self.state()
        revised = json.loads((self.root / state['session']['proposal']['path']).read_text())
        row = next(r for r in state['items'] if r['key'] == 'evidence_atoms/E_STORY_1')
        self.assertEqual(row['review_status'], 'awaiting_review')
        self.assertNotIn('decision', row)
        self.assertEqual((self.root / initial['saved_pack']).read_bytes(), original)
        saved = self.apply(self.choices({'evidence_atoms/E_STORY_1': 'accept'}, revised))
        final = json.loads((self.root / saved['saved_pack']).read_text())
        self.assertEqual(final['evidence_atoms'][0]['star']['action'], wording)
        self.assertEqual(len(final['employment']), 1)
        self.assertEqual(len(final['source_records']), 2)
        self.assertFalse(final['evidence_atoms'][0]['external_safe'])
        self.assertEqual((self.root / initial['saved_pack']).read_bytes(), original)

    def test_unchanged_pending_approvals_survive_revised_proposal(self):
        payload = self.choices({'employment/EMP_CURRENT': 'accept', 'evidence_atoms/E_STORY_2': 'accept'})
        self.put('data/private/edit.json', {'decisions': payload, 'edits': [{'key': 'evidence_atoms/E_STORY_1',
                 'fingerprint': fingerprint('evidence_atoms/E_STORY_1', self.pack), 'fields': {'star.action': 'I helped a colleague test the procedure.'}}]})
        self.session = self.cli('review', 'correct', '--session', self.session, '--input', 'data/private/edit.json').stdout.strip()
        state = self.state(); rows = {r['key']: r for r in state['items']}
        self.assertEqual(rows['evidence_atoms/E_STORY_2']['decision']['action'], 'accept')
        self.assertEqual(rows['employment/EMP_CURRENT']['decision']['action'], 'accept')
        self.assertNotIn('decision', rows['evidence_atoms/E_STORY_1'])
        # Carried decisions keep the original batch receipt, never a fabricated new reviewer action.
        self.assertIn('/first/', rows['employment/EMP_CURRENT']['decision']['batch']['path'])

    def test_old_approval_cannot_overwrite_a_newer_accepted_fact(self):
        self.first_save()
        old_session = self.session
        newer = copy.deepcopy(self.pack)
        newer['evidence_atoms'][0]['star']['action'] = 'I contributed the test plan with the team.'
        self.put('data/candidates/newer.json', newer)
        self.session = self.cli('review', 'start', '--candidate', 'data/candidates/newer.json', '--id', 'newer').stdout.strip()
        self.apply(self.choices({'evidence_atoms/E_STORY_1': 'accept'}, newer))
        older = copy.deepcopy(self.pack)
        older['evidence_atoms'][1]['title'] += ' revised'
        self.put('data/candidates/older.json', older)
        self.session = self.cli('review', 'revise', '--session', old_session, '--candidate', 'data/candidates/older.json', '--id', 'older-revised').stdout.strip()
        rows = {r['key']: r for r in self.state()['items']}
        self.assertNotIn('decision', rows['evidence_atoms/E_STORY_1'])
        self.assertIn('decision', rows['employment/EMP_CURRENT'])
        result = self.apply(self.choices({}, older))
        self.assertIsNone(result['saved_pack'])
        packs = [json.loads(p.read_text()) for p in (self.root/'data/packs').glob('*.json')]
        self.assertEqual(len(packs), 2)
        self.assertTrue(any(p['evidence_atoms'][0]['star']['action'] == newer['evidence_atoms'][0]['star']['action'] for p in packs))

    def test_old_external_permission_cannot_undo_newer_privacy_restriction(self):
        payload = self.choices({'employment/EMP_CURRENT': 'accept', 'evidence_atoms/E_STORY_1': 'accept'})
        payload['decisions'][1]['publication'] = 'external'
        self.apply(payload)
        old_session = self.session
        self.session = self.cli('review','start','--candidate','data/candidates/first.json','--id','privacy').stdout.strip()
        payload = self.choices({'evidence_atoms/E_STORY_1':'later'})
        payload['decisions'][0]['publication'] = 'private'
        result = self.apply(payload)
        saved = json.loads((self.root/result['saved_pack']).read_text())
        self.assertFalse(saved['evidence_atoms'][0]['external_safe'])
        self.session = self.cli('review','revise','--session',old_session,'--candidate','data/candidates/first.json','--id','revisit-private').stdout.strip()
        self.assertIsNone(self.apply(self.choices({}))['saved_pack'])
        self.assertEqual(len(list((self.root/'data/packs').glob('*.json'))),2)

    def test_old_approval_cannot_resurrect_a_removed_fact(self):
        self.first_save()
        old_session = self.session
        removed = copy.deepcopy(self.pack)
        removed['evidence_atoms'] = [a for a in removed['evidence_atoms'] if a['id'] != 'E_STORY_1']
        # Only the original saved role/achievement exist in the accepted pack.
        removed['strengths_profile'] = []
        self.put('data/candidates/remove.json', removed)
        self.session = self.cli('review', 'start', '--candidate', 'data/candidates/remove.json', '--id', 'remove').stdout.strip()
        self.apply(self.choices({'evidence_atoms/E_STORY_1': 'accept'}, removed))
        self.session = self.cli('review', 'revise', '--session', old_session, '--candidate', 'data/candidates/first.json', '--id', 'revisit').stdout.strip()
        self.assertNotIn('decision', next(r for r in self.state()['items'] if r['key']=='evidence_atoms/E_STORY_1'))
        self.assertIsNone(self.apply(self.choices({}))['saved_pack'])

    def test_intake_after_save_accepts_relative_and_symlinked_workspaces(self):
        self.first_save()
        self.write('data/sources/new.md', 'A new contribution.')
        alias = self.root/'workspace-link'
        alias.symlink_to(self.root.resolve(), target_is_directory=True)
        for workspace in (str(alias), '.'):
            result = subprocess.run([sys.executable, '-B', str(ROOT/'scripts/career_core.py'), 'intake', 'data/sources/new.md'],
                cwd=self.root, env={**os.environ, 'CAREER_WORKSPACE': workspace}, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            self.assertEqual(len(json.loads(result.stdout)['sources']), 1)

    def test_correcting_multiple_items_preserves_all_edits_without_old_acceptance(self):
        keys = ['evidence_atoms/E_STORY_1', 'evidence_atoms/E_STORY_2']
        payload = self.choices({key: 'accept' for key in keys})
        self.put('data/private/edit.json', {'decisions':payload, 'edits':[
            {'key':key, 'fingerprint':fingerprint(key,self.pack), 'fields':{'star.action':'Contributed with colleagues '+key}}
            for key in keys]})
        old_session = self.session
        self.session = self.cli('review', 'correct', '--session', self.session, '--input', 'data/private/edit.json').stdout.strip()
        for row in self.state()['items']:
            if row['key'] in keys:
                self.assertNotIn('decision',row)
                self.assertEqual(row['after']['star']['action'], 'Contributed with colleagues '+row['key'])
        old_state = json.loads(self.cli('review','status','--session',old_session).stdout)
        self.assertFalse(any(r.get('decision',{}).get('action')=='accept' for r in old_state['items']))

    def test_repeated_save_does_not_create_another_pack(self):
        payload = self.choices({'employment/EMP_CURRENT': 'accept', 'evidence_atoms/E_STORY_1': 'accept'})
        self.apply(payload)
        result = self.apply(payload)
        self.assertIsNone(result['saved_pack'])
        self.assertEqual(len(list((self.root / 'data/packs').glob('*.json'))), 1)

    def test_grouped_page_prioritizes_roles_and_achievements(self):
        self.cli('review', 'render', '--session', self.session, '--output', 'outputs/review.html')
        page = (self.root / 'outputs/review.html').read_text()
        self.assertIn('Roles and achievements first', page)
        self.assertIn('Your contribution', page)
        self.assertNotIn('data-key="source_records/', page)
        self.assertLess(page.index('data-key="employment/'), page.index('data-key="evidence_atoms/'))
        self.assertIn('Show original source excerpts', page)

    def test_intake_reports_duplicates_advice_and_unreadable_files(self):
        self.write('data/sources/resume.md', 'I designed a rehearsal format with colleagues.')
        self.write('data/sources/copy.md', 'I designed a rehearsal format with colleagues.')
        self.write('data/sources/guide.md', '# Resume writing guide\nHow to write a resume.')
        self.write('data/sources/vacancy.md', '# Job description\nWe are hiring an engineer.')
        self.write('data/sources/image.png', 'not actually an image')
        report = json.loads(self.cli('intake', 'data/sources').stdout)
        self.assertEqual(report['counts'], {'read': 3, 'unreadable': 1, 'duplicate': 1})
        rows = {r['path']: r for r in report['sources']}
        self.assertEqual(rows['data/sources/guide.md']['purpose_hint'], 'writing_reference')
        self.assertEqual(rows['data/sources/vacancy.md']['purpose_hint'], 'job_context')
        self.assertEqual(rows['data/sources/vacancy.md']['purpose'], 'needs_classification')
        self.assertFalse(list((self.root / 'data/packs').glob('*.json')))

    def test_intake_keyword_hint_cannot_exclude_career_material(self):
        self.write('data/sources/interview.md', '# An interview with Jules\n'
                   'Jules described the team she founded: "We are hiring engineers."')
        report = json.loads(self.cli('intake', 'data/sources/interview.md').stdout)
        self.assertEqual(report['sources'][0]['purpose_hint'], 'job_context')
        self.assertEqual(report['sources'][0]['purpose'], 'needs_classification')
        self.assertTrue(report['has_new_material'])
        self.put('data/private/classifications.json', {'data/sources/interview.md': 'career_evidence'})
        reviewed = json.loads(self.cli('intake', 'data/sources/interview.md', '--classifications',
                                        'data/private/classifications.json').stdout)
        self.assertEqual(reviewed['sources'][0]['purpose'], 'career_evidence')
        self.assertEqual(reviewed['sources'][0]['purpose_origin'], 'supplied')
        self.put('data/private/classifications.json', {'data/sources/interview.md': 'job_context'})
        excluded = json.loads(self.cli('intake', 'data/sources/interview.md', '--classifications',
                                        'data/private/classifications.json').stdout)
        self.assertFalse(excluded['has_new_material'])

    def test_intake_keeps_scope_and_does_not_guess_career_facts(self):
        self.write('data/sources/resume.md', 'I worked with colleagues.')
        self.write('data/sources/later.md', 'Not selected for this intake.')
        report = json.loads(self.cli('intake', 'data/sources/resume.md').stdout)
        self.assertEqual(len(report['sources']), 1)
        self.assertEqual(report['sources'][0]['purpose'], 'needs_classification')
        self.assertNotIn('evidence_atoms', report)
        self.cli('intake', 'reviews/onboarding.md', ok=False)

    def test_stale_browser_cannot_save_over_a_newer_pack(self):
        # Exercise the exact-state save operation in an isolated process without a browser.
        payload = self.choices({'employment/EMP_CURRENT': 'accept', 'evidence_atoms/E_STORY_1': 'accept'})
        self.put('data/private/choices.json', payload)
        code = """
from career_review import save, state_token
import pack_review
from pack_io import read
session='reviews/pack-reviews/first/session.json'
token=state_token(pack_review.status(session))
payload=read('data/private/choices.json')
assert save(session,payload,token)['saved_pack']
try: save(session,payload,token)
except ValueError as error: assert 'Reload' in str(error)
else: raise AssertionError('stale save was accepted')
"""
        result = subprocess.run([sys.executable, '-B', '-c', code], cwd=self.root,
            env={**os.environ, 'CAREER_WORKSPACE': str(self.root), 'PYTHONPATH': str(ROOT/'scripts')}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertEqual(len(list((self.root/'data/packs').glob('*.json'))), 1)

    def test_role_change_reopens_dependent_achievement_approval(self):
        payload = self.choices({'employment/EMP_CURRENT': 'accept', 'evidence_atoms/E_STORY_1': 'accept'})
        self.put('data/private/edit.json', {'decisions': payload, 'edits': [{'key': 'employment/EMP_CURRENT',
            'fingerprint': fingerprint('employment/EMP_CURRENT', self.pack), 'fields': {'title': 'Principal Engineer'}}]})
        self.session = self.cli('review','correct','--session',self.session,'--input','data/private/edit.json').stdout.strip()
        rows = {row['key']: row for row in self.state()['items']}
        self.assertNotIn('decision', rows['employment/EMP_CURRENT'])
        self.assertNotIn('decision', rows['evidence_atoms/E_STORY_1'])

    def test_minimal_first_pack_across_career_types(self):
        for index, person in enumerate(personas()[1:], 1):
            with self.subTest(person=person['id']):
                # Use distinct temporary workspaces so careers never mix.
                with tempfile.TemporaryDirectory(prefix='career-persona-') as directory:
                    previous = self.root, self.pack, self.session
                    try:
                        self.root = Path(directory); shutil.copytree(ROOT/'schemas', self.root/'schemas')
                        self.pack = pack_for(person); self.pack['metadata'] = {}
                        self.write('reviews/onboarding.md', self.pack['evidence_atoms'][0]['source_refs'][0]['excerpt'])
                        self.put('data/candidates/first.json', self.pack)
                        self.session='reviews/pack-reviews/first/session.json'
                        self.cli('review','start','--candidate','data/candidates/first.json','--id','first')
                        result = self.first_save()
                        saved = json.loads((self.root/result['saved_pack']).read_text())
                        self.assertEqual(saved['evidence_atoms'][0]['star'], next(a for a in self.pack['evidence_atoms'] if a['id']=='E_STORY_1')['star'])
                    finally:
                        self.root, self.pack, self.session = previous

    def test_repeated_choices_in_a_larger_batch_keep_original_receipts(self):
        first = self.first_save()
        old = json.loads((self.root/first['saved_pack']).read_text())
        key = 'evidence_atoms/E_STORY_1'
        payload = self.choices({'employment/EMP_CURRENT':'accept', key:'accept', 'evidence_atoms/E_STORY_2':'accept'})
        second = self.apply(payload)
        new = json.loads((self.root/second['saved_pack']).read_text())
        self.assertEqual(old['metadata']['human_review']['items'][key], new['metadata']['human_review']['items'][key])
        self.assertIsNone(self.apply(payload)['saved_pack'])

    def test_independent_work_saves_while_other_role_stays_pending(self):
        self.pack['employment'].append(dict(self.pack['employment'][0], employment_id='EMP_OTHER', title='Another role'))
        self.pack['evidence_atoms'][1]['employment_id']='EMP_OTHER'
        self.put('data/candidates/two-roles.json', self.pack)
        self.session=self.cli('review','start','--candidate','data/candidates/two-roles.json','--id','two-roles').stdout.strip()
        choices=self.choices({'employment/EMP_CURRENT':'accept','evidence_atoms/E_STORY_1':'accept','evidence_atoms/E_STORY_2':'accept'})
        self.put('data/private/choices.json', choices)
        result=json.loads(self.cli('review','apply','--input','data/private/choices.json',ok=False).stdout)
        self.assertTrue(result['saved_pack'])
        saved=json.loads((self.root/result['saved_pack']).read_text())
        self.assertEqual([a['id'] for a in saved['evidence_atoms']], ['E_STORY_1'])
        pending=next(row for row in result['items'] if row['key']=='evidence_atoms/E_STORY_2')
        self.assertNotEqual(pending['review_status'],'accepted')
        result=self.apply(self.choices({'employment/EMP_OTHER':'accept'}))
        self.assertIsNone(result['save_blocked'])
        saved=json.loads((self.root/result['saved_pack']).read_text())
        self.assertEqual({a['id'] for a in saved['evidence_atoms']}, {'E_STORY_1','E_STORY_2'})

    def test_pending_removal_approval_survives_unchanged_revision(self):
        self.first_save()
        candidate=copy.deepcopy(self.pack)
        candidate['strengths_profile']=[]
        candidate['evidence_atoms']=[a for a in candidate['evidence_atoms'] if a['id']!='E_STORY_1']
        self.put('data/candidates/removal.json',candidate)
        self.session=self.cli('review','start','--candidate','data/candidates/removal.json','--id','removal').stdout.strip()
        self.put('data/private/remove-choice.json',self.choices({'evidence_atoms/E_STORY_1':'accept'},candidate))
        self.cli('review','record','--session',self.session,'--input','data/private/remove-choice.json')
        self.session=self.cli('review','revise','--session',self.session,'--candidate','data/candidates/removal.json','--id','removal-revised').stdout.strip()
        row=next(row for row in self.state()['items'] if row['key']=='evidence_atoms/E_STORY_1')
        self.assertEqual(row['decision']['action'],'accept')
        result=self.apply(self.choices({}))
        saved=json.loads((self.root/result['saved_pack']).read_text())
        self.assertEqual(saved['evidence_atoms'],[])

    def test_omission_feedback_survives_a_corrected_proposal(self):
        payload=self.choices({})
        payload['omissions']=[{'prompt':'What important work is missing?', 'answer':'The mentoring work is missing.'}]
        self.apply(payload)
        changed=copy.deepcopy(self.pack); changed['evidence_atoms'][0]['title']='Clarified contribution'
        self.put('data/candidates/revised.json',changed)
        self.session=self.cli('review','revise','--session',self.session,'--candidate','data/candidates/revised.json','--id','revised').stdout.strip()
        self.assertEqual(self.state()['omissions'],payload['omissions'])

    def test_default_questions_focus_on_accuracy_without_publication_pressure(self):
        from open_questions import career_questions
        self.pack['metadata']['known_conflicts']=['Two source documents disagree about the start date.']
        for atom in self.pack['evidence_atoms']:
            atom['external_safe']=False
        questions=career_questions(self.pack)
        self.assertEqual(questions[0]['kind'],'conflict')
        self.assertFalse({'withheld','screen_gap','proposed_link','publications','classification'} & {q['kind'] for q in questions})
        self.assertTrue(all(q['optional'] for q in career_questions(self.pack,True) if q['kind']=='publications'))

    def test_workspace_installation_excludes_personal_data_and_refuses_overwrite(self):
        destination = self.root/'personal-workspace'
        result = self.cli('workspace','create','--directory',str(destination))
        self.assertTrue((destination/'scripts/career_core.py').is_file())
        self.assertFalse((destination/'scripts/editorial.py').exists())
        self.assertFalse(list((destination/'data/packs').glob('*.json')))
        self.assertFalse((destination/'reviews/onboarding.md').exists())
        self.assertTrue((destination/'components/workspace/installation.json').is_file())
        self.cli('workspace','create','--directory',str(destination),ok=False)
        run = subprocess.run([sys.executable,'-B','scripts/start.py','--flow','career','--print-prompt'],cwd=destination,
                             env={**os.environ,'CAREER_WORKSPACE':str(destination)},capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)



if __name__ == '__main__':
    unittest.main(verbosity=2)
