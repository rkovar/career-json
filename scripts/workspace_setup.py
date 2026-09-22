"""Create a separate career workspace from the public component file lists.

Only application files are installed. Career sources and histories are never
copied from a developer checkout, and existing destinations are never replaced.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tempfile

TOOL = Path(__file__).resolve().parent.parent
PUBLIC = {'scripts', 'schemas', 'docs', 'examples', 'tests', '.claude', 'components'}
ROOT_FILES = {'README.md', 'CLAUDE.md', 'Makefile', 'Makefile.resume', 'LICENSE', '.gitignore', 'START-HERE.html'}


def create(destination, with_resume=False, tool=TOOL):
    requested = Path(destination).expanduser()
    if requested.is_symlink() or requested.exists():
        raise ValueError('Choose a new directory; existing career workspaces are never overwritten.')
    target = requested.absolute()
    if target.resolve().is_relative_to(tool.resolve()):
        raise ValueError('Create your personal workspace outside the application checkout.')
    components = ['core', 'resume'] if with_resume else ['core']
    from check_components import check
    check(tool, require='resume' if with_resume else 'core')
    files, versions = {}, {}
    for component in components:
        manifest = json.loads((tool / 'components' / component / 'component.json').read_text())
        installed = (tool / 'components' / component / 'release.json').is_file()
        versions[component] = manifest['version']
        for name, source in manifest['files'].items():
            for value in (name, source):
                path = PurePosixPath(value)
                if (path.is_absolute() or '..' in path.parts or '\\' in value or not path.parts or
                        (path.parts[0] not in PUBLIC and value not in ROOT_FILES)):
                    raise ValueError('Unsafe application manifest path: ' + value)
            original = tool / (name if installed else source)
            if original.is_symlink() or not original.resolve().is_relative_to(tool.resolve()) or not original.is_file():
                raise ValueError('Missing or unsafe application file: ' + str(original))
            if name in files:
                raise ValueError('Components overlap: ' + name)
            files[name] = original
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.career-install-', dir=target.parent))
    staging.chmod(0o700)
    try:
        hashes = {}
        for name, original in files.items():
            path = staging / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, path)
            hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        for directory in ('data/sources', 'data/packs', 'data/capture', 'reviews', 'outputs'):
            (staging / directory).mkdir(mode=0o700, parents=True, exist_ok=True)
        record = {'workspace_kind': 'career-workspace', 'components': versions, 'application_files': hashes,
                  'created_from': 'public component allowlists', 'personal_files_copied': False}
        config = staging / 'components/workspace/installation.json'
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(json.dumps(record, indent=2) + '\n')
        # The installation can itself create another clean workspace without
        # relying on development-only file paths.
        for component in components:
            manifest = json.loads((staging / 'components' / component / 'component.json').read_text())
            inventory = {'name': manifest['name'], 'version': manifest['version'],
                         'files': {name: hashes[name] for name in manifest['files']}}
            (staging / 'components' / component / 'release.json').write_text(json.dumps(inventory, indent=2) + '\n')
        # Reserve the name exclusively before moving files into it. Never replace
        # a directory another process or person created during installation.
        target.mkdir(mode=0o700)
        try:
            for child in staging.iterdir():
                shutil.move(str(child), str(target / child.name))
            staging.rmdir()
        except BaseException:
            # This directory belongs to this installation only.
            shutil.rmtree(target, ignore_errors=True)
            raise
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return {'workspace': str(target), 'components': versions,
            'next': 'Open this directory in Claude Code or run make start here. Put your material in data/sources.',
            'backup': 'Ask to back up this career workspace. GitHub backup requires a separately configured private repository.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    setup = sub.add_parser('create')
    setup.add_argument('--directory', required=True)
    setup.add_argument('--with-resume', action='store_true')
    args = parser.parse_args(argv)
    try:
        print(json.dumps(create(args.directory, args.with_resume), indent=2))
        return 0
    except (ValueError, OSError) as exc:
        parser.exit(1, 'workspace: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()
