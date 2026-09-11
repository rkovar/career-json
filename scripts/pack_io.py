"""Private workspace paths and immutable atomic JSON writes."""
import json
import os
import tempfile
from pathlib import Path
from current_pack import ROOT, sha256

def local(path, root=ROOT):
    path = (root / path).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('editorial paths must stay inside CAREER_WORKSPACE')
    return path


def read(path, root=ROOT):
    return json.loads(local(path, root).read_text())


def pin(path, root=ROOT):
    path = local(path, root)
    return {'path': str(path.relative_to(root.resolve())), 'sha256': sha256(path)}


def pin_errors(record, root=ROOT):
    try:
        path = local(record['path'], root)
        if not path.is_file():
            return [f"missing input: {record['path']}"]
        if sha256(path) != record['sha256']:
            return [f"changed input: {record['path']}"]
    except (ValueError, KeyError) as exc:
        return [str(exc)]
    return []


def write_new(path, record, root=ROOT):
    path = local(path, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Publish complete bytes atomically without replacing an existing version.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(json.dumps(record, indent=2, ensure_ascii=False) + '\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return path
