#!/usr/bin/env python3
"""Resume guided-start journeys, with real brief and selection consumers."""
import json
import os
import subprocess
import sys
import unittest

from test_startup import ROOT, StartupCase, answered, empty


class ResumeStartupTests(StartupCase):
    entry = 'editorial.py'

    def target(self, **extras):
        return answered({'mode': 'role', 'description': 'Staff platform engineer', **extras})

    def handoff(self, row, bid='brief-one', *extras, fail=None):
        return self.command('handoff', '--session', row['session'], '--id', bid,
                            '--application', 'application-one', *extras, fail=fail)

    def test_missing_pack_preserves_private_brief_and_defaults(self):
        values = {'target': self.target(), 'focus': answered({'text': 'Architectural judgement and mentoring'}),
                  'achievements': answered({'notes': 'Give less space to public speaking'}),
                  'constraints': answered({'market': 'UK'}), 'review_mode': answered('interactive')}
        row = self.create(values)
        self.assertEqual(row['questions'], [])
        finished = self.handoff(row)
        self.assertEqual(finished['handoff']['action'], 'build_pack_then_resume')
        self.assertEqual(row['continue_prompt'], 'Continue my resume setup named "first".')
        self.assertEqual(finished['continue_prompt'], 'Continue creating my resume from saved setup named "first".')
        self.assertIn('brief', finished['saved'])
        import html
        page = html.unescape((self.root/finished['summary']).read_text())
        self.assertIn(finished['continue_prompt'], page)
        self.assertIn('<h1>Create a resume</h1>', page)
        brief = json.loads((self.root/finished['handoff']['brief']['path']).read_text())
        self.assertEqual(brief['application']['required_exports'], ['pdf', 'txt', 'docx', 'md'])
        self.assertEqual(brief['application']['paper_size'], 'A4')
        self.assertEqual(brief['application']['review_mode'], 'interactive')
        self.assertIn('mentoring', brief['instructions'])
        self.assertIn('public speaking', brief['instructions'])
        self.assertFalse(brief['external_safe'])
        self.assertEqual(brief['strength_ids'], [])
        self.assertFalse((self.root/'data/packs').exists())
        self.pack()
        resumed = self.command('refresh', '--session', finished['session'])
        self.assertEqual(resumed['answers'], values)
        self.assertEqual(resumed['questions'], [])
        self.assertEqual(self.handoff(resumed, 'brief-two')['handoff']['action'], 'prepare_selection')

    def test_skipped_optional_questions_do_not_block_automatic_brief(self):
        row = self.create({'target': self.target(), 'focus': empty('skipped'),
                           'achievements': empty('none'), 'constraints': empty('later'),
                           'review_mode': empty('skipped')})
        row = self.handoff(row)
        brief = json.loads((self.root/row['handoff']['brief']['path']).read_text())
        self.assertEqual(brief['application']['review_mode'], 'automatic')
        self.assertEqual(brief['application']['setting_sources']['review_mode']['origin'], 'inferred')

    def test_explore_does_not_silently_choose_a_role(self):
        row = self.create({'target': answered({'mode': 'explore'}), 'focus': answered({'suggest': True})})
        self.handoff(row, fail='choose a target')
        self.assertFalse((self.root/'data/briefs').exists())
        row = self.change(row, {'target': self.target()})
        self.assertNotIn('focus', [q['id'] for q in row['questions']])
        self.handoff(row)

    def test_reuses_all_saved_choices_including_jd_and_deferrals(self):
        self.write('data/sources/job.md', 'Staff engineer, fictional')
        values = {'target': answered({'mode': 'job_description', 'path': 'data/sources/job.md'}),
                  'focus': empty('later'), 'achievements': empty('none'),
                  'constraints': answered({'market': 'US', 'page_limit': 2}),
                  'review_mode': answered('automatic')}
        first = self.handoff(self.create(values))
        second = self.create(None, 'returning', '--brief', first['handoff']['brief']['path'])
        self.assertEqual(second['questions'], [])
        self.assertEqual(second['answers']['target']['value'], values['target']['value'])
        self.assertEqual(second['answers']['focus']['state'], 'later')
        brief = json.loads((self.root/self.handoff(second, 'brief-two')['handoff']['brief']['path']).read_text())
        self.assertEqual(brief['application']['paper_size'], 'Letter')
        self.assertEqual(brief['application']['page_limit'], 2)

    def test_job_description_requires_matching_profile_and_unchanged_bytes(self):
        self.pack()
        self.write('data/sources/job.md', 'Fictional platform role')
        row = self.create({'target': answered({'mode': 'job_description', 'path': 'data/sources/job.md'})})
        self.handoff(row, fail='role profile')
        profile = {'role_id': 'platform', 'title': 'Platform engineer',
                   'central_requirement': 'Build platforms', 'requirements': [{'text': 'Build platforms', 'weight': 'essential'}],
                   'source': 'data/sources/wrong.md'}
        self.write('data/roles/platform.json', profile)
        self.handoff(row, 'brief-one', '--role', 'platform', fail='job description')
        profile['source'] = 'data/sources/job.md'
        self.write('data/roles/platform.json', profile)
        self.write('data/sources/job.md', 'Changed role requirements')
        self.handoff(row, 'brief-one', '--role', 'platform', fail='changed input')
        row = self.change(row, {'target': answered({'mode': 'job_description', 'path': 'data/sources/job.md'})})
        result = self.handoff(row, 'brief-one', '--role', 'platform')
        self.assertEqual(result['handoff']['action'], 'prepare_selection')

    def test_constraints_privacy_and_provenance(self):
        row = self.create({'target': self.target(), 'constraints': answered({
            'audience': 'named_recipient', 'contact_mode': 'anonymous', 'page_limit': 2,
            'employer_instructions': 'Anonymous application, two pages.',
            'setting_sources': {'contact_mode': {'origin': 'employer', 'reason': 'Recorded in employer instructions.'},
                                'page_limit': {'origin': 'employer', 'reason': 'Recorded in employer instructions.'}}})})
        result = self.handoff(row)
        brief = json.loads((self.root/result['handoff']['brief']['path']).read_text())
        self.assertEqual(brief['application']['contact_mode'], 'anonymous')
        self.assertEqual(brief['application']['setting_sources']['page_limit']['origin'], 'employer')
        other = self.create({'target': self.target(), 'constraints': answered({
            'audience': 'public', 'contact_mode': 'standard'})}, 'bad-public')
        self.handoff(other, 'brief-bad', fail='private contact')
        self.assertFalse((self.root/'data/briefs/brief-bad.json').exists())

    def test_invalid_answer_is_rejected_before_persisting(self):
        row = self.create({'target': self.target()})
        for bad in ({'page_limit': 0}, {'page_limit': True}, {'market': 'Mars'}, {'required_exports': ['pdf']}):
            self.change(row, {'constraints': answered(bad)}, fail='error:')
        self.change(row, {'achievements': answered({'include_ids': ['E_1'], 'deemphasize_ids': ['E_1']})},
                    fail='both')
        self.assertEqual(self.command('show')['revision'], 1)

    def test_no_unknown_strengths_or_achievement_ids(self):
        self.pack()
        row = self.create({'target': self.target(), 'focus': answered({'strength_ids': ['invented']})})
        self.handoff(row, fail='unknown references')
        row = self.change(row, {'focus': empty('none'), 'achievements': answered({'deemphasize_ids': ['invented']})})
        self.handoff(row, fail='unknown IDs')
        self.assertFalse((self.root/'data/briefs').exists())

    def test_brief_is_consumed_by_existing_selection_with_no_fact_change(self):
        pack = self.pack()
        before = (self.root/'data/packs/accepted.json').read_bytes()
        eid = pack['evidence_atoms'][0]['id']
        row = self.create({'target': self.target(role_family='platform'),
                           'achievements': answered({'include_ids': [eid]}),
                           'review_mode': answered('interactive')})
        finished = self.handoff(row)
        proc = subprocess.run([sys.executable, str(ROOT/'scripts/editorial.py'), 'prepare',
                               '--brief', finished['handoff']['brief']['path'], '--id', 'selection-one',
                               '--output', 'data/selections/selection-one.json'], cwd=self.root,
                              env={**os.environ, 'CAREER_WORKSPACE': str(self.root), 'PYTHONDONTWRITEBYTECODE': '1'},
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout+proc.stderr)
        selection = json.loads((self.root/'data/selections/selection-one.json').read_text())
        self.assertIn(eid, selection['candidate_ids'])
        self.assertEqual(selection['review_status'], 'proposed')
        self.assertEqual((self.root/'data/packs/accepted.json').read_bytes(), before)

    def test_duplicate_brief_does_not_create_a_partial_handoff(self):
        first = self.handoff(self.create({'target': self.target()}))
        original = (self.root/first['handoff']['brief']['path']).read_bytes()
        other = self.create({'target': self.target()}, 'other')
        self.handoff(other, fail='already exists')
        self.assertEqual(self.command('show', '--session', other['session'])['status'], 'active')
        self.assertEqual((self.root/first['handoff']['brief']['path']).read_bytes(), original)

    def test_target_change_reopens_employer_constraints_without_losing_answers(self):
        constraints = answered({'market': 'UK', 'employer_instructions': 'Anonymous two-page application',
                                 'contact_mode': 'anonymous', 'page_limit': 2})
        row = self.create({'target': self.target(), 'constraints': constraints,
                           'focus': answered({'text': 'Technical judgement'}), 'review_mode': answered('interactive')})
        row = self.change(row, {'target': answered({'mode': 'role', 'description': 'Engineering director'})})
        self.assertIn('constraints', [q['id'] for q in row['questions']])
        self.assertEqual(row['context']['constraints_to_review'], constraints)
        self.assertEqual(row['answers']['review_mode']['value'], 'interactive')
        self.handoff(row, fail='previous employer constraints')
        row = self.command('back', '--session', row['session'], '--question', 'constraints')
        self.handoff(row, fail='previous employer constraints')
        row = self.change(row, {'constraints': answered({'market': 'UK'})})
        result = self.handoff(row)
        brief = json.loads((self.root/result['handoff']['brief']['path']).read_text())
        self.assertEqual(brief['application']['employer_instructions'], '')
        self.assertEqual(brief['application']['market'], 'UK')

    def test_reusing_brief_does_not_acknowledge_a_changed_job_description(self):
        self.write('data/sources/job.md', 'Original job')
        first = self.handoff(self.create({'target': answered({'mode': 'job_description', 'path': 'data/sources/job.md'})}))
        self.write('data/sources/job.md', 'Different job now')
        reused = self.create(None, 'reuse', '--brief', first['handoff']['brief']['path'])
        self.handoff(reused, 'brief-two', fail='changed input')


if __name__ == '__main__':
    unittest.main()
