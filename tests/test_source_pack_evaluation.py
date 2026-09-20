"""Calibrate source checks with paraphrases and intentional factual errors.

These fixtures test the evaluator, not the model. Live extraction runs separately.
"""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from source_pack_evaluation import FIXTURES, SOURCE_CASES, ReviewStructure, evaluate
from run_editorial_scenarios import workspace, checks, script, save
from build_review_navigation_fixture import fixture
from review_html import render_review


def example(case):
    if (FIXTURES/case/'calibration.json').is_file():
        return json.loads((FIXTURES/case/'calibration.json').read_text())
    source = (FIXTURES/case/'sources/resume.md').read_text()
    ref = {'source_id':'SRC_RESUME','excerpt':source}
    common = {'external_safe':False,'evidence_status':'self_asserted','source_refs':[ref]}
    if case == 'collaboration':
        roles = [{'employment_id':'R1','employer':'Northstar Software','title':'Platform Engineer','start':'2019-03','end':'2022-06'},
                 {'employment_id':'R2','employer':'Northstar Software','title':'Senior Platform Engineer','start':'2022-07','end':'2025-11'}]
        claims = [('Cedar rehearsal runner','Collaborated with three engineers to build the Cedar runner.', 'Two teams adopted rehearsals.','R2'),
                  ('Willow mentoring','Mentored two graduate engineers in Willow sessions.', 'They facilitated subsequent reviews themselves.','R2')]
        qualification = {'education_id':'Q1','institution':'Learning Grove','qualification':'Safe Systems training course','end':'2023'}
    else:
        roles = [{'employment_id':'R1','employer':'Relay Ops Services','employer_of_record':'Relay Ops Services','title':'Service Reliability Analyst','start':'2020-02','end':None}]
        claims = [('Lantern recovery','Found the stale credential during Lantern and replaced it with the service owner.', 'The scheduled failover completed.','R1'),
                  ('Moth handover','Created the Moth checklist with colleagues.', 'Both shifts used it to find unresolved tickets.','R1')]
        qualification = {'education_id':'Q1','institution':'Example Qualifications','qualification':'ITIL Foundation certification','end':'2019'}
    atoms = [dict(copy.deepcopy(common), id='E'+str(n), title=title, employment_id=role,
                  star={'situation':title,'task':'Contribute to the work','action':action,'result':result},
                  metrics=[],skills=[],outcome_type='output',corroborators=[])
             for n,(title,action,result,role) in enumerate(claims)]
    pack = {'schema_version':'1.4','name':'Fictional evaluator calibration',
            'employment':[dict(copy.deepcopy(common),**role) for role in roles], 'evidence_atoms':atoms,
            'education':[dict(copy.deepcopy(common),**qualification)],
            'source_records':[{'source_id':'SRC_RESUME','source_type':'markdown','path':'data/sources/resume.md',
                               'sha256':hashlib.sha256(source.encode()).hexdigest(),'character_count':len(source),'independent':False}]}
    if case == 'operations':
        pack['employment'][0]['notes'] = 'Unresolved date conflict: July 2024 in the contract note, August 2024 in the resume; please confirm.'
        pack['employment'][0]['evidence_status'] = 'unresolved'
    return pack


class EvaluationTests(unittest.TestCase):
    def failures(self, pack, case='collaboration'):
        return [r['check'] for r in evaluate(pack,case) if not r['passed']]

    def test_reasonable_paraphrases_pass(self):
        for case in SOURCE_CASES.values():
            with self.subTest(case=case):
                self.assertEqual(self.failures(example(case),case),[])
        pack=example('collaboration')
        pack['evidence_atoms'][0]['star']['action']='Co-developed the Cedar runner with 3 other engineers.'
        pack['evidence_atoms'][0]['star']['result']='Used by 2 teams.'
        self.assertEqual(self.failures(pack),[])

    def test_shared_ownership_inflation_fails(self):
        pack=example('collaboration')
        pack['evidence_atoms'][0]['star']['action']='Solely built the Cedar runner.'
        self.assertIn('cedar_fact_1',self.failures(pack))
        self.assertIn('no_unsupported_claim_1',self.failures(pack))

    def test_missing_distinctive_work_does_not_pass_via_source_quotes(self):
        pack=example('collaboration'); pack['evidence_atoms'].pop()
        self.assertIn('willow_present_once',self.failures(pack))

    def test_correct_basis_does_not_hide_wrong_metric_value(self):
        pack = example('leadership')
        atom = next(a for a in pack['evidence_atoms'] if 'Juniper' in a['title'])
        atom['metrics'] = [{'value': '$32M cumulative revenue',
                            'basis': 'Cumulative pipeline on touched accounts, not booked revenue.'}]
        self.assertIn('juniper_metric_value_1', self.failures(pack, 'leadership'))
        atom['metrics'][0]['value'] = '$32M cumulative pipeline, not booked revenue'
        self.assertNotIn('juniper_metric_value_1', self.failures(pack, 'leadership'))
        atom['metrics'].append('$32M revenue')
        self.assertIn('juniper_metric_value_1', self.failures(pack, 'leadership'))

    def test_dates_scope_and_role_assignment_fail_independently(self):
        mutations=[('role_chronology_1',lambda p:p['employment'][0].update(start='2018-03')),
                   ('cedar_fact_3',lambda p:p['evidence_atoms'][0]['star'].update(result='20 teams adopted it.')),
                   ('cedar_role_link',lambda p:p['evidence_atoms'][0].update(employment_id='R1'))]
        for expected,mutate in mutations:
            pack=example('collaboration');mutate(pack)
            self.assertIn(expected,self.failures(pack))

    def test_training_promoted_to_certification_fails(self):
        pack=example('collaboration');pack['education'][0]['qualification']='Safe Systems professional certification'
        self.assertIn('training_not_promoted_to_award',self.failures(pack))

    def test_duplicate_achievement_and_job_requirement_contamination_fail(self):
        pack=example('collaboration');pack['evidence_atoms'].append(copy.deepcopy(pack['evidence_atoms'][0]))
        self.assertIn('cedar_present_once',self.failures(pack))
        pack=example('collaboration');pack['evidence_atoms'][0]['skills']=['Kubernetes']
        self.assertIn('no_unsupported_claim_2',self.failures(pack))

    def test_unmeasured_outcome_inflation_fails(self):
        pack=example('operations');pack['evidence_atoms'][0]['star']['result']='Saved £500000 and reduced risk by 40%.'
        self.assertIn('no_unsupported_claim_2',self.failures(pack,'operations'))

    def test_client_as_employer_and_hidden_conflict_fail(self):
        pack=example('operations');pack['employment'][0]['employer']='Harbour Care';pack['employment'][0]['employer_of_record']='Harbour Care'
        self.assertIn('no_extra_employers',self.failures(pack,'operations'))
        pack=example('operations');pack['employment'][0].pop('notes')
        self.assertIn('date_conflict_visible',self.failures(pack,'operations'))

    def test_structural_checks_use_real_renderer_and_survive_copy_changes(self):
        state=fixture();state['groups']=[{'achievement':'evidence_atoms/E_NAV_000','support':['field/name']}]
        page=render_review(state)
        for rendered in (page,page.replace('Your proposed career record','Proposed history').replace('Show achievement and role together','Related records')):
            parsed=ReviewStructure(rendered)
            self.assertTrue(parsed.readable)
            self.assertTrue(parsed.has_connected_review)
        self.assertFalse(ReviewStructure(page.replace('id="career-overview"','id="removed"')).readable)
        self.assertFalse(ReviewStructure(page.replace('class="connected"','class="unrelated"')).has_connected_review)

    def test_operations_candidate_uses_valid_schema_and_can_be_reviewed(self):
        root=workspace('source-operations')
        self.addCleanup(shutil.rmtree,root)
        pack=example('operations')
        save(root,'data/candidates/proposed.json',pack)
        session=script(root,'career_core.py','review','start','--candidate','data/candidates/proposed.json','--id','operations').strip()
        script(root,'career_core.py','review','render','--session',session,'--output','outputs/review.html')
        result=checks(root,'source-operations',{'is_error':False,'result':'Review ready.'})
        self.assertTrue(all(r['passed'] for r in result),result)
        # The schema also permits a client display name when the actual employer
        # is explicitly retained as employer_of_record.
        pack['employment'][0]['employer']='Harbour Care'
        self.assertEqual(self.failures(pack,'operations'),[])

    def test_runner_starts_with_only_raw_sources_and_evaluates_staged_proposal(self):
        root=workspace('source-collaboration')
        self.addCleanup(shutil.rmtree,root)
        self.assertFalse(list((root/'data/packs').glob('*.json')))
        self.assertFalse(list(root.rglob('expected.json')))
        self.assertFalse(list((root/'data/candidates').glob('*')))
        pack=example('collaboration')
        save(root,'data/candidates/proposed.json',pack)
        session=script(root,'career_core.py','review','start','--candidate','data/candidates/proposed.json','--id','first').strip()
        script(root,'career_core.py','review','render','--session',session,'--output','outputs/review.html')
        result=checks(root,'source-collaboration',{'is_error':False,'result':'Review ready.'})
        self.assertTrue(all(r['passed'] for r in result),result)
        first=checks(root,'first-pack',{'is_error':False,'result':'The rehearsal contribution is ready to review. You can pause here.'})
        self.assertTrue(all(r['passed'] for r in first),first)
        maintenance=checks(root,'maintenance',{'is_error':False,'result':'Review ready.'})
        self.assertTrue(next(r['passed'] for r in maintenance if r['check']=='connected_review_available'))
        # The handed-off proposal, rather than an unrelated passing candidate,
        # must match the immutable session pin.
        pack['evidence_atoms'][0]['star']['action']='Solely built the Cedar runner.'
        save(root,'data/candidates/proposed.json',pack)
        self.assertTrue(all(r['passed'] for r in checks(root,'source-collaboration',{'is_error':False,'result':'Review ready.'})))
        proposal=json.loads((root/session).read_text())['proposal']['path']
        save(root,proposal,pack)
        result=checks(root,'source-collaboration',{'is_error':False,'result':'Review ready.'})
        self.assertIn('proposal_matches_review',[r['check'] for r in result if not r['passed']])


if __name__ == '__main__':
    unittest.main(verbosity=2)
