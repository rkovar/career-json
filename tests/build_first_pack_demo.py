#!/usr/bin/env python3
"""Build Jules's entirely fictional career-review walkthrough in isolation.

Extraction, answers and decisions are authored fixtures. Review, capture,
acceptance, rendering and retrieval use the real tools; no model is called.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from editorial_fixture import ROOT, fingerprint
from jules_fixture import (initial, ref, source_record, atom, COACHING_ANSWER,
                           STRENGTH_ANSWER, DIRECTION_ANSWER, QUEUE_NOTE, NOTE, UPDATE)
from jules_pages import landing

MARKER = 'Entirely fictional first-pack demonstration. Safe to regenerate with build_first_pack_demo.py.\n'


def build(destination):
    destination = Path(destination).resolve()
    marker = destination / 'FICTIONAL_DEMO.txt'
    if destination == ROOT.resolve() or (destination.exists() and any(destination.iterdir()) and
                                        (not marker.is_file() or marker.read_text() != MARKER)):
        raise ValueError('demo output must be a new directory or a marked fictional demo; never a career workspace')
    pack, sources = initial()
    with tempfile.TemporaryDirectory(prefix='career-first-pack-demo-') as folder:
        work = Path(folder)
        shutil.copytree(ROOT / 'schemas', work / 'schemas')

        def put(path, value):
            target = work / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(value, indent=2) + '\n')

        def read(path):
            return json.loads((work / path).read_text())

        def write_source(path, text):
            target = work / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)

        def run(script, *args):
            result = subprocess.run([sys.executable, str(ROOT / 'scripts' / script), *args], cwd=work,
                                    env={**os.environ, 'CAREER_WORKSPACE': str(work)}, capture_output=True, text=True)
            if result.returncode:
                raise ValueError(script + ': ' + result.stdout + result.stderr)
            return result.stdout

        def begin(candidate, review_id, page):
            run('pack_review.py', 'start', '--candidate', candidate, '--id', review_id)
            session = 'reviews/pack-reviews/' + review_id + '/session.json'
            run('pack_review.py', 'render', '--session', session, '--output', page)
            return session, json.loads(run('pack_review.py', 'status', '--session', session))

        def apply(state, overrides, filename, output, omissions=()):
            rows = []
            for item in state['items']:
                if item['review_status'] == 'accepted' and item['key'] not in overrides:
                    continue
                action, publication, note = overrides.get(item['key'], ('accept', 'unchanged', ''))
                rows.append({'key': item['key'], 'fingerprint': item['fingerprint'], 'action': action,
                             'publication': publication, 'note': note})
            choices = {'review_id': state['session']['review_id'], 'proposal_sha256': state['session']['proposal']['sha256'],
                       'reviewed_by': 'Jules Elm (scripted fictional example)', 'omissions': list(omissions), 'decisions': rows}
            put(filename, choices)
            return json.loads(run('pack_review.py', 'apply', '--input', filename, '--output', output))['summary']

        for path, text in sources.items():
            write_source(path, text)
        put('data/candidates/proposal.json', pack)
        session, state = begin('data/candidates/proposal.json', 'fictional-first-pack', 'review.html')
        unresolved = {
            'evidence_atoms/E_REVIEW_SPEED': ('unsure', 'private', 'I cannot recover the baseline or period. Keep the 35% estimate out of the accepted record.'),
            'strengths_profile/S_TRANSLATION': ('later', 'unchanged', 'I want to revisit the wording after reading the examples.'),
            'strengths_profile/S_ENTERPRISE': ('correct', 'private', 'Enterprise-scale transformation overstates my remit. I lead a focused group and work through others.'),
        }
        choices = {**unresolved,
                   'evidence_atoms/E_STORY_2': ('correct', 'private', COACHING_ANSWER),
                   'evidence_atoms/E_QUEUE_DUPLICATE': ('correct', 'private', 'This is the same March 2016 dashboard. Combine the accounts; do not count it twice.'),
                   'strengths_profile/S_DISTINCTIVE': ('later', 'private', 'Correct the coaching example before we discuss this interpretation.'),
                   'evidence_atoms/E_PRIVATE_REVIEW': ('accept', 'private', 'Accurate, but keep this supplier review private.'),
                   'evidence_atoms/E_TALK': ('accept', 'external', 'Allow this exact co-presenter wording externally; no audience-impact claim.'),
                   'publications/PUB_DEPLOYMENT_TALK': ('accept', 'external', 'Allow the matching talk listing with shared speaker credit.'),
                   'employment/EMP_STAFF': ('accept', 'external', 'Allow my Staff Engineer title and dates externally.')}
        summaries = {'initial': apply(state, choices, 'decisions.json', 'data/packs/accepted.json',
                                     [{'prompt': 'What important work is missing?', 'answer': 'I also help product and operations make migration decisions. I will add a concrete example later.'}])}
        run('pack_review.py', 'render', '--session', session, '--output', 'after-review.html')
        run('career_page.py', '--pack', 'data/packs/accepted.json', '--output', 'outputs/first-career.html')

        # Corrections are new proposals; free-text notes above are not approvals.
        corrected = read('data/packs/accepted.json')
        answers = '# Scripted fictional review answers\n\n' + COACHING_ANSWER + '\n\n' + STRENGTH_ANSWER + '\n\n' + DIRECTION_ANSWER + '\n'
        write_source('data/sources/review-answers.md', answers)
        corrected['source_records'].append(source_record('SRC_ANSWERS', 'data/sources/review-answers.md', answers, kind='person'))
        corrected['positioning_preferences'] = [{'id': 'P_DIRECTION', 'kind': 'direction', 'text': DIRECTION_ANSWER,
                                               'status': 'active', 'external_safe': False,
                                               'source_refs': [ref('SRC_ANSWERS', DIRECTION_ANSWER)]}]
        coaching = copy.deepcopy(next(a for a in pack['evidence_atoms'] if a['id'] == 'E_STORY_2'))
        coaching['star']['action'] = 'Sponsored the peer design-review pilot and coached three engineering managers; Mara Vale and Theo Reed designed the format, and the managers shared hiring responsibility.'
        coaching['source_refs'].append(ref('SRC_ANSWERS', COACHING_ANSWER))
        corrected['evidence_atoms'].append(coaching)
        dashboard = next(a for a in corrected['evidence_atoms'] if a['id'] == 'E_QUEUE_VISIBILITY')
        dashboard['source_refs'].append(ref('SRC_NOTES', QUEUE_NOTE))
        # Carry unresolved work forward so the newest review still exposes it.
        corrected['evidence_atoms'].append(copy.deepcopy(next(a for a in pack['evidence_atoms'] if a['id'] == 'E_REVIEW_SPEED')))
        corrected['strengths_profile'] = copy.deepcopy(pack['strengths_profile'])
        distinct = corrected['strengths_profile'][0]
        distinct.update(status='confirmed', question_status='answered',
                        limitations=['Shared ownership is explicit; the coaching benefit has not been measured.'],
                        source_refs=[ref('SRC_ANSWERS', STRENGTH_ANSWER)])
        for item in corrected['strengths_profile']:
            item['evidence_fingerprints'] = {a['id']: fingerprint(a) for a in corrected['evidence_atoms'] if a['id'] in item['evidence_ids']}
        put('data/candidates/corrected.json', corrected)
        session, state = begin('data/candidates/corrected.json', 'fictional-correction', 'correction-review.html')
        summaries['correction'] = apply(state, unresolved, 'correction-decisions.json', 'data/packs/corrected.json')
        run('pack_review.py', 'render', '--session', session, '--output', 'after-correction.html')
        run('career_page.py', '--pack', 'data/packs/corrected.json', '--output', 'outputs/corrected-career.html')

        before = (work / 'data/packs/corrected.json').read_bytes()
        run('capture.py', NOTE, '--occurred', '2026-08', '--tag', 'migration', '--skill', 'stakeholder communication')
        notes = json.loads(run('capture.py', '--list', '--json'))
        assert (work / 'data/packs/corrected.json').read_bytes() == before
        put('data/sources/captured-note.json', notes[0])
        put('capture-before-review.json', {'notes': notes, 'accepted_pack_sha256': hashlib.sha256(before).hexdigest(), 'pack_changed': False})
        update_text = '# Fictional follow-up account — August 2026\n\n' + UPDATE + '\n'
        write_source('data/sources/update-2026.md', update_text)
        update = read('data/packs/corrected.json')
        update['source_records'].extend([
            source_record('SRC_CAPTURE', 'data/sources/captured-note.json', (work / 'data/sources/captured-note.json').read_text(), kind='json'),
            source_record('SRC_UPDATE', 'data/sources/update-2026.md', update_text),
        ])
        migration = atom('E_MIGRATION_PLANNING', 'Agreed a phased customer-data migration', 'EMP_CURRENT', '2026-08',
                         'Product wanted a single migration while operations wanted a rehearsed fallback.',
                         'Help both groups agree a migration sequence and decision points.',
                         'Facilitated the planning discussion and wrote a rollback decision guide; operations ran the rehearsal.',
                         'Product owners agreed to migrate in phases. The migration had not yet run.',
                         ['stakeholder communication', 'software architecture'], [ref('SRC_CAPTURE', NOTE), ref('SRC_UPDATE', UPDATE)])
        migration['capture'] = {'method': 'note', 'note_id': notes[0]['note_id']}
        update['evidence_atoms'].append(migration)
        update['evidence_atoms'].append(copy.deepcopy(next(a for a in corrected['evidence_atoms'] if a['id'] == 'E_REVIEW_SPEED')))
        update['strengths_profile'].extend(copy.deepcopy(corrected['strengths_profile'][1:]))
        put('data/candidates/update.json', update)
        session, state = begin('data/candidates/update.json', 'fictional-update', 'update-review.html')
        summaries['update'] = apply(state, unresolved, 'update-decisions.json', 'data/packs/updated.json')
        run('capture.py', '--promote', notes[0]['note_id'], '--atom', 'E_MIGRATION_PLANNING')
        run('pack_review.py', 'render', '--session', session, '--output', 'after-update.html')
        run('career_page.py', '--pack', 'data/packs/updated.json', '--output', 'outputs/career.html')
        put('summary.json', summaries['initial'])
        put('stages.json', summaries)
        queries = {'rehearsal': 'deployment rehearsal', 'coaching': 'coached',
                   'architecture': 'service separation', 'migration': 'customer-data migration'}
        recalled = {name: json.loads(run('find.py', term, '--json')) for name, term in queries.items()}
        put('recall.json', recalled['rehearsal'])
        put('use-cases.json', {name: {'query': queries[name], 'results': items} for name, items in recalled.items()})
        (work / 'index.html').write_text(landing(summaries, recalled))
        run('validate_pack.py')
        run('verify_excerpts.py', '--quiet')

        destination.mkdir(parents=True, exist_ok=True)
        marker.write_text(MARKER)
        for name in ('data', 'reviews'):
            shutil.copytree(work / name, destination / name, dirs_exist_ok=True, ignore=shutil.ignore_patterns('.pack-write.lock'))
        for path in work.iterdir():
            if path.is_file():
                shutil.copy(path, destination / path.name)
        for name in ('first-career.html', 'corrected-career.html', 'career.html'):
            shutil.copy(work / 'outputs' / name, destination / name)
        generated_pages = {p.name for p in work.glob('*.html')} | {'first-career.html', 'corrected-career.html', 'career.html'}
        for name in generated_pages:
            if name != 'index.html':
                page = destination / name
                page.write_text(page.read_text().replace('<body>', '<body><p style="padding:16px;background:#fff2cd;text-align:center"><strong>Fictional demonstration.</strong> All sources and decisions are scripted. <a href="index.html">Explore Jules’s career and review stages</a>.</p>', 1))
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    print(build(args.output_dir))
