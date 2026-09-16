#!/usr/bin/env python3
"""Exercise guided starts via the real CLI in empty fictional workspaces."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


def answered(value, origin='user'):
    return {'state': 'answered', 'origin': origin, 'value': value}


def empty(state):
    return {'state': state, 'origin': 'user', 'value': None}


class StartupCase(unittest.TestCase):
    entry = 'career_core.py'

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='fictional-startup-')
        self.root = Path(self.tmp.name)
        shutil.copytree(ROOT/'schemas', self.root/'schemas')
        (self.root/'data/private').mkdir(parents=True)
        self.seq = 0

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, path, value):
        out = self.root/path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(value) if not isinstance(value, str) else value)
        return path

    def command(self, *args, fail=None):
        proc = subprocess.run([sys.executable, str(ROOT/'scripts'/self.entry), 'start', *args],
                              cwd=self.root, capture_output=True, text=True,
                              env={**os.environ, 'CAREER_WORKSPACE': str(self.root), 'PYTHONDONTWRITEBYTECODE': '1'})
        if fail:
            self.assertNotEqual(proc.returncode, 0, proc.stdout)
            self.assertIn(fail, proc.stderr)
            return proc
        self.assertEqual(proc.returncode, 0, proc.stdout+proc.stderr)
        return json.loads(proc.stdout)

    def create(self, answers=None, sid='first', *args):
        flags = []
        if answers is not None:
            self.seq += 1
            flags = ['--answers', self.write('data/private/answers-{}.json'.format(self.seq), answers)]
        return self.command('create', '--id', sid, *flags, *args)

    def change(self, session, values, fail=None):
        self.seq += 1
        path = self.write('data/private/answers-{}.json'.format(self.seq), values)
        return self.command('answer', '--session', session['session'], '--input', path, fail=fail)

    def pack(self):
        record = json.loads((ROOT/'examples/career.example.json').read_text())
        self.write('data/packs/accepted.json', record)
        return record


class CareerStartupTests(StartupCase):
    def test_empty_workspace_does_not_create_facts(self):
        row = self.create()
        self.assertEqual(row['context']['inventory'], [])
        self.assertEqual([q['id'] for q in row['questions']], ['route'])
        self.assertFalse((self.root/'data/packs').exists())
        self.assertFalse((self.root/'data/candidates').exists())
        self.assertTrue((self.root/row['summary']).is_file())

    def test_explicit_scope_excludes_context_and_future_sources(self):
        choices = []
        for name, purpose in [('resume.md', 'career_evidence'), ('job.md', 'job_context'),
                              ('guide.md', 'writing_reference'), ('later.md', 'defer')]:
            self.write('data/sources/'+name, '# Fictional material')
            choices.append({'path': 'data/sources/'+name, 'purpose': purpose})
        row = self.create({'route': answered('existing'), 'sources': answered(choices)})
        self.write('data/sources/new.md', '# A source added after selection')
        result = self.command('handoff', '--session', row['session'])
        handoff = result['handoff']
        self.assertEqual([s['path'] for s in handoff['career_sources']], ['data/sources/resume.md'])
        self.assertEqual(len(handoff['context_sources']), 2)
        self.assertEqual(handoff['deferred_sources'], ['data/sources/later.md'])
        self.assertFalse(handoff['external_safe_default'])
        self.assertFalse((self.root/'data/packs').exists())

    def test_resume_preserves_none_later_and_not_applicable(self):
        values = {'route': answered('gather'), 'missing_work': empty('none'),
                  'restrictions': empty('later'), 'materials': answered({
                      'public_work': {'state': 'none'}, 'linkedin': {'state': 'not_applicable'},
                      'reviews': {'state': 'later', 'detail': 'Find last year’s review'}})}
        row = self.create(values)
        paused = self.command('pause', '--session', row['session'])
        self.assertEqual(paused['questions'], [])
        self.assertEqual(paused['continue_prompt'], 'Continue my career pack setup named "first".')
        self.assertIn('saved', paused['saved'])
        import html
        page = html.unescape((self.root/paused['summary']).read_text())
        self.assertIn(paused['continue_prompt'], page)
        self.assertIn('<h1>Build my career pack</h1>', page)
        resumed = self.command('resume')
        self.assertEqual(resumed['answers'], values)
        self.assertEqual(resumed['questions'], [])
        finished = self.command('handoff')
        self.assertEqual(finished['handoff']['action'], 'gather_sources')
        self.assertEqual(finished['handoff']['materials'], values['materials'])
        self.assertEqual(finished['continue_prompt'], 'Continue building my career pack from saved setup named "first".')
        self.assertNotEqual(finished['continue_prompt'], paused['continue_prompt'])

    def test_back_reopens_only_requested_question_and_keeps_history(self):
        row = self.create({'route': answered('gather'), 'missing_work': empty('skipped'),
                           'restrictions': empty('none'), 'materials': empty('later')})
        old = (self.root/row['session']).read_bytes()
        new = self.command('back', '--session', row['session'], '--question', 'missing_work')
        self.assertEqual([q['id'] for q in new['questions']], ['missing_work'])
        self.assertEqual((self.root/row['session']).read_bytes(), old)
        self.assertEqual(new['previous']['sha256'], hashlib.sha256(old).hexdigest())
        self.change(row, {'missing_work': answered('Old edit')}, fail='latest')

    def test_changed_source_requires_explicit_reselection_even_after_refresh(self):
        self.write('data/sources/resume.md', 'Original')
        values = {'route': answered('existing'), 'sources': answered([
            {'path': 'data/sources/resume.md', 'purpose': 'career_evidence'}])}
        row = self.create(values)
        self.write('data/sources/resume.md', 'Changed')
        row = self.command('refresh', '--session', row['session'])
        self.command('handoff', '--session', row['session'], fail='changed input')
        row = self.change(row, {'sources': values['sources']})
        self.assertEqual(self.command('handoff', '--session', row['session'])['handoff']['action'], 'ingest_candidates')

    def test_no_documents_preserves_exact_account_without_acceptance(self):
        text = 'I mentored two engineers. <script>alert("x")</script> & café'
        row = self.create({'route': answered('conversation'), 'career_story': answered(text)})
        result = self.command('handoff', '--session', row['session'])
        self.assertEqual(result['handoff']['user_accounts'][0]['text'], text)
        page = (self.root/result['summary']).read_text()
        self.assertIn('&lt;script&gt;', page)
        self.assertNotIn('<script>', page)
        self.assertFalse((self.root/'data/packs').exists())
        self.assertFalse((self.root/'data/sources').exists())

    def test_assistant_guess_is_not_a_user_account(self):
        row = self.create({'route': answered('conversation'),
                           'career_story': answered('Perhaps you led a team', 'inferred')})
        self.command('handoff', '--session', row['session'], fail='no career material')

    def test_multiple_starts_require_specific_resume(self):
        first = self.create(sid='first')
        self.create(sid='second')
        self.command('resume', fail='2 unfinished')
        self.assertEqual(self.command('show', '--session', first['session'])['session_id'], 'first')

    def test_invalid_inputs_do_not_advance_revision(self):
        row = self.create()
        self.change(row, {'route': answered('unknown')}, fail='choose')
        self.change(row, {'extra': answered('unknown')}, fail='known question')
        self.change(row, {'route': {'state': 'none', 'origin': 'user', 'value': 'existing'}},
                    fail='null value')
        self.assertEqual(self.command('show')['revision'], 1)
        self.command('create', '--id', '../escape', fail='ID')

    def test_external_source_and_symlink_are_rejected(self):
        self.write('outside.md', 'Not in Sources')
        self.change(self.create(), {'sources': answered([
            {'path': 'outside.md', 'purpose': 'career_evidence'}])}, fail='inside data/sources')
        directory = self.root/'data/sources'
        directory.mkdir()
        (directory/'link.md').symlink_to(self.root/'outside.md')
        row = self.command('refresh')
        self.assertEqual(row['context']['inventory'], [])
        self.change(row, {'sources': answered([
            {'path': 'data/sources/link.md', 'purpose': 'career_evidence'}])}, fail='inside data/sources')

    def test_finished_setup_can_be_reopened_without_reasking_saved_answers(self):
        row = self.create({'route': answered('gather'), 'materials': empty('none'),
                           'missing_work': empty('none'), 'restrictions': empty('skipped')})
        row = self.command('handoff')
        self.command('resume', '--session', row['session'], fail='handed off')
        refreshed = self.command('refresh', '--session', row['session'])
        self.assertEqual(refreshed['questions'], [])
        self.assertEqual(refreshed['answers'], row['answers'])


if __name__ == '__main__':
    unittest.main()
