#!/usr/bin/env python3
"""Exercise the actual download in empty folders, with no Git, make or PDF tools."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from build_starter import build_starter, FOLDER
import desktop_setup
from pack_review import units, fingerprint


class StarterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build_dir = tempfile.TemporaryDirectory(prefix='starter-build-')
        cls.archive = build_starter(Path(cls.build_dir.name))

    @classmethod
    def tearDownClass(cls):
        cls.build_dir.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='starter-user-')
        self.addCleanup(self.temp.cleanup)
        with zipfile.ZipFile(self.archive) as archive:
            # A normal ZIP extraction, without our release tests' chmod helper.
            archive.extractall(self.temp.name)
        self.root = Path(self.temp.name) / FOLDER

    def run_tool(self, name, *args, success=True):
        result = subprocess.run([sys.executable, '-B', 'scripts/' + name, *args],
            cwd=self.root, capture_output=True, text=True,
            env={**os.environ, 'CAREER_WORKSPACE': str(self.root), 'PATH': '/no-developer-tools'})
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result.stdout

    def put(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content if isinstance(content, str) else json.dumps(content))

    def test_download_is_reproducible_and_contains_only_inventoried_public_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self.archive.read_bytes(), build_starter(Path(tmp)).read_bytes())
        with zipfile.ZipFile(self.archive) as archive:
            inventory_path = FOLDER + '/components/starter/inventory.json'
            inventory = json.loads(archive.read(inventory_path))
            expected = {FOLDER + '/' + name for name in inventory['files']} | {inventory_path}
            self.assertEqual(set(archive.namelist()), expected)
            self.assertEqual(len(archive.namelist()), len(expected))
            for name, digest in inventory['files'].items():
                self.assertNotIn(Path(name).parts[0], {'data', 'reviews', 'outputs', 'backups', '.git', '.agents', '.codex'})
                self.assertEqual(hashlib.sha256(archive.read(FOLDER + '/' + name)).hexdigest(), digest)
        self.assertTrue((self.root / 'START-HERE.html').is_file())
        self.assertTrue((self.root / '.claude/skills/build-career-pack/SKILL.md').is_file())
        self.assertTrue((self.root / '.claude/skills/make-resume/SKILL.md').is_file())

    def test_first_achievement_is_reviewed_saved_and_retrieved_after_reopening(self):
        ready = json.loads(self.run_tool('desktop_setup.py', '--prepare'))
        self.assertTrue(ready['ready'])
        self.assertTrue(os.access(self.root / 'scripts/extract_text.sh', os.X_OK))
        self.assertEqual(json.loads(self.run_tool('career_core.py', 'health', '--summary', '--json'))['state'], 'new')
        account = ('Fictional test account. My name is Avery Reed. I worked at Example Services as a '
                   'Support Specialist from January 2021 through December 2023 in London. '
                   'Customers asked the same questions. I wrote a guide and trained two colleagues. '
                   'Both colleagues used the guide. My manager led the wider project. We did not measure time saved.')
        self.put('data/private/account.txt', account)
        ref = {'source_id': 'SRC_ACCOUNT', 'excerpt': account}
        candidate = {
            'schema_version': '1.4', 'name': 'Avery Reed', 'purpose': 'Fictional starter acceptance test',
            'source_records': [{'source_id': 'SRC_ACCOUNT', 'source_type': 'person',
                'path': 'data/private/account.txt', 'retrieved': '2026-09-21', 'independent': False,
                'sha256': hashlib.sha256(account.encode()).hexdigest()}],
            'employment': [{'employment_id': 'EMP_SUPPORT', 'employer': 'Example Services',
                'employer_of_record': 'Example Services', 'title': 'Support Specialist',
                'start': '2021-01', 'end': '2023-12', 'location': 'London',
                'parent_employment_id': None, 'source_refs': [ref], 'evidence_status': 'self_asserted',
                'external_safe': False, 'corroborators': []}],
            'evidence_atoms': [{'id': 'E_GUIDE', 'title': 'Wrote a customer questions guide',
                'star': {'situation': 'Customers asked the same questions', 'task': None,
                         'action': 'Wrote a guide and trained two colleagues',
                         'result': 'Both colleagues used the guide'},
                'metrics': [], 'skills': [], 'source_refs': [ref], 'evidence_status': 'self_asserted',
                'external_safe': False, 'outcome_type': 'output', 'corroborators': [],
                'employment_id': 'EMP_SUPPORT', 'occurred': {'start': '2021-01', 'end': '2023-12', 'inferred': True}}],
        }
        self.put('data/candidates/proposal.json', candidate)
        self.run_tool('validate_pack.py', 'data/candidates/proposal.json')
        self.run_tool('career_core.py', 'review', 'start', '--candidate', 'data/candidates/proposal.json', '--id', 'first', '--records')
        self.assertFalse(list((self.root / 'data/packs').glob('*.json')), 'A proposal must not become accepted automatically')
        session = json.loads((self.root / 'reviews/pack-reviews/first/session.json').read_text())
        decisions = {'review_id': 'first', 'proposal_sha256': session['proposal']['sha256'],
            'reviewed_by': 'Avery Reed (scripted fictional test)', 'omissions': [],
            'decisions': [{'key': key, 'fingerprint': fingerprint(key, candidate), 'action': 'accept',
                'publication': 'private' if isinstance(record, dict) and 'external_safe' in record else 'unchanged',
                'note': ''} for key, record in units(candidate).items()]}
        self.put('data/private/decisions.json', decisions)
        accepted = json.loads(self.run_tool('career_core.py', 'review', 'apply', '--input', 'data/private/decisions.json'))
        self.assertIsNotNone(accepted['saved_pack'])
        self.assertIsNone(accepted['save_blocked'])
        saved = (self.root / accepted['saved_pack']).read_bytes()
        self.run_tool('career_core.py', 'view')
        # Each command starts a separate process and reloads all state from disk.
        state = json.loads(self.run_tool('career_core.py', 'health', '--summary', '--json'))
        self.assertEqual(state['saved'], {'roles': 1, 'achievements': 1})
        self.assertEqual(state['reading_page']['state'], 'current')
        self.assertIn('E_GUIDE', self.run_tool('find.py', 'guide'))
        self.run_tool('verify_excerpts.py', '--json')
        self.assertFalse(json.loads(saved)['evidence_atoms'][0]['external_safe'])
        self.assertIn('Wrote a customer questions guide', (self.root / 'outputs/career-record.html').read_text())
        # Repeating setup preserves both the accepted version and its source.
        self.run_tool('desktop_setup.py', '--prepare')
        self.assertEqual((self.root / accepted['saved_pack']).read_bytes(), saved)
        self.assertEqual((self.root / 'data/private/account.txt').read_text(), account)
        self.run_tool('career_core.py', 'backup', '--output', 'backups/first-save.zip')
        restored = Path(self.temp.name) / 'Restored Career'
        self.run_tool('career_core.py', 'restore', '--input', 'backups/first-save.zip', '--destination', str(restored))
        self.assertTrue((restored / 'START-HERE.html').is_file())
        self.assertTrue(desktop_setup.inspect(restored)['ready'])
        self.assertEqual((restored / accepted['saved_pack']).read_bytes(), saved)

    def test_missing_or_changed_application_is_blocked_without_overwriting_career_data(self):
        self.put('data/private/keep.txt', 'personal sentinel')
        (self.root / 'scripts/find.py').write_text('damaged download')
        report = json.loads(self.run_tool('desktop_setup.py', '--prepare', success=False))
        self.assertIn('changed', report['problems'][0])
        self.assertEqual((self.root / 'data/private/keep.txt').read_text(), 'personal sentinel')
        (self.root / 'scripts/find.py').unlink()
        report = json.loads(self.run_tool('desktop_setup.py', success=False))
        self.assertIn('missing', report['problems'][0])

    def test_setup_repairs_zip_permissions_so_a_text_cv_can_be_read(self):
        extractor = self.root / 'scripts/extract_text.sh'
        extractor.chmod(0o644)
        self.run_tool('desktop_setup.py', '--prepare')
        self.put('data/sources/cv.txt', 'Fictional CV: wrote a customer guide.')
        result = subprocess.run([sys.executable, '-B', 'scripts/career_core.py', 'intake', 'data/sources/cv.txt'],
            cwd=self.root, capture_output=True, text=True, env={**os.environ, 'CAREER_WORKSPACE': str(self.root)})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        reports = list((self.root / 'reviews/intake').glob('*.json'))
        self.assertEqual(len(reports), 1)
        self.assertEqual(json.loads(reports[0].read_text())['sources'][0]['status'], 'read')

    def test_old_python_and_native_windows_are_not_reported_as_ready(self):
        with patch.object(desktop_setup.sys, 'version_info', (3, 8)):
            self.assertIn('Python', desktop_setup.inspect(self.root)['problems'][0])
        with patch.object(desktop_setup.sys, 'platform', 'win32'):
            report = desktop_setup.inspect(self.root)
            self.assertFalse(report['ready'])
            self.assertIn('Windows', report['problems'][0])

    def test_private_directory_symlink_cannot_redirect_setup_outside_folder(self):
        outside = Path(self.temp.name) / 'outside'
        outside.mkdir()
        (self.root / 'data').symlink_to(outside, target_is_directory=True)
        report = json.loads(self.run_tool('desktop_setup.py', '--prepare', success=False))
        self.assertIn('unexpected path', report['problems'][0])
        self.assertEqual(list(outside.iterdir()), [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
