#!/usr/bin/env python3
"""Behavioral checks for editorial review, complementary selection and omissions."""
import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from test_resume_workflow import ResumeTests, completed_process, document, workflow, editorial, exporter, validate_records
import resume_process as process
import resume_quality as quality
import resume_layout as layout
from select_evidence import role_score, view, complementary_shortlist


class QualityTests(unittest.TestCase):
    setUp = ResumeTests.setUp
    tearDown = ResumeTests.tearDown
    put = ResumeTests.put
    strength = ResumeTests.strength
    selection = ResumeTests.selection
    cli = ResumeTests.cli
    refresh_plan = ResumeTests.refresh_plan
    approve_guidance = ResumeTests.approve_guidance
    fake_pdf = ResumeTests.fake_pdf
    representation = ResumeTests.representation
    delivery_fixture = ResumeTests.delivery_fixture

    def role(self):
        return {'role_id': 'technical', 'title': 'Principal Engineer', 'central_requirement': 'Build reliable systems',
                'requirements': [{'text': 'Build reliable systems', 'weight': 'essential', 'kind': 'build', 'evidenced_by': [self.aid]},
                                 {'text': 'Teach engineers', 'weight': 'important', 'kind': 'communicate', 'evidenced_by': [self.other]}]}

    def test_type_money_and_age_do_not_override_relevance(self):
        atom = copy.deepcopy(self.pack['evidence_atoms'][0]); atom['id'] = self.aid
        atom.update(outcome_type='output', occurred={'start': '2001'})
        score, reasons = role_score(atom, self.role(), {})
        for category in ('business_outcome', 'output', 'activity', None):
            changed = dict(atom, outcome_type=category, occurred={'start': '2026'})
            self.assertEqual(role_score(changed, self.role(), {})[0], score)
        self.assertTrue(any('proposed link' in r for r in reasons))
        self.assertGreater(score, role_score(dict(atom, id='E_UNRELATED', outcome_type='business_outcome'), self.role(), {})[0])

    def test_complementary_selection_covers_missing_requirement(self):
        role = self.role(); role['requirements'][0]['evidenced_by'].append('E_DUPLICATE')
        atoms = [{'id': self.aid}, {'id': 'E_DUPLICATE'}, {'id': self.other}]
        result = complementary_shortlist(atoms, role, 2)
        self.assertEqual({a['id'] for a in result}, {self.aid, self.other})
        with self.assertRaises(ValueError): complementary_shortlist(atoms, role, 0)

    def test_brief_builder_preserves_complementary_coverage(self):
        role = self.role()
        duplicate = copy.deepcopy(next(a for a in self.pack['evidence_atoms'] if a['id'] == self.aid))
        duplicate['id'] = 'E_DUPLICATE'; self.pack['evidence_atoms'].append(duplicate)
        role['requirements'][0]['evidenced_by'].append('E_DUPLICATE')
        self.put('data/packs/pack.json', self.pack); self.put('data/roles/technical.json', role)
        self.brief['role_id'] = 'technical'; self.put('data/briefs/resume-a-brief.json', self.brief)
        _, selection = self.selection(limit=2)
        chosen = {r['evidence_id'] for r in selection['recommendations']}
        self.assertIn(self.other, chosen)
        self.assertIn('communication and knowledge sharing', next(r['contribution'] for r in selection['recommendations'] if r['evidence_id'] == self.other))

    def test_unselected_available_atom_is_not_a_new_fact_question(self):
        doc = document.document_from_markdown(self.md)
        specs = quality.omission_specs(self.pack, self.plan, doc, self.role())
        omitted = next(s for s in specs if s['kind'] == 'requirement')
        self.assertEqual(omitted['availability'], 'available_omission')
        self.assertIn(self.other, omitted['candidate_ids'])
        context = {'editorial': [], 'omissions': [omitted]}
        pending = quality.pending_quality(context)
        pending['omissions'][0].update(disposition='needs_evidence', reason='Request facts already in pack')
        self.assertTrue(quality.quality_errors(pending, context, doc))

    def test_private_declined_and_explicitly_omitted_evidence_is_not_suggested(self):
        role = self.role(); role['requirements'][1]['evidenced_by'] = [self.private, self.other]
        specs = quality.omission_specs(self.pack, self.plan, document.document_from_markdown(self.md), role, excluded=[self.other])
        self.assertTrue(all(not s['candidate_ids'] for s in specs if s['kind'] == 'requirement'))
        self.assertNotIn('E_CX_INTERNAL_TOOL', json.dumps(specs))
        atom = next(a for a in self.pack['evidence_atoms'] if a['id'] == self.other); atom['evidence_status'] = 'declined'
        specs = quality.omission_specs(self.pack, self.plan, document.document_from_markdown(self.md), role)
        self.assertTrue(all(self.other not in s['candidate_ids'] for s in specs))

    def test_no_link_is_unmapped_not_proof_of_missing_experience(self):
        role = self.role(); role['requirements'][1]['evidenced_by'] = []
        row = next(s for s in quality.omission_specs(self.pack, self.plan, document.document_from_markdown(self.md), role) if s['kind'] == 'requirement')
        self.assertEqual(row['availability'], 'unmapped')

    def test_latest_role_review_does_not_demand_metrics(self):
        rows = quality.omission_specs(self.pack, self.plan, document.document_from_markdown(self.md))
        self.assertTrue(any(r['kind'] == 'recent_work' for r in rows))
        self.assertTrue(any(self.aid in r['support_in_draft'] for r in rows))

    def test_pending_editorial_review_cannot_pass_without_reasoned_passages(self):
        record = completed_process(self)
        record['quality']['editorial'][0].update(reason='', passages=[])
        self.assertTrue(any('reasoning and visible passages' in e for e in process.process_errors(record)))
        record = completed_process(self)
        record['quality']['editorial'][0]['passages'][0]['text'] = 'A different, invented accomplishment.'
        self.assertTrue(any('reviewed block' in e for e in process.process_errors(record)))

    def test_review_questions_and_omissions_cannot_disappear(self):
        record = completed_process(self); record['quality']['editorial'].pop()
        self.assertTrue(any('exact current review' in e for e in process.process_errors(record)))
        record = completed_process(self); record['quality']['omissions'] = []
        self.assertTrue(any('exact current review' in e for e in process.process_errors(record)))

    def test_summary_and_metric_value_get_specific_review(self):
        self.artifact.write_text(self.md.replace('## Experience', 'A proven innovative leader.\n\n## Experience'))
        record = process.prepare(self.artifact, self.plan_path)
        opening = next(r for r in record['quality']['editorial'] if r['dimension'] == 'opening')
        blocks = {b['id']: b for b in document.document_from_markdown(self.artifact.read_text())['blocks']}
        self.assertTrue(any('proven' in blocks[bid]['text'] for bid in opening['block_ids']))
        self.assertTrue(any(r['dimension'] == 'metric_value' for r in record['quality']['editorial']))

    def test_explicit_summary_heading_is_reviewed(self):
        self.artifact.write_text(self.md.replace('## Experience', '## Professional Summary\n\nAn innovative executive and proven leader.\n\n## Experience'))
        record = process.prepare(self.artifact, self.plan_path)
        opening = next(r for r in record['quality']['editorial'] if r['dimension'] == 'opening')
        blocks = {b['id']:b for b in document.document_from_markdown(self.artifact.read_text())['blocks']}
        self.assertTrue(any('innovative executive' in blocks[bid]['text'] for bid in opening['block_ids']))

    def test_legacy_reviews_remain_readable_but_do_not_gain_new_approval(self):
        record = completed_process(self); record['process_version'] = 1; record.pop('quality')
        self.assertEqual(process.process_errors(record, final=False), [])
        self.assertTrue(any('legacy process' in e for e in process.process_errors(record)))
        path = self.put('outputs/old-process.json', record)
        revised = process.prepare(self.artifact, self.plan_path, path)
        self.assertEqual(revised['process_version'], 2)
        self.assertTrue(all(r['status'] == 'pending' for r in revised['quality']['editorial']))

    def test_layout_observations_are_required_for_publication(self):
        evaluation = self.delivery_fixture()
        path = self.root/'outputs/technical-draft-process.json'
        record = json.loads(path.read_text()); record['quality'].pop('layout')
        self.assertIn('visual review', quality.delivery_quality_errors(record, evaluation['run']['exports'])[0])

    def test_layout_is_bound_to_the_actual_exports(self):
        evaluation = self.delivery_fixture()
        process_record = json.loads((self.root/'outputs/technical-draft-process.json').read_text())
        self.assertEqual(quality.delivery_quality_errors(process_record, evaluation['run']['exports']), [])
        changed = dict(evaluation['run']['exports'], sha256='0'*64)
        self.assertTrue(quality.delivery_quality_errors(process_record, changed))

    def test_layout_cli_creates_pending_review_and_preserves_content_review(self):
        evaluation = self.delivery_fixture()
        source = self.root/'outputs/technical-draft-process.json'
        result = self.cli('resume_process.py', 'layout', '--input', source,
                          '--exports', evaluation['run']['exports']['path'], '--output', 'outputs/layout-process.json')
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        saved = json.loads((self.root/'outputs/layout-process.json').read_text())
        self.assertEqual(saved['quality']['layout']['status'], 'pending')
        self.assertEqual(saved['quality']['editorial'], json.loads(source.read_text())['quality']['editorial'])
        self.assertTrue(process.process_errors(saved))

    @unittest.skipUnless(os.environ.get('CAREER_TEST_REAL_PDF') == '1', 'set CAREER_TEST_REAL_PDF=1 for real page geometry')
    def test_real_pdf_locates_all_blocks_across_multiple_pages(self):
        filler = '\n- Co-designed a recovery procedure; validated it in quarterly exercises. <!-- Evidence: ' + self.aid + ' -->\n'
        self.artifact.write_text(self.md + filler * 45)
        report, path = exporter.export(self.artifact, 'outputs/real-quality', self.plan_path)
        self.assertTrue(report['complete'], report)
        pdf = report['formats']['pdf']
        self.assertGreater(pdf['pages'], 1)
        self.assertEqual(pdf['layout']['status'], 'measured')
        self.assertEqual(len(pdf['layout']['pages']), pdf['pages'])
        self.assertEqual(len(pdf['layout']['blocks']), len(document.document_from_markdown(self.artifact.read_text())['blocks']))
        self.assertEqual(exporter.validate_export_report(path), [])
        self.assertEqual(self.pack_path.read_bytes(), self.pack_before)



class GeometryTests(unittest.TestCase):
    def page(self, number, texts, spacing=18):
        return {'page': number, 'width': 600, 'height': 800,
                'lines': [{'text': t, 'x': 40, 'y': 40+i*spacing, 'width': 480, 'height': 14} for i,t in enumerate(texts)]}

    def test_split_bullet_and_late_evidence_are_located(self):
        doc = document.document_from_markdown('# Alex Vale\n\n## Experience\n\n- Co-built recovery tooling. <!-- Evidence: E_RECOVERY -->\n\n- Taught engineers. <!-- Evidence: E_TEACH -->')
        pages = [self.page(1, ['Alex Vale', 'Experience', 'Co-built recovery']), self.page(2, ['tooling.', 'Taught engineers.'])]
        plan = {'impressions': [{'prominence': 'leading', 'basis': 'direct', 'evidence_ids': ['E_TEACH']}]}
        report = layout.diagnostics(doc, pages, plan)
        self.assertEqual(report['status'], 'measured')
        self.assertEqual(report['blocks'][2]['pages'], [1,2])
        self.assertEqual({f['kind'] for f in report['findings']}, {'split_prose','late_leading_evidence'})

    def test_sparse_final_page_and_orphan_heading_are_review_findings(self):
        doc = document.document_from_markdown('# Alex Vale\n\n## Experience\n\n- Built tooling.')
        pages = [self.page(1, ['Alex Vale']+['Filler']*39+['Experience']), self.page(2, ['Built tooling.'])]
        kinds = {f['kind'] for f in layout.diagnostics(doc, pages)['findings']}
        self.assertIn('uneven_final_page', kinds); self.assertIn('separated_heading', kinds)

    def test_repeated_text_is_matched_in_order(self):
        doc = document.document_from_markdown('# Alex Vale\n\n- Shared wording.\n\n- Shared wording.')
        report = layout.diagnostics(doc, [self.page(1,['Alex Vale','Shared wording.']), self.page(2,['Shared wording.'])])
        self.assertEqual([b['pages'] for b in report['blocks']], [[1],[1],[2]])

    def test_missing_geometry_and_unmatched_text_are_honest(self):
        doc = document.document_from_markdown('# Alex Vale')
        self.assertEqual(layout.diagnostics(doc, None)['status'], 'unavailable')
        report = layout.diagnostics(doc, [self.page(1,['Something else'])])
        self.assertEqual(report['status'], 'partial'); self.assertEqual(report['blocks'][0]['pages'], [])

    def test_poppler_coordinates_and_anchor_text_are_preserved(self):
        xml = '<?xml version="1.0"?><pdf2xml><page number="1" width="600" height="800"><text top="40" left="30" width="200" height="15">See <a href="https://example.invalid">work</a>.</text></page></pdf2xml>'
        pages = layout.poppler_geometry(xml)
        self.assertEqual(pages[0]['lines'][0]['text'], 'See work.')
        self.assertEqual(pages[0]['lines'][0]['y'], 40)


class CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tempfile
        from run_resume_quality import prepare
        cls.temp = tempfile.TemporaryDirectory(prefix='career-quality-corpus-')
        cls.suite = Path(cls.temp.name)/'suite'
        cls.manifest = prepare(cls.suite)

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def test_five_fictional_packs_are_schema_valid_and_no_candidate_is_invented(self):
        from validate_pack import check
        from run_resume_quality import check_suite
        from schema_tools import load
        for case in self.manifest['cases']:
            path = self.suite/case['case_id']/'data/packs/fixture.json'
            result = check(path, load('career.schema.json'), root=path.parents[2])
            self.assertFalse(result[0], result)
        report = check_suite(self.suite)
        self.assertEqual(len(report['cases']), 5)
        self.assertFalse(report['complete'])
        self.assertTrue(all(r['reader_quality']=='unmeasured' for r in report['cases']))

    def test_missing_cases_or_changed_inputs_cannot_pass_the_benchmark(self):
        from run_resume_quality import check_suite
        coordinator = self.suite/'coordinator.json'; original = coordinator.read_bytes()
        altered = json.loads(original); altered['cases'] = []
        try:
            coordinator.write_text(json.dumps(altered))
            with self.assertRaisesRegex(ValueError, 'exact fixture'): check_suite(self.suite)
        finally: coordinator.write_bytes(original)
        path = self.suite/'promotions/data/packs/fixture.json'; original = path.read_bytes()
        try:
            path.write_text('{}')
            result = next(r for r in check_suite(self.suite)['cases'] if r['case_id']=='promotions')
            self.assertTrue(any('fixture input changed' in e for e in result['deterministic_errors']))
        finally: path.write_bytes(original)

    def test_reader_judgment_needs_exact_candidate_and_actual_passages(self):
        from run_resume_quality import check_suite, digest
        workspace = self.suite/'nonfinancial-impact'
        pack = json.loads((workspace/'data/packs/fixture.json').read_text()); atom = pack['evidence_atoms'][0]
        path = workspace/'outputs/candidate-draft.md'
        path.write_text('# Casey Hart\n\nLondon · casey.hart@example.invalid\n\n## Experience\n\n### Alder Systems | Principal Engineer | 2022-03 to present\n\n- '+atom['star']['action']+' '+atom['star']['result']+' <!-- Evidence: E_PREVENTION -->\n')
        report = check_suite(self.suite); result = next(r for r in report['cases'] if r['case_id']=='nonfinancial-impact')
        self.assertFalse(result['deterministic_errors'], result)
        self.assertEqual(result['reader_quality'], 'unmeasured')
        review_path = workspace/'reader-review.json'; review = json.loads(review_path.read_text())
        review.update(reviewer='Fictional test reviewer', context='shared', artifact_sha256=digest(path), observations=['Shared technical delivery with adoption.'])
        for row in review['criteria']: row.update(status='pass', reason='Explicit fictional reviewer response for validator testing.', passages=[atom['star']['action']])
        review_path.write_text(json.dumps(review))
        result = next(r for r in check_suite(self.suite)['cases'] if r['case_id']=='nonfinancial-impact')
        self.assertEqual(result['reader_quality'],'reviewed_pass')
        path.write_text(path.read_text()+'\nChanged wording.\n')
        result = next(r for r in check_suite(self.suite)['cases'] if r['case_id']=='nonfinancial-impact')
        self.assertEqual(result['reader_quality'],'unmeasured')
        path.unlink(); review_path.write_text(json.dumps(dict(review, artifact_sha256=None)))


del ResumeTests
if __name__ == '__main__': unittest.main(verbosity=2)
