#!/usr/bin/env python3
"""A fictional multi-position employer stays understandable across formats."""
import copy
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
import render
import resume_employment as employment
import resume_document as document
import resume_workflow as workflow
import resume_process as process
import export_resume as exporter
import validate_artifact
from test_resume_workflow import ResumeTests, completed_process


class EmployerTests(unittest.TestCase):
    setUp = ResumeTests.setUp
    tearDown = ResumeTests.tearDown
    put = ResumeTests.put
    strength = ResumeTests.strength
    selection = ResumeTests.selection
    fake_pdf = ResumeTests.fake_pdf

    def grouped(self):
        return ('# Morgan Vale\n\nLondon · morgan.vale@example.invalid\n\n## Experience\n\n'
                '### Northwind Systems | January 2017 to present | London\n\n'
                '**Director of Platform Security** | March 2022 to present\n\n'
                '**Lead Security Engineer** | June 2019 to March 2022\n\n'
                '**Security Engineer** | January 2017 to June 2019\n\n'
                '#### Career highlights\n\n'
                '- Co-designed a recovery procedure; validated it in quarterly exercises. <!-- Evidence: ' + self.aid + ' -->\n')

    def test_safe_view_supplies_one_employer_with_all_positions(self):
        view = workflow.plan_view(self.plan_path)
        groups = view['resume_plan']['employment_groups']
        northwind = [g for g in groups if g['employer'] == 'Northwind Systems']
        self.assertEqual(len(northwind), 1)
        self.assertEqual(northwind[0]['start'], '2017-01')
        self.assertEqual(northwind[0]['end'], 'present')
        self.assertEqual([r['title'] for r in northwind[0]['roles']], ['Director of Platform Security', 'Lead Security Engineer', 'Security Engineer'])
        self.assertEqual(self.pack_path.read_bytes(), self.pack_before)

    def test_return_to_same_employer_does_not_hide_a_break(self):
        roles = copy.deepcopy(self.pack['employment'][:3])
        roles[0]['start'] = '2024-03'
        groups = employment.employment_groups(roles)
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0]['start'], '2024-03')
        self.assertEqual(groups[1]['end'], '2022-03')

    def test_adjacent_december_and_january_positions_stay_together(self):
        roles = copy.deepcopy(self.pack['employment'][:2])
        roles[1]['end'] = '2021-12'; roles[0]['start'] = '2022-01'
        self.assertEqual(len(employment.employment_groups(roles)), 1)

    def test_equal_start_dates_do_not_invent_a_position_order(self):
        pack = copy.deepcopy(self.pack)
        pack['employment'] = pack['employment'][:2]
        for role in pack['employment']: role.update(start='2022-03', end='present')
        md = ('### Northwind Systems | March 2022 to present\n\n'
              '**Lead Security Engineer** | March 2022 to present\n\n'
              '**Director of Platform Security** | March 2022 to present\n')
        self.assertEqual(employment.chronology_errors(document.document_from_markdown(md), pack), [])

    def test_known_position_order_is_reverse_chronological(self):
        doc = document.document_from_markdown(self.grouped())
        positions = [index for index, block in enumerate(doc['blocks']) if block.get('employment_part') == 'position']
        first, second = positions[:2]
        doc['blocks'][first], doc['blocks'][second] = doc['blocks'][second], doc['blocks'][first]
        self.assertTrue(any('reverse chronological' in e for e in employment.chronology_errors(doc, self.pack)))

    def test_unknown_end_is_not_replaced_with_present(self):
        role = copy.deepcopy(self.pack['employment'][0]); role['end'] = None
        self.assertIsNone(employment.employment_groups([role])[0]['end'])

    def test_compact_progression_has_clear_shared_scope_and_valid_review(self):
        self.artifact.write_text(self.grouped())
        doc = document.document_from_markdown(self.grouped())
        self.assertEqual(employment.chronology_errors(doc, self.pack), [])
        self.assertEqual(validate_artifact.check(self.artifact, None, self.pack)[0], [])
        self.assertEqual(process.process_errors(completed_process(self)), [])
        self.assertEqual(sum(b.get('employment_part') == 'position' for b in doc['blocks']), 3)

    def test_existing_four_field_headings_do_not_bypass_date_checks(self):
        md = self.md.replace('2022-03 to present', 'January 2017 to present')
        md = md.replace('January 2017 to present\n', 'January 2017 to present | London\n')
        errors = employment.chronology_errors(document.document_from_markdown(md), self.pack)
        self.assertTrue(any('title tenure' in e for e in errors), errors)

    def test_multiple_flat_entries_for_one_tenure_require_grouping(self):
        md = self.md + '\n### Northwind Systems | Lead Security Engineer | June 2019 to March 2022 | London\n'
        self.assertTrue(any('repeat employer headings' in e for e in employment.chronology_errors(document.document_from_markdown(md), self.pack)))

    def test_group_dates_cannot_extend_latest_title_tenure(self):
        md = self.grouped().replace('March 2022 to present\n', 'January 2017 to present\n', 1)
        self.assertTrue(any('position title/dates' in e for e in employment.chronology_errors(document.document_from_markdown(md), self.pack)))

    def test_missing_or_duplicate_position_cannot_be_hidden_by_group_header(self):
        position = '**Security Engineer** | January 2017 to June 2019\n\n'
        for replacement in ('', position * 2):
            md = self.grouped().replace(position, replacement)
            self.assertTrue(any('each position' in e for e in employment.chronology_errors(document.document_from_markdown(md), self.pack)))

    def test_achievement_scope_must_be_explicit_after_compact_timeline(self):
        md = self.grouped().replace('#### Career highlights\n\n', '')
        self.assertTrue(any('explicit role or Career highlights' in e for e in employment.chronology_errors(document.document_from_markdown(md), self.pack)))

    def test_spanning_achievement_belongs_to_company_not_one_position(self):
        pack = copy.deepcopy(self.pack)
        atom = next(a for a in pack['evidence_atoms'] if a['id'] == self.aid)
        atom['occurred'] = {'start': '2018', 'end': '2025'}
        self.assertEqual(employment.chronology_errors(document.document_from_markdown(self.grouped()), pack), [])
        md = self.grouped().replace('**Director of Platform Security** | March 2022 to present\n\n', '')
        md = md.replace('#### Career highlights', '#### Director of Platform Security | March 2022 to present')
        self.assertTrue(any('spans dates outside' in e for e in employment.chronology_errors(document.document_from_markdown(md), pack)))

    def test_empty_role_subsection_should_be_a_timeline_row(self):
        md = self.grouped().replace('**Director of Platform Security**', '#### Director of Platform Security')
        self.assertTrue(any('empty position subsection' in e for e in employment.chronology_errors(document.document_from_markdown(md), self.pack)))

    def test_an_employer_group_cannot_absorb_a_different_employers_role(self):
        md = self.grouped().replace('**Security Engineer** | January 2017 to June 2019', '**Senior Systems Engineer** | April 2013 to December 2016')
        self.assertTrue(employment.chronology_errors(document.document_from_markdown(md), self.pack))

    def test_human_dates_preserve_precision(self):
        self.assertEqual(employment.date_range('September 2015 – February 2018'), ('2015-09', '2018-02'))
        self.assertEqual(employment.date_range('2015-2018'), ('2015', '2018'))
        self.assertFalse(employment.matches_range(('2015-01', '2018-01'), '2015', '2018'))
        self.assertTrue(employment.matches_range(('2015', '2018'), '2015-09', '2018-02'))

    def test_html_and_docx_preserve_hierarchy_without_repeated_employer(self):
        doc = document.document_from_markdown(self.grouped())
        for html in (render.render(self.grouped()), document.submission_html(doc)):
            self.assertEqual(html.count('Northwind Systems'), 1)
            self.assertIn('<h4>Career highlights</h4>', html)
            self.assertEqual(html.count('<p class="position">'), 3)
        path = self.root / 'outputs/grouped.docx'; exporter.write_docx(doc, path)
        exporter.validate_content(doc, exporter.docx_text(path))
        with zipfile.ZipFile(path) as archive:
            tree = ET.fromstring(archive.read('word/document.xml'))
            styles = [n.get('{' + exporter.W + '}val') for n in tree.iter('{' + exporter.W + '}pStyle')]
        self.assertEqual(styles.count('Position'), 3)
        self.assertIn('Heading3', styles)

    def test_grouped_plan_exports_without_altering_career_facts(self):
        self.artifact.write_text(self.grouped()); doc = document.document_from_markdown(self.grouped())
        details = {'pages': 1, 'links': [], 'text': '\n'.join(document.paragraphs(doc))}
        with patch.object(exporter, 'write_pdf', side_effect=self.fake_pdf), patch.object(exporter, 'pdf_details', return_value=details):
            report, path = exporter.export(self.artifact, 'outputs/grouped', self.plan_path)
        self.assertTrue(report['complete'], report)
        self.assertEqual(exporter.validate_export_report(path), [])
        self.assertEqual(self.pack_path.read_bytes(), self.pack_before)

    @unittest.skipUnless(os.environ.get('CAREER_TEST_REAL_PDF') == '1', 'set CAREER_TEST_REAL_PDF=1 for real PDF layout verification')
    def test_real_grouped_pdf_preserves_position_order_and_content(self):
        self.artifact.write_text(self.grouped())
        report, path = exporter.export(self.artifact, 'outputs/real-grouped', self.plan_path)
        self.assertTrue(report['complete'], report)
        self.assertEqual(report['formats']['pdf']['pages'], 1)
        self.assertEqual(exporter.validate_export_report(path), [])
        self.assertEqual(self.pack_path.read_bytes(), self.pack_before)


del ResumeTests
if __name__ == '__main__':
    unittest.main(verbosity=2)
