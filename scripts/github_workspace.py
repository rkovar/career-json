#!/usr/bin/env python3
"""Prepare, connect and synchronize a private GitHub career workspace."""
import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from current_pack import ROOT, resolve
from pack_io import workspace_lock
from workspace_backup import PRIVATE, PUBLIC, ROOT_FILES, backup_workspace, restore_workspace, reference_audit

CONFIG = 'components/workspace/github.json'
HOOKS = 'scripts/github_hooks'
IGNORE = '''# Personal career workspace: career records and sources are intentionally tracked.
.DS_Store
__pycache__/
*.pyc
*.tmp
*.swp
node_modules/
.env
.env.*
.git-credentials
.netrc
id_rsa
id_ed25519
backups/
dist/
reviews/.pack-write.lock
.claude/settings.local.json
'''


def run(args, root=ROOT, env=None, check=True):
    result = subprocess.run(args, cwd=root, env=env, text=True, capture_output=True)
    if check and result.returncode:
        raise ValueError((result.stderr or result.stdout or 'Command failed: ' + args[0]).strip())
    return result


def git(*args, root=ROOT, env=None, check=True):
    git_env = dict(os.environ if env is None else env, CAREER_WORKSPACE=str(root.resolve()))
    return run(['git', *args], root, git_env, check)


def repository(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9][A-Za-z0-9_.-]*', value):
        raise ValueError('Use a GitHub repository name in OWNER/NAME form.')
    return value


def config(root=ROOT):
    value = json.loads((root / CONFIG).read_text())
    if value.get('format') != 'career-github-workspace' or value.get('version') != 1:
        raise ValueError('Unsupported GitHub workspace configuration.')
    repository(value.get('repository'))
    if value.get('branch') != 'main':
        raise ValueError('This workspace requires its configured main branch.')
    return value


def private_repository(repo, root=ROOT):
    value = json.loads(run(['gh', 'api', '--hostname', 'github.com', 'repos/' + repository(repo)], root).stdout)
    if (value.get('full_name', '').lower() != repo.lower() or value.get('private') is not True
            or value.get('fork') or value.get('archived')):
        raise ValueError('The destination must be an independent, writable private GitHub repository.')
    return value


def git_root(root=ROOT):
    if Path(git('rev-parse', '--show-toplevel', root=root).stdout.strip()).resolve() != root.resolve():
        raise ValueError('Use a separate Git repository rooted in this career workspace.')


def remote_guard(root=ROOT, online=True, remote='origin', url=None):
    cfg = config(root)
    git_root(root)
    repo = cfg['repository']
    urls = {f'https://github.com/{repo}', f'https://github.com/{repo}.git',
            f'git@github.com:{repo}', f'git@github.com:{repo}.git',
            f'ssh://git@github.com/{repo}', f'ssh://git@github.com/{repo}.git'}
    if remote != 'origin' or (url is not None and url not in urls):
        raise ValueError('Only the configured private origin is allowed.')
    for args in [('remote', 'get-url', '--all', 'origin'), ('remote', 'get-url', '--push', '--all', 'origin')]:
        found = git(*args, root=root).stdout.splitlines()
        if not found or any(item not in urls for item in found):
            raise ValueError('Origin does not match the configured private career repository.')
    if online:
        private_repository(repo, root)
    return cfg


def excluded(name):
    parts = Path(name).parts
    return (any(p in ('__pycache__', 'node_modules', 'backups', 'dist') for p in parts)
            or any(p == '.env' or p.startswith('.env.') for p in parts)
            or Path(name).name in ('.DS_Store', '.git-credentials', '.netrc', 'id_rsa', 'id_ed25519', '.pack-write.lock')
            or name == '.claude/settings.local.json'
            or Path(name).suffix in ('.pyc', '.tmp', '.swp'))


def permitted(name):
    path = Path(name)
    return (not path.is_absolute() and '..' not in path.parts and not excluded(name)
            and (path.parts[0] in PRIVATE + PUBLIC or name in ROOT_FILES))


def check_workspace(root=ROOT):
    from schema_tools import walk
    from validate_pack import check
    from career_state import history_errors
    errors = reference_audit(root)['errors']
    for path in sorted((root / 'data/packs').glob('*.json')):
        pack = json.loads(path.read_text())
        schema = json.loads((root / ('schemas/archive/career-1.3.schema.json'
                            if pack.get('schema_version') == '1.3' else 'schemas/career.schema.json')).read_text())
        structural = []
        walk(pack, schema, schema, path.name, structural)
        errors.extend(structural)
        if not structural:
            errors.extend(check(path, schema, root=root)[0])
    head = resolve(root / 'data/packs', root)
    errors.extend(history_errors(head, root))
    if errors:
        raise ValueError('Workspace references or records need repair: ' + '; '.join(dict.fromkeys(errors)))
    return head


def overview():
    from career_markdown import refresh
    head = check_workspace()
    if head:
        refresh(head)
        text = (ROOT / 'outputs/career.md').read_text()
    else:
        text = '# My career record\n\nNo career pack has been accepted yet. Captured notes and pending reviews are saved separately.\n'
    from pack_io import write_view
    write_view(ROOT / 'CAREER.md', text)


def invoke(root, command):
    env = dict(os.environ, CAREER_WORKSPACE=str(root), PYTHONDONTWRITEBYTECODE='1')
    for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR'):
        env.pop(key, None)
    return run([sys.executable, '-B', str(root / 'scripts/github_workspace.py'), command], root, env)


def readme(repo):
    return f'''# My private career workspace

**[Read my complete career record](CAREER.md)** · [Workspace guide](docs/github-workspace.md)

This repository, [{repo}](https://github.com/{repo}), contains career records,
sources, pending notes, review history and generated documents. Keep it private.
Saving to GitHub does not accept a claim or permit its external use.

Run `make start` to continue career work. JSON records are authoritative;
`CAREER.md` is regenerated from the accepted pack and does not sync edits back.
Open `outputs/career-record.html` locally for the browser view; GitHub shows its source.

| Command | Purpose |
| --- | --- |
| `make status` | Check local changes and GitHub status |
| `make sync` | Validate, refresh the record, commit and push |
| `make pull` | Get remote changes when the working tree is clean |
| `make check` | Validate career records and source/history references |
| `make overview` | Refresh the Markdown and browser views |
| `make hooks` | Restore private-workspace Git hooks after cloning |

Clone this repository on another machine, run `make hooks`, then `make start`.
Use GitHub CLI authentication (`gh auth login`) for sync. Python 3.9+, Git and
GitHub CLI are required; conversational workflows also need Claude Code.

Installed component versions are recorded under `components/`. Upgrade the tool
deliberately, retaining career files and history. See the workspace guide for recovery.
'''


def prepare(destination, repo, root=ROOT):
    repo = repository(repo)
    target = Path(destination).expanduser().absolute()
    if target.exists() or target.is_symlink() or target.resolve().is_relative_to(root.resolve()):
        raise ValueError('Choose a new workspace directory outside the current workspace.')
    if (root / CONFIG).exists():
        raise ValueError('This is already a GitHub workspace. Use connect, sync or clone.')
    # Reuse the portable archive contract: validated references, one stable
    # snapshot, no Git history from the application repository.
    with tempfile.TemporaryDirectory(prefix='career-github-') as temp:
        archive = backup_workspace(Path(temp) / 'workspace.zip', root)
        staged = restore_workspace(archive, Path(temp) / 'workspace', root)
        for path in sorted(staged.rglob('*'), reverse=True):
            if path.is_file() and excluded(str(path.relative_to(staged))):
                path.unlink()
        (staged / 'CAREER-OVERVIEW.html').unlink(missing_ok=True)
        versions = {path.parent.name: json.loads(path.read_text())['version']
                    for path in staged.glob('components/*/component.json')}
        runtime = {str(path.relative_to(staged)): hashlib.sha256(path.read_bytes()).hexdigest()
                   for folder in ('scripts', 'schemas', '.claude')
                   for path in (staged / folder).rglob('*') if path.is_file()}
        cfg = {'format': 'career-github-workspace', 'version': 1, 'repository': repo, 'branch': 'main',
               'components': versions, 'prepared_runtime_sha256': runtime}
        (staged / CONFIG).parent.mkdir(parents=True, exist_ok=True)
        (staged / CONFIG).write_text(json.dumps(cfg, indent=2) + '\n')
        (staged / '.gitignore').write_text(IGNORE)
        (staged / '.gitattributes').write_text('* -text\n')
        (staged / 'README.md').write_text(readme(repo))
        (staged / 'Makefile').write_text('''# Personal workspace commands
.PHONY: start hooks status sync pull check overview
start: hooks
	@python3 scripts/start.py
hooks:
	@python3 scripts/career_core.py github hooks
status:
	@python3 scripts/career_core.py github status --fetch
sync:
	@python3 scripts/career_core.py github sync
pull:
	@python3 scripts/career_core.py github pull
check:
	@python3 scripts/career_core.py github check
overview:
	@python3 scripts/career_core.py github overview
''')
        invoke(staged, 'overview')
        # Initialize only after all source and generated-view checks pass.
        git('init', '-b', 'main', root=staged)
        install_hooks(staged)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.mkdir(mode=0o700)
        try:
            for child in staged.iterdir():
                shutil.move(str(child), str(target / child.name))
        except BaseException:
            shutil.rmtree(target)
            raise
    return {'workspace': str(target), 'repository': repo, 'uploaded': False,
            'next': 'Continue career work in this directory. Run github preview, then github connect --create (or connect for an empty private repository), then github sync.',
            'source': 'The original workspace is unchanged; retain it for recovery and stop editing it after switching.'}


def install_hooks(root=ROOT):
    config(root)
    git_root(root)
    git('config', 'core.hooksPath', HOOKS, root=root)
    git('config', 'core.autocrlf', 'false', root=root)
    git('config', 'pull.ff', 'only', root=root)
    for name in ('pre-commit', 'pre-push'):
        (root / HOOKS / name).chmod(0o700)


def connect(create=False, root=ROOT):
    cfg = config(root)
    git_root(root)
    existing = git('remote', 'get-url', 'origin', root=root, check=False)
    if existing.returncode == 0:
        remote_guard(root)
        install_hooks(root)
        return status(root=root)
    repo = cfg['repository']
    if create:
        run(['gh', 'repo', 'create', repo, '--private'], root, env=dict(os.environ, GH_HOST='github.com'))
    private_repository(repo, root)
    url = 'https://github.com/' + repo + '.git'
    if git('ls-remote', '--heads', url, root=root).stdout.strip():
        raise ValueError('Repository already contains history. Use github clone to resume it; no files were uploaded.')
    git('remote', 'add', 'origin', url, root=root)
    remote_guard(root)
    install_hooks(root)
    return {'repository': repo, 'uploaded': False, 'next': 'Run github preview, then github sync.'}


def fetch(root=ROOT):
    remote_guard(root)
    git('fetch', '--prune', 'origin', root=root)


def status(fetch_remote=False, root=ROOT):
    if not (root / CONFIG).exists():
        return {'state': 'local_only', 'message': 'Saved locally. GitHub workspace is not configured.'}
    cfg = config(root)
    git_root(root)
    connected = git('remote', 'get-url', 'origin', root=root, check=False).returncode == 0
    if connected:
        remote_guard(root, online=False)
        if fetch_remote:
            fetch(root)
    dirty = bool(git('status', '--porcelain', '--untracked-files=all', root=root).stdout)
    head = git('rev-parse', '--verify', 'HEAD', root=root, check=False).returncode == 0
    remote = 'refs/remotes/origin/main'
    remote_exists = git('rev-parse', '--verify', remote, root=root, check=False).returncode == 0
    ahead, behind = 0, 0
    if head and remote_exists:
        ahead, behind = map(int, git('rev-list', '--left-right', '--count', 'HEAD...' + remote, root=root).stdout.split())
    state = ('not_connected' if not connected else 'diverged' if ahead and behind else
             'remote_changes' if behind else 'pending' if dirty or ahead or not remote_exists else 'current')
    return {'state': state, 'repository': cfg['repository'], 'url': 'https://github.com/' + cfg['repository'],
            'local_changes': dirty, 'ahead': ahead, 'behind': behind,
            'remote_checked': bool(connected and fetch_remote),
            'message': 'Remote status uses the last fetch; use status --fetch to check GitHub.' if not fetch_remote else state}


def preview(root=ROOT):
    config(root)
    names = set(git('ls-files', '-z', root=root).stdout.split('\0'))
    names.update(git('ls-files', '--others', '--exclude-standard', '-z', root=root).stdout.split('\0'))
    names.discard('')
    return {'repository': config(root)['repository'], 'visibility': 'private required',
            'includes': 'Sources, accepted records, pending notes/reviews, outputs and installed runtime.',
            'files': sorted(names), 'blocked': sorted(n for n in names if not permitted(n)), 'uploaded': False}


def check_staged(root=ROOT):
    for row in filter(None, git('ls-files', '--stage', '-z', root=root).stdout.split('\0')):
        metadata, name = row.split('\t', 1)
        mode, oid, stage = metadata.split()
        if stage != '0' or mode not in ('100644', '100755') or not permitted(name):
            raise ValueError('Unsupported or excluded staged path: ' + name)
        if int(git('cat-file', '-s', oid, root=root).stdout) >= 100 * 1024 * 1024:
            raise ValueError('File is too large for this Git output; choose separate storage: ' + name)
    with tempfile.TemporaryDirectory(prefix='career-github-index-') as temp:
        git('checkout-index', '--all', '--prefix=' + temp + os.sep, root=root)
        invoke(Path(temp), 'check')
        # Re-render using exactly the staged sources, and compare before commit.
        saved = (Path(temp) / 'CAREER.md').read_bytes()
        invoke(Path(temp), 'overview')
        if (Path(temp) / 'CAREER.md').read_bytes() != saved:
            raise ValueError('CAREER.md is stale. Run github overview before committing.')


def sync(message=None, root=ROOT):
    with workspace_lock(root):
        remote_guard(root)
        if git('branch', '--show-current', root=root).stdout.strip() != 'main':
            raise ValueError('Switch to main before synchronizing this career workspace.')
        install_hooks(root)
        fetch(root)
        ref = 'refs/remotes/origin/main'
        if git('rev-parse', '--verify', ref, root=root, check=False).returncode == 0:
            if git('merge-base', '--is-ancestor', ref, 'HEAD', root=root, check=False).returncode:
                raise ValueError('GitHub has changes not present locally. Pull or reconcile them first; no merge was attempted.')
        invoke(root, 'overview')
        blocked = preview(root)['blocked']
        if blocked:
            raise ValueError('Unexpected files in workspace: ' + ', '.join(blocked))
        git('add', '--all', '--', '.', root=root)
        if git('diff', '--cached', '--quiet', root=root, check=False).returncode:
            check_staged(root)
            git('commit', '-m', message or 'Update private career workspace ' + date.today().isoformat(), root=root)
        remote_guard(root)
        git('push', '--set-upstream', 'origin', 'HEAD:refs/heads/main', root=root)
    return status(root=root)


def pull(root=ROOT):
    with workspace_lock(root):
        remote_guard(root)
        if git('branch', '--show-current', root=root).stdout.strip() != 'main':
            raise ValueError('Switch to main before pulling.')
        if git('status', '--porcelain', root=root).stdout.strip():
            raise ValueError('Local changes must be saved before pulling.')
        install_hooks(root)
        fetch(root)
        git('merge', '--ff-only', 'refs/remotes/origin/main', root=root)
        invoke(root, 'check')
    return status(root=root)


def clone(repo, destination, root=ROOT):
    repo = repository(repo)
    private_repository(repo, root)
    target = Path(destination).expanduser().absolute()
    if target.exists() or target.is_symlink() or target.resolve().is_relative_to(root.resolve()):
        raise ValueError('Clone needs a new destination directory outside the current workspace.')
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.career-clone-', dir=target.parent) as temp:
        staged = Path(temp) / 'workspace'
        git('clone', '--branch', 'main', 'https://github.com/' + repo + '.git', str(staged), root=root)
        if config(staged)['repository'].lower() != repo.lower():
            raise ValueError('This is not the configured career repository.')
        remote_guard(staged)
        invoke(staged, 'check')
        install_hooks(staged)
        target.mkdir(mode=0o700)
        for child in staged.iterdir():
            shutil.move(str(child), str(target / child.name))
    return {'workspace': str(target), 'repository': repo, 'next': 'Run make start in this workspace.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('prepare', 'clone'):
        command = sub.add_parser(name)
        command.add_argument('--repo', required=True)
        command.add_argument('--directory', required=True)
    sub.add_parser('connect').add_argument('--create', action='store_true')
    sub.add_parser('status').add_argument('--fetch', action='store_true')
    sub.add_parser('sync').add_argument('--message')
    for name in ('preview', 'pull', 'overview', 'check', 'hooks', 'check-staged'):
        sub.add_parser(name)
    guard = sub.add_parser('pre-push')
    guard.add_argument('remote'); guard.add_argument('url')
    args = parser.parse_args(argv)
    try:
        if args.command in ('prepare', 'clone'):
            result = (prepare(args.directory, args.repo) if args.command == 'prepare' else clone(args.repo, args.directory))
        elif args.command == 'connect': result = connect(args.create)
        elif args.command == 'status': result = status(args.fetch)
        elif args.command == 'sync': result = sync(args.message)
        elif args.command == 'pre-push':
            sys.stdin.read()
            result = remote_guard(remote=args.remote, url=args.url)
        else:
            result = {'preview': preview, 'pull': pull, 'overview': overview, 'check': check_workspace,
                      'hooks': install_hooks, 'check-staged': check_staged}[args.command]()
        print(json.dumps(result, indent=2, default=str))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print('GitHub workspace: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
