#!/usr/bin/env python3
"""Behavioral invariants of planning, editorial review and export on fictional data."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import test_editorial as fixtures
import editorial
import manifest
import resume_workflow as workflow
import export_resume as exporter
import resume_document as document
import validate_records
import resume_process


def completed_process(fixture, record=None):
    """An explicit fictional reviewer response, never production auto-approval."""
    record = record or resume_process.prepare(fixture.artifact, fixture.plan_path)
    blocks = {b['id']: b for b in document.document_from_markdown(fixture.artifact.read_text())['blocks']}
    for row in record['checks']:
        row.update(status='pass', reason='Fictional reviewer compared this passage with the recorded evidence and scope.',
                   artifact_excerpt=blocks[row['block_id']]['text'])
    for row in record['quality']['editorial']:
        row.update(status='pass', reason='Fictional reviewer found a specific shared contribution, useful verification context and clear wording.',
                   passages=[{'block_id': row['block_ids'][0], 'text': blocks[row['block_ids'][0]]['text']}])
    for row in record['quality']['omissions']:
        row.update(disposition='retain', reason='Fictional reviewer inspected alternatives and retained the narrowly scoped recovery example.')
    record['cold_read'] = {'context': 'shared', 'impressions': ['Designed and tested recovery procedures.']}
    for row in record['prominence']:
        row.update(block_ids=[b['id'] for b in blocks.values() if b['evidence_ids']], observed='leading',
                   reader_impression_indexes=[0], status='pass', reason='Concrete contribution stands out in the first experience bullet.')
    record['revision']['stop_reason'] = 'complete'
    for finding in record['revision']['findings']:
        finding.update(disposition='resolved', reason='Fictional reviewer inspected the comparison and retained the supported meaning.')
    return record


class ResumeTests(unittest.TestCase):
    def setUp(self):
        fixtures.EditorialTests.setUp(self)
        for module in (workflow, exporter):
            self.saved.append((module, 'ROOT', module.ROOT)); module.ROOT = self.root
        shutil.copytree(ROOT / 'docs/policies', self.root / 'docs/policies')
        self.brief['application'] = workflow.default_application('UK')
        self.brief_path = self.put('data/briefs/resume-a-brief.json', self.brief)
        self.selection_path, self.selection_record = self.selection()
        self.plan = workflow.prepare_plan(self.selection_path, 'plan-v1')
        self.plan['status'] = 'ready'
        self.plan['drafting_review_sha256'] = workflow.guidance_fingerprint(self.plan, self.brief)
        self.plan_path = self.put('data/plans/v1-plan.json', self.plan)
        self.md = '# Morgan Vale\n\nLondon · morgan.vale@example.invalid\n\n## Experience\n\n### Northwind Systems | Director of Platform Security | 2022-03 to present\n\n- Co-designed a recovery procedure; validated it in quarterly exercises. <!-- Evidence: ' + self.aid + ' -->\n'
        self.artifact = self.root / 'outputs/technical-draft.md'; self.artifact.write_text(self.md)
        self.pack_before = self.pack_path.read_bytes()

    tearDown = fixtures.EditorialTests.tearDown
    put = fixtures.EditorialTests.put
    strength = fixtures.EditorialTests.strength
    selection = fixtures.EditorialTests.selection
    cli = fixtures.EditorialTests.cli
    decision = fixtures.EditorialTests.decision

    def refresh_plan(self):
        self.put('data/briefs/resume-a-brief.json', self.brief)
        self.selection_path, self.selection_record = self.selection()
        self.plan = workflow.prepare_plan(self.selection_path, 'revised-plan')
        self.plan['status'] = 'ready'
        self.approve_guidance()

    def approve_guidance(self):
        self.plan['drafting_review_sha256'] = workflow.guidance_fingerprint(self.plan, self.brief)
        self.put('data/plans/v1-plan.json', self.plan)

    def test_public_and_named_views_allow_only_known_contact_fields(self):
        import select_evidence
        self.pack['private_profile'].update(notes='PRIVATE_NOTE', medical_history='PRIVATE_HISTORY')
        self.put('data/packs/pack.json', self.pack)
        for audience in ('public', 'named_recipient'):
            self.brief['audience'] = audience
            self.brief['application'] = workflow.default_application('UK', audience=audience)
            self.refresh_plan()
            view = workflow.plan_view(self.plan_path)
            self.assertNotIn('PRIVATE_NOTE', json.dumps(view))
            self.assertNotIn('PRIVATE_HISTORY', json.dumps(view))
            self.assertNotIn('publication_policy', view['contact'])
            self.assertIn('name', view['contact'])
            self.assertEqual('email' in view['contact'], audience == 'named_recipient')
        no_profile = copy.deepcopy(self.pack); no_profile.pop('private_profile')
        self.assertEqual(select_evidence.view(no_profile)['contact']['name'], self.pack['name'])

    def test_interactive_proposal_can_be_reviewed_but_not_generated_or_exported(self):
        self.brief['application']['review_mode'] = 'interactive'
        self.refresh_plan()
        self.assertEqual(self.selection_record['review_status'], 'proposed')
        for action in (lambda: workflow.plan_view(self.plan_path),
                       lambda: editorial.generation_view(self.selection_path),
                       lambda: manifest.manifest(artifact=self.artifact, selection=self.selection_path, plan=self.plan_path),
                       lambda: exporter.export(self.artifact, 'outputs/blocked', self.plan_path)):
            with self.assertRaisesRegex(ValueError, 'interactive'): action()
        self.assertFalse((self.root / 'outputs/blocked').exists())
        self.plan['status'] = 'proposed'; self.put('data/plans/v1-plan.json', self.plan)
        self.assertIn('Your resume choices', workflow.review_page(self.plan_path))
        self.selection_record.update(review_status='accepted', review_source_refs=[self.ref])
        self.put('data/selections/a-selection.json', self.selection_record)
        self.plan['selection'] = editorial.pin(self.selection_path); self.plan['status'] = 'ready'
        self.approve_guidance()
        self.assertTrue(workflow.plan_view(self.plan_path)['atoms'])

    def test_interactive_acceptance_without_person_source_stays_blocked(self):
        self.brief['application']['review_mode'] = 'interactive'; self.refresh_plan()
        self.selection_record['review_status'] = 'accepted'
        self.put('data/selections/a-selection.json', self.selection_record)
        with self.assertRaisesRegex(ValueError, 'answer source'):
            editorial.generation_view(self.selection_path)

    def test_drafting_guidance_preserves_employer_requirements_and_limitations(self):
        self.brief['application']['employer_instructions'] = 'Include availability.'
        self.brief['application']['submission_channel'] = 'portal'
        self.refresh_plan()
        self.plan['impressions'][0].update(basis='transferable', limitation='No direct experience in the target sector.')
        self.approve_guidance()
        view = workflow.plan_view(self.plan_path)['resume_plan']
        self.assertEqual(view['employer_instructions'], 'Include availability.')
        self.assertEqual(view['submission_channel'], 'portal')
        self.assertEqual(view['impressions'][0]['basis'], 'transferable')
        self.assertEqual(view['impressions'][0]['limitation'], 'No direct experience in the target sector.')

    def test_changed_or_unreviewed_guidance_cannot_reach_writer(self):
        original = copy.deepcopy(self.plan)
        for change in ('missing_review', 'message', 'limitation'):
            self.plan = copy.deepcopy(original)
            if change == 'missing_review': self.plan.pop('drafting_review_sha256')
            else: self.plan['impressions'][0][change] = 'PRIVATE_UNREVIEWED_TEXT'
            self.put('data/plans/v1-plan.json', self.plan)
            with self.assertRaisesRegex(ValueError, 'drafting guidance review'):
                workflow.plan_view(self.plan_path)
        preview = self.cli('resume_workflow.py', 'guidance', '--plan', self.plan_path)
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertIn('private_review_preview', json.loads(preview.stdout))
        self.assertNotEqual(json.loads(preview.stdout)['drafting_review_sha256'], original['drafting_review_sha256'])

    def test_role_assessment_reaches_writer_and_instruction_changes_require_review(self):
        self.put('data/roles/technical.json', {'role_id': 'technical', 'title': 'Technical specialist',
            'central_requirement': 'Technical design', 'requirements': [
                {'text': 'Technical design', 'weight': 'essential', 'evidenced_by': [
                    {'id': self.aid, 'linked_by': 'subject', 'note': 'My technical design contribution.'}]}]})
        self.brief['role_id'] = 'technical'; self.refresh_plan()
        self.plan['requirements'][0].update(assessment='transferable', explanation='Related setting only.')
        self.approve_guidance()
        self.assertEqual(workflow.plan_view(self.plan_path)['resume_plan']['requirements'], self.plan['requirements'])
        self.brief['application']['employer_instructions'] = 'Changed instructions.'
        self.put('data/briefs/resume-a-brief.json', self.brief)
        self.selection_path, self.selection_record = self.selection()
        self.plan['selection'] = editorial.pin(self.selection_path)
        self.put('data/plans/v1-plan.json', self.plan)
        with self.assertRaisesRegex(ValueError, 'drafting guidance review'): workflow.plan_view(self.plan_path)

    def test_anonymous_validation_covers_canonical_name_with_or_without_profile(self):
        import validate_artifact
        for mode in ('absent', 'different'):
            pack = copy.deepcopy(self.pack)
            if mode == 'absent': pack.pop('private_profile')
            else: pack['private_profile']['name'] = 'Alternative Name'
            self.artifact.write_text('# Morgan Vale\n\n- Co-designed recovery. <!-- Evidence: ' + self.aid + ' -->\n')
            errors, _ = validate_artifact.check(self.artifact, None, pack, application={'contact_mode': 'anonymous'})
            self.assertTrue(any('canonical name' in e for e in errors))
            self.artifact.write_text('# Applicant\n\n- Co-designed recovery. <!-- Evidence: ' + self.aid + ' -->\n')
            self.assertFalse(validate_artifact.check(self.artifact, None, pack, application={'contact_mode': 'anonymous'})[0])

    def test_representation_requires_excerpt_and_support_in_same_visible_block(self):
        excerpt = 'Investigated fraud alerts.'
        self.artifact.write_text(self.md + '\n- ' + excerpt + ' <!-- Evidence: ' + self.other + ' -->\n'
                                 + '\n<!-- A hidden claim. Evidence: ' + self.aid + ' -->\n')
        for invalid in (excerpt, 'Morgan Vale', 'A hidden claim.'):
            review = self.representation()
            review['strengths'][0]['artifact_excerpt'] = invalid
            review['impressions'] = [{'impression_id': self.plan['impressions'][0]['id'],
                'status': 'clearly_represented', 'evidence_ids': [self.aid], 'artifact_excerpt': invalid, 'reason': 'Test.'}]
            errors, _ = editorial.validate_record('representation', review)
            self.assertTrue(any('strength excerpt must be visible' in e for e in errors), errors)
            self.assertTrue(any('impression excerpt must be visible' in e for e in errors), errors)
        self.assertTrue(editorial.excerpt_supported('- Co-designed **recovery**. <!-- Evidence: ' + self.aid + ' -->',
                                                   'Co-designed **recovery**.', [self.aid]))
        self.assertFalse(editorial.excerpt_supported('<!-- Evidence: ' + self.aid + ' -->', self.aid, [self.aid]))

    def test_export_verification_preserves_word_boundaries(self):
        doc = document.document_from_markdown('# Zoë García\n\n- Built SQL pipelines in New York.')
        for recovered in ('ZoëGarcía Built SQL pipelines in New York.',
                          'Zoë García BuiltSQLpipelines in New York.',
                          'Zoë García Built SQL pipelines in NewYork.',
                          'Zoë García Bu ilt SQL pipelines in New York.'):
            with self.assertRaises(ValueError): exporter.validate_content(doc, recovered)
        exporter.validate_content(doc, 'Zoe\u0308 García\n\n• Built SQL\npipelines in New\u00a0York.\n')

    def test_plan_is_ready_and_facts_unchanged(self):
        self.assertEqual(workflow.plan_errors(self.plan, ready=True), [])
        self.assertEqual(self.pack_path.read_bytes(), self.pack_before)
        self.assertEqual(validate_records.check(self.plan_path)[1], [])

    def test_proposal_cannot_drive_generation(self):
        self.plan['status'] = 'proposed'; self.put('data/plans/v1-plan.json', self.plan)
        with self.assertRaisesRegex(ValueError, 'proposed'): workflow.plan_view(self.plan_path)

    def test_ready_requires_intended_message(self):
        self.plan['impressions'] = []
        self.assertTrue(workflow.plan_errors(self.plan))

    def test_no_private_support_or_unselected_support(self):
        self.plan['impressions'][0]['evidence_ids'] = [self.private]
        self.assertTrue(any('selected eligible' in e for e in workflow.plan_errors(self.plan)))

    def test_gap_cannot_look_supported(self):
        row = self.plan['impressions'][0]; row['basis'] = 'gap'; row['limitation'] = 'Not established'
        self.assertTrue(any('gaps need' in e for e in workflow.plan_errors(self.plan)))

    def test_transferable_needs_limitation(self):
        row = self.plan['impressions'][0]; row['basis'] = 'transferable'; row['limitation'] = ''
        self.assertTrue(any('limitation' in e for e in workflow.plan_errors(self.plan)))

    def test_each_selected_example_is_allocated(self):
        self.plan['sections'][0]['evidence_ids'] = []
        self.assertTrue(any('allocate exactly' in e for e in workflow.plan_errors(self.plan)))

    def test_stale_policy_and_selection_are_rejected(self):
        policy = self.root / workflow.POLICY; policy.write_text(policy.read_text() + '\n')
        self.assertTrue(any('changed input' in e for e in workflow.plan_errors(self.plan)))

    def test_new_brief_requires_plan_in_manifest(self):
        with self.assertRaisesRegex(ValueError, 'requires a ready'): manifest.manifest(selection=self.selection_path)
        record = manifest.manifest(artifact=self.artifact, selection=self.selection_path, plan=self.plan_path)
        self.assertEqual(manifest.editorial_staleness(record), [])
        self.plan_path.write_text(self.plan_path.read_text() + '\n')
        self.assertTrue(manifest.editorial_staleness(record))

    def test_format_settings_have_sources(self):
        app = self.brief['application']; app['setting_sources'].pop('paper_size')
        self.assertTrue(workflow.application_errors(self.brief))

    def test_invalid_page_limit_rejected(self):
        self.brief['application']['page_limit'] = 0
        self.assertTrue(workflow.application_errors(self.brief))

    def test_no_missing_required_export(self):
        self.brief['application']['required_exports'] = ['pdf']
        self.assertTrue(workflow.application_errors(self.brief))

    def test_safe_view_excludes_private_plan_prose_and_keeps_constraints(self):
        self.plan['sections'][0]['space_reason'] = 'PRIVATE_PLAN_REASON'
        self.put('data/plans/v1-plan.json', self.plan)
        view = workflow.plan_view(self.plan_path)
        self.assertNotIn('PRIVATE_PLAN_REASON', json.dumps(view))
        self.assertTrue(view['atoms'])
        self.assertIn('constraints', view['atoms'][0])

    def test_anonymous_view_suppresses_contact(self):
        self.brief['application']['contact_mode'] = 'anonymous'
        self.put('data/briefs/resume-a-brief.json', self.brief)
        self.selection_path, self.selection_record = self.selection()
        self.plan = workflow.prepare_plan(self.selection_path, 'plan-v2'); self.plan['status'] = 'ready'
        self.plan['drafting_review_sha256'] = workflow.guidance_fingerprint(self.plan, self.brief)
        self.put('data/plans/v1-plan.json', self.plan)
        self.assertEqual(workflow.plan_view(self.plan_path)['contact'], {})

    def test_selection_page_explains_choices_and_escapes_text(self):
        self.selection_record['recommendations'][0]['reason'] = '<script>alert(1)</script>'
        self.put('data/selections/a-selection.json', self.selection_record)
        self.plan['selection'] = editorial.pin(self.selection_path); self.put('data/plans/v1-plan.json', self.plan)
        page = workflow.review_page(self.plan_path)
        self.assertIn('What it adds', page); self.assertIn('&lt;script&gt;', page)
        self.assertNotIn('<script>', page); self.assertNotIn('PRIVATE_CANARY', page)

    def test_wording_preferences_require_a_person(self):
        record = self.decision(); record['subject'] = {'kind': 'wording', 'id': 'plain-verbs'}
        record['wording'] = {'text': 'Built', 'external_safe': True}
        self.assertTrue(editorial.validate_record('decision', record)[0])
        record.update(made_by='user', source_refs=[self.ref], action='include')
        self.assertEqual(editorial.validate_record('decision', record)[0], [])
        self.put('reviews/decisions/voice-decision.json', record)
        ctx = editorial.context_for(self.pack, self.brief)
        self.assertEqual(ctx['wording_preferences'], [{'example': 'Built', 'usage': 'prefer'}])
        self.assertNotIn(record['reason'], json.dumps(ctx))

    def test_specific_wording_replaces_broader_example(self):
        broad = self.decision(author='user', action='include', scope='person', scope_id='person')
        broad['subject'] = {'kind': 'wording', 'id': 'verbs'}
        broad['wording'] = {'text': 'Created', 'external_safe': True}
        self.put('reviews/decisions/broad-decision.json', broad)
        narrow = copy.deepcopy(broad)
        narrow.update(decision_id='D_NARROW', scope={'kind': 'application', 'id': self.brief['application_id']},
                      wording={'text': 'Built', 'external_safe': True})
        self.put('reviews/decisions/narrow-decision.json', narrow)
        self.assertEqual(editorial.context_for(self.pack, self.brief)['wording_preferences'], [{'example': 'Built', 'usage': 'prefer'}])

    def test_conflicting_wording_requires_supersession(self):
        record = self.decision(author='user', action='include')
        record['subject'] = {'kind': 'wording', 'id': 'verbs'}
        record['wording'] = {'text': 'Created', 'external_safe': True}
        self.put('reviews/decisions/one-decision.json', record)
        record.update(decision_id='D_TWO', wording={'text': 'Built', 'external_safe': True})
        self.put('reviews/decisions/two-decision.json', record)
        with self.assertRaisesRegex(ValueError, 'conflicting wording'): editorial.context_for(self.pack, self.brief)

    def representation(self):
        run = manifest.manifest(artifact=self.artifact, selection=self.selection_path, plan=self.plan_path)
        return {'artifact': 'outputs/technical-draft.md', 'run': run,
                'reader_impressions': ['Designs dependable systems'],
                'strengths': [{'strength_id': 'S_DEPTH', 'status': 'clearly_represented', 'evidence_ids': [self.aid],
                               'artifact_excerpt': 'Co-designed a recovery procedure', 'reason': 'Contribution is explicit.'}],
                'findings': []}

    def test_plan_impressions_must_be_reviewed_even_if_strengths_are_reviewed(self):
        review = self.representation()
        self.assertTrue(any('every planned impression' in e for e in editorial.validate_record('representation', review)[0]))
        review['impressions'] = [{'impression_id': self.plan['impressions'][0]['id'], 'status': 'clearly_represented',
                                  'evidence_ids': [self.aid], 'artifact_excerpt': 'Co-designed a recovery procedure', 'reason': 'Explicit action.'}]
        self.assertEqual(editorial.validate_record('representation', review)[0], [])
        review['impressions'][0]['artifact_excerpt'] = 'Invented passage'
        self.assertTrue(any('exact artifact excerpt' in e for e in editorial.validate_record('representation', review)[0]))

    def test_planned_resume_cannot_be_publishable_without_all_exports(self):
        review = self.representation()
        review['impressions'] = [{'impression_id': self.plan['impressions'][0]['id'], 'status': 'clearly_represented',
                                  'evidence_ids': [self.aid], 'artifact_excerpt': 'Co-designed a recovery procedure', 'reason': 'Explicit action.'}]
        self.put('outputs/technical-draft-representation.json', review)
        evaluation = {'artifacts': ['outputs/technical-draft.md'], 'target_role': 'Engineering', 'publishable': True,
                      'evaluation_date': '2026-09-14', 'run': review['run'], 'findings': [], 'passed_checks': ['grounding']}
        path = self.put('outputs/technical-evaluation.json', evaluation)
        self.assertTrue(any('verified PDF' in e for e in validate_records.check(path)[1]))

    def test_default_cli_records_explicit_market_origin(self):
        result = self.cli('editorial.py', 'init-brief', '--id', 'other', '--application', 'other', '--market', 'US',
                          '--output', 'data/briefs/other-brief.json')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        app = editorial.read('data/briefs/other-brief.json')['application']
        self.assertEqual(app['paper_size'], 'Letter')
        self.assertEqual(app['setting_sources']['market']['origin'], 'user')

    def test_revision_reports_ownership_and_strength_loss(self):
        after = self.md.replace('Co-designed a recovery procedure; validated it in quarterly exercises.', 'Led resilience transformation.')
        findings = workflow.revision_findings(self.md, after, self.pack)
        row = next(f for f in findings if f['kind'] == 'claim_rewritten')
        self.assertIn('Co-designed', row['removed_qualifiers']); self.assertIn('quarterly', row['removed_qualifiers'])
        self.assertTrue(any(f['kind'] == 'strength_support_removed' for f in workflow.revision_findings(self.md, '# Morgan\n', self.pack)))

    def test_identical_revision_with_repeated_citations_has_no_false_findings(self):
        md = self.md + '\n- Another contribution. <!-- Evidence: ' + self.aid + ' -->\n'
        self.assertEqual(workflow.revision_findings(md, md, self.pack), [])

    def test_related_results_flagged_without_automatic_omission(self):
        atoms = [{'id': 'E_A', 'title': 'A', 'star': {'result': 'Shared result'}},
                 {'id': 'E_B', 'title': 'B', 'star': {'result': 'Shared result'}}]
        self.assertEqual(workflow.overlaps(atoms)[0]['evidence_ids'], ['E_A', 'E_B'])

    def test_docx_is_editable_semantic_unicode_and_matches_txt(self):
        md = self.md.replace('Morgan Vale', 'Zoë García').replace('quarterly exercises.', 'quarterly exercises. [Public work](https://example.invalid/work)')
        doc = document.document_from_markdown(md, 'Letter'); path = self.root / 'outputs/resume.docx'
        exporter.write_docx(doc, path)
        exporter.validate_content(doc, exporter.docx_text(path))
        exporter.validate_content(doc, document.plain_text(doc))
        with zipfile.ZipFile(path) as z:
            xml = z.read('word/document.xml').decode(); styles = z.read('word/styles.xml').decode()
            self.assertIn('Zoë García', xml); self.assertIn('numPr', xml); self.assertIn('outlineLvl', styles)
            self.assertNotIn('E_CX_', xml); self.assertNotIn('tbl', xml); self.assertNotIn('txbx', xml)
            self.assertIn('12240', xml)
        self.assertNotIn('evidence', document.submission_html(doc))
        self.assertNotIn('text-transform: uppercase', document.submission_html(doc))

    def test_export_rejects_missing_or_reordered_content(self):
        doc = document.document_from_markdown(self.md)
        with self.assertRaises(ValueError): exporter.validate_content(doc, '\n'.join(reversed(document.paragraphs(doc))))
        with self.assertRaises(ValueError): exporter.validate_content(doc, '\n'.join(document.paragraphs(doc)[:-1]))

    def test_unsupported_markup_never_silently_disappears(self):
        for markup in ('# Name\n\n| Hidden | table |', '# Name\n\n![photo](x)', '# Name\n\n<script>x</script>', '# Name\n\n[link](file:///private)'):
            with self.assertRaises(ValueError): document.document_from_markdown(markup)

    def test_pdf_failure_retains_txt_docx_and_fails_bundle(self):
        with patch.object(exporter, 'write_pdf', side_effect=ValueError('No PDF renderer')):
            report, path = exporter.export(self.artifact, 'outputs/export-v1', self.plan_path)
        self.assertFalse(report['complete'])
        self.assertEqual(report['formats']['txt']['status'], 'verified')
        self.assertEqual(report['formats']['docx']['status'], 'verified')
        self.assertTrue(exporter.validate_export_report(path))
        self.assertEqual(self.pack_path.read_bytes(), self.pack_before)
        with self.assertRaisesRegex(ValueError, 'exists'): exporter.export(self.artifact, 'outputs/export-v1')

    def fake_pdf(self, html, target):
        target.write_bytes(b'%PDF-test-fixture'); return 'fixture'

    def delivery_fixture(self):
        shutil.copytree(ROOT / 'scripts', self.root / 'scripts')
        recovered = '\n'.join(document.paragraphs(document.document_from_markdown(self.md)))
        with patch.object(exporter, 'write_pdf', side_effect=self.fake_pdf), patch.object(exporter, 'pdf_details', return_value={'text': recovered, 'pages': 1, 'links': []}):
            _, export_path = exporter.export(self.artifact, 'outputs/delivery', self.plan_path)
        from resume_quality import pending_layout
        reviewed = completed_process(self)
        reviewed['quality']['layout'] = pending_layout(export_path)
        reviewed['quality']['layout'].update(status='reviewed', observations='Fictional visual-review response for the mocked PDF; not a real rendering test.')
        process_path = self.put('outputs/technical-draft-process.json', reviewed)
        run = manifest.manifest(artifact=self.artifact, selection=self.selection_path, plan=self.plan_path, exports=export_path, process=process_path)
        rep = self.representation(); rep['run'] = run
        rep['impressions'] = [{'impression_id': self.plan['impressions'][0]['id'], 'status': 'clearly_represented',
                              'evidence_ids': [self.aid], 'artifact_excerpt': 'Co-designed a recovery procedure', 'reason': 'Explicit.'}]
        self.put('outputs/technical-draft-representation.json', rep)
        evaluation = {'artifacts': ['outputs/technical-draft.md'], 'target_role': 'Engineering', 'publishable': True,
                      'evaluation_date': '2026-09-14', 'run': run, 'findings': [], 'passed_checks': ['grounding']}
        self.put('outputs/technical-draft-evaluation.json', evaluation)
        self.put('outputs/technical-draft-screen.json', {'artifact': 'outputs/technical-draft.md', 'target_role': 'Engineering',
            'screened': '2026-09-14', 'verdict': 'advance', 'reason': 'Fictional test.', 'passes': {'screen': 'advance', 'hiring_manager': 'convinced'},
            'fix_in_document': [], 'needs_new_evidence': [], 'top_changes': ['No blocking changes in this fixture.'], 'context': 'shared', 'run': run})
        return evaluation

    def scenario_checks(self):
        from run_editorial_scenarios import checks
        return checks(self.root, 'resume', {'is_error': False, 'result': 'Review ready.'})

    def test_resume_scenario_accepts_coherent_current_delivery(self):
        self.delivery_fixture()
        checks = self.scenario_checks()
        self.assertTrue(all(row['passed'] for row in checks), checks)

    def test_resume_scenario_rejects_empty_reviews_and_unpublishable_output(self):
        evaluation = self.delivery_fixture()
        for relative in ('outputs/technical-draft-evaluation.json', 'outputs/technical-draft-representation.json'):
            path = self.root / relative; original = path.read_bytes()
            for content in ('{}', '{broken json'):
                path.write_text(content)
                self.assertFalse(all(row['passed'] for row in self.scenario_checks()))
            path.write_bytes(original)
        evaluation['publishable'] = False; self.put('outputs/technical-draft-evaluation.json', evaluation)
        self.assertFalse(all(row['passed'] for row in self.scenario_checks()))

    def test_resume_scenario_rejects_stale_or_unrelated_delivery(self):
        self.delivery_fixture()
        self.artifact.write_text(self.md + '\nChanged after evaluation.\n')
        self.assertFalse(all(row['passed'] for row in self.scenario_checks()))
        self.artifact.write_text(self.md)
        unrelated = self.root / 'outputs/unrelated-draft.md'; unrelated.write_text(self.md)
        self.assertFalse(all(row['passed'] for row in self.scenario_checks()))
        unrelated.unlink()
        (self.root / 'outputs/technical-draft-screen.json').write_text('{}')
        self.assertFalse(all(row['passed'] for row in self.scenario_checks()))

    def test_export_hashes_invalidate_approval(self):
        recovered = '\n'.join(document.paragraphs(document.document_from_markdown(self.md)))
        with patch.object(exporter, 'write_pdf', side_effect=self.fake_pdf), patch.object(exporter, 'pdf_details', return_value={'text': recovered, 'pages': 1, 'extractor': 'fixture', 'links': []}):
            report, path = exporter.export(self.artifact, 'outputs/export-v1', self.plan_path)
        self.assertTrue(report['complete']); self.assertEqual(exporter.validate_export_report(path), [])
        run = manifest.manifest(artifact=self.artifact, selection=self.selection_path, plan=self.plan_path, exports=path)
        self.assertEqual(manifest.editorial_staleness(run), [])
        local_txt = self.root / report['formats']['txt']['file']['path']; local_txt.write_text('Changed')
        self.assertTrue(manifest.editorial_staleness(run))

    def test_real_page_limit_violation_is_failure(self):
        recovered = '\n'.join(document.paragraphs(document.document_from_markdown(self.md)))
        with patch.object(exporter, 'write_pdf', side_effect=self.fake_pdf), patch.object(exporter, 'pdf_details', return_value={'text': recovered, 'pages': 3, 'links': []}):
            report, _ = exporter.export(self.artifact, 'outputs/over-limit', page_limit=1)
        self.assertFalse(report['complete']); self.assertIn('3 pages', report['formats']['pdf']['error'])

    def test_export_cannot_override_pinned_application(self):
        with self.assertRaisesRegex(ValueError, 'paper size contradicts'):
            exporter.export(self.artifact, 'outputs/override', self.plan_path, paper_size='Letter')

    def test_repeated_exports_retain_canonical_content(self):
        doc = document.document_from_markdown(self.md)
        left, right = self.root / 'outputs/a.docx', self.root / 'outputs/b.docx'
        exporter.write_docx(doc, left); exporter.write_docx(doc, right)
        self.assertEqual(left.read_bytes(), right.read_bytes())

    def test_source_outside_workspace_refused(self):
        with self.assertRaises(ValueError): exporter.export('/etc/passwd', 'outputs/leak')

    def test_index_and_validator_find_full_draft_stem_evaluation(self):
        import artifact_index
        import validate_artifact
        evaluation = {'publishable': False, 'run': manifest.manifest(artifact=self.artifact, selection=self.selection_path, plan=self.plan_path)}
        self.put('outputs/technical-draft-evaluation.json', evaluation)
        self.assertEqual(validate_artifact.evaluation_record(self.artifact), evaluation)
        with patch.object(artifact_index, 'ROOT', self.root), patch.object(artifact_index, 'OUTPUTS', self.root / 'outputs'), patch.object(artifact_index, 'resolve', return_value=self.pack_path):
            row = next(artifact_index.rows())
        self.assertIs(row['publishable'], False)
        self.assertIs(row['stale'], False)


if __name__ == '__main__':
    unittest.main(verbosity=2)
