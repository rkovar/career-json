"""An 80-question fictional review for browser navigation tests."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
from review_html import render_review


def fixture():
    rows = []
    for number in range(79):
        value = {'id': f'E_NAV_{number:03}', 'title': f'Fictional achievement {number + 1}',
                 'star': {'situation': 'A fictional team needed reliable services. ' * 8,
                          'task': 'Help the team.', 'action': 'Co-designed a recovery procedure. ' * 12,
                          'result': 'The team rehearsed recovery.'},
                 'evidence_status': 'self_asserted', 'external_safe': False, 'source_refs': []}
        rows.append({'key': 'evidence_atoms/' + value['id'], 'before': None, 'after': value,
                     'change': 'added', 'review_status': 'awaiting_review', 'fingerprint': f'{number:064x}'})
    rows.append({'key': 'field/purpose', 'before': 'An earlier description.', 'after': 'A fictional career record.',
                 'change': 'changed', 'review_status': 'awaiting_review', 'fingerprint': 'a' * 64})
    rows.append({'key': 'field/name', 'before': 'Fictional Reviewer', 'after': 'Fictional Reviewer',
                 'change': 'unchanged', 'review_status': 'accepted', 'fingerprint': 'b' * 64})
    return {'session': {'review_id': 'navigation-test', 'proposal': {'sha256': 'c' * 64}},
            'items': rows, 'groups': [], 'omissions': [], 'summary': {}}


if __name__ == '__main__':
    Path(sys.argv[1]).write_text(render_review(fixture()))
