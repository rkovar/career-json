#!/usr/bin/env python3
"""Assemble a review body with an exact saved manifest; validate before publishing."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

from editorial import local, read, write_new, pin_errors
from manifest import editorial_staleness, skill_versions
from current_pack import resolve, sha256
from validate_records import check, load, walk


def save_review(kind, body_path, run_path, output, replace=False):
    body, run = read(body_path), read(run_path)
    if not isinstance(body, dict) or 'run' in body:
        raise ValueError('review body must be an object without run; use the saved manifest')
    record = dict(body, run=run)
    schema = load(kind + '-record.schema.json')
    errors = []
    walk(record, schema, schema, '', errors)
    if errors:
        raise ValueError('; '.join(errors))
    errors.extend(editorial_staleness(run))
    errors.extend(pin_errors({'path': run['pack'], 'sha256': run['pack_sha256']}))
    if run['skill_versions'] != skill_versions():
        errors.append('workflow versions changed')
    current = resolve()
    if current and sha256(current) != run['pack_sha256']:
        errors.append('current career pack changed')
    artifacts = [record['artifact']] if kind == 'representation' else [p for p in record['artifacts'] if p.endswith('.md')]
    if len(artifacts) != 1:
        errors.append('one Markdown artifact per review manifest is required')
    for artifact in artifacts:
        target = local(artifact)
        if not target.is_file() or sha256(target) != run.get('artifact_sha256'):
            errors.append('review manifest does not match the exact artifact')
    output = local(output)
    if output.parent != local('outputs') or not output.name.endswith('-' + kind + '.json'):
        errors.append(f'review must be saved as outputs/<stem>-{kind}.json')
    if kind == 'representation' and artifacts and output != local(artifacts[0]).with_name(Path(artifacts[0]).stem + '-representation.json'):
        errors.append('representation sidecar must match its artifact stem')
    if errors:
        raise ValueError('; '.join(errors))
    output.parent.mkdir(parents=True, exist_ok=True)
    # Run the same cross-record checks as the public validator, including the
    # representation gate on publishability, before an existing review changes.
    with tempfile.NamedTemporaryFile(mode='w', suffix='-' + kind + '.json', dir=output.parent) as handle:
        json.dump(record, handle)
        handle.flush()
        _, errors, warnings = check(Path(handle.name))
    if errors:
        raise ValueError('; '.join(errors))
    if replace:
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', dir=output.parent, delete=False) as handle:
                temporary = Path(handle.name)
                json.dump(record, handle, indent=2, ensure_ascii=False)
                handle.write('\n')
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, output)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    else:
        write_new(output, record)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=('representation', 'evaluation'), required=True)
    parser.add_argument('--body', required=True, help='model-authored JSON without run')
    parser.add_argument('--run', required=True, help='exact JSON emitted by manifest.py')
    parser.add_argument('--output', required=True)
    parser.add_argument('--replace', action='store_true', help='atomically replace a disposable review after validation')
    args = parser.parse_args()
    try:
        print(save_review(args.kind, args.body, args.run, args.output, args.replace))
        return 0
    except (ValueError, KeyError, OSError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
