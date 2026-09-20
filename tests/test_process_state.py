"""Regressions from real intake failures, using private fictional workspaces."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from editorial_fixture import ROOT, personas, pack_for
sys.path.insert(0, str(ROOT/'scripts'))
import question_history as questions
from career_profile import digest, reassess_strength
from career_review import source_annotations
from career_state import dates, reading_state
from career_intake import reading_batches
from pack_io import pin, write_view
from verify_excerpts import verify
try:
    from source_pack_evaluation import evaluate
    from test_source_pack_evaluation import example
    from run_editorial_scenarios import run_model, completed
    DEVELOPER_EVALUATION = True
except ModuleNotFoundError:
    DEVELOPER_EVALUATION = False


def assessment(pack, strength=None):
    strength = strength or pack['strengths_profile'][0]
    atoms = {a['id']: a for a in pack['evidence_atoms']}
    return {'strength_sha256': digest(strength), 'support': {i: digest(atoms[i]) for i in strength['evidence_ids']},
            'interpretation': strength['interpretation'], 'reason': 'Reviewed the same recurring contribution against the corrected evidence.',
            'limitations': [{'index': i, 'action': 'retain', 'reason': 'This qualification still applies to the corrected evidence.'}
                            for i, _ in enumerate(strength.get('limitations', []))]}


class ProcessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='career-process-test-')
        self.root = Path(self.temp.name)
        self.pack = pack_for(personas()[0])
        self.pack['metadata'] = {}
        self.path = self.write('data/candidates/proposal.json', self.pack)
        self.target = 'evidence_atoms/' + self.pack['evidence_atoms'][0]['id']

    def tearDown(self): self.temp.cleanup()

    def write(self, name, value):
        p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(value if isinstance(value,str) else json.dumps(value,indent=2));return p

    def ask(self, text='Was this delivered by the team?', **kwargs):
        return questions.ask({'question':text,'targets':[self.target],**kwargs},self.path,self.root)

    def test_answer_survives_restart_and_reimport_does_not_reopen(self):
        row=self.ask();answer=questions.respond(row['id'],1,'answered','Yes, by the team.','Fictional owner',root=self.root)
        self.assertEqual(self.ask()['state'],'answered')
        self.assertEqual(questions.load(row['id'],root=self.root)[0]['revision'],2)
        generated=[{'question':row['question'],'subject':self.target.split('/')[1],'optional':False}]
        self.assertEqual(questions.queue(self.pack,generated,root=self.root),[])
        self.assertEqual(answer['source_record']['sha256'],pin(self.root/answer['record']['path'],self.root)['sha256'])

    def test_short_answer_cannot_be_cited_for_an_unrelated_record(self):
        row=self.ask();answer=questions.respond(row['id'],1,'answered','Yes','Fictional owner',root=self.root)
        self.pack['source_records']=[answer['source_record']]
        self.pack['evidence_atoms'][0]['source_refs']=[answer['source_ref']]
        self.pack['evidence_atoms'][1]['source_refs']=[answer['source_ref']]
        report=verify(self.pack,self.root)
        own=[r for r in report['excerpts'] if r['record']==self.target]
        other=[r for r in report['excerpts'] if r['record']=='evidence_atoms/'+self.pack['evidence_atoms'][1]['id']]
        self.assertEqual(own[0]['status'],'verified')
        self.assertEqual(other[0]['status'],'mismatch')

    def test_question_keeps_exact_proposal_context_after_candidate_changes(self):
        row = self.ask()
        self.write('data/candidates/proposal.json', {})
        answer = questions.respond(row['id'], 1, 'answered', 'Yes', 'Fictional owner', root=self.root)
        context = json.loads((self.root / answer['context']['pack']['path']).read_text())
        self.assertEqual(context, self.pack)
        self.assertIsNone(questions.answer_scope_error(answer['source_record'], self.target, self.root))

    def test_stale_revision_cannot_answer_changed_question(self):
        row=self.ask();questions.respond(row['id'],1,'deferred',by='Fictional owner',root=self.root)
        with self.assertRaisesRegex(ValueError,'Question changed'):
            questions.respond(row['id'],1,'answered','Yes','Fictional owner',root=self.root)

    def test_deferred_and_declined_are_not_required_questions(self):
        for state in ['deferred','declined']:
            row=self.ask('May we discuss '+state+' work?')
            questions.respond(row['id'],1,state,by='Fictional owner',root=self.root)
        self.assertEqual(questions.queue(self.pack,root=self.root),[])
        self.assertEqual(len(questions.queue(self.pack,include_closed=True,root=self.root)),2)

    def test_enrichment_cannot_be_marked_required(self):
        with self.assertRaises(ValueError):self.ask(kind='enrichment',required=True)
        row=self.ask(kind='enrichment')
        self.assertFalse(row['required'])
        self.assertEqual(questions.queue(self.pack,root=self.root),[])
        self.assertEqual(len(questions.queue(self.pack,optional=True,root=self.root)),1)

    def test_tampered_question_history_is_detected(self):
        row=self.ask();questions.respond(row['id'],1,'answered','Team','Fictional owner',root=self.root)
        self.write(row['record']['path'],'{}')
        with self.assertRaisesRegex(ValueError,'changed input'):questions.catalogue(self.root)

    def test_legacy_import_is_previewable_idempotent_and_preserves_pack(self):
        before=self.path.read_bytes();log=self.write('reviews/old.md','Who delivered it? The team.')
        mapping=self.write('data/private/mapping.json',{'answers':[{'question':'Who delivered it?','answer':'The team.',
                    'targets':[self.target],'by':'Fictional owner','pack':str(self.path),'source':pin(log,self.root)}]})
        self.assertEqual(questions.import_answers(mapping,root=self.root)['entries'][0]['status'],'ready')
        self.assertFalse((self.root/'reviews/questions').exists())
        questions.import_answers(mapping,True,self.root);questions.import_answers(mapping,True,self.root)
        self.assertEqual(questions.catalogue(self.root)[0]['revision'],2)
        self.assertEqual(self.path.read_bytes(),before)

    def test_unknown_legacy_mapping_is_reported_not_guessed(self):
        mapping=self.write('data/private/mapping.json',{'answers':[{'question':'Who?'}]})
        self.assertEqual(questions.import_answers(mapping,root=self.root)['entries'][0]['status'],'needs_mapping')

    def test_invalid_legacy_mapping_is_rejected_in_preview_without_partial_question(self):
        source = self.write('reviews/old.md', 'Who? Team.')
        mapping = self.write('data/private/mapping.json', {'answers': [{'question': 'Who?', 'answer': 'Team.',
            'targets': ['evidence_atoms/MISSING'], 'by': 'Owner', 'pack': str(self.path), 'source': pin(source, self.root)}]})
        for apply in (False, True):
            self.assertEqual(questions.import_answers(mapping, apply, self.root)['entries'][0]['status'], 'needs_mapping')
            self.assertFalse((self.root / 'reviews/questions').exists())

    def test_new_source_notes_are_annotations_not_authority(self):
        source={'source_id':'S','source_type':'text','path':'data/sources/a.txt','independent':False,'notes':'Assistant summary'}
        proposed={'source_records':[copy.deepcopy(source)]}
        notes=source_annotations(proposed,{})
        self.assertNotIn('notes',proposed['source_records'][0]);self.assertEqual(notes['S']['authority'],'import_commentary')
        existing={'source_records':[copy.deepcopy(source)]}
        self.assertEqual(source_annotations(existing,existing),{})
        self.assertIn('notes',existing['source_records'][0])

    def test_unknown_source_fields_and_independence_do_not_bypass_review(self):
        for extra in ({'independent':True},{'claims':'Invented'}):
            s={'source_id':'S','source_type':'text','path':'a','independent':False,'notes':'Comment',**extra}
            self.assertEqual(source_annotations({'source_records':[s]},{}),{})

    def test_unresolved_dates_stay_visible_and_unknown_does_not_mean_present(self):
        role={'start':'2020','end':'2024-08','evidence_status':'unresolved','notes':'July or August 2024; sources disagree.'}
        self.assertIn('Unresolved',dates(role));self.assertIn('July or August',dates(role))
        self.assertIn('End not recorded',dates({'start':'2020'}))

    def test_large_intake_batches_preserve_scope_and_flag_oversized_sources(self):
        rows = [{'path': str(i), 'status': 'read', 'extracted_text': str(i)+'.txt', 'character_count': size}
                for i, size in enumerate((40000, 30000, 90000, 10000))]
        rows += [{'path': 'duplicate', 'status': 'duplicate'}, {'path': 'old', 'status': 'unchanged'}]
        batches = reading_batches(rows)
        self.assertEqual([s['path'] for b in batches for s in b['sources']], ['0', '1', '2', '3'])
        self.assertTrue(next(s for b in batches for s in b['sources'] if s['path'] == '2')['read_in_sections'])
        self.assertTrue(all(b['characters'] <= 60000 or len(b['sources']) == 1 for b in batches))
        self.assertEqual(reading_batches(rows[-2:]), [])

    def test_failed_view_replace_preserves_last_good_page(self):
        path=self.write('outputs/career-record.html','last good page')
        with patch.object(Path,'replace',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):write_view(path,'new page',self.root)
        self.assertEqual(path.read_text(),'last good page')
        self.assertEqual(reading_state(self.path,self.root)['state'],'stale')

    def test_reassessment_requires_each_limitation_and_current_evidence(self):
        s=self.pack['strengths_profile'][0];s['limitations']=['Measurement basis unrecorded.','Independent corroboration unavailable.']
        a=assessment(self.pack);a['limitations'].pop()
        with self.assertRaisesRegex(ValueError,'every prior limitation'):reassess_strength(s,self.pack,a)
        a=assessment(self.pack);a['support']={}
        with self.assertRaisesRegex(ValueError,'does not match'):reassess_strength(s,self.pack,a)

    def test_reassessment_replaces_stale_caveat_and_preserves_residual_unknown(self):
        s=self.pack['strengths_profile'][0];s['limitations']=['Measurement basis unrecorded.','Independent corroboration unavailable.']
        a=assessment(self.pack);a['limitations'][0]={'index':0,'action':'replace','text':'Based on the owner’s recorded tracker; denominator remains unknown.','reason':'The owner supplied the measurement source.'}
        receipt=reassess_strength(s,self.pack,a)
        self.assertNotIn('Measurement basis unrecorded.',s['limitations'])
        self.assertIn('Independent corroboration unavailable.',s['limitations'])
        self.assertEqual(receipt['result_sha256'],digest(s))

    @unittest.skipUnless(DEVELOPER_EVALUATION, 'model evaluator belongs to the developer checkout')
    def test_negation_is_not_an_award_but_a_separate_affirmative_award_fails(self):
        p=example('collaboration');p['education'][0]['qualification']='Safe Systems training course (no certification awarded)'
        self.assertTrue(next(r['passed'] for r in evaluate(p,'collaboration') if r['check']=='training_not_promoted_to_award'))
        p['education'][0]['qualification']+='; professional certification in production safety'
        self.assertFalse(next(r['passed'] for r in evaluate(p,'collaboration') if r['check']=='training_not_promoted_to_award'))

    @unittest.skipUnless(DEVELOPER_EVALUATION, 'model evaluator belongs to the developer checkout')
    def test_model_error_retains_exit_stderr_subtype_and_cost(self):
        response={'is_error':True,'subtype':'error_max_budget_usd','total_cost_usd':2.03,'errors':['Stopped']}
        with patch('run_editorial_scenarios.subprocess.run',return_value=subprocess.CompletedProcess([],1,json.dumps(response),'diagnostic')):
            payload,details=run_model([],self.root)
        self.assertEqual(payload,response);self.assertEqual(details['exit_code'],1);self.assertEqual(details['stderr'],'diagnostic')
        self.assertFalse(completed({'is_error': False, 'result': None}))
        self.assertFalse(completed({'is_error': False, 'result': ''}))

    @unittest.skipUnless(DEVELOPER_EVALUATION, 'model evaluator belongs to the developer checkout')
    def test_malformed_response_and_timeout_keep_partial_output(self):
        with patch('run_editorial_scenarios.subprocess.run',return_value=subprocess.CompletedProcess([],2,'partial','error')):
            payload,details=run_model([],self.root)
        self.assertTrue(payload['is_error']);self.assertEqual(details['stdout'],'partial')
        with patch('run_editorial_scenarios.subprocess.run',side_effect=subprocess.TimeoutExpired([],1,output=b'partial',stderr=b'timed out')):
            payload,details=run_model([],self.root)
        self.assertEqual(details['stdout'],'partial');self.assertEqual(details['stderr'],'timed out')

    @unittest.skipUnless(DEVELOPER_EVALUATION, 'model evaluator belongs to the developer checkout')
    def test_streamed_progress_survives_and_final_result_is_selected(self):
        event = {'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': 'Reading sources.'}]}}
        result = {'type': 'result', 'is_error': False, 'result': 'Review ready.', 'total_cost_usd': 0.5}
        stream = json.dumps(event) + '\n' + json.dumps(result) + '\n'
        with patch('run_editorial_scenarios.subprocess.run', return_value=subprocess.CompletedProcess([], 0, stream, '')):
            payload, details = run_model([], self.root)
        self.assertEqual(payload, result)
        self.assertEqual(details['stdout'], stream)
        with patch('run_editorial_scenarios.subprocess.run', side_effect=subprocess.TimeoutExpired([], 1, output=json.dumps(event).encode())):
            payload, details = run_model([], self.root)
        self.assertFalse(completed(payload))
        self.assertIn('Reading sources.', details['stdout'])

    @unittest.skipUnless(DEVELOPER_EVALUATION, 'model evaluator belongs to the developer checkout')
    def test_new_raw_source_profiles_reject_protected_fact_mutations(self):
        mutations=[
            ('leadership',lambda p:p['employment'][0].update(title='Director')),
            ('leadership',lambda p:p.pop('positioning_preferences')),
            ('leadership',lambda p:p['evidence_atoms'][1]['star'].update(result='$32M booked revenue.')),
            ('leadership',lambda p:p['evidence_atoms'][0]['star'].update(action='Sponsored the Cobalt project.')),
            ('leadership',lambda p:p['evidence_atoms'][2]['star'].update(result='Four staff at peak, three at departure; recognition covered 700 people.')),
            ('leadership',lambda p:p['evidence_atoms'][-1]['star'].update(action='Founded the existing support team.')),
            ('early-career',lambda p:p['evidence_atoms'][1]['star'].update(action='Sole author of the Aster handbook.')),
            ('early-career',lambda p:p['evidence_atoms'][2].update(evidence_status='externally_verified')),
            ('transition',lambda p:p['employment'][0].update(start='2019-01')),
            ('transition',lambda p:p['evidence_atoms'][2]['star'].update(action='Sole inventor on a granted patent.')),
            ('transition',lambda p:p['evidence_atoms'].pop(0)),
        ]
        for case,mutate in mutations:
            with self.subTest(case=case):
                p=example(case);self.assertTrue(all(r['passed'] for r in evaluate(p,case)))
                mutate(p);self.assertTrue(any(not r['passed'] for r in evaluate(p,case)))

    @unittest.skipUnless(DEVELOPER_EVALUATION, 'model evaluator belongs to the developer checkout')
    def test_equivalent_split_claims_do_not_need_identical_record_count(self):
        p=example('collaboration');first=p['evidence_atoms'][0]
        split=copy.deepcopy(first);split['id']='E_SPLIT';split['title']='Cedar adoption';split['star']['action']='Supported the Cedar rollout.'
        first['star']['result']='Implementation completed.'
        p['evidence_atoms'].append(split)
        self.assertTrue(all(r['passed'] for r in evaluate(p,'collaboration')))

    @unittest.skipUnless(DEVELOPER_EVALUATION, 'model evaluator belongs to the developer checkout')
    def test_forbidden_claim_cannot_be_assembled_across_unrelated_records(self):
        p = example('leadership')
        p['employment'][0]['notes'] = p['employment'][0].get('notes', '') + ' No recognition claim was generated.'
        self.assertTrue(all(r['passed'] for r in evaluate(p, 'leadership')))
        p['evidence_atoms'][1]['star']['result'] = 'Generated $32M in revenue.'
        self.assertFalse(next(r['passed'] for r in evaluate(p, 'leadership') if r['check'] == 'no_unsupported_claim_1'))


if __name__=='__main__':unittest.main(verbosity=2)
