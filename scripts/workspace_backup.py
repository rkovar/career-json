"""Portable private archives with verified references and non-overwriting restore."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import zipfile

from current_pack import ROOT, resolve, sha256
from pack_io import local

PRIVATE = ('data', 'reviews', 'outputs')
PUBLIC = ('scripts', 'schemas', '.claude', 'components', 'docs', 'tests', 'examples')
ROOT_FILES = ('README.md', 'CLAUDE.md', 'LICENSE', 'Makefile', 'Makefile.resume', '.gitignore')


def reference_audit(root):
    """Verify stored local references and pins without executing restored code."""
    root = Path(root).resolve()
    errors, warnings = [], []
    def check_path(value, expected, owner):
        if not isinstance(value, str):
            errors.append(owner + ': invalid path reference'); return
        if value.startswith(('https://', 'http://')):
            warnings.append(owner + ': remote source is not embedded'); return
        try:
            if Path(value).is_absolute():
                raise ValueError('absolute references are not portable; import this source into the workspace')
            path = local(value, root)
            if not path.is_file():
                errors.append(owner + ': missing reference ' + value)
            elif expected and sha256(path) != expected:
                # A policy upgrade can stale a historical plan without corrupting
                # its immutable career inputs. Preserve that history with notice.
                messages = warnings if owner.startswith('data/plans/') and value == 'docs/policies/resume-authoring.json' else errors
                messages.append(owner + ': changed reference ' + value)
        except ValueError as exc:
            errors.append(owner + ': ' + str(exc))
    def inspect(value, owner):
        if isinstance(value, list):
            for child in value: inspect(child, owner)
        elif isinstance(value, dict):
            if 'source_type' in value and 'source_id' in value:
                if value.get('source_type') == 'url':
                    if value.get('saved_copy'):
                        check_path(value['saved_copy'], value.get('saved_sha256'), owner)
                    else:
                        warnings.append(owner + ': remote source without a saved copy: ' + value['source_id'])
                else:
                    check_path(value.get('path'), value.get('sha256'), owner)
            elif 'path' in value and 'sha256' in value:
                check_path(value['path'], value['sha256'], owner)
            if isinstance(value.get('supersedes'), str) and value['supersedes'].startswith(('data/', 'reviews/')):
                check_path(value['supersedes'], None, owner)
            if isinstance(value.get('pack'), str):
                check_path(value['pack'], value.get('pack_sha256'), owner)
            if isinstance(value.get('artifact'), str) and value.get('run'):
                check_path(value['artifact'], value['run'].get('artifact_sha256'), owner)
            for child in value.values(): inspect(child, owner)
    for folder in ('data/packs', 'data/candidates', 'data/selections', 'data/briefs', 'data/plans',
                   'reviews/pack-reviews', 'reviews/decisions', 'reviews/startup', 'reviews/questions'):
        for path in (root / folder).rglob('*.json'):
            try: inspect(json.loads(path.read_text()), str(path.relative_to(root)))
            except (ValueError, OSError, TypeError) as exc: errors.append(str(path.relative_to(root)) + ': ' + str(exc))
    # Generated documents are disposable; stale evaluations are useful history,
    # and are archived verbatim without treating them as current truth.
    return {'errors': list(dict.fromkeys(errors)), 'warnings': list(dict.fromkeys(warnings))}


def archive_name(name):
    p = PurePosixPath(name)
    if (not name or '\\' in name or p.is_absolute() or '..' in p.parts or
            str(p) != name or not p.parts or
            (p.parts[0] not in PRIVATE + PUBLIC and name not in ROOT_FILES + ('backup-manifest.json', 'CAREER-OVERVIEW.html'))):
        raise ValueError('unsafe archive path: ' + name)
    return p


def backup_workspace(output, root=ROOT):
    from pack_io import workspace_lock
    with workspace_lock(root):
        return _backup_workspace(output, root)


def _backup_workspace(output, root=ROOT):
    root = Path(root).resolve()
    target = Path(output).expanduser()
    target = (root / target).resolve()
    if target.is_relative_to(root.resolve()) and target.parent != (root / 'backups').resolve():
        raise ValueError('save private archives in backups/ or outside the workspace')
    if target.suffix.lower() != '.zip':
        raise ValueError('backup output must end in .zip')
    audit = reference_audit(root)
    if audit['errors']:
        raise ValueError('backup cannot preserve broken references: ' + '; '.join(audit['errors']))
    head = resolve(root / 'data/packs', root)
    paths = []
    for folder in PRIVATE + PUBLIC:
        if (root / folder).is_symlink():
            raise ValueError('backup does not follow symlinks: ' + folder)
        for p in (root / folder).rglob('*'):
            if p.is_symlink():
                raise ValueError('backup does not follow symlinks: ' + str(p.relative_to(root)))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc' and p.name not in ('.DS_Store', '.pack-write.lock'):
                paths.append(p)
    paths += [root / name for name in ROOT_FILES if (root / name).is_file()]
    if any(p.is_symlink() for p in paths):
        raise ValueError('backup does not follow symlinked root files')
    payload = {str(p.relative_to(root)): p.read_bytes() for p in paths}
    from review_html import show
    pack = json.loads(head.read_text()) if head else {}
    overview = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Private career backup</title><body><h1>Your saved career record</h1><p>Private backup. Includes career history, sources, and pending reviews.</p>'
    for field, title in [('employment', 'Career timeline'), ('evidence_atoms', 'Achievements'), ('strengths_profile', 'Strengths')]:
        overview += '<h2>' + title + '</h2>' + show(pack.get(field, []))
    overview += '<h2>Unavailable remote sources</h2>' + show(audit['warnings']) + '</body></html>'
    payload['CAREER-OVERVIEW.html'] = overview.encode('utf-8')
    manifest = {'format': 'career-workspace-backup', 'version': 1, 'current_pack': str(head.relative_to(root)) if head else None,
                'warnings': audit['warnings'], 'files': {name: hashlib.sha256(data).hexdigest() for name, data in payload.items()}}
    payload['backup-manifest.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as handle:
            temporary = Path(handle.name)
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in sorted(payload.items()):
                archive_name(name)
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                executable = name.startswith('scripts/') and os.access(root / name, os.X_OK)
                info.external_attr = (0o100700 if executable else 0o100600) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data)
        # Recheck after reading so a changing workspace cannot create torn pins.
        for path in paths:
            if path.read_bytes() != payload[str(path.relative_to(root))]:
                raise ValueError('workspace changed during backup; retry')
        os.link(temporary, target)
    finally:
        if temporary: temporary.unlink(missing_ok=True)
    return target


def restore_workspace(input_path, destination, root=ROOT):
    root = Path(root).resolve()
    archive_path = (root / input_path).resolve()
    target = (root / destination).resolve()
    if target.exists():
        raise ValueError('restore needs a new destination; existing workspaces are never overwritten')
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.career-restore-', dir=target.parent))
    try:
        with zipfile.ZipFile(archive_path) as archive:
            entries = archive.infolist()
            names = [e.filename for e in entries]
            if len(names) != len(set(names)) or len(entries) > 100000 or sum(e.file_size for e in entries) > 2 * 1024**3:
                raise ValueError('duplicate entries or archive exceeds restore limits (100,000 files / 2 GiB)')
            for entry in entries:
                archive_name(entry.filename)
                if entry.is_dir() or stat.S_ISLNK(entry.external_attr >> 16):
                    raise ValueError('archive entries must be regular files')
            manifest = json.loads(archive.read('backup-manifest.json'))
            if manifest.get('format') != 'career-workspace-backup' or manifest.get('version') != 1:
                raise ValueError('unsupported backup format')
            if set(manifest['files']) != set(names) - {'backup-manifest.json'}:
                raise ValueError('archive inventory does not match manifest')
            for name, expected in manifest['files'].items():
                data = archive.read(name)
                if hashlib.sha256(data).hexdigest() != expected:
                    raise ValueError('backup checksum mismatch: ' + name)
                path = staging / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
                mode = archive.getinfo(name).external_attr >> 16
                path.chmod(0o700 if mode & 0o111 else 0o600)
        audit = reference_audit(staging)
        if audit['errors']:
            raise ValueError('restored references are invalid: ' + '; '.join(audit['errors']))
        head = resolve(staging / 'data/packs', staging)
        if (str(head.relative_to(staging)) if head else None) != manifest['current_pack']:
            raise ValueError('restored current pack differs from the manifest')
        # Reserve the new destination; a failed restore leaves no partial workspace.
        target.mkdir(mode=0o700)
        try:
            for path in staging.iterdir():
                shutil.move(str(path), str(target / path.name))
        except BaseException:
            shutil.rmtree(target)
            raise
        return target
    finally:
        shutil.rmtree(staging, ignore_errors=True)
