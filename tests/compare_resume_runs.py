#!/usr/bin/env python3
"""Prepare a paired, blinded human review of resumes generated from one fictional pack.

No model calls. No hiring score. The reviewer reads A/B before inspecting the
pack, plan, or generation rationale. Supply actual saved baseline and revised
Markdown, not synthetic improvement scores.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from resume_document import document_from_markdown, submission_html
from resume_workflow import revision_findings


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare(pack, baseline, revised, output):
    output.mkdir(parents=True, exist_ok=False)
    record = json.loads(pack.read_text())
    # Deterministic counterbalancing; mapping is kept out of the reader pages.
    paths = [baseline, revised]
    if int(digest(pack)[0], 16) % 2: paths.reverse()
    for label, path in zip(('A', 'B'), paths):
        (output / (label + '.html')).write_text(submission_html(document_from_markdown(path.read_text())), encoding='utf-8')
    mapping = {'A': str(paths[0]), 'B': str(paths[1])}
    report = {'pack_sha256': digest(pack), 'baseline_sha256': digest(baseline), 'revised_sha256': digest(revised),
              'mapping_for_coordinator': mapping, 'revision_findings': revision_findings(baseline.read_text(), revised.read_text(), record),
              'human_quality': None, 'human_burden': None, 'generation_cost': None,
              'instructions': 'Read A and B first and record impressions. Then inspect the pack/brief. Keep factual preservation separate from preference; do not infer hiring success.'}
    (output / 'coordinator.json').write_text(json.dumps(report, indent=2) + '\n')
    template = json.loads((ROOT / 'tests/fixtures/resume-review.template.json').read_text())
    (output / 'reader-review.json').write_text(json.dumps(template, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('pack', 'baseline', 'revised', 'output'): parser.add_argument('--' + flag, type=Path, required=True)
    args = parser.parse_args()
    try:
        compare(args.pack, args.baseline, args.revised, args.output)
        print(args.output); return 0
    except (ValueError, OSError) as exc:
        print('error: ' + str(exc), file=sys.stderr); return 1


if __name__ == '__main__': sys.exit(main())
