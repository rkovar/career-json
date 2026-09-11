#!/usr/bin/env python3
"""Core contract tests that also run in the core-only release archive."""
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
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from career_profile import profile_state, safe_strengths
from schema_tools import walk


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='career-core-')
        self.root = Path(self.tmp.name)
        shutil.copytree(ROOT / 'schemas', self.root / 'schemas')
        (self.root / 'data/packs').mkdir(parents=True)
        (self.root / 'reviews').mkdir()
        self.pack = pack_for(personas()[0])
        self.save(self.pack)
        (self.root / 'reviews/onboarding.md').write_text(self.pack['strengths_profile'][0]['source_refs'][0]['excerpt'])

    def tearDown(self):
        self.tmp.cleanup()

    def save(self, pack):
        (self.root / 'data/packs/pack.json').write_text(json.dumps(pack))

    def run_cli(self, script, *args):
        return subprocess.run([sys.executable, str(ROOT / 'scripts' / script), *args],
                              cwd=self.root, env={**os.environ, 'CAREER_WORKSPACE':str(self.root)},
                              text=True, capture_output=True)

    def test_diverse_packs_validate_and_export_losslessly(self):
        for n, person in enumerate(personas()):
            with self.subTest(person=person['id']):
                pack = pack_for(person)
                self.save(pack)
                before = (self.root / 'data/packs/pack.json').read_bytes()
                result = self.run_cli('validate_pack.py')
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                output = f'data/private/export-{n}.json'
                result = self.run_cli('career_core.py', 'export', '--output', output)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads((self.root / output).read_text()), pack)
                self.assertEqual((self.root / 'data/packs/pack.json').read_bytes(), before)
                self.assertNotEqual(self.run_cli('career_core.py', 'export', '--output', output).returncode, 0)
                self.assertEqual(self.run_cli('current_pack.py').stdout.strip(), 'data/packs/pack.json')

    def test_export_cannot_create_a_chain_head_or_escape_workspace(self):
        for output in ('data/packs/export.json', '../outside.json'):
            result = self.run_cli('career_core.py', 'export', '--output', output)
            self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(list((self.root / 'data/packs').glob('*.json'))), 1)

    def test_legacy_migration_preserves_facts_and_lineage(self):
        self.pack['schema_version'] = '1.3'
        self.pack.pop('strengths_profile'); self.pack.pop('positioning_preferences')
        self.save(self.pack)
        before = (self.root / 'data/packs/pack.json').read_bytes()
        result = self.run_cli('career_core.py', 'migrate', '--output', 'data/packs/v2.json')
        self.assertEqual(result.returncode, 0, result.stderr)
        migrated = json.loads((self.root / 'data/packs/v2.json').read_text())
        self.assertEqual(migrated['evidence_atoms'], self.pack['evidence_atoms'])
        self.assertEqual(migrated['metadata']['supersedes'], 'data/packs/pack.json')
        self.assertEqual((self.root / 'data/packs/pack.json').read_bytes(), before)
        self.assertEqual(self.run_cli('current_pack.py').stdout.strip(), 'data/packs/v2.json')

    def test_strength_changes_stale_without_upgrading_evidence(self):
        strength = self.pack['strengths_profile'][0]
        aid = strength['evidence_ids'][0]
        atom = next(a for a in self.pack['evidence_atoms'] if a['id'] == aid)
        original_status = atom['evidence_status']
        atom['star']['action'] += '; corrected ownership'
        self.assertEqual(profile_state(strength, self.pack), 'stale')
        self.assertEqual(safe_strengths(self.pack), [])
        self.save(self.pack)
        status = json.loads(self.run_cli('career_core.py', 'status').stdout)
        self.assertTrue(status['strengths'][0]['ask'])
        result = self.run_cli('career_core.py', 'bind-strength', '--pack', 'data/packs/pack.json',
                              '--strength', strength['id'], '--output', 'data/packs/v2.json')
        self.assertEqual(result.returncode, 0, result.stderr)
        bound = json.loads((self.root / 'data/packs/v2.json').read_text())
        self.assertEqual(bound['strengths_profile'][0]['status'], strength['status'])
        self.assertEqual(next(a for a in bound['evidence_atoms'] if a['id'] == aid)['evidence_status'], original_status)

    def test_core_recall_and_questions_work_without_roles(self):
        for script, args in [('open_questions.py',['--json']), ('coverage.py',[]), ('find.py',[]),
                             ('dedupe.py',[]), ('pack_html.py',[]), ('verify_excerpts.py',['--quiet'])]:
            result = self.run_cli(script, *args)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_schema_union_and_external_reference_still_validate(self):
        for node, expected in [('text', False), ({'value':'an estimate'}, False), ([], True)]:
            errors=[]
            walk(node, {'anyOf':[{'type':'string'},{'type':'object','required':['value']}]}, {}, '', errors)
            self.assertEqual(bool(errors), expected)
        errors=[]
        walk('bad', {'$ref':'other.json#/$defs/item'}, {}, '', errors,
             loader=lambda name:{'$defs':{'item':{'type':'integer'}}})
        self.assertTrue(errors)


if __name__ == '__main__':
    unittest.main(verbosity=2)
