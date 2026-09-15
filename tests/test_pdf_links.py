#!/usr/bin/env python3
"""PDF URL regressions; optional real Chrome/extractor test uses fictional data."""
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
from resume_document import document_from_markdown, paragraphs, plain_text, submission_html
from resume_links import canonical_url, expected_links, validate_pdf_links
import export_resume as exporter
from test_resume_workflow import ResumeTests


class Anchors(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.links = []; self.active = None; self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.active = {'target': dict(attrs)['href'], 'text': ''}
            self.links.append(self.active)

    def handle_data(self, text):
        if self.active is not None:
            self.active['text'] += text

    def handle_endtag(self, tag):
        if tag == 'a':
            self.active = None


class LinkTests(unittest.TestCase):
    def test_explicit_link_survives_as_clickable_anchor_with_unchanged_text(self):
        doc = document_from_markdown('# Example\n\nRead [the report](https://example.com/report).')
        self.assertEqual(doc['blocks'][1]['text'], 'Read the report (https://example.com/report).')
        self.assertEqual(Anchors(submission_html(doc)).links, expected_links(doc))
        self.assertIn('the report (https://example.com/report)', plain_text(doc))

    def test_bare_url_excludes_sentence_punctuation_and_unmatched_parenthesis(self):
        doc = document_from_markdown('See (https://example.com/Research_(2026).pdf), then https://example.com/next.')
        self.assertEqual([l['target'] for l in expected_links(doc)],
                         ['https://example.com/Research_(2026).pdf', 'https://example.com/next'])
        self.assertEqual(doc['blocks'][0]['text'], 'See (https://example.com/Research_(2026).pdf), then https://example.com/next.')

    def test_markdown_target_preserves_parentheses_and_terminal_punctuation(self):
        doc = document_from_markdown('[Paper](https://example.com/Research_(2026).pdf) and [literal](https://example.com/path.)')
        self.assertEqual([l['target'] for l in expected_links(doc)],
                         ['https://example.com/Research_(2026).pdf', 'https://example.com/path.'])
        self.assertEqual(Anchors(submission_html(doc)).links, expected_links(doc))

    def test_query_ampersands_fragments_and_percent_encoding_are_not_rewritten(self):
        target = 'https://example.com/report.pdf?title=a%20b&edition=2#section-3'
        doc = document_from_markdown('[Report](' + target + ')')
        self.assertEqual(Anchors(submission_html(doc)).links[0]['target'], target)
        self.assertIn('&amp;edition=2', submission_html(doc))

    def test_mailto_targets_remain_explicit(self):
        target = 'mailto:person@example.com?subject=Resume%20review'
        doc = document_from_markdown('[Email](' + target + ')')
        self.assertEqual(Anchors(submission_html(doc)).links[0]['target'], target)

    def test_emphasis_and_word_boundaries_crossing_links_are_preserved(self):
        doc = document_from_markdown('Before **read [the guide](https://example.com/guide) carefully** afterwards.')
        self.assertEqual(doc['blocks'][0]['text'], 'Before read the guide (https://example.com/guide) carefully afterwards.')
        self.assertEqual(Anchors(submission_html(doc)).links, expected_links(doc))

    def test_emphasized_bare_urls_do_not_include_markdown_delimiters(self):
        for markup in ('**https://example.com/report**', '*https://example.com/report*', '**See https://example.com/report**.'):
            doc = document_from_markdown(markup)
            self.assertEqual(expected_links(doc)[0]['target'], 'https://example.com/report')
            self.assertNotIn('*', doc['blocks'][0]['text'])

    def test_comments_and_plain_hostnames_do_not_invent_links(self):
        doc = document_from_markdown('example.com <!-- private https://example.com/private -->')
        self.assertEqual(expected_links(doc), [])
        self.assertNotIn('private', submission_html(doc))

    def test_unsafe_and_malformed_targets_fail_before_export(self):
        for target in ['javascript:alert(1)', 'data:text/html,hello', 'https://', 'https://example.com/a b',
                       'https://example.com/%xx', 'https://example.com:bad/', 'https://example.com/\\evil']:
            with self.subTest(target=target), self.assertRaises(ValueError):
                document_from_markdown('[Link](' + target + ')')

    def test_unclosed_markdown_link_is_not_silently_shortened(self):
        with self.assertRaisesRegex(ValueError, 'unclosed'):
            document_from_markdown('[Paper](https://example.com/Research_(2026).pdf')

    def test_browser_uri_serialization_is_allowed_without_changing_path_or_query(self):
        self.assertEqual(canonical_url('HTTPS://EXAMPLE.COM:443/café?q=%c3%a9'),
                         canonical_url('https://example.com/caf%C3%A9?q=%C3%A9'))
        self.assertEqual(canonical_url('https://example.com'), canonical_url('https://example.com/'))
        self.assertNotEqual(canonical_url('https://example.com/path?'), canonical_url('https://example.com/path'))
        self.assertNotEqual(canonical_url('https://example.com/path#'), canonical_url('https://example.com/path'))
        for changed in ['https://example.com/Report', 'https://example.com/report?edition=2', 'http://example.com/report']:
            self.assertNotEqual(canonical_url('https://example.com/report'), canonical_url(changed))

    def test_wrapped_link_matches_all_clickable_fragments(self):
        target = 'https://example.com/research/long-report'
        doc = document_from_markdown('[Report](' + target + ')')
        annotations = [{'target': target, 'text': 'Report (https://example.com/research/'},
                       {'target': target, 'text': 'long-report)'}]
        result = validate_pdf_links(doc, annotations)
        self.assertEqual(result['expected_links'], 1)
        self.assertEqual(result['annotation_fragments'], 2)

    def test_missing_wrong_extra_or_incomplete_annotations_fail(self):
        doc = document_from_markdown('[Report](https://example.com/report)')
        expected = expected_links(doc)
        bad = [[], None, [{'target': expected[0]['target'], 'text': 'Report'}],
               [dict(expected[0], target='https://example.com/wrong')], expected * 2]
        for annotations in bad:
            with self.subTest(annotations=annotations), self.assertRaises(ValueError):
                validate_pdf_links(doc, annotations)

    def test_one_wrapped_link_cannot_mask_a_missing_repeated_link(self):
        target = 'https://example.com/long/report'
        doc = document_from_markdown('[Report](' + target + ')\n\n[Report](' + target + ')')
        fragments = [{'target': target, 'text': 'Report (https://example.com/long/'}, {'target': target, 'text': 'report)'}]
        with self.assertRaises(ValueError): validate_pdf_links(doc, fragments)
        self.assertEqual(validate_pdf_links(doc, fragments * 2)['expected_links'], 2)

    def test_url_text_alone_does_not_pass_clickability(self):
        doc = document_from_markdown('https://example.com/report')
        exporter.validate_content(doc, 'https://example.com/report', pdf=True)
        with self.assertRaises(ValueError): validate_pdf_links(doc, [])

    def test_poppler_xml_preserves_pdf_destinations_and_nested_label_text(self):
        xml = '''<?xml version="1.0"?><pdf2xml><page number="1"><text>
        <a href="https://example.com/report.pdf?edition=2&amp;view=full"><b>Report</b> (https://example.com/report.pdf?edition=2&amp;view=full)</a>
        </text></page></pdf2xml>'''
        result = exporter.poppler_links(xml)
        self.assertEqual(result[0]['target'], 'https://example.com/report.pdf?edition=2&view=full')
        self.assertTrue(result[0]['text'].startswith('Report ('))
        with self.assertRaises(ValueError): exporter.poppler_links('broken output')


class ExportLinkTests(unittest.TestCase):
    setUp = ResumeTests.setUp
    tearDown = ResumeTests.tearDown
    put = ResumeTests.put
    strength = ResumeTests.strength
    selection = ResumeTests.selection
    fake_pdf = ResumeTests.fake_pdf

    def linked_fixture(self):
        self.artifact.write_text('# Example Person\n\n[Profile](https://example.com/profile)\n')
        return document_from_markdown(self.artifact.read_text())

    def test_export_fails_when_text_passes_but_pdf_links_are_missing(self):
        doc = self.linked_fixture()
        details = {'text': '\n'.join(paragraphs(doc)), 'pages': 1, 'links': []}
        with patch.object(exporter, 'write_pdf', side_effect=self.fake_pdf), patch.object(exporter, 'pdf_details', return_value=details):
            report, _ = exporter.export(self.artifact, 'outputs/missing-links')
        self.assertFalse(report['complete'])
        self.assertEqual(report['formats']['txt']['status'], 'verified')
        self.assertEqual(report['formats']['docx']['status'], 'verified')
        self.assertIn('hyperlinks differ', report['formats']['pdf']['error'])

    def test_report_retains_verified_targets_and_checks_them_again(self):
        doc = self.linked_fixture()
        details = {'text': '\n'.join(paragraphs(doc)), 'pages': 1, 'links': expected_links(doc)}
        with patch.object(exporter, 'write_pdf', side_effect=self.fake_pdf), patch.object(exporter, 'pdf_details', return_value=details):
            report, path = exporter.export(self.artifact, 'outputs/linked')
        self.assertTrue(report['complete'])
        self.assertEqual(exporter.validate_export_report(path), [])
        report['formats']['pdf']['links'][0]['target'] = 'https://example.com/wrong'
        path.write_text(json.dumps(report))
        self.assertTrue(exporter.validate_export_report(path))

    def test_legacy_report_cannot_claim_hyperlink_verification(self):
        doc = self.linked_fixture()
        details = {'text': '\n'.join(paragraphs(doc)), 'pages': 1, 'links': expected_links(doc)}
        with patch.object(exporter, 'write_pdf', side_effect=self.fake_pdf), patch.object(exporter, 'pdf_details', return_value=details):
            report, path = exporter.export(self.artifact, 'outputs/legacy')
        report['export_version'] = 1; path.write_text(json.dumps(report))
        self.assertTrue(any('legacy export' in e for e in exporter.validate_export_report(path)))

    @unittest.skipUnless(os.environ.get('CAREER_TEST_REAL_PDF') == '1', 'set CAREER_TEST_REAL_PDF=1 to run Chrome and the installed PDF extractor')
    def test_real_pdf_wraps_repeated_and_unicode_links_without_losing_targets(self):
        long = 'https://example.com/research/' + 'multi-region-recovery/' * 8 + 'report.pdf?edition=2026&view=full#findings'
        self.artifact.write_text('# Example Person\n\n[Profile](https://example.com/profile)\n\n'
            '- Read [the report](' + long + ').\n\n- Revisit [Profile](https://example.com/profile).\n\n'
            '- Published [paper](https://example.com/papers/Research_(2026).pdf).\n\n'
            '- Reference: https://example.com/plain?edition=2&view=full#summary.\n\n'
            '- Email [Contact](mailto:person@example.com?subject=Resume%20review).\n\n'
            '- International [paper](https://example.com/café).\n')
        report, path = exporter.export(self.artifact, 'outputs/real-links')
        self.assertTrue(report['complete'], report['formats'])
        pdf = report['formats']['pdf']
        self.assertEqual(pdf['hyperlinks']['expected_links'], 7)
        self.assertGreater(pdf['hyperlinks']['annotation_fragments'], 7)
        self.assertEqual(exporter.validate_export_report(path), [])
        self.assertEqual(self.pack_path.read_bytes(), self.pack_before)


del ResumeTests
if __name__ == '__main__':
    unittest.main(verbosity=2)
