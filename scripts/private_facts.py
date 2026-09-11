#!/usr/bin/env python3
"""Recorded date and measurement facts for private preparation; absence stays unknown."""
import json
import re
import sys
from pathlib import Path
from current_pack import resolve

IDS = re.compile(r'\bE_[A-Z0-9_]+\b')
RELATIVE_AGE = re.compile(r'\b(?:\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|several|a few)\s+(?:years?|months?|decades?)\s+(?:ago|old)\b', re.I)
NEGATIVE_MEASUREMENT = re.compile(r'\b(?:not measured|never measured|unmeasured|wasn[’\']t measured|weren[’\']t measured)\b', re.I)


def facts(pack):
    rows = []
    for atom in pack.get('evidence_atoms', []):
        metrics = []
        for metric in atom.get('metrics', []):
            m = metric if isinstance(metric, dict) else {'value': metric}
            status = ('not_measured' if m.get('measured') is False else
                      'measured' if m.get('measured') is True else 'unknown')
            metrics.append({'text': m.get('value', ''), 'measurement_status': status,
                            'measurement_basis': m.get('basis')})
        rows.append({'evidence_id': atom['id'], 'occurred': atom.get('occurred'),
                     'metrics': metrics, 'metrics_recorded': bool(metrics)})
    return {'date_policy': 'Use recorded dates and their precision, not relative ages.',
            'measurement_policy': 'Missing metrics, measured status or basis means not recorded. Only explicit measured:false supports not measured for that metric.',
            'atoms': rows}


def grounding_errors(md, pack):
    """Conservative prose guardrails, not a substitute for a semantic review.

    Negative measurement statements require local cited, explicit support. A
    section heading can supply the evidence scope for its paragraphs. Dates use
    a stable absolute form so copied drafts cannot retain a stale elapsed age.
    """
    errors = []
    atoms = {a['evidence_id']: a for a in facts(pack)['atoms']}
    for match in RELATIVE_AGE.finditer(md):
        errors.append(f'private grounding: replace relative age "{match.group()}" with the recorded date')
    scope = set()
    for paragraph in re.split(r'\n\s*\n', md):
        if paragraph.lstrip().startswith('#'):
            scope = set(IDS.findall(paragraph))
        if not NEGATIVE_MEASUREMENT.search(paragraph):
            continue
        ids = set(IDS.findall(paragraph)) or scope
        supported = bool(ids) and ids <= atoms.keys()
        for aid in ids & atoms.keys():
            metrics = atoms[aid]['metrics']
            # A false flag supports its named metric, not arbitrary outcomes
            # in the same atom. Keep the metric text adjacent to the claim.
            explicit = [m for m in metrics if m['measurement_status'] == 'not_measured']
            supported = supported and bool(explicit) and (
                any(m['text'] and m['text'].lower() in paragraph.lower() for m in explicit))
        if not supported:
            errors.append('private grounding: negative measurement claim needs a locally cited metric with measured:false and its recorded text; otherwise say measurement information is not recorded')
    return errors


def main():
    path = resolve()
    if not path:
        print('error: no career pack found', file=sys.stderr)
        return 1
    print(json.dumps(facts(json.loads(Path(path).read_text())), indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
