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

    def test_capture_serializes_every_read_modify_write(self):
        # Probe the OS lock from an independent descriptor at the actual read,
        # rather than relying on scheduling to expose a lost update.
        worker = '''
import fcntl, sys, time
sys.path.insert(0, sys.argv[1])
import capture
original = capture.load
def guarded_load():
    with (capture.ROOT / 'reviews/.pack-write.lock').open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            pass
        else:
            raise AssertionError('capture read without the workspace lock')
    notes = original()
    time.sleep(0.02)
    return notes
capture.load = guarded_load
if sys.argv[2] == 'api':
    capture.add(sys.argv[3], [], [], None)
else:
    sys.exit(capture.main(['capture.py', *sys.argv[2:]]))
'''
        def batch(commands):
            processes = []
            try:
                for command in commands:
                    processes.append(subprocess.Popen(
                        [sys.executable, '-c', worker, str(ROOT / 'scripts'), *command],
                        cwd=self.root, env={**os.environ, 'CAREER_WORKSPACE': str(self.root)},
                        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE))
                for process in processes:
                    out, err = process.communicate(timeout=30)
                    self.assertEqual(process.returncode, 0, out + err)
            finally:
                for process in processes:
                    if process.poll() is None:
                        process.kill()
                    process.communicate()
        batch([['api', 'API note']] + [[f'Concurrent note {n}'] for n in range(7)])
        path = self.root / 'data/capture/notes.jsonl'
        notes = [json.loads(line) for line in path.read_text().splitlines()]
        self.assertEqual({n['note_id'] for n in notes}, {f'N{n:04d}' for n in range(1, 9)})
        self.assertEqual({n['text'] for n in notes}, {'API note'} | {f'Concurrent note {n}' for n in range(7)})
        batch([['--edit', 'N0001', 'Corrected'], ['--delete', 'N0002'],
               ['--promote', 'N0003', '--atom', 'E_FICTIONAL'], ['Another note']])
        notes = {n['note_id']: n for n in map(json.loads, path.read_text().splitlines())}
        self.assertEqual(len(notes), 8)
        self.assertEqual(notes['N0001']['text'], 'Corrected')
        self.assertNotIn('N0002', notes)
        self.assertEqual(notes['N0003']['promoted_to'], 'E_FICTIONAL')
        self.assertEqual(notes['N0009']['text'], 'Another note')

    def test_capture_failed_replace_preserves_log_and_cleans_temporary_file(self):
        from unittest.mock import patch
        import capture
        path = self.root / 'data/capture/notes.jsonl'
        path.parent.mkdir(parents=True)
        path.write_text('original note\n')
        with patch.object(capture.os, 'replace', side_effect=OSError('injected failure')):
            with self.assertRaisesRegex(OSError, 'injected failure'):
                capture._write_atomically(path, 'replacement\n')
        self.assertEqual(path.read_text(), 'original note\n')
        self.assertEqual(list(path.parent.iterdir()), [path])

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

    def test_employment_parent_cycles_are_invalid(self):
        first = self.pack['employment'][0]
        for mutual in (False, True):
            with self.subTest(mutual=mutual):
                first['parent_employment_id'] = 'EMP_CHILD' if mutual else first['employment_id']
                self.pack['employment'] = [first]
                if mutual:
                    self.pack['employment'].append(dict(first, employment_id='EMP_CHILD',
                                                       parent_employment_id=first['employment_id']))
                self.save(self.pack)
                result = self.run_cli('validate_pack.py')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('cycle in parent_employment_id', result.stdout + result.stderr)

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
        from editorial_fixture import strength_assessment
        (self.root/'assessment.json').write_text(json.dumps(strength_assessment(self.pack)))
        result = self.run_cli('career_core.py', 'bind-strength', '--pack', 'data/packs/pack.json',
                              '--strength', strength['id'], '--output', 'data/candidates/v2.json', '--assessment', 'assessment.json')
        self.assertEqual(result.returncode, 0, result.stderr)
        bound = json.loads((self.root / 'data/candidates/v2.json').read_text())
        self.assertEqual(bound['strengths_profile'][0]['status'], 'proposed')
        self.assertEqual(bound['strengths_profile'][0]['question_status'], 'open')
        self.assertFalse(bound['strengths_profile'][0]['external_safe'])
        self.assertEqual(next(a for a in bound['evidence_atoms'] if a['id'] == aid)['evidence_status'], original_status)

    def test_core_recall_and_questions_work_without_roles(self):
        for script, args in [('open_questions.py',['--json']), ('coverage.py',[]), ('find.py',[]),
                             ('dedupe.py',[]), ('pack_html.py',[]), ('verify_excerpts.py',['--quiet'])]:
            result = self.run_cli(script, *args)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_binding_first_import_never_links_a_temporary_candidate(self):
        (self.root/'data/packs/pack.json').unlink()
        candidate=self.root/'data/candidates/unbound.json'
        candidate.parent.mkdir(parents=True)
        candidate.write_text(json.dumps(self.pack))
        from editorial_fixture import strength_assessment
        (self.root/'assessment.json').write_text(json.dumps(strength_assessment(self.pack)))
        result=self.run_cli('career_core.py','bind-strength','--pack','data/candidates/unbound.json',
                            '--strength','S_DISTINCTIVE','--output','data/candidates/proposal.json','--assessment','assessment.json')
        self.assertEqual(result.returncode,0,result.stderr)
        candidate.unlink()
        proposal=json.loads((self.root/'data/candidates/proposal.json').read_text())
        self.assertNotIn('supersedes',proposal['metadata'])
        valid=self.run_cli('validate_pack.py','data/candidates/proposal.json')
        self.assertEqual(valid.returncode,0,valid.stdout+valid.stderr)

    def test_binding_later_candidate_links_the_accepted_head(self):
        candidate=self.root/'data/candidates/unbound.json'
        candidate.parent.mkdir(parents=True)
        candidate.write_text(json.dumps(self.pack))
        from editorial_fixture import strength_assessment
        (self.root/'assessment.json').write_text(json.dumps(strength_assessment(self.pack)))
        result=self.run_cli('career_core.py','bind-strength','--pack','data/candidates/unbound.json',
                            '--strength','S_DISTINCTIVE','--output','data/candidates/proposal.json','--assessment','assessment.json')
        self.assertEqual(result.returncode,0,result.stderr)
        candidate.unlink()
        proposal=json.loads((self.root/'data/candidates/proposal.json').read_text())
        self.assertEqual(proposal['metadata']['supersedes'],'data/packs/pack.json')

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
