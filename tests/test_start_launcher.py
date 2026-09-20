#!/usr/bin/env python3
"""Exercise the entry menu and process handoff without calling a real model."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import start


class Terminal(io.StringIO):
    def isatty(self):
        return True


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='career-launcher-')
        self.root = Path(self.temp.name) / 'fictional workspace'
        self.root.mkdir()
        shutil.copytree(ROOT / 'schemas', self.root / 'schemas')
        self.core = json.loads((ROOT / 'components/core/component.json').read_text())
        self.write('components/core/component.json', self.core)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value if isinstance(value, str) else json.dumps(value))
        return path

    def addon(self, version=None):
        self.write('components/resume/component.json', {
            'requires': {'career-core': version or self.core['version']},
            'career_schema_versions': self.core['career_schema_versions']})
        self.write('scripts/editorial.py', '# Fictional installed module')
        self.write('.claude/skills/make-resume/SKILL.md', '# Fictional installed skill')

    def session(self, kind='career', sid='first', revision=1, status='paused'):
        return self.write('reviews/startup/{}/{}/{:06d}.json'.format(kind, sid, revision), {
            'version': 1, 'flow': kind, 'session_id': sid, 'revision': revision,
            'updated_at': '2026-09-16T12:00:00Z', 'status': status,
            'answers': {}, 'context': {}, 'previous': None, 'handoff': None})

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def run_start(self, *args, inputs='', tty=True, nested=''):
        out, err = (Terminal() if tty else io.StringIO()), io.StringIO()
        incoming = Terminal(inputs) if tty else io.StringIO(inputs)
        with redirect_stdout(out), redirect_stderr(err), patch.object(sys, 'stdin', incoming), \
                patch.dict(os.environ, {'CLAUDECODE': nested}):
            code = start.main(list(args), root=self.root)
        return code, out.getvalue(), err.getvalue()

    def test_continue_lists_latest_revision_and_independent_review(self):
        from pack_io import pin
        from pack_review import session_catalog
        previous = None
        for rid in ('first-materials', 'correction-one', 'correction-two'):
            row = {'review_id': rid, 'created': '2026-09-18'}
            if previous:
                row['previous_review'] = pin(previous, self.root)
            previous = self.write('reviews/pack-reviews/'+rid+'/session.json', row)
        self.write('reviews/pack-reviews/independent/session.json', {'review_id':'independent','created':'2026-09-18'})
        saved, errors = start.saved_work(self.root, False)
        self.assertEqual(errors,0)
        self.assertEqual(len(saved),2)
        latest = next(r for r in saved if 'first-materials' in r['label'])
        self.assertIn('correction-two',latest['prompt'])
        self.assertEqual(len(session_catalog(self.root)),4)
        self.assertEqual(len(start.saved_work(self.root, False, history=True)[0]), 4)

    def test_review_branches_remain_distinguishable(self):
        from pack_io import pin
        original = self.write('reviews/pack-reviews/original/session.json', {'review_id':'original','created':''})
        for rid in ('branch-one','branch-two'):
            self.write('reviews/pack-reviews/'+rid+'/session.json', {'review_id':rid,'created':'', 'previous_review':pin(original,self.root)})
        saved, errors = start.saved_work(self.root,False)
        self.assertEqual(errors,0)
        self.assertEqual(len(saved),2)
        self.assertTrue(all('original (branch-' in r['label'] for r in saved))

    def test_changed_history_pin_does_not_hide_original(self):
        previous = self.write('reviews/pack-reviews/original/session.json', {'review_id':'original','created':''})
        self.write('reviews/pack-reviews/correction/session.json', {'review_id':'correction','created':'',
            'previous_review': {'path':str(previous.relative_to(self.root)), 'sha256':'0'*64}})
        saved, errors = start.saved_work(self.root,False)
        self.assertEqual(errors,1)
        self.assertEqual(len(saved),1)
        self.assertIn('original',saved[0]['prompt'])

    def test_core_only_offers_career_and_no_empty_continuation(self):
        with patch.object(start.subprocess, 'run') as child:
            code, out, _ = self.run_start(inputs='q\n')
        self.assertEqual(code, 0)
        self.assertIn('1. Build my career pack', out)
        self.assertNotIn('2. Create a resume', out)
        self.assertNotIn('Continue saved work', out)
        child.assert_not_called()

    def test_existing_pack_offers_update_first(self):
        self.write('data/packs/first.json', {'schema_version':'1.3','evidence_atoms':[]})
        code,out,_=self.run_start('--print-prompt',inputs='1\n')
        self.assertEqual(code,0)
        self.assertIn('1. Update my career pack',out)
        self.assertIn(start.PROMPTS['update'],out)

    def test_completed_setup_only_appears_in_history(self):
        self.session(status='handed_off')
        self.assertEqual(start.saved_work(self.root, False)[0], [])
        self.assertEqual(len(start.saved_work(self.root, False, history=True)[0]), 1)

    def test_broken_pack_chain_is_not_a_new_user(self):
        self.write('data/packs/broken.json', {'schema_version': '1.4',
            'metadata': {'supersedes': 'missing.json'}})
        code, out, err = self.run_start('--print-prompt', inputs='1\n')
        self.assertEqual(code, 1)
        self.assertIn('repair', (out + err).lower())
        self.assertNotIn('1. Build my career pack', out)

    def test_combined_installation_routes_each_new_path(self):
        self.addon()
        before = self.snapshot()
        for choice, phrase in [('1', start.PROMPTS['career']), ('2', start.PROMPTS['resume'])]:
            code, out, _ = self.run_start('--print-prompt', inputs=choice+'\n')
            self.assertEqual(code, 0)
            self.assertIn(phrase, out)
        self.assertEqual(self.snapshot(), before)

    def test_incompatible_addon_is_not_offered(self):
        self.addon(version='wrong')
        code, out, _ = self.run_start(inputs='q\n')
        self.assertEqual(code, 0)
        self.assertIn('requires career-core wrong', out)
        self.assertNotIn('2. Create a resume', out)
        self.assertEqual(self.run_start('--flow', 'resume', '--print-prompt')[0], 1)

    def test_latest_setup_revision_and_flow_names_disambiguate(self):
        self.addon()
        self.session(revision=1, status='active')
        self.session(revision=2, status='paused')
        self.session(kind='resume', status='paused')
        rows, errors = start.saved_work(self.root, True)
        self.assertEqual(errors, 0)
        self.assertEqual(len(rows), 2)
        self.assertTrue(any('(Paused)' in row['label'] and 'career pack' in row['label'] for row in rows))
        self.assertTrue(any('Continue my resume setup named "first".' == row['prompt'] for row in rows))

    def test_select_named_saved_work_without_numbered_json_paths(self):
        self.session(sid='first')
        self.session(sid='second')
        rows, _ = start.saved_work(self.root, False)
        before = self.snapshot()
        code, out, _ = self.run_start('--flow', 'continue', '--print-prompt', inputs='2\n')
        self.assertEqual(code, 0)
        self.assertIn(rows[1]['prompt'], out)
        self.assertNotIn('.json', out)
        self.assertEqual(self.snapshot(), before)

    def test_existing_review_can_be_continued_without_any_setup(self):
        self.write('reviews/pack-reviews/review-one/session.json', {
            'review_id': 'review-one', 'created': '2026-09-16'})
        code, out, _ = self.run_start('--flow', 'continue', '--print-prompt')
        self.assertEqual(code, 0)
        self.assertIn('Continue my career-pack review named "review-one".', out)
        self.assertFalse((self.root/'reviews/startup').exists())

    def test_corrupt_latest_revision_does_not_resume_an_old_answer(self):
        self.session()
        self.write('reviews/startup/career/first/000002.json', '{broken')
        rows, errors = start.saved_work(self.root, False)
        self.assertEqual(rows, [])
        self.assertEqual(errors, 1)
        self.assertIn('could not be read', self.run_start(inputs='q\n')[1])

    def test_external_symlink_is_not_read_as_a_session(self):
        outside = Path(self.temp.name)/'outside'
        outside.mkdir()
        (outside/'000001.json').write_text('{}')
        parent = self.root/'reviews/startup/career'
        parent.mkdir(parents=True)
        (parent/'external').symlink_to(outside, target_is_directory=True)
        self.assertEqual(start.saved_work(self.root, False), ([], 1))

    def test_core_does_not_offer_saved_resume_setup_without_addon(self):
        self.session(kind='resume')
        rows, _ = start.saved_work(self.root, False)
        self.assertEqual(rows, [])
        self.assertNotIn('Continue saved work', self.run_start(inputs='q\n')[1])

    def test_eof_and_invalid_choice_do_not_start_or_write_anything(self):
        before = self.snapshot()
        with patch.object(start.subprocess, 'run') as child:
            for inputs in ('', '9\nq\n'):
                self.assertEqual(self.run_start(inputs=inputs)[0], 0)
        child.assert_not_called()
        self.assertEqual(self.snapshot(), before)

    def test_missing_cli_and_nested_conversation_provide_a_prompt(self):
        with patch.object(start.shutil, 'which', return_value=None), patch.object(start.subprocess, 'run') as child:
            code, out, _ = self.run_start('--flow', 'career')
            self.assertEqual(code, 1)
            self.assertIn(start.PROMPTS['career'], out)
            self.assertIn('not found on PATH', out)
            code, out, _ = self.run_start('--flow', 'career', nested='1')
            self.assertEqual(code, 0)
            self.assertIn('Paste this prompt', out)
        child.assert_not_called()

    def test_noninteractive_use_never_opens_model_session(self):
        with patch.object(start.subprocess, 'run') as child:
            code, out, _ = self.run_start(tty=False)
            self.assertEqual(code, 0)
            self.assertIn(start.PROMPTS['career'], out)
        child.assert_not_called()

    def test_real_process_receives_prompt_and_workspace_without_shell(self):
        capture = Path(self.temp.name)/'invocation.json'
        fake = Path(self.temp.name)/'fake claude'
        fake.write_text('#!'+sys.executable+'\nimport json,os,sys\nfrom pathlib import Path\n'
                        'Path(os.environ["CAREER_LAUNCH_CAPTURE"]).write_text(json.dumps({"cwd":os.getcwd(),"args":sys.argv[1:]}))\n'
                        'raise SystemExit(7)\n')
        fake.chmod(0o755)
        with patch.object(start.shutil, 'which', return_value=str(fake)), \
                patch.dict(os.environ, {'CAREER_LAUNCH_CAPTURE': str(capture)}):
            code, _, _ = self.run_start('--flow', 'career')
        self.assertEqual(code, 7)
        self.assertEqual(json.loads(capture.read_text()), {
            'cwd': str(self.root.resolve()), 'args': [start.PROMPTS['career']]})


if __name__ == '__main__':
    unittest.main(verbosity=2)
