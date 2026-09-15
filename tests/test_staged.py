#!/usr/bin/env python3
"""Pre-commit checks use staged content and exclude private worktree state."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/'scripts'))
import check_staged


class StagedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='career-index-test-')
        self.root = Path(self.tmp.name)/'repo'
        self.root.mkdir()
        self.git('init', '-q')

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True,
                              capture_output=True, env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')})

    def write(self, name, text):
        path = self.root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def test_snapshot_includes_staged_version_and_excludes_private_worktree(self):
        self.write('README.md', 'staged version')
        self.git('add', 'README.md')
        self.write('README.md', 'unstaged edit')
        self.write('outputs/private-evaluation.json', '{broken')
        self.write('data/sources/private.txt', 'PRIVATE_CANARY')
        out = Path(self.tmp.name)/'snapshot'
        out.mkdir()
        check_staged.snapshot(self.root, out)
        self.assertEqual((out/'README.md').read_text(), 'staged version')
        self.assertFalse((out/'outputs').exists())
        self.assertFalse((out/'data').exists())

    def test_private_inputs_and_backups_are_blocked_before_snapshot(self):
        for name in ('data/sources/a.txt', 'outputs/result.json', 'reviews/a.json',
                     'backups/private.zip', 'archive/old.tar', 'resume_information/notes.md'):
            with self.subTest(name=name):
                self.write(name, 'private')
                self.git('add', '-f', name)
                with self.assertRaisesRegex(ValueError, 'private material'):
                    check_staged.snapshot(self.root, Path(self.tmp.name)/'snapshot')
                self.git('rm', '--cached', '--', name)

    def test_only_exact_placeholders_are_allowed(self):
        self.write('data/packs/.gitkeep', '')
        self.git('add', '-f', 'data/packs/.gitkeep')
        check_staged.check_private_paths(check_staged.index_paths(self.root))
        self.write('data/private/nested/.gitkeep', 'secret')
        self.git('add', '-f', 'data/private/nested/.gitkeep')
        with self.assertRaises(ValueError):
            check_staged.check_private_paths(check_staged.index_paths(self.root))

    def test_staged_failure_cannot_be_hidden_by_unstaged_fix(self):
        self.write('Makefile', 'check:\n\t@python3 -c "raise SystemExit(1)"\n')
        self.git('add', 'Makefile')
        self.write('Makefile', 'check:\n\t@true\n')
        self.assertNotEqual(check_staged.check(self.root), 0)

    def test_private_content_cannot_hide_in_an_allowed_placeholder(self):
        self.write('data/packs/.gitkeep', 'private career facts')
        self.git('add', '-f', 'data/packs/.gitkeep')
        with self.assertRaisesRegex(ValueError, 'placeholder must be empty'):
            check_staged.snapshot(self.root, Path(self.tmp.name)/'snapshot')

    def test_live_environment_and_invalid_outputs_do_not_redirect_checks(self):
        self.write('Makefile', 'check:\n\t@python3 -c "import os; assert not os.environ.get(\'CAREER_WORKSPACE\'); assert not os.path.exists(\'outputs/private.json\')"\n')
        self.git('add', 'Makefile')
        self.write('outputs/private.json', '{invalid')
        with patch.dict(os.environ, {'CAREER_WORKSPACE': str(self.root)}):
            self.assertEqual(check_staged.check(self.root), 0)


if __name__ == '__main__':
    unittest.main()
