#!/usr/bin/env python3
"""Build the entirely fictional first-pack walkthrough in an isolated workspace.

No live career pack is read. The scripted decisions are demonstration fixtures,
never approvals for a real person. Run after changing the review renderer.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from editorial_fixture import ROOT, personas, pack_for


def build(destination):
    destination = Path(destination).resolve()
    marker = destination / 'FICTIONAL_DEMO.txt'
    marker_text = 'Entirely fictional first-pack demonstration. Safe to regenerate with build_first_pack_demo.py.\n'
    if destination == ROOT.resolve() or (destination.exists() and any(destination.iterdir()) and
                                        (not marker.is_file() or marker.read_text() != marker_text)):
        raise ValueError('demo output must be a new directory or a marked fictional demo; never a career workspace')
    person = next(p for p in personas() if p['id'] == 'technical-leader')
    pack = pack_for(person)
    pack['purpose'] = 'Entirely fictional first-pack demonstration; never use as personal evidence.'
    pack['evidence_atoms'] = pack['evidence_atoms'][:2]
    pack['private_profile'] = {'name': person['name'], 'location': 'London'}
    pack['positioning_preferences'] = []
    strength = pack['strengths_profile'][0]
    strength.update(status='proposed', question_status='open', external_safe=False, source_refs=[],
                    review_question='Does building technical capabilities that teams adopt describe your contribution?')
    role = pack['employment'][0]
    source = ('# Jules Elm — fictional resume\n\n'
              'Head of Engineering at Fictional Fieldwork Ltd, January 2018 to present. London.\n\n'
              'In March 2019 I designed a deployment rehearsal format and co-built its runner with engineers. '
              'Two teams adopted rehearsals before deployment.\n\n'
              'In February 2025 I hired and coached engineers while introducing peer design reviews. '
              'The engineering group adopted peer design reviews.\n')
    pack['source_records'] = [{'source_id':'SRC_SUBJECT','source_type':'markdown',
                               'path':'data/sources/resume.md','independent':False,
                               'sha256':hashlib.sha256(source.encode()).hexdigest(),'character_count':len(source)}]
    role['source_refs'] = [{'source_id':'SRC_SUBJECT','excerpt':source.split('\n\n')[1]}]
    role['external_safe'] = False
    for atom, excerpt in zip(pack['evidence_atoms'], source.strip().split('\n\n')[2:]):
        atom['source_refs'] = [{'source_id':'SRC_SUBJECT','excerpt':excerpt}]
        atom['external_safe'] = False
    pack['evidence_atoms'][1]['open_questions'] = ['What part of coaching was most useful to the engineers?']
    # Rebind a deliberately proposed interpretation to these fictional atoms.
    from editorial_fixture import fingerprint
    strength['evidence_fingerprints'] = {a['id']:fingerprint(a) for a in pack['evidence_atoms']}
    with tempfile.TemporaryDirectory(prefix='career-first-pack-demo-') as folder:
        work = Path(folder)
        shutil.copytree(ROOT/'schemas',work/'schemas')
        def put(path,value):
            p=work/path;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(json.dumps(value,indent=2)+'\n')
        def run(script,*args):
            result=subprocess.run([sys.executable,str(ROOT/'scripts'/script),*args],cwd=work,
                env={**os.environ,'CAREER_WORKSPACE':str(work)},capture_output=True,text=True)
            if result.returncode:raise ValueError(result.stdout+result.stderr)
            return result.stdout
        source_path=work/'data/sources/resume.md';source_path.parent.mkdir(parents=True);source_path.write_text(source)
        put('data/candidates/proposal.json',pack)
        run('pack_review.py','start','--candidate','data/candidates/proposal.json','--id','fictional-first-pack')
        session='reviews/pack-reviews/fictional-first-pack/session.json'
        run('pack_review.py','render','--session',session,'--output','review.html')
        state=json.loads(run('pack_review.py','status','--session',session))
        choices={'review_id':'fictional-first-pack','proposal_sha256':state['session']['proposal']['sha256'],
                 'reviewed_by':'Jules Elm (scripted fictional example)', 'omissions':[],
                 'decisions':[{'key':r['key'],'fingerprint':r['fingerprint'],
                               'action':'later' if r['key'].startswith('strengths_profile/') else 'accept',
                               'publication':'unchanged','note':''} for r in state['items']]}
        put('decisions.json',choices)
        applied=json.loads(run('pack_review.py','apply','--input','decisions.json','--output','data/packs/accepted.json'))
        run('pack_review.py','render','--session',session,'--output','after-review.html')
        run('pack_html.py','--pack','data/packs/accepted.json','--output','career.html')
        put('summary.json',applied['summary'])
        recalled=json.loads(run('find.py','rehearsal','--json'))
        put('recall.json',recalled)
        destination=Path(destination)
        destination.mkdir(parents=True,exist_ok=True)
        marker.write_text(marker_text)
        for name in ('data','reviews'):
            shutil.copytree(work/name,destination/name,dirs_exist_ok=True)
        for name in ('review.html','after-review.html','career.html','summary.json','decisions.json','recall.json'):
            shutil.copy(work/name,destination/name)
        for name in ('review.html','after-review.html','career.html'):
            p=destination/name
            p.write_text(p.read_text().replace('<body>','<body><p style="padding:16px;background:#fff2cd;text-align:center"><strong>Fictional demonstration.</strong> No real career or approvals are represented. <a href="README.md">Read the walkthrough</a>.</p>',1))
    return destination


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    print(build(args.output_dir))
