#!/usr/bin/env python3
"""Maintain and export career truth without installing the resume application."""
import argparse
import copy
import json
from pathlib import Path
import sys
import tempfile

from current_pack import ROOT, resolve
from pack_io import local, read, write_new
from career_profile import atoms_by_id, digest, profile_state


def validate_candidate(record, destination):
    from validate_pack import check, SCHEMA
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', dir=destination.parent) as handle:
        json.dump(record, handle)
        handle.flush()
        errors, warnings = check(Path(handle.name), json.loads(SCHEMA.read_text()))
    if errors:
        raise ValueError('; '.join(errors))
    return warnings


def main(argv=None, _locked=False):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == 'migrate' and not _locked:
        from pack_io import workspace_lock
        with workspace_lock():
            return main(argv, _locked=True)
    if argv and argv[0] == "workspace":
        from workspace_setup import main as workspace_main
        return workspace_main(argv[1:])
    if argv and argv[0] == "intake":
        from career_intake import main as intake_main
        return intake_main(argv[1:])
    if argv and argv[0] == 'questions':
        from question_history import main as questions_main
        return questions_main(argv[1:])
    if argv and argv[0] == 'recover':
        from career_state import recover
        print(json.dumps(recover(), indent=2)); return 0
    if argv and argv[0] == 'export-markdown':
        from career_markdown import main as markdown_main
        return markdown_main(argv[1:])
    if argv and argv[0] == 'view':
        from career_review import reading_page
        from pack_io import workspace_lock
        with workspace_lock():
            page = reading_page()
        print((page + '\noutputs/career.md') if page else 'No saved career pack yet.'); return 0
    if argv and argv[0] == 'health' and '--summary' in argv:
        from career_state import summary
        state = summary()
        print(json.dumps(state, indent=2) if '--json' in argv else state['next'] + '\n' +
              str(state['questions']['required']) + ' factual questions; ' + str(state['questions']['optional']) + ' optional questions.')
        return 1 if state['errors'] else 0
    if argv and argv[0] == "start":
        from career_start import main as start_main
        return start_main(argv[1:])
    if argv and argv[0] == "review":
        from pack_review import main as review_main
        return review_main(argv[1:])
    if argv and argv[0] in ('health', 'history', 'maintain', 'backup', 'restore'):
        from workspace_tools import main as workspace_main
        return workspace_main(argv)
    parser = argparse.ArgumentParser(description=__doc__, epilog="Also available: intake, start, review, view, export-markdown, workspace, health, history, maintain, backup and restore. Use <command> --help for details.")
    sub = parser.add_subparsers(dest='command', required=True)
    status = sub.add_parser('status', help='private strengths interview queue')
    status.add_argument('--pack', help='inspect a proposal before its first acceptance')
    migrate = sub.add_parser('migrate', help='create a new schema 1.4 version without changing facts')
    migrate.add_argument('--output', required=True)
    bind = sub.add_parser('bind-strength', help='refresh only reassessed support; never promotes confidence')
    bind.add_argument('--pack', required=True)
    bind.add_argument('--strength', required=True)
    bind.add_argument('--output', required=True)
    bind.add_argument('--assessment', help='JSON explaining the interpretation and every limitation against current support')
    export = sub.add_parser('export', help='lossless private JSON copy; source files must be backed up separately')
    export.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        path = local(args.pack) if getattr(args, 'pack', None) else resolve()
        if args.command == 'status':
            pack = read(path) if path else {}
            rows = []
            for strength in pack.get('strengths_profile', []):
                state = profile_state(strength, pack)
                rows.append({'id': strength['id'], 'state': state, 'interpretation': strength['interpretation'],
                             'question': strength.get('review_question'),
                             'ask': strength['status'] != 'rejected' and strength['question_status'] != 'declined'
                                    and (state == 'stale' or strength['question_status'] == 'open')})
            print(json.dumps({'strengths': rows, 'legacy_pack': pack.get('schema_version') == '1.3'}, indent=2))
            return 0
        if not path:
            raise ValueError('no pack found')
        path = local(path)
        record = copy.deepcopy(read(path))
        destination = local(args.output)
        if args.command == 'export':
            if destination.parent not in (local('data/private'), local('outputs')):
                raise ValueError('private exports belong in data/private or outputs, never data/packs')
        else:
            if destination.parent not in (local('data/packs'), local('data/candidates')):
                raise ValueError('new pack versions belong in data/candidates or data/packs')
            if args.command == 'bind-strength' and destination.parent != local('data/candidates'):
                raise ValueError('strength reassessment must produce a candidate; accept it through human review')
            if record['schema_version'] not in ('1.3', '1.4'):
                raise ValueError('unsupported source schema version')
            record['schema_version'] = '1.4'
            record.setdefault('strengths_profile', [])
            record.setdefault('positioning_preferences', [])
            metadata = record.setdefault('metadata', {})
            if args.command == 'migrate':
                metadata['supersedes'] = str(path.relative_to(ROOT.resolve()))
            elif path.parent == local('data/packs') or not metadata.get('supersedes'):
                # Working candidates are not pack history. A first import has
                # no predecessor; later candidates refer to the accepted head.
                previous = resolve()
                if previous:
                    metadata['supersedes'] = str(local(previous).relative_to(ROOT.resolve()))
            if args.command == 'bind-strength':
                strength = next((s for s in record['strengths_profile'] if s['id'] == args.strength), None)
                if strength is None:
                    raise ValueError('unknown strength')
                if not args.assessment:
                    raise ValueError('bind-strength needs --assessment: reassess the interpretation and every limitation; refreshing hashes alone is insufficient')
                from career_profile import reassess_strength
                from pack_io import pin
                receipt = reassess_strength(strength, record, read(args.assessment))
                receipt['assessment'] = pin(args.assessment)
                metadata.setdefault('strength_reassessments', {})[strength['id']] = receipt
        validate_candidate(record, destination)
        written = write_new(destination, record)
        print(written.relative_to(ROOT.resolve()))
        return 0
    except (ValueError, KeyError, OSError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
