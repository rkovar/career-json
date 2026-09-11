#!/usr/bin/env python3
"""Human review contracts in fictional workspaces, including partial acceptance."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from editorial_fixture import personas, pack_for
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
from pack_review import fingerprint, units


class PackReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='pack-review-test-')
        self.root=Path(self.temp.name)
        shutil.copytree(ROOT/'schemas',self.root/'schemas')
        self.pack=pack_for(personas()[0])
        self.pack['metadata']={}
        self.put('data/packs/base.json',self.pack)
        self.proposed=copy.deepcopy(self.pack)
        self.proposed['evidence_atoms'][0]['star']['action']+='; clarified shared ownership'
        self.session='reviews/pack-reviews/check/session.json'

    def tearDown(self):self.temp.cleanup()

    def put(self,path,value):
        p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value));return p

    def cli(self,*args,success=True):
        r=subprocess.run([sys.executable,str(ROOT/'scripts/pack_review.py'),*args],cwd=self.root,
                         env={**os.environ,'CAREER_WORKSPACE':str(self.root)},text=True,capture_output=True)
        if success:self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        else:self.assertNotEqual(r.returncode,0,r.stdout+r.stderr)
        return r

    def start(self):
        self.put('data/candidates/proposal.json',self.proposed)
        self.cli('start','--candidate','data/candidates/proposal.json','--id','check')
        return json.loads(self.cli('status','--session',self.session).stdout)

    def choices(self,actions,publication='unchanged',omissions=None):
        s=json.loads((self.root/self.session).read_text())
        payload={'review_id':'check','proposal_sha256':s['proposal']['sha256'],'reviewed_by':'Fictional Person',
                 'decisions':[{'key':key,'fingerprint':fingerprint(key,self.proposed),'action':action,
                               'publication':publication if 'external_safe' in (units(self.proposed).get(key) or {}) else 'unchanged',
                               'note':'Please keep my shared contribution clear.' if action=='correct' else ''} for key,action in actions.items()],
                 'omissions':omissions or []}
        self.put('reviews/choices.json',payload)
        self.cli('record','--session',self.session,'--input','reviews/choices.json')
        return payload

    def publish(self,name='accepted',success=True):
        self.cli('publish','--session',self.session,'--output',f'data/packs/{name}.json',success=success)
        return json.loads((self.root/f'data/packs/{name}.json').read_text()) if success else None

    def test_staging_never_changes_current_pack(self):
        before=(self.root/'data/packs/base.json').read_bytes()
        state=self.start()
        self.assertTrue(any(r['change']=='changed' for r in state['items']))
        self.assertEqual(list((self.root/'data/packs').glob('*.json')),[self.root/'data/packs/base.json'])
        self.assertEqual((self.root/'data/packs/base.json').read_bytes(),before)
        self.publish(success=False)

    def test_acceptance_does_not_raise_confidence_or_grant_publication(self):
        self.proposed['evidence_atoms'][0]['evidence_status']='corroborated'
        self.start();self.choices({'evidence_atoms/E_STORY_1':'accept'})
        accepted=self.publish()
        atom=accepted['evidence_atoms'][0]
        self.assertEqual(atom['star'],self.proposed['evidence_atoms'][0]['star'])
        self.assertEqual(atom['evidence_status'],'self_asserted')
        self.assertFalse(atom['external_safe'])
        self.assertEqual(accepted['evidence_atoms'][1],self.pack['evidence_atoms'][1])
        self.assertIn('evidence_atoms/E_STORY_1',accepted['metadata']['human_review']['items'])

    def test_explicit_external_permission_is_separate(self):
        self.start();self.choices({'evidence_atoms/E_STORY_1':'accept'},publication='external')
        self.assertTrue(self.publish()['evidence_atoms'][0]['external_safe'])

    def test_corrections_deferral_and_omissions_survive_restart(self):
        self.start();self.choices({'evidence_atoms/E_STORY_1':'correct','evidence_atoms/E_STORY_2':'later'},
                                 omissions=[{'prompt':'What important work is missing?','answer':'A mentoring programme.'}])
        state=json.loads(self.cli('status','--session',self.session).stdout)
        self.assertEqual(state['omissions'][0]['answer'],'A mentoring programme.')
        self.assertEqual(next(r for r in state['items'] if r['key']=='evidence_atoms/E_STORY_1')['decision']['action'],'correct')
        self.publish(success=False)

    def test_private_restriction_does_not_accept_pending_correction(self):
        self.start();self.choices({'evidence_atoms/E_STORY_1':'correct'},publication='private')
        accepted=self.publish()
        self.assertEqual(accepted['evidence_atoms'][0]['star'],self.pack['evidence_atoms'][0]['star'])
        self.assertFalse(accepted['evidence_atoms'][0]['external_safe'])
        self.assertNotIn('evidence_atoms/E_STORY_1',accepted['metadata']['human_review']['items'])

    def test_partial_acceptance_can_resume_without_repeating_prior_choices(self):
        self.start();self.choices({'evidence_atoms/E_STORY_1':'accept','evidence_atoms/E_STORY_2':'later'})
        first=self.publish('first')
        self.choices({'evidence_atoms/E_STORY_2':'accept'})
        second=self.publish('second')
        self.assertEqual(second['metadata']['supersedes'],'data/packs/first.json')
        self.assertEqual(first['evidence_atoms'][0],second['evidence_atoms'][0])
        self.assertEqual(len(second['metadata']['human_review']['items']),2)
        self.publish('repeat',success=False)

    def test_new_pack_can_accept_all_without_resume_application(self):
        (self.root/'data/packs/base.json').unlink()
        self.proposed=self.pack
        self.start();self.choices({key:'accept' for key in units(self.proposed)})
        pack=self.publish()
        self.assertNotIn('supersedes',pack['metadata'])
        self.assertEqual(pack['strengths_profile'][0]['status'],self.proposed['strengths_profile'][0]['status'])
        self.assertFalse(pack['evidence_atoms'][0]['external_safe'])

    def test_stale_proposal_base_or_decision_is_rejected(self):
        self.start()
        payload=self.choices({'evidence_atoms/E_STORY_1':'accept'})
        payload['decisions'][0]['fingerprint']='0'*64
        self.put('reviews/wrong.json',payload)
        self.cli('record','--session',self.session,'--input','reviews/wrong.json',success=False)
        self.proposed['name']='Changed'
        self.put('reviews/pack-reviews/check/proposal.json',self.proposed)
        self.publish(success=False)

    def test_new_current_pack_requires_new_comparison(self):
        self.start();self.choices({'evidence_atoms/E_STORY_1':'accept'})
        newer=copy.deepcopy(self.pack);newer['metadata']['supersedes']='data/packs/base.json'
        self.put('data/packs/unrelated.json',newer)
        self.publish(success=False)

    def test_source_changes_require_review_of_affected_records(self):
        self.proposed=copy.deepcopy(self.pack)
        self.proposed['source_records'][0]['retrieved']='2026-09-09'
        self.start();self.choices({'source_records/SRC_SUBJECT':'accept'})
        self.publish(success=False)

    def test_html_contains_all_sections_source_excerpts_and_safe_text(self):
        self.proposed['evidence_atoms'][0]['star']['action']='<script>alert("not executable")</script>'
        self.start()
        self.cli('render','--session',self.session,'--output','outputs/review.html')
        text=(self.root/'outputs/review.html').read_text()
        for value in ('My career timeline','My strengths','What I want next','Show original source excerpts',
                      'What have we missed?',self.pack['source_records'][0]['path'],'Looks accurate'):
            self.assertIn(value,text)
        self.assertNotIn('<script>alert',text)
        self.assertIn('&lt;script&gt;',text)
        embedded=text.split('id="review-data">',1)[1].split('</script>',1)[0]
        self.assertEqual(json.loads(embedded)['review_id'],'check')

    def test_rejected_change_does_not_delete_previous_achievement(self):
        self.proposed['evidence_atoms']=self.proposed['evidence_atoms'][1:]
        self.proposed['strengths_profile']=[]
        self.start();self.choices({'evidence_atoms/E_STORY_1':'later','evidence_atoms/E_STORY_2':'accept'})
        accepted=self.publish()
        self.assertIn('E_STORY_1',[a['id'] for a in accepted['evidence_atoms']])

    def test_reimport_is_idempotent_but_later_reconsideration_is_preserved(self):
        self.start()
        first=self.choices({'evidence_atoms/E_STORY_1':'accept'})
        self.choices({'evidence_atoms/E_STORY_1':'accept'})
        folder=self.root/'reviews/pack-reviews/check/decisions'
        self.assertEqual(len(list(folder.glob('*.json'))),1)
        self.choices({'evidence_atoms/E_STORY_1':'correct'})
        self.put('reviews/again.json',first)
        self.cli('record','--session',self.session,'--input','reviews/again.json')
        self.assertEqual(len(list(folder.glob('*.json'))),3)
        self.assertEqual(self.publish()['evidence_atoms'][0]['star'],self.proposed['evidence_atoms'][0]['star'])

    def test_changed_wording_reopens_only_affected_accepted_item(self):
        self.start();self.choices({'evidence_atoms/E_STORY_1':'accept','evidence_atoms/E_STORY_2':'accept'})
        accepted=self.publish()
        accepted['evidence_atoms'][0]['star']['action']+='; newly proposed detail'
        self.put('data/candidates/next.json',accepted)
        self.cli('start','--candidate','data/candidates/next.json','--id','next')
        state=json.loads(self.cli('status','--session','reviews/pack-reviews/next/session.json').stdout)
        states={r['key']:r['review_status'] for r in state['items']}
        self.assertEqual(states['evidence_atoms/E_STORY_1'],'awaiting_review')
        self.assertEqual(states['evidence_atoms/E_STORY_2'],'accepted')

    def test_applied_decision_tampering_blocks_further_acceptance(self):
        self.start();self.choices({'evidence_atoms/E_STORY_1':'accept'})
        self.publish('first')
        batch=self.root/'reviews/pack-reviews/check/decisions/000001.json'
        changed=json.loads(batch.read_text());changed['reviewed_by']='Different Person'
        batch.write_text(json.dumps(changed))
        self.choices({'evidence_atoms/E_STORY_2':'accept'})
        self.publish('second',success=False)

    def test_first_import_questions_and_strengths_use_candidate(self):
        (self.root/'data/packs/base.json').unlink()
        self.put('data/candidates/proposal.json',self.proposed)
        for script,args in [('career_core.py',['status']),('open_questions.py',['--json'])]:
            result=subprocess.run([sys.executable,str(ROOT/'scripts'/script),*args,'--pack','data/candidates/proposal.json'],
                cwd=self.root,env={**os.environ,'CAREER_WORKSPACE':str(self.root)},capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIsInstance(json.loads(result.stdout),dict)

    def test_legacy_schema_issues_can_be_reviewed_but_not_silently_accepted(self):
        self.pack['evidence_atoms'][0]['capture']={'method':'manual','captured':'2026-08'}
        self.proposed=self.pack
        self.put('data/packs/base.json',self.pack)
        self.cli('start','--candidate','data/packs/base.json','--id','check')
        state=json.loads(self.cli('status','--session',self.session).stdout)
        self.assertTrue(state['session']['validation_warnings'])
        self.choices({'evidence_atoms/E_STORY_1':'accept'})
        self.publish(success=False)


if __name__=='__main__':unittest.main(verbosity=2)
