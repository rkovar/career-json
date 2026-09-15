#!/usr/bin/env python3
"""Prepare fictional resume workspaces and inspect real candidate/reviewer files.

No model calls, paid services, automatically approved prose, or hiring scores.
Use a new suite directory for each generation version and compare saved results.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/'scripts'))
from resume_document import document_from_markdown, normalized
from resume_employment import chronology_errors
from validate_artifact import check as check_artifact
from evidence_rules import linked_ids


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f: f.write(json.dumps(value,indent=2)+'\n')


def cases(): return json.loads((ROOT/'tests/fixtures/resume-quality-cases.json').read_text())['cases']


def prepare(output):
    output.mkdir(parents=True, exist_ok=False)
    manifest = {'fixture_sha256':digest(ROOT/'tests/fixtures/resume-quality-cases.json'), 'cases':[]}
    # Copy only release-allowlisted code, docs and fictional examples. Never copy
    # live data, outputs, reviews or the caller's career pack into a test suite.
    code = {}
    for component in ('core','resume'):
        code.update(json.loads((ROOT/'components'/component/'component.json').read_text())['files'])
    for case in cases():
        workspace=output/case['case_id']; workspace.mkdir()
        for dest, source in code.items():
            target=workspace/dest; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(ROOT/source if (ROOT/source).is_file() else ROOT/dest,target)
        pack_path=workspace/'data/packs/fixture.json'; role_path=workspace/'data/roles'/ (case['case_id']+'.json')
        write(pack_path,case['pack']); write(role_path,case['role'])
        source=workspace/'data/sources/fixture.txt';source.parent.mkdir(parents=True,exist_ok=True)
        source.write_text('Fully fictional source for quality testing.\n'+json.dumps(case['pack'],indent=2)+'\n'+'\n'.join(a['star']['action']+' '+a['star']['result'] for a in case['pack']['evidence_atoms']))
        (source.parent/'role.txt').write_text(json.dumps(case['role'],indent=2))
        (workspace/'outputs').mkdir(exist_ok=True)
        (workspace/'TASK.md').write_text('Use make-resume to generate a resume for the saved role in data/roles/'+case['case_id']+'.json from the approved fictional pack. Use automatic review mode. Save the final cited Markdown as outputs/candidate-draft.md and deliver PDF, TXT and DOCX through the normal workflow. Do not read the coordinator expectations before recording a cold reader impression.\n')
        write(workspace/'reader-review.json',{'reviewer':None,'context':None,'artifact_sha256':None,'observations':[],
              'criteria':[{'criterion':c,'status':'unmeasured','passages':[],'reason':''} for c in case['criteria']],
              'limitations':[]})
        pins={str(p.relative_to(output)):digest(p) for p in (pack_path,role_path,source,source.parent/'role.txt')}
        manifest['cases'].append({'case_id':case['case_id'],'inputs':pins,'criteria':case['criteria']})
    write(output/'coordinator.json',manifest)
    return manifest


def check_suite(suite):
    saved=json.loads((suite/'coordinator.json').read_text()); reports=[]
    known={c['case_id']:c for c in cases()}
    if (saved.get('fixture_sha256') != digest(ROOT/'tests/fixtures/resume-quality-cases.json')
            or [c.get('case_id') for c in saved.get('cases',[])] != list(known)
            or any(c.get('criteria') != known[c['case_id']]['criteria'] for c in saved['cases'])):
        raise ValueError('suite must retain the exact fixture version, cases and review criteria')
    for case in saved['cases']:
        workspace=suite/case['case_id']; path=workspace/'outputs/candidate-draft.md'
        result={'case_id':case['case_id'],'deterministic_errors':[], 'reader_quality':'unmeasured','reader_findings':[], 'exports':'not_assessed_by_this_runner'}
        errors=result['deterministic_errors']
        for rel,sha in case['inputs'].items():
            candidate=(suite/rel).resolve()
            if not candidate.is_relative_to(suite.resolve()) or not candidate.is_file() or digest(candidate)!=sha:
                errors.append('fixture input changed or missing: '+rel)
        if not path.exists():
            errors.append('candidate has not been generated');reports.append(result);continue
        if errors: reports.append(result);continue
        pack=json.loads((workspace/'data/packs/fixture.json').read_text())
        role=json.loads((workspace/'data/roles'/(case['case_id']+'.json')).read_text())
        if pack != known[case['case_id']]['pack'] or role != known[case['case_id']]['role']:
            errors.append('candidate changed the canonical fictional pack or role'); reports.append(result); continue
        try:
            doc=document_from_markdown(path.read_text())
            problems,warnings=check_artifact(path,None,pack,role=role)
            errors.extend(problems);errors.extend(chronology_errors(doc,pack));result['diagnostics']=warnings
            used={a for b in doc['blocks'] for a in b['evidence_ids']}
            for req in role['requirements']:
                if req['weight']=='essential' and not used & set(linked_ids(req)):
                    errors.append('central fixture evidence absent: '+req['text'])
            review=json.loads((workspace/'reader-review.json').read_text())
            valid=bool(review.get('reviewer') and review.get('context') in ('fresh','shared') and review.get('observations')
                       and review.get('artifact_sha256')==digest(path)
                       and [r.get('criterion') for r in review.get('criteria',[])]==case['criteria'])
            text=normalized(' '.join(b['text'] for b in doc['blocks']))
            for row in review.get('criteria',[]):
                if (row.get('status') not in ('pass','issue') or not row.get('reason','').strip() or not row.get('passages')
                        or any(not p.strip() or normalized(p) not in text for p in row['passages'])): valid=False
            if valid:
                result['reader_quality']='issues' if any(r['status']=='issue' for r in review['criteria']) else 'reviewed_pass'
                result['reader_findings']=review['criteria'];result['reader_context']=review['context']
                result['reader_limitations']=review.get('limitations',[])
        except (ValueError, KeyError, OSError, TypeError) as exc: errors.append(str(exc))
        reports.append(result)
    return {'cases':reports,'complete':all(not r['deterministic_errors'] and r['reader_quality']=='reviewed_pass' for r in reports),
            'limitation':'Deterministic preservation and recorded reader judgments are separate. No prose improvement, export success or hiring outcome is inferred from a missing review.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare');p.add_argument('--output',type=Path,required=True)
    p=sub.add_parser('check');p.add_argument('--suite',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:
        if args.command=='prepare': prepare(args.output); print(args.output);return 0
        report=check_suite(args.suite);write(args.output,report);print(args.output);return 0 if report['complete'] else 1
    except (ValueError,OSError) as exc: print('error: '+str(exc),file=sys.stderr);return 1

if __name__=='__main__':sys.exit(main())
