"""Real Git lifecycle against a local bare remote; no accounts or personal data."""
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
import github_workspace as github
from workspace_setup import create
from editorial_fixture import pack_for, personas


class GitHubWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='career-github-test-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / 'source'
        create(self.source, tool=ROOT)
        pack = pack_for(personas()[0]); pack['metadata'] = {}
        self.pack = pack
        self.write(self.source, 'data/packs/first.json', json.dumps(pack))
        self.write(self.source, 'reviews/onboarding.md', pack['evidence_atoms'][0]['source_refs'][0]['excerpt'])
        self.write(self.source, 'data/capture/notes.jsonl', '{"note":"Unreviewed fictional note"}\n')
        self.identity = patch.dict(os.environ, {'GIT_AUTHOR_NAME':'Fictional Author',
            'GIT_COMMITTER_NAME':'Fictional Author', 'GIT_AUTHOR_EMAIL':'fictional@example.invalid',
            'GIT_COMMITTER_EMAIL':'fictional@example.invalid'})
        self.identity.start(); self.addCleanup(self.identity.stop)
        self.workspace = self.base / 'personal'
        self.repo = 'fictional/career'
        self.remote = self.base / 'remote.git'
        self.real_git = github.git
        self.real_git('init', '--bare', '-b', 'main', str(self.remote), root=self.base)

    def write(self, root, name, content):
        path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(content)
        return path

    def prepared(self):
        github.prepare(self.workspace, self.repo, self.source)
        return self.workspace

    def transport(self, *args, root=github.ROOT, env=None, check=True):
        # Substitute only network transport; local staging, commits, hooks,
        # cloning and ancestry checks still use the real Git executable.
        if args[0] == 'ls-remote':
            return self.real_git('ls-remote', '--heads', str(self.remote), root=root)
        if args[0] == 'fetch':
            return self.real_git('fetch', str(self.remote), '+refs/heads/*:refs/remotes/origin/*', root=root)
        if args[0] == 'push':
            github.remote_guard(root)  # Online policy is tested separately below.
            result = self.real_git('-c', 'core.hooksPath=/dev/null', 'push', str(self.remote), 'HEAD:refs/heads/main', root=root)
            self.real_git('update-ref', 'refs/remotes/origin/main', 'HEAD', root=root)
            return result
        if args[0] == 'clone':
            result = self.real_git('clone', '--branch', 'main', str(self.remote), args[-1], root=root)
            self.real_git('remote', 'set-url', 'origin', 'https://github.com/' + self.repo + '.git', root=Path(args[-1]))
            return result
        return self.real_git(*args, root=root, env=env, check=check)

    def network(self):
        self.addCleanup(patch.stopall)
        patch.object(github, 'private_repository', return_value={'private':True}).start()
        patch.object(github, 'git', side_effect=self.transport).start()

    def test_prepare_preserves_records_excludes_credentials_and_uploads_nothing(self):
        secret = self.write(self.source, 'data/sources/.env', 'FICTIONAL_SECRET')
        self.write(self.source, '.claude/settings.local.json', '{}')
        original = (self.source / 'data/packs/first.json').read_bytes()
        result = github.prepare(self.workspace, self.repo, self.source)
        self.assertFalse(result['uploaded'])
        self.assertEqual((self.workspace / 'data/packs/first.json').read_bytes(), original)
        self.assertEqual((self.source / 'data/packs/first.json').read_bytes(), original)
        self.assertTrue(secret.exists())
        self.assertFalse((self.workspace / 'data/sources/.env').exists())
        self.assertFalse((self.workspace / '.claude/settings.local.json').exists())
        self.assertEqual((self.workspace / 'CAREER.md').read_bytes(), (self.workspace / 'outputs/career.md').read_bytes())
        self.assertIn('data/capture/notes.jsonl', github.preview(self.workspace)['files'])
        self.assertEqual(github.status(root=self.workspace)['state'], 'not_connected')
        self.assertEqual(self.real_git('remote', root=self.workspace).stdout, '')

    def test_create_save_clone_resume_and_conflict(self):
        root = self.prepared(); self.network()
        github.connect(root=root)
        self.assertEqual(github.sync(root=root)['state'], 'current')
        clone = self.base / 'other-machine'
        github.clone(self.repo, clone, root=self.source)
        self.assertEqual((clone / 'data/packs/first.json').read_bytes(), (root / 'data/packs/first.json').read_bytes())
        self.assertEqual((clone / 'data/capture/notes.jsonl').read_bytes(), (root / 'data/capture/notes.jsonl').read_bytes())
        self.assertEqual(self.real_git('config', 'core.hooksPath', root=clone).stdout.strip(), github.HOOKS)
        self.write(clone, 'data/capture/second.jsonl', '{"note":"Second-machine note"}\n')
        github.sync(root=clone)
        self.assertEqual(github.status(True, root)['state'], 'remote_changes')
        head = self.real_git('rev-parse', 'HEAD', root=root).stdout
        with self.assertRaisesRegex(ValueError, 'GitHub has changes'):
            github.sync(root=root)
        self.assertEqual(self.real_git('rev-parse', 'HEAD', root=root).stdout, head)
        github.pull(root)
        self.assertTrue((root / 'data/capture/second.jsonl').exists())
        # Independent commits must never be merged automatically.
        for folder, name in [(root, 'local'), (clone, 'remote')]:
            self.write(folder, 'data/capture/' + name + '.txt', name)
            self.real_git('add', '--all', root=folder)
            self.real_git('commit', '-m', name, root=folder)
        github.sync(root=clone)
        self.assertEqual(github.status(True, root)['state'], 'diverged')
        with self.assertRaisesRegex(ValueError, 'GitHub has changes'):
            github.sync(root=root)

    def test_no_pack_can_sync_pending_work(self):
        (self.source / 'data/packs/first.json').unlink()
        root = self.prepared(); self.network()
        github.connect(root=root); github.sync(root=root)
        self.assertIn('No career pack has been accepted', (root / 'CAREER.md').read_text())
        self.assertIn('Unreviewed', self.real_git('show', 'HEAD:data/capture/notes.jsonl', root=root).stdout)

    def test_staged_missing_source_and_stale_overview_block_commit(self):
        root = self.prepared()
        self.real_git('add', '--all', root=root)
        self.real_git('rm', '--cached', 'reviews/onboarding.md', root=root)
        with self.assertRaisesRegex(ValueError, 'missing reference'):
            github.check_staged(root)
        self.real_git('add', '--all', root=root)
        self.write(root, 'CAREER.md', 'A stale or manually edited view')
        self.real_git('add', 'CAREER.md', root=root)
        with self.assertRaisesRegex(ValueError, 'stale'):
            github.check_staged(root)

    def test_git_hook_ignores_another_workspaces_environment(self):
        root = self.prepared()
        self.real_git('add', '--all', root=root)
        result = subprocess.run(['git','commit','-m','Fictional workspace snapshot'], cwd=root,
            env=dict(os.environ, CAREER_WORKSPACE=str(self.source)), text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_symlinks_unknown_files_and_forced_credentials_block_commit(self):
        root = self.prepared()
        self.real_git('add', '--all', root=root)
        for name in ('data/sources/.env', 'unexpected.txt'):
            self.write(root, name, 'Fictional excluded file')
            self.real_git('add', '-f', name, root=root)
            with self.assertRaisesRegex(ValueError, 'excluded staged path'):
                github.check_staged(root)
            self.real_git('rm', '--cached', name, root=root)
            (root / name).unlink()
        (root / 'data/sources/link').symlink_to(root / 'README.md')
        self.real_git('add', 'data/sources/link', root=root)
        with self.assertRaisesRegex(ValueError, 'excluded staged path'):
            github.check_staged(root)

    def test_remote_visibility_and_push_url_are_checked(self):
        root = self.prepared()
        self.real_git('remote', 'add', 'origin', 'https://github.com/' + self.repo + '.git', root=root)
        for info in ({'private':False}, {'private':True,'fork':True}, {'private':True,'archived':True}):
            response = subprocess.CompletedProcess([],0,json.dumps({'full_name':self.repo, **info}),'')
            with patch.object(github, 'run', return_value=response), self.assertRaisesRegex(ValueError, 'private GitHub'):
                github.private_repository(self.repo, root)
        self.real_git('remote', 'set-url', '--add', '--push', 'origin', 'https://github.com/other/public.git', root=root)
        with self.assertRaisesRegex(ValueError, 'Origin does not match'):
            github.remote_guard(root, online=False)

    def test_prepare_refuses_overwrite_and_missing_references(self):
        self.workspace.mkdir()
        with self.assertRaisesRegex(ValueError, 'new workspace'):
            github.prepare(self.workspace, self.repo, self.source)
        (self.source / 'reviews/onboarding.md').unlink()
        with self.assertRaisesRegex(ValueError, 'broken references'):
            github.prepare(self.base / 'missing', self.repo, self.source)
        self.assertFalse((self.base / 'missing').exists())

    def test_populated_remote_needs_clone_and_failed_push_keeps_commit(self):
        root = self.prepared(); self.network()
        github.connect(root=root)
        transport = self.transport
        def fail_push(*args, **kwargs):
            if args[0] == 'push': raise ValueError('Fictional network failure')
            return transport(*args, **kwargs)
        with patch.object(github, 'git', side_effect=fail_push), self.assertRaisesRegex(ValueError, 'network failure'):
            github.sync(root=root)
        self.assertEqual(self.real_git('rev-parse', '--verify', 'HEAD', root=root).returncode, 0)
        github.sync(root=root)
        second = self.base / 'second'
        github.prepare(second, self.repo, self.source)
        with self.assertRaisesRegex(ValueError, 'already contains history'):
            github.connect(root=second)

    def test_create_requests_private_repository_and_does_not_push(self):
        root = self.prepared()
        original = github.run
        calls = []
        def commands(args, *other, **kwargs):
            if args[0] == 'gh':
                calls.append(args)
                output = json.dumps({'full_name':self.repo, 'private':True, 'fork':False}) if args[1] == 'api' else ''
                return subprocess.CompletedProcess(args, 0, output, '')
            return original(args, *other, **kwargs)
        with patch.object(github, 'run', side_effect=commands), patch.object(github, 'git', side_effect=self.transport):
            self.assertFalse(github.connect(create=True, root=root)['uploaded'])
        self.assertIn(['gh','repo','create',self.repo,'--private'], calls)
        self.assertEqual(self.real_git('show-ref', root=self.remote, check=False).returncode, 1)

    def test_github_output_round_trips_through_offline_backup(self):
        from workspace_backup import backup_workspace, restore_workspace
        root = self.prepared()
        archive = backup_workspace(self.base / 'backup.zip', root)
        restored = restore_workspace(archive, self.base / 'restored', root)
        for name in ('CAREER.md', '.gitattributes', github.CONFIG, 'data/packs/first.json', 'data/capture/notes.jsonl'):
            self.assertEqual((root / name).read_bytes(), (restored / name).read_bytes())
        self.assertFalse((restored / '.git').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
