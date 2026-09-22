#!/usr/bin/env python3
"""Markdown export structure, privacy, format failures and report compatibility."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import export_resume as exporter
import resume_document as document
import resume_markdown as markdown
from resume_links import expected_links
import test_resume_workflow as fixtures


class ResumeMarkdownTests(unittest.TestCase):
    setUp = fixtures.ResumeTests.setUp
    tearDown = fixtures.ResumeTests.tearDown
    put = fixtures.ResumeTests.put
    strength = fixtures.ResumeTests.strength
    selection = fixtures.ResumeTests.selection
    fake_pdf = fixtures.ResumeTests.fake_pdf

    def bundle(self):
        self.artifact.write_text('# Zoë Vale\n\n## Experience\n\n### Example\n\n#### Projects\n\n'
            '- **Co-designed** *recovery* with [the team](https://example.invalid/a(b)?x=1&y=2#part). '
            '<!-- Evidence: E_EXAMPLE -->\n')
        doc = document.document_from_markdown(self.artifact.read_text())
        details = {'text': '\n'.join(document.paragraphs(doc)), 'pages': 1, 'links': expected_links(doc)}
        with patch.object(exporter, 'write_pdf', side_effect=self.fake_pdf), patch.object(exporter, 'pdf_details', return_value=details):
            report, path = exporter.export(self.artifact, 'outputs/markdown-export')
        return doc, report, path

    def test_four_files_structure_formatting_links_and_privacy(self):
        doc, report, path = self.bundle()
        self.assertTrue(report['complete'], report)
        self.assertEqual(report['export_version'], 4)
        self.assertEqual(set(report['formats']), {'md', 'pdf', 'txt', 'docx'})
        text = (path.parent.parent / 'files/resume.md').read_text()
        self.assertIn('# Zoë Vale', text)
        self.assertIn('#### Projects', text)
        self.assertIn('- **Co\\-designed** *recovery*', text)
        self.assertIn('[the team](https://example.invalid/a\\(b\\)?x=1&y=2#part)', text)
        self.assertNotIn('E_EXAMPLE', text)
        self.assertNotIn('<!--', text)
        self.assertEqual(exporter.validate_export_report(path), [])
        exporter.validate_content(doc, markdown.validate_markdown(doc, text))
        self.assertIn('E_EXAMPLE', self.artifact.read_text())

    def test_changed_bytes_structure_or_links_fail_even_with_updated_pin(self):
        _, report, path = self.bundle()
        md = path.parent.parent / 'files/resume.md'
        original = md.read_text()
        for changed in (original.replace('recovery', 'delivery'), original.replace('#### Projects', '## Projects'),
                        original.replace('x=1', 'x=2'), original + '\nExtra content\n',
                        original.replace('*recovery*', 'recovery')):
            md.write_text(changed)
            self.assertTrue(exporter.validate_export_report(path))
            report['formats']['md']['file']['sha256'] = exporter.sha256(md)
            path.write_text(json.dumps(report))
            self.assertTrue(exporter.validate_export_report(path))

    def test_old_three_format_report_and_new_missing_format(self):
        _, report, path = self.bundle()
        del report['formats']['md']
        path.write_text(json.dumps(report))
        self.assertTrue(exporter.validate_export_report(path))
        for version in (2, 3):
            report['export_version'] = version
            path.write_text(json.dumps(report))
            self.assertEqual(exporter.validate_export_report(path), [])

    def test_failed_markdown_keeps_other_formats_but_not_completion(self):
        doc = document.document_from_markdown(self.md)
        details = {'text': '\n'.join(document.paragraphs(doc)), 'pages': 1, 'links': []}
        with patch.object(exporter, 'submission_markdown', side_effect=ValueError('fixture serialization failure')), \
             patch.object(exporter, 'write_pdf', side_effect=self.fake_pdf), \
             patch.object(exporter, 'pdf_details', return_value=details):
            report, _ = exporter.export(self.artifact, 'outputs/failed-markdown')
        self.assertFalse(report['complete'])
        self.assertEqual(report['formats']['md']['status'], 'failed')
        self.assertTrue(all(report['formats'][fmt]['status'] == 'verified' for fmt in ('pdf', 'txt', 'docx')))

    def test_missing_pdf_retains_verified_markdown(self):
        with patch.object(exporter, 'write_pdf', side_effect=ValueError('missing browser')):
            report, _ = exporter.export(self.artifact, 'outputs/failed-pdf')
        self.assertFalse(report['complete'])
        self.assertEqual(report['formats']['md']['status'], 'verified')

    def test_literal_markdown_and_emphasis_across_links(self):
        doc = document.document_from_markdown('# Name\n\n**See [the *report*](https://example.invalid/report)** '
                                               'and literal _word_ &amp; C:\\tools.\n')
        text = markdown.submission_markdown(doc)
        self.assertIn('**See [the *report*]', text)
        self.assertIn(r'\_word\_', text)
        self.assertIn(r'\&amp;', text)
        self.assertIn(r'C:\\tools', text)
        exporter.validate_content(doc, markdown.validate_markdown(doc, text))

    def test_emphasis_padding_keeps_text_without_literal_delimiters(self):
        doc = document.document_from_markdown('# Name\n\nBefore ** padded ** after.\n')
        text = markdown.submission_markdown(doc)
        self.assertIn('Before  **padded**  after', text)
        self.assertNotIn('** padded **', text)

    def test_unrepresentable_emphasis_fails_instead_of_adding_asterisks(self):
        doc = document.document_from_markdown('# Name\n\na**!**b\n')
        with self.assertRaisesRegex(ValueError, 'emphasis boundary'):
            markdown.submission_markdown(doc)


if __name__ == '__main__':
    unittest.main()
