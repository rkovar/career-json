#!/usr/bin/env python3
"""Check a Desktop workspace without requiring Git, make, or the Claude CLI."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import stat
import tempfile

ROOT = Path(__file__).resolve().parent.parent
DIRECTORIES = ('data/sources', 'data/private', 'data/candidates', 'data/packs',
               'data/capture', 'reviews', 'outputs')


def inspect(root=ROOT, prepare=False):
    root = Path(root).resolve()
    result = {'ready': False, 'workspace': str(root), 'problems': [],
              'next': 'Help me start my career notebook.'}
    if sys.version_info < (3, 9):
        result['problems'].append('Install Python 3.9 or newer, reopen Claude, and try again.')
        return result
    if sys.platform == 'win32':
        result['problems'].append(
            'Native Windows is not supported by the current career tools. Use a Mac or a configured Linux/WSL environment; do not create career records here.')
        return result
    try:
        from check_components import check
        check(root)
        for component in ('core', 'resume'):
            path = root / 'components' / component / 'component.json'
            if component == 'resume' and not path.exists():
                continue
            check(root, require=component)
            manifest = json.loads(path.read_text())
            release = path.with_name('release.json')
            hashes = json.loads(release.read_text())['files'] if release.exists() else {}
            if release.exists() and set(hashes) != set(manifest['files']):
                raise ValueError('The application inventory is incomplete. Download a fresh starter into a separate folder.')
            for name, source in manifest['files'].items():
                value = name if release.exists() else source
                relative = PurePosixPath(value)
                if (relative.is_absolute() or '..' in relative.parts or '\\' in value or not relative.parts):
                    raise ValueError('The application inventory contains an invalid path.')
                target = root / value
                if not target.resolve().is_relative_to(root) or not target.is_file():
                    raise ValueError('An application file is missing: ' + value + '. Download a fresh starter into a separate folder; keep the old folder.')
                if hashes and hashlib.sha256(target.read_bytes()).hexdigest() != hashes[name]:
                    raise ValueError('An application file has changed: ' + name + '. Keep your saved work; do not overwrite this folder with another download.')
        for name in DIRECTORIES:
            path = root / name
            if not path.resolve().is_relative_to(root) or (path.exists() and not path.is_dir()):
                raise ValueError('The career folder has an unexpected path: ' + name + '. Choose a fresh folder; keep this one intact.')
        with tempfile.TemporaryDirectory(prefix='.career-check-', dir=root) as tmp:
            probe = Path(tmp) / 'write-check'
            probe.write_text('setup check', encoding='utf-8')
            probe.rename(Path(tmp) / 'renamed-check')
        if prepare:
            # Finder normally preserves this bit; other ZIP extractors may not.
            # Repair only this already-verified, shipped application script.
            extractor = root / 'scripts/extract_text.sh'
            extractor.chmod(extractor.stat().st_mode | stat.S_IXUSR)
            for name in DIRECTORIES:
                (root / name).mkdir(mode=0o700, parents=True, exist_ok=True)
        result['ready'] = True
        result['message'] = 'Ready to record one achievement. A typed account needs no document or PDF software.'
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result['problems'].append(str(exc))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true', help='create missing private folders; preserve existing files')
    args = parser.parse_args()
    result = inspect(prepare=args.prepare)
    print(json.dumps(result, indent=2))
    return 0 if result['ready'] else 1


if __name__ == '__main__':
    sys.exit(main())
