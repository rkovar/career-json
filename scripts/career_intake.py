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
                row['purpose'] = purpose(text)
        except (ValueError, OSError, RuntimeError, UnicodeError) as exc:
            row.update(status='unreadable', error=str(exc))
    report = {'intake_id': run, 'created': datetime.now(timezone.utc).isoformat(),
              'scope': [str(p) for p in paths], 'current_pack': str(local(current).relative_to(ROOT.resolve())) if current else None,
              'sources': rows, 'has_new_material': any(row['status'] == 'read' and row['purpose'] not in ('job_context', 'writing_reference') for row in rows), 'counts': dict(Counter(row['status'] for row in rows)),
              'next': 'Read new extracted text and classify ambiguous material before proposing career facts. Compare with the current pack; preserve conflicts and existing IDs. No career facts have been changed.'}
    destination = write_new('reviews/intake/' + run + '.json', report)
    return dict(report, report=str(destination.relative_to(ROOT.resolve())))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sources', nargs='+', help='authorized file(s) or data/sources for the whole directory')
    parser.add_argument('--classifications', help='JSON mapping inspected paths to purpose; no factual authority')
    args = parser.parse_args(argv)
    try:
        report = scan(args.sources, read(args.classifications) if args.classifications else None)
        print(json.dumps(report, indent=2))
        return 0
    except (ValueError, OSError) as exc:
        parser.exit(1, 'intake: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()
