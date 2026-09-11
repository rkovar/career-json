#!/usr/bin/env python3
"""Check installed component versions and their shared career schema contract."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent


def check(root=ROOT, require='core'):
    core_path = root / 'components/core/component.json'
    if not core_path.is_file():
        raise ValueError('Career Evidence Core is not installed')
    core = json.loads(core_path.read_text())
    schema = json.loads((root / 'schemas/career.schema.json').read_text())
    if schema['properties']['schema_version']['const'] not in core['career_schema_versions']:
        raise ValueError('installed career schema is incompatible with the core')
    resume_path = root / 'components/resume/component.json'
    if require == 'resume' and not resume_path.is_file():
        raise ValueError('Resume Application is not installed')
    if require == 'resume' and resume_path.is_file():
        resume = json.loads(resume_path.read_text())
        if resume['requires'].get('career-core') != core['version']:
            raise ValueError('Resume Application requires career-core ' + resume['requires']['career-core'])
        if not set(core['career_schema_versions']) <= set(resume['career_schema_versions']):
            raise ValueError('Resume Application does not support the core schema versions')
    return core['version']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require', choices=('core', 'resume'), default='core')
    args = parser.parse_args()
    try:
        print('compatible: career-core ' + check(require=args.require))
        return 0
    except (ValueError, KeyError, OSError) as exc:
        print('error: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
