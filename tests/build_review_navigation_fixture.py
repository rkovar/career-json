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


def connected_fixture(workspace):
    import copy
    import os
    import shutil
    import subprocess
    from editorial_fixture import personas, pack_for
    root = Path(__file__).resolve().parent.parent
    workspace.mkdir()
    shutil.copytree(root/'schemas', workspace/'schemas')
    pack = pack_for(personas()[0]); pack['metadata'] = {}; pack['strengths_profile'] = []
    original = copy.deepcopy(pack['evidence_atoms'][0])
    pack['evidence_atoms'] = [dict(copy.deepcopy(original), id=f'E_BROWSER_{n:02}', title=f'Fictional contribution {n}') for n in range(14)]
    (workspace/'reviews').mkdir()
    (workspace/'reviews/onboarding.md').write_text(original['source_refs'][0]['excerpt'])
    (workspace/'data/candidates').mkdir(parents=True)
    (workspace/'data/candidates/browser.json').write_text(json.dumps(pack))
    subprocess.run([sys.executable, '-B', str(root/'scripts/career_core.py'), 'review', 'start',
                    '--candidate','data/candidates/browser.json','--id','browser'], check=True, capture_output=True,
                   env={**os.environ, 'CAREER_WORKSPACE':str(workspace)})


if __name__ == '__main__':
    if sys.argv[1] == '--workspace':
        connected_fixture(Path(sys.argv[2]))
    else:
        Path(sys.argv[1]).write_text(render_review(fixture()))
