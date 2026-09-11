#!/usr/bin/env python3
"""Build separate, reproducible local release archives from explicit public files."""
import argparse
import ast
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent
PRIVATE = {'data', 'outputs', 'reviews', 'dist', '.git', '.codex', '.agents'}
PUBLIC = {'scripts', 'schemas', 'docs', 'examples', 'tests', '.claude', 'components'}
ROOT_FILES = {'README.md', 'CLAUDE.md', 'Makefile', 'Makefile.resume', 'LICENSE', '.gitignore'}


def public_path(name):
    path = PurePosixPath(name)
    if (path.is_absolute() or '..' in path.parts or not path.parts or
            path.parts[0] in PRIVATE or '__pycache__' in path.parts or
            (path.parts[0] not in PUBLIC and name not in ROOT_FILES)):
        raise ValueError('not an allowed public release path: ' + name)
    return path


def manifest(component, root=ROOT):
    record = json.loads((root / 'components' / component / 'component.json').read_text())
    if not re.fullmatch(r'[a-z][a-z0-9-]*', record['name']) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:-[a-z0-9.]+)?', record['version']):
        raise ValueError('invalid release name or version')
    return record


def entries(component, root=ROOT):
    record = manifest(component, root)
    files = dict(record['files'])
    for target, source in files.items():
        public_path(target)
        relative = public_path(source)
        path = root / relative
        if any((root.joinpath(*relative.parts[:i])).is_symlink() for i in range(1, len(relative.parts) + 1)):
            raise ValueError('release source cannot be a symlink: ' + source)
        if not path.is_file():
            raise ValueError('missing release source: ' + source)
    return files


def validate_layout(root=ROOT, component='all'):
    core = entries('core', root)
    resume = {} if component == 'core' else entries('resume', root)
    overlap = set(core) & set(resume)
    if overlap:
        raise ValueError('add-on overwrites core files: ' + ', '.join(sorted(overlap)))
    from check_components import check
    check(root, require='core' if component == 'core' else 'resume')
    local_modules = {p.stem for p in (root / 'scripts').glob('*.py')}
    for component, files, available in [('core', core, set(core)), ('resume', resume, set(core) | set(resume))]:
        for target, source in files.items():
            if not target.startswith('scripts/') or not target.endswith('.py'):
                continue
            tree = ast.parse((root / source).read_text())
            for node in ast.walk(tree):
                modules = ([node.module.split('.')[0]] if isinstance(node, ast.ImportFrom) and node.module else
                           [a.name.split('.')[0] for a in node.names] if isinstance(node, ast.Import) else [])
                for module in modules:
                    if module in local_modules and f'scripts/{module}.py' not in available:
                        raise ValueError(f'{component}: {target} depends on unavailable {module}')
    return core, resume


def build(component, output_dir, root=ROOT):
    core, resume = validate_layout(root, component)
    files = core if component == 'core' else resume
    record = manifest(component, root)
    payload = {target: (root / source).read_bytes() for target, source in files.items()}
    inventory = {'name': record['name'], 'version': record['version'], 'channel': record['channel'],
                 'requires': record['requires'], 'career_schema_versions': record['career_schema_versions'],
                 'files': {name: hashlib.sha256(data).hexdigest() for name, data in sorted(payload.items())}}
    payload[f"components/{component}/release.json"] = (json.dumps(inventory, indent=2) + '\n').encode()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{record['name']}-{record['version']}.zip"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output_dir, delete=False) as handle:
            temporary = Path(handle.name)
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in sorted(payload.items()):
                info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = (0o100755 if name.startswith('scripts/') else 0o100644) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data)
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('component', choices=('core', 'resume', 'all'))
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    try:
        for component in (('core', 'resume') if args.component == 'all' else (args.component,)):
            path = build(component, args.output_dir)
            print(f'{path.name} sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}')
        return 0
    except (ValueError, KeyError, OSError) as exc:
        print('error: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
