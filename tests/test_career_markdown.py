#!/usr/bin/env python3
"""Complete private snapshots, exercised only with fictional packs."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import career_markdown as markdown


class CareerMarkdownTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='career-markdown-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / 'schemas', self.root / 'schemas')
        (self.root / 'data/packs').mkdir(parents=True)
        self.pack = json.loads((ROOT / 'examples/career.example.json').read_text())
        self.path = self.root / 'data/packs/fictional.json'
        self.save()

    def save(self):
        self.path.write_text(json.dumps(self.pack, ensure_ascii=False), encoding='utf-8')

    def run_command(self, script='career_markdown.py', *args):
        return subprocess.run([sys.executable, str(ROOT / 'scripts' / script), *args],
                              env={**os.environ, 'CAREER_WORKSPACE': str(self.root)},
                              capture_output=True, text=True)

    def test_complete_private_snapshot_and_repeatable_bytes(self):
        # Schema-permitted extensions must survive too, including false/zero/null.
        self.pack['metadata']['extension'] = {'zero': 0, 'false': False, 'missing': None,
                                            'empty': [], 'quote': '<b>Zoë & team</b> *literal*'}
        self.save()
        before = self.path.read_bytes()
        result = self.run_command()
        self.assertEqual(result.returncode, 0, result.stderr)
        path = self.root / 'outputs/career.md'
        first = path.read_bytes()
        text = first.decode()
        self.assertIn(hashlib.sha256(before).hexdigest(), text)
        self.assertIn('Personal record', text)
        self.assertIn('JSON is authoritative', text)
        self.assertIn('**zero:** 0', text)
        self.assertIn('**false:** false', text)
        self.assertIn('**missing:** null', text)
        self.assertIn('&lt;b&gt;Zoë &amp; team&lt;/b&gt;', text)
        self.assertNotIn('<b>', text)
        # Every recorded scalar appears in literal escaped form, including private
        # profile details, evidence restrictions and every source excerpt.
        def leaves(node):
            if isinstance(node, dict):
                for value in node.values(): yield from leaves(value)
            elif isinstance(node, list):
                for value in node: yield from leaves(value)
            else: yield node
        for value in leaves(self.pack):
            literal = value if isinstance(value, str) else json.dumps(value)
            self.assertIn(markdown.escape(literal), text)
        self.assertEqual(self.run_command().returncode, 0)
        self.assertEqual(first, path.read_bytes())
        self.assertEqual(before, self.path.read_bytes())

    def test_invalid_nested_field_retains_previous_snapshot(self):
        self.assertEqual(self.run_command().returncode, 0)
        out = self.root / 'outputs/career.md'
        before = out.read_bytes()
        self.pack['evidence_atoms'][0]['unsupported_field'] = 'must not disappear'
        self.save()
        result = self.run_command()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('unsupported_field', result.stderr)
        self.assertEqual(before, out.read_bytes())

    def test_schema_14_strengths_and_preferences_keep_recorded_states(self):
        from editorial_fixture import pack_for, personas
        self.pack = pack_for(personas()[0])
        self.pack['metadata'] = {}
        self.save()
        result = self.run_command()
        self.assertEqual(result.returncode, 0, result.stderr)
        text = (self.root / 'outputs/career.md').read_text()
        self.assertIn('## Strengths (recorded states)', text)
        self.assertIn('## Positioning preferences', text)
        for strength in self.pack['strengths_profile']:
            self.assertIn(markdown.escape(strength['interpretation']), text)
            self.assertIn('**status:** ' + markdown.escape(strength['status']), text)

    def test_reading_page_refresh_and_explicit_destination(self):
        result = self.run_command('career_core.py', 'view')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root / 'outputs/career-record.html').exists())
        self.assertTrue((self.root / 'outputs/career.md').exists())
        result = self.run_command('career_core.py', 'export-markdown', '--pack',
                                  'data/packs/fictional.json', '-o', 'outputs/copy.md')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / 'outputs/copy.md').read_bytes(),
                         (self.root / 'outputs/career.md').read_bytes())
        result = self.run_command('career_markdown.py', '-o', 'data/packs/unsafe.md')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / 'data/packs/unsafe.md').exists())

    def test_unlinked_work_and_repeated_employer_roles(self):
        pack = copy.deepcopy(self.pack)
        role = pack['employment'][0]
        child = dict(role, employment_id='EMP_CHILD', title='Later role',
                     parent_employment_id=role['employment_id'])
        pack['employment'].append(child)
        pack['evidence_atoms'][0]['employment_id'] = 'EMP_CHILD'
        pack['evidence_atoms'][1]['employment_id'] = None
        text = markdown.build(pack, 'data/packs/fictional.json', '0' * 64)
        self.assertIn('#### Later role', text)
        self.assertIn('## Other recorded work', text)
        self.assertIn(markdown.escape(pack['evidence_atoms'][0]['title']), text)
        pack['employment'][0]['parent_employment_id'] = 'EMP_CHILD'
        with self.assertRaisesRegex(ValueError, 'cycle'):
            markdown.build(pack, 'fixture', '0' * 64)


if __name__ == '__main__':
    unittest.main()
