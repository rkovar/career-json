"""Inventory authorized career sources and extract only new material.

This produces an intake report, not career facts or approvals. The conversational
operator classifies ambiguous material and proposes additions against the pack.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import os
import tempfile
import uuid

from current_pack import ROOT, resolve, sha256
from pack_io import local, read, write_new
from verify_excerpts import extract, html_text

PURPOSES = ('career_evidence', 'job_context', 'writing_reference', 'defer')


def coverage(report, pack, dispositions=None, root=ROOT):
    """Account for the whole intake against actual claim-to-source links.

    A batch boundary is not an exclusion. Links can support existing achievements
    without adding a publication. This checks bookkeeping, not prose entailment.
    """
    from pack_review import units
    dispositions = {} if dispositions is None else dispositions
    if not isinstance(report, dict) or not isinstance(report.get('sources'), list):
        raise ValueError('Supply a saved intake report with its sources inventory.')
    if any(not isinstance(row, dict) or not isinstance(row.get('path'), str) for row in report['sources']):
        raise ValueError('Every intake source needs its original path.')
    names = {row['path'] for row in report['sources']}
    if len(names) != len(report['sources']):
        raise ValueError('The intake inventory contains repeated source paths.')
    if not isinstance(dispositions, dict) or set(dispositions) - names:
        raise ValueError('Source dispositions must map paths within this intake.')
    for name, decision in dispositions.items():
        if (not isinstance(decision, dict) or set(decision) - {'outcome', 'reason', 'purpose'}
                or decision.get('outcome') not in ('exclude', 'defer')
                or not isinstance(decision.get('reason'), str) or not decision['reason'].strip()):
            raise ValueError('Explain an exclusion or deferral for ' + name + '; relevant sources must link to a career record.')
        if decision['outcome'] == 'exclude' and decision.get('purpose') not in ('job_context', 'writing_reference', 'not_career_evidence'):
            raise ValueError('Exclusions need an inspected non-career purpose: ' + name)
    records = units(pack)
    sources = pack.get('source_records', [])
    rows, errors = [], []
    for entry in report['sources']:
        name, checksum = entry['path'], entry.get('sha256')
        decision = dispositions.get(name, {})
        row = {'path': name, 'outcome': 'pending', 'record_keys': []}
        rows.append(row)
        try:
            path = local(name, root)
            if not path.is_relative_to(local('data/sources', root)):
                raise ValueError('intake sources must remain inside data/sources')
            if not checksum or sha256(path) != checksum:
                raise ValueError('source changed since intake; run intake again')
        except (ValueError, OSError) as exc:
            errors.append(name + ': ' + str(exc))
            continue
        ids = {s['source_id'] for s in sources if (s.get('saved_sha256') or s.get('sha256')) == checksum
               or (name in (s.get('path'), s.get('saved_copy')) and not (s.get('saved_sha256') or s.get('sha256')))}
        row['record_keys'] = sorted(key for key, record in records.items()
            if not key.startswith('source_records/') and isinstance(record, dict)
            and any(ref.get('source_id') in ids and ref.get('excerpt', '').strip() for ref in record.get('source_refs', [])))
        if row['record_keys']:
            row['outcome'] = 'linked'
        elif decision.get('outcome') == 'exclude':
            if entry.get('purpose') == 'career_evidence':
                raise ValueError('Career evidence needs a record link or explicit deferral, not exclusion: ' + name)
            row.update(outcome='excluded', reason=decision['reason'], purpose=decision['purpose'])
        elif decision.get('outcome') == 'defer' or entry.get('purpose') == 'defer':
            row.update(outcome='deferred', reason=decision.get('reason', 'Deferred in the supplied intake scope.'))
        elif entry.get('purpose') in ('job_context', 'writing_reference') and entry.get('purpose_origin') == 'supplied':
            row.update(outcome='excluded', reason='Inspected and classified as ' + entry['purpose'], purpose=entry['purpose'])
        elif entry.get('status') == 'unreadable':
            row['reason'] = entry.get('error', 'Source needs direct inspection or a readable copy.')
    counts = dict(Counter(row['outcome'] for row in rows))
    return {'sources': rows, 'counts': counts, 'errors': errors,
            'complete': not errors and not counts.get('pending') and not counts.get('deferred'),
            'limit': 'Links account for source files, not every fact within them. Review claim coverage and meaning separately.'}


def reading_batches(rows, character_limit=60000):
    """Bound the reading plan without creating another writable progress store."""
    batches, pending, size = [], [], 0
    for row in rows:
        if row['status'] != 'read':
            continue
        count = row['character_count']
        if pending and size + count > character_limit:
            batches.append({'sources': pending, 'characters': size})
            pending, size = [], 0
        pending.append({'path': row['path'], 'extracted_text': row['extracted_text'],
                        'read_in_sections': count > character_limit})
        size += count
    if pending:
        batches.append({'sources': pending, 'characters': size})
    return batches


def purpose(text):
    """Conservative content hints. Ambiguous purpose remains visible to the operator."""
    beginning = text[:12000].lower()
    job = bool(re.search(r'\b(job description|about the role|what you.ll bring|we are (hiring|looking for))\b', beginning))
    advice = bool(re.search(r'\b(resume writing (guide|tips)|how to write (a |your )?(resume|cv)|resume best practices)\b', beginning))
    if job and not advice:
        return 'job_context'
    if advice and not job:
        return 'writing_reference'
    return 'needs_classification'


def scan(paths, classifications=None):
    if not paths:
        raise ValueError('Choose a file or data/sources explicitly; scanning never expands the requested scope.')
    classifications = classifications or {}
    if not isinstance(classifications, dict) or any(v not in PURPOSES for v in classifications.values()):
        raise ValueError('Classifications map source paths to career_evidence, job_context, writing_reference or defer.')
    root = local('data/sources')
    files = {}
    for value in paths:
        target = local(value)
        if not target.is_relative_to(root) or not target.exists():
            raise ValueError('Choose an existing file or directory inside data/sources: ' + str(value))
        candidates = sorted(target.rglob('*')) if target.is_dir() else [target]
        for path in candidates:
            if any(part.startswith('.') for part in path.relative_to(root).parts):
                continue
            if path.is_symlink():
                raise ValueError('Source intake does not follow symlinks: ' + str(path.relative_to(ROOT.resolve())))
            if path.is_file():
                files[str(path.relative_to(ROOT.resolve()))] = path
    if set(classifications) - set(files):
        raise ValueError('A classification names material outside this intake scope.')
    current = resolve()
    pack = read(current) if current else {}
    known = {}
    for source in pack.get('source_records', []):
        digest = source.get('saved_sha256') or source.get('sha256')
        if digest:
            known[digest] = source
    rows, seen = [], {}
    run = 'intake-' + uuid.uuid4().hex[:12]
    for name, path in files.items():
        row = {'path': name, 'purpose': classifications.get(name, 'needs_classification'),
               'purpose_origin': 'supplied' if name in classifications else 'content_hint'}
        rows.append(row)
        try:
            digest = sha256(path)
            row.update(sha256=digest, byte_size=path.stat().st_size)
            if row['purpose'] == 'defer':
                row['status'] = 'deferred'; continue
            if digest in seen:
                row.update(status='duplicate', duplicate_of=seen[digest]); continue
            seen[digest] = name
            if digest in known:
                row.update(status='unchanged', source_id=known[digest]['source_id'], purpose=classifications.get(name, 'already_in_pack'))
                continue
            cache = local('reviews/intake/text/' + digest + '.txt')
            if cache.exists():
                text = cache.read_text(encoding='utf-8')
            else:
                text = extract(path)
                if path.suffix.lower() in ('.html', '.htm'):
                    text = html_text(text)
                if not text.strip():
                    raise ValueError('No readable text was extracted; OCR or a text copy may be needed.')
                if sha256(path) != digest:
                    raise ValueError('Source changed during extraction; retry this file.')
                cache.parent.mkdir(parents=True, exist_ok=True)
                # Publish complete cache entries atomically; never expose a partial extraction.
                descriptor, pending = tempfile.mkstemp(prefix='.extract-', dir=cache.parent)
                try:
                    with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
                        handle.write(text)
                    try:
                        os.link(pending, cache)
                    except FileExistsError:
                        pass
                finally:
                    Path(pending).unlink(missing_ok=True)
            row.update(status='read', character_count=len(text), extracted_text=str(cache.relative_to(ROOT.resolve())))
            if name not in classifications:
                # A quoted hiring phrase or site navigation can occur in a
                # career article. Hints must never exclude that source.
                row['purpose_hint'] = purpose(text)
        except (ValueError, OSError, RuntimeError, UnicodeError) as exc:
            row.update(status='unreadable', error=str(exc))
    report = {'intake_id': run, 'created': datetime.now(timezone.utc).isoformat(),
              'scope': [str(p) for p in paths], 'current_pack': str(local(current).relative_to(ROOT.resolve())) if current else None,
              'sources': rows, 'has_new_material': any(row['status'] == 'read' and row['purpose'] not in ('job_context', 'writing_reference') for row in rows), 'counts': dict(Counter(row['status'] for row in rows)),
              'reading_batches': reading_batches(rows),
              'next': 'Read new extracted text and classify material before proposing career facts. purpose_hint is a suggestion, never an exclusion: inspect the source before supplying its classification. Compare with the current pack; preserve conflicts and existing IDs. No career facts have been changed.'}
    destination = write_new('reviews/intake/' + run + '.json', report)
    return dict(report, report=str(destination.relative_to(ROOT.resolve())))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sources', nargs='*', help='authorized file(s) or data/sources for the whole directory')
    parser.add_argument('--classifications', help='JSON mapping inspected paths to purpose; no factual authority')
    parser.add_argument('--report', help='check coverage of a saved intake report instead of rescanning')
    parser.add_argument('--candidate', help='proposal whose claim-to-source links should account for the intake')
    parser.add_argument('--dispositions', help='JSON of explained non-career exclusions or deferred source work')
    args = parser.parse_args(argv)
    try:
        if args.report:
            if args.sources or args.classifications or not args.candidate:
                raise ValueError('Coverage needs --report and --candidate, without a new scan scope.')
            report = coverage(read(args.report), read(args.candidate), read(args.dispositions) if args.dispositions else None)
        else:
            if args.candidate or args.dispositions:
                raise ValueError('--candidate and --dispositions require --report.')
            report = scan(args.sources, read(args.classifications) if args.classifications else None)
        print(json.dumps(report, indent=2))
        return 1 if args.report and not report['complete'] else 0
    except (ValueError, OSError) as exc:
        parser.exit(1, 'intake: ' + str(exc) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
