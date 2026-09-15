#!/usr/bin/env python3
"""Process regressions use fictional people and explicit reviewer responses."""
import copy
import json
import unittest

from test_resume_workflow import ResumeTests, completed_process, workflow, editorial, document, exporter, manifest, validate_records
import resume_process as process


class ProcessTests(unittest.TestCase):
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

    def test_preparation_does_not_approve_or_change_inputs(self):
        before = [p.read_bytes() for p in (self.pack_path, self.plan_path, self.artifact)]
        record = process.prepare(self.artifact, self.plan_path)
        self.assertTrue(all(r['status'] == 'pending' for r in record['checks']))
        self.assertTrue(process.process_errors(record))
        self.assertEqual(process.process_errors(record, final=False), [])
        self.assertEqual(before, [p.read_bytes() for p in (self.pack_path, self.plan_path, self.artifact)])

    def test_every_constraint_needs_its_own_review(self):
        atom = next(a for a in self.pack['evidence_atoms'] if a['id'] == self.aid)
        atom['constraints'] = ['Co-created Recovery Lab with Alex Chen; do not imply sole program creation.',
                               'Credit Priya Shah when naming the conference talk.']
        self.put('data/packs/pack.json', self.pack)
        self.pack['strengths_profile'][0] = self.strength('S_DEPTH', [self.aid])
        self.put('data/packs/pack.json', self.pack); self.refresh_plan()
        record = completed_process(self)
        constraints = [r for r in record['checks'] if r['kind'] == 'constraint']
        self.assertEqual([r['source'] for r in constraints], atom['constraints'])
        constraints[0].update(status='issue', reason='Created the program implies sole ownership; dataset co-authorship concerns a different object.')
        self.assertTrue(any('unresolved constraint' in e for e in process.process_errors(record)))
        record['checks'].remove(constraints[1])
        self.assertTrue(any('every claim' in e for e in process.process_errors(record)))

    def test_passed_check_requires_own_visible_excerpt(self):
        record = completed_process(self)
        row = next(r for r in record['checks'] if r['kind'] == 'ownership')
        row['artifact_excerpt'] = 'Morgan Vale'
        self.assertTrue(any('own block' in e for e in process.process_errors(record)))

    def test_prominent_strength_cannot_pass_on_presence_alone(self):
        record = completed_process(self)
        record['prominence'][0].update(observed='supporting', reader_impression_indexes=[])
        self.assertTrue(any('presence alone' in e for e in process.process_errors(record)))

    def test_supporting_prominence_is_a_valid_explicit_choice(self):
        self.plan['impressions'][0]['prominence'] = 'supporting'; self.approve_guidance()
        record = completed_process(self)
        record['prominence'][0].update(observed='supporting', reader_impression_indexes=[])
        self.assertEqual(process.process_errors(record), [])

    def test_prominence_cannot_cite_missing_reader_observation(self):
        record = completed_process(self); record['prominence'][0]['reader_impression_indexes'] = [99]
        self.assertTrue(any('missing reader observation' in e for e in process.process_errors(record)))

    def test_private_strength_cannot_be_relabelled_as_an_impression(self):
        original = copy.deepcopy(self.plan['impressions'][0])
        self.brief['priority_evidence_ids'] = [self.aid]
        self.put('data/briefs/resume-a-brief.json', self.brief)
        self.pack['strengths_profile'][0]['external_safe'] = False
        self.put('data/packs/pack.json', self.pack)
        self.selection_path, _ = self.selection()
        self.plan = workflow.prepare_plan(self.selection_path, 'private-review')
        original['strength_ids'] = []; self.plan['impressions'] = [original]; self.plan['status'] = 'ready'
        self.approve_guidance()
        errors = workflow.plan_errors(self.plan)
        self.assertTrue(any('empty strength_ids' in e for e in errors))
        self.plan['privacy_reviews'] = [{'impression_id': original['id'], 'strength_id': 'S_DEPTH',
            'disposition': 'independent_evidence', 'reason': 'Attempted relabeling of the same private interpretation.'}]
        self.approve_guidance()
        self.assertTrue(any('restricted strength interpretation' in e for e in workflow.plan_errors(self.plan)))
        self.plan['impressions'][0]['message'] = 'Designed and exercised recovery procedures.'
        self.plan['privacy_reviews'][0]['reason'] = 'Only the approved project action is expressed; the broader private interpretation is excluded.'
        self.approve_guidance()
        self.assertEqual(workflow.plan_errors(self.plan), [])
        view = workflow.plan_view(self.plan_path)
        self.assertNotIn('privacy_reviews', json.dumps(view))
        self.assertNotIn(self.pack['strengths_profile'][0]['interpretation'], json.dumps(view))

    def test_privacy_review_changes_invalidate_drafting_review(self):
        self.plan['privacy_reviews'] = [{'impression_id': 'fake', 'strength_id': 'fake', 'disposition': 'pending', 'reason': ''}]
        self.assertTrue(any('drafting guidance review' in e for e in workflow.plan_errors(self.plan)))

    def chronology_fixture(self):
        pack = {'employment': [
            {'employment_id': 'ENG', 'employer': 'Example Labs', 'title': 'Engineer', 'start': '2015-09', 'end': '2018-02', 'external_safe': True},
            {'employment_id': 'STAFF', 'employer': 'Example Labs', 'title': 'Staff Engineer', 'start': '2018-02', 'end': '2020-11', 'external_safe': True}],
            'evidence_atoms': [{'id': 'E_TALKS', 'employment_id': 'STAFF', 'occurred': {'start': '2015', 'end': '2020'}}]}
        return pack

    def test_spanning_achievement_is_not_owned_by_one_title(self):
        pack = self.chronology_fixture()
        doc = document.document_from_markdown('### Example Labs | Staff Engineer | 2018-02 to 2020-11\n\n- Presented public talks. <!-- Evidence: E_TALKS -->')
        self.assertTrue(any('spans dates outside' in e for e in process.chronology_errors(doc, pack)))
        doc['blocks'][0]['text'] = 'Example Labs | Career highlights | 2015-09 to 2020-11'
        # Year-only event start is compatible with a September company start.
        self.assertEqual(process.chronology_errors(doc, pack), [])

    def test_title_dates_cannot_borrow_employer_wide_tenure(self):
        doc = document.document_from_markdown('### Example Labs | Staff Engineer | 2015 to 2020')
        self.assertTrue(any('title tenure' in e for e in process.chronology_errors(doc, self.chronology_fixture())))

    def test_wrong_employment_link_requires_core_correction(self):
        pack = self.chronology_fixture()
        pack['evidence_atoms'][0].update(employment_id='ENG', occurred={'start': '2019', 'end': '2020'})
        doc = document.document_from_markdown('### Example Labs | Staff Engineer | 2018 to 2020\n\n- Presented talks. <!-- Evidence: E_TALKS -->')
        self.assertTrue(any('through Core' in e for e in process.chronology_errors(doc, pack)))

    def test_undated_or_inferred_event_needs_review_without_false_date_error(self):
        pack = self.chronology_fixture(); pack['evidence_atoms'][0]['occurred']['inferred'] = True
        doc = document.document_from_markdown('### Example Labs | Staff Engineer | 2018 to 2020\n\n- Presented talks. <!-- Evidence: E_TALKS -->')
        self.assertEqual(process.chronology_errors(doc, pack), [])
        self.assertTrue(any(c['kind'] == 'chronology' for c in process.required_checks(doc, pack)))

    def test_unused_cycles_cannot_be_called_exhausted(self):
        record = completed_process(self); record['revision']['stop_reason'] = 'budget_exhausted'
        self.assertTrue(any('cycles remain' in e for e in process.process_errors(record)))

    def test_revision_history_counts_drafts_not_repeat_reviews(self):
        first = completed_process(self); path = self.put('outputs/v1-process.json', first)
        second = completed_process(self, process.prepare(self.artifact, self.plan_path, path))
        self.assertEqual(process.revision_count(second), 0)
        self.artifact = self.root / 'outputs/v2-draft.md'
        self.artifact.write_text(self.md.replace('a recovery procedure', 'recovery procedures'))
        third = completed_process(self, process.prepare(self.artifact, self.plan_path, path))
        self.assertEqual(process.revision_count(third), 1)
        self.assertEqual(process.process_errors(third), [])
        third['revision']['stop_reason'] = 'budget_exhausted'
        self.assertTrue(any('cycles remain' in e for e in process.process_errors(third)))

    def test_outstanding_findings_cannot_disappear(self):
        first = completed_process(self)
        first['revision'].update(stop_reason='needs_user', findings=[{'category': 'user_choice', 'description': 'Choose emphasis.', 'disposition': 'open', 'reason': 'Two supported directions.'}])
        path = self.put('outputs/v1-process.json', first)
        second = process.prepare(self.artifact, self.plan_path, path)
        second['revision']['findings'] = []
        self.assertTrue(any('cannot disappear' in e for e in process.process_errors(second, final=False)))

    def test_budget_exhaustion_does_not_approve_unfixed_editing(self):
        record = completed_process(self)
        record['revision'].update(limit=0, budget_origin='user', budget_reason='Fictional user requested review only.', stop_reason='budget_exhausted', findings=[
            {'category': 'editing', 'description': 'Program co-creator missing.', 'disposition': 'deferred', 'reason': 'Review-only run.'}])
        self.assertTrue(any('budget exhaustion does not waive' in e for e in process.process_errors(record)))

    def test_shortening_needs_an_actual_reviewed_candidate(self):
        record = completed_process(self, process.prepare(self.artifact, self.plan_path, compression_requested=True, target='Shorter without losing evidence'))
        self.assertTrue(any('actual compression attempt' in e for e in process.process_errors(record)))
        record['compression'].update(status='attempted', baseline=record['artifact'], candidate=record['artifact'])
        self.assertTrue(any('no-op' in e for e in process.process_errors(record)))

    def test_compression_measures_text_and_requires_meaning_review(self):
        baseline = self.root / 'outputs/longer-draft.md'; baseline.write_text(self.md.replace('Co-designed', 'Jointly worked with colleagues and co-designed'))
        record = completed_process(self)
        record['compression'].update(requested=True, target='Concise wording', status='attempted', baseline=editorial.pin(baseline),
            candidate=record['artifact'], assessment='Reduced wording while retaining ownership and quarterly verification.',
            meaning_review=[{'dimension': d, 'status': 'pass', 'reason': 'Reviewed against the cited recovery example.'}
                            for d in ('ownership','context','method','timeframe','scope','strengths')])
        self.assertEqual(process.process_errors(record), [])
        measured = process.compression_report(record, self.pack)
        self.assertLess(measured['after_words'], measured['before_words'])
        record['compression']['meaning_review'][0]['status'] = 'issue'
        self.assertTrue(any('meaning losses' in e for e in process.process_errors(record)))

    def test_pdf_wrap_tolerance_is_expected_source_aware(self):
        doc = document.document_from_markdown('# Taylor Quinn\n\n- Built individual-contributor paths; see https://example.invalid/a/very/long/path.')
        text = '\n'.join(document.paragraphs(doc))
        wrapped = text.replace('individual-contributor', 'individual-\ncontributor').replace('/very/long/', '/very/\nlong/')
        self.assertEqual(exporter.validate_content(doc, wrapped, pdf=True), 'expected_text_with_physical_pdf_wraps')
        for invalid in (wrapped.replace('Taylor Quinn', 'TaylorQuinn'), wrapped.replace('Built individual', 'Builtindividual'),
                        text.replace('individual-contributor', 'individual- contributor'), text.replace('/very/long/', '/very/ long/'),
                        wrapped.replace('/path.', '/other.')):
            with self.assertRaises(ValueError): exporter.validate_content(doc, invalid, pdf=True)
        with self.assertRaises(ValueError): exporter.validate_content(doc, wrapped)  # no PDF tolerance in DOCX/TXT

    def test_orphan_citation_is_an_authored_error(self):
        with self.assertRaisesRegex(ValueError, 'orphan'):
            document.document_from_markdown('- Co-designed recovery.\n<!-- Evidence: E_RECOVERY -->')
        self.assertEqual(document.document_from_markdown('- Co-designed recovery.\n  <!-- Evidence: E_RECOVERY -->')['blocks'][0]['evidence_ids'], ['E_RECOVERY'])

    def test_publishable_requires_process_even_with_verified_exports(self):
        evaluation = self.delivery_fixture(); path = self.root / 'outputs/technical-draft-evaluation.json'
        self.assertEqual(validate_records.check(path)[1], [])
        evaluation['run'].pop('process'); self.put('outputs/technical-draft-evaluation.json', evaluation)
        self.assertTrue(any('pinned process review' in e for e in validate_records.check(path)[1]))

    def test_process_pin_cannot_approve_a_different_draft(self):
        reviewed = completed_process(self); path = self.put('outputs/v1-process.json', reviewed)
        self.artifact.write_text(self.md + '\nChanged text.\n')
        with self.assertRaises(ValueError):
            manifest.manifest(artifact=self.artifact, selection=self.selection_path, plan=self.plan_path, process=path)

    def test_handoff_derives_status_and_links_without_inventing_gap(self):
        record = completed_process(self); path = self.put('outputs/v1-process.json', record)
        text = process.handoff(path)
        self.assertIn('0/2 used; 2 remaining', text)
        self.assertIn('No evaluation supplied', text)
        self.assertIn('Reader context: `shared`', text)
        self.assertIn('SHA-256', text)
        self.assertNotIn('one-year gap', text)
        self.assertNotIn('must stay', text)
        self.assertEqual(self.pack_path.read_bytes(), self.pack_before)

    def test_handoff_with_delivery_uses_validated_files(self):
        self.delivery_fixture()
        text = process.handoff('outputs/technical-draft-process.json', 'outputs/technical-draft-evaluation.json')
        self.assertIn('Publishable: true', text)
        for fmt in ('PDF','TXT','DOCX'):
            self.assertIn(fmt + ': verified', text)
        (self.root / 'outputs/delivery/files/resume.txt').write_text('Lost content')
        with self.assertRaises(ValueError):
            process.handoff('outputs/technical-draft-process.json', 'outputs/technical-draft-evaluation.json')

    def test_previous_screen_findings_are_imported_and_cannot_be_dropped(self):
        self.delivery_fixture()
        path = self.root / 'outputs/technical-draft-screen.json'
        screen = json.loads(path.read_text())
        screen['fix_in_document'] = ['Credit the program co-creator, not only the dataset authors.']
        self.put('outputs/technical-draft-screen.json', screen)
        record = process.prepare(self.artifact, self.plan_path, 'outputs/technical-draft-process.json')
        self.assertEqual(record['revision']['findings'][0]['description'], screen['fix_in_document'][0])
        self.assertEqual(process.process_errors(record, final=False), [])
        record['revision']['findings'] = []
        self.assertTrue(any('actionable imported' in e for e in process.process_errors(record, final=False)))

    def test_feedback_for_an_unrelated_draft_is_rejected(self):
        self.delivery_fixture()
        path = self.root / 'outputs/technical-draft-screen.json'
        screen = json.loads(path.read_text()); screen['run']['artifact_sha256'] = '0' * 64
        self.put('outputs/unrelated-screen.json', screen)
        record = process.prepare(self.artifact, self.plan_path, feedback=['outputs/unrelated-screen.json'])
        self.assertTrue(any('outside this revision chain' in e for e in process.process_errors(record, final=False)))

    def test_cli_does_not_replace_existing_record(self):
        result = self.cli('resume_process.py', 'prepare', '--artifact', self.artifact, '--plan', self.plan_path, '--output', 'outputs/v1-process.json')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        again = self.cli('resume_process.py', 'prepare', '--artifact', self.artifact, '--plan', self.plan_path, '--output', 'outputs/v1-process.json')
        self.assertNotEqual(again.returncode, 0)


del ResumeTests  # Do not rediscover the imported fixture's separate test suite.

if __name__ == '__main__':
    unittest.main(verbosity=2)
