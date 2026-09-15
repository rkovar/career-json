#!/usr/bin/env python3
"""Validate the exact Git index in an isolated workspace before committing."""
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile

PRIVATE = {'data', 'outputs', 'reviews', 'backups', 'archive', 'archives', 'resume_information'}
PLACEHOLDERS = {'data/sources/.gitkeep', 'data/packs/.gitkeep', 'data/private/.gitkeep',
                'data/roles/.gitkeep', 'data/capture/.gitkeep', 'outputs/.gitkeep', 'reviews/.gitkeep'}


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args])


def index_paths(root):
    return [os.fsdecode(p) for p in git(root, 'ls-files', '--cached', '-z').split(b'\0') if p]


def check_private_paths(paths):
    forbidden = [name for name in paths if PurePosixPath(name).parts[0] in PRIVATE and name not in PLACEHOLDERS]
    if forbidden:
        raise ValueError('private material is staged/tracked: ' + ', '.join(forbidden))


def snapshot(root, target):
    """Copy index blobs, including executable bits, without reading worktree data."""
    paths = index_paths(root)
    check_private_paths(paths)
    for name in PLACEHOLDERS.intersection(paths):
        if git(root, 'cat-file', '-s', ':' + name).strip() != b'0':
            raise ValueError('private placeholder must be empty: ' + name)
    prefix = str(Path(target).resolve()) + os.sep
    subprocess.run(['git', '-C', str(root), 'checkout-index', '--all', '--prefix=' + prefix], check=True)


def check(root):
    with tempfile.TemporaryDirectory(prefix='career-staged-check-') as temp:
        snapshot(root, temp)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        # Worktree paths and Git hook environment must not redirect the check.
        for key in ('CAREER_WORKSPACE', 'GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR'):
            env.pop(key, None)
        print('Checking staged source in a clean fictional workspace.', flush=True)
        return subprocess.run(['make', 'check'], cwd=temp, env=env).returncode


def main():
    try:
        root = Path(git(Path.cwd(), 'rev-parse', '--show-toplevel').decode().strip())
        return check(root)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print('pre-commit: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
