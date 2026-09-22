#!/usr/bin/env python3
"""Bundle public Core and Resume releases into one ready-to-open folder."""
import argparse
import hashlib
import json
from pathlib import Path
import os
import tempfile
import zipfile

from build_release import ROOT, build

FOLDER = 'My Career'
FILENAME = 'career-json-starter.zip'


def build_starter(output_dir, root=ROOT):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    # Only the existing release allowlists supply application files.
    # Never archive a working directory or copy personal data into a download.
    with tempfile.TemporaryDirectory(prefix='career-starter-') as tmp:
        payload, versions = {}, {}
        for component in ('core', 'resume'):
            archive = build(component, Path(tmp), root)
            with zipfile.ZipFile(archive) as source:
                for entry in source.infolist():
                    if entry.filename in payload:
                        raise ValueError('Starter components overlap: ' + entry.filename)
                    payload[entry.filename] = (source.read(entry), entry.external_attr)
                versions[component] = json.loads(source.read(
                    'components/' + component + '/release.json'))['version']
        inventory = {
            'kind': 'career-json-starter', 'components': versions,
            'files': {name: hashlib.sha256(data).hexdigest()
                      for name, (data, _) in sorted(payload.items())},
        }
        payload['components/starter/inventory.json'] = (
            (json.dumps(inventory, indent=2) + '\n').encode(), 0o100644 << 16)
        with tempfile.NamedTemporaryFile(dir=output_dir, delete=False) as handle:
            temporary = Path(handle.name)
        try:
            with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                for name, (data, mode) in sorted(payload.items()):
                    entry = zipfile.ZipInfo(FOLDER + '/' + name, (2026, 1, 1, 0, 0, 0))
                    entry.create_system = 3
                    entry.external_attr = mode
                    entry.compress_type = zipfile.ZIP_DEFLATED
                    archive.writestr(entry, data)
            target = output_dir / FILENAME
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    print(build_starter(args.output_dir))
