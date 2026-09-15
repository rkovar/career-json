#!/usr/bin/env python3
"""Regression and lifecycle tests using only isolated fictional workspaces."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
import test_pack_review
from pack_review import units, fingerprint
from editorial_fixture import personas, pack_for
from workspace_backup import backup_workspace, restore_workspace, reference_audit


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_pack_review.PackReviewTests(); self.fixture.setUp()
        self.root = self.fixture.root
        (self.root / 'reviews').mkdir(exist_ok=True)
        self.source = self.root / 'reviews/onboarding.md'
        self.source.write_text(self.fixture.pack['evidence_atoms'][0]['source_refs'][0]['excerpt'])

    def tearDown(self): self.fixture.tearDown()

    def cli(self, *args, success=True, root=None):
        root = root or self.root
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/career_core.py'), *args], cwd=root,
                           env={**os.environ, 'CAREER_WORKSPACE': str(root)}, capture_output=True, text=True)
        self.assertEqual(r.returncode == 0, success, r.stdout + r.stderr)
        return r

    def test_privacy_restriction_survives_later_wording_acceptance(self):
        t = self.fixture; t.proposed = copy.deepcopy(t.pack)
        t.start(); t.choices({'evidence_atoms/E_STORY_1': 'later'}, publication='private')
        self.assertFalse(t.publish('private')['evidence_atoms'][0]['external_safe'])
        t.choices({'evidence_atoms/E_STORY_1': 'accept'})
        self.assertFalse(t.publish('accepted')['evidence_atoms'][0]['external_safe'])

    def test_explicit_resolution_is_sourced_and_separate_from_wording(self):
        t = self.fixture
        t.pack['evidence_atoms'][0]['evidence_status'] = 'unresolved'
        t.pack['evidence_atoms'][0]['open_questions'] = ['What was your role?']
        t.put('data/packs/base.json', t.pack)
        t.proposed['evidence_atoms'][0]['open_questions'] = []
        t.start(); payload = t.choices({'evidence_atoms/E_STORY_1': 'accept'})
        self.assertEqual(t.publish('wording')['evidence_atoms'][0]['evidence_status'], 'unresolved')
        payload['decisions'][0]['reassessment'] = {'status': 'self_asserted', 'reason': 'My recorded answer resolves ownership.',
                                                   'source_refs': t.proposed['evidence_atoms'][0]['source_refs']}
        t.put('reviews/reassessment.json', payload)
        self.cli('review', 'apply', '--input', 'reviews/reassessment.json', '--output', 'data/packs/resolved.json')
        self.assertEqual(json.loads((self.root / 'data/packs/resolved.json').read_text())['evidence_atoms'][0]['evidence_status'], 'self_asserted')

    def test_unverified_reassessment_cannot_raise_status(self):
        t = self.fixture; t.proposed['evidence_atoms'][0]['evidence_status'] = 'corroborated'
        t.start(); payload = t.choices({'evidence_atoms/E_STORY_1': 'accept'})
        payload['decisions'][0]['reassessment'] = {'status': 'corroborated', 'reason': 'I say so', 'source_refs': t.proposed['evidence_atoms'][0]['source_refs']}
        t.put('reviews/reassessment.json', payload)
        self.cli('review', 'apply', '--input', 'reviews/reassessment.json', '--output', 'data/packs/bad.json', success=False)
        self.assertFalse((self.root / 'data/packs/bad.json').exists())

    def test_binding_cannot_publish_unreviewed_candidate(self):
        t = self.fixture; t.put('data/candidates/proposal.json', t.proposed)
        self.cli('bind-strength', '--pack', 'data/candidates/proposal.json', '--strength', 'S_DISTINCTIVE', '--output', 'data/packs/bad.json', success=False)
        self.assertEqual(len(list((self.root / 'data/packs').glob('*.json'))), 1)

    def test_binding_second_version_links_candidate_to_current_head(self):
        t = self.fixture; p = copy.deepcopy(t.pack); p['metadata']['supersedes'] = 'data/packs/base.json'; t.put('data/packs/v2.json', p)
        self.cli('bind-strength', '--pack', 'data/packs/v2.json', '--strength', 'S_DISTINCTIVE', '--output', 'data/candidates/v3.json')
        candidate = json.loads((self.root / 'data/candidates/v3.json').read_text())
        self.assertEqual(candidate['metadata']['supersedes'], 'data/packs/v2.json')
        self.assertEqual(len(list((self.root / 'data/packs').glob('*.json'))), 2)

    def test_acceptance_blocks_false_source_excerpts(self):
        t = self.fixture
        t.proposed['evidence_atoms'][0]['source_refs'] = [{'source_id': 'SRC_SUBJECT', 'excerpt': 'Words not present in source'}]
        t.start(); t.choices({'evidence_atoms/E_STORY_1': 'accept'})
        self.assertIn('source excerpt mismatch', t.cli('accept', '--session', t.session, '--output', 'data/packs/bad.json', success=False).stderr)
        self.assertFalse((self.root / 'data/packs/bad.json').exists())

    def test_verifier_checks_employment_education_strengths_and_preferences(self):
        from verify_excerpts import verify
        pack = copy.deepcopy(self.fixture.pack)
        for group in ('employment', 'strengths_profile', 'positioning_preferences'):
            pack[group][0]['source_refs'] = [{'source_id': 'SRC_SUBJECT', 'excerpt': 'Incorrect source excerpt'}]
        pack['education'] = [{'education_id': 'ED_ONE', 'source_refs': [{'source_id': 'SRC_SUBJECT', 'excerpt': 'Incorrect source excerpt'}]}]
        report = verify(pack, self.root)
        self.assertEqual(report['counts']['mismatch'], 4)
        self.assertEqual({r['record'].split('/')[0] for r in report['excerpts'] if r['status'] == 'mismatch'}, {'employment', 'education', 'strengths_profile', 'positioning_preferences'})

    def test_export_ignores_withheld_and_unresolved_promotion_dates(self):
        if not (ROOT / 'scripts/export_resume_json.py').exists(): self.skipTest('resume add-on is absent')
        from export_resume_json import export
        pack = copy.deepcopy(self.fixture.pack)
        for safe, status in [(False, 'self_asserted'), (True, 'unresolved')]:
            child = dict(pack['employment'][0], employment_id='EMP_OLD', parent_employment_id='EMP_CURRENT', start='1991', end='2000', external_safe=safe, evidence_status=status)
            pack['employment'] = [pack['employment'][0], child]
            self.assertEqual(export(pack, 'public')['work'][0]['startDate'], pack['employment'][0]['start'])

    def test_preview_is_read_only_and_matches_saved_changes(self):
        t = self.fixture; t.start(); t.choices({'evidence_atoms/E_STORY_1': 'accept'})
        before = {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        preview = json.loads(self.cli('review', 'preview', '--session', t.session, '--input', 'reviews/choices.json').stdout)
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        self.assertTrue(preview['can_save']); self.assertIn('evidence_atoms/E_STORY_1', preview['accepted_keys'])
        t.publish()

    def test_connected_review_keeps_explicit_support_controls(self):
        t = self.fixture; state = t.start()
        group = next(g for g in state['groups'] if g['achievement'] == 'evidence_atoms/E_STORY_1')
        self.assertIn('employment/EMP_CURRENT', group['support'])
        self.assertIn('source_records/SRC_SUBJECT', group['support'])
        t.cli('render', '--session', t.session, '--output', 'outputs/review.html')
        page = (self.root / 'outputs/review.html').read_text()
        self.assertIn('Preview what will be saved', page)
        self.assertIn('Review achievement and supporting records together', page)
        self.assertEqual(page.count('class="card" data-key="employment/EMP_CURRENT"'), 1)

    def test_health_separates_integrity_from_career_completeness(self):
        result = json.loads(self.cli('health', '--json').stdout)
        self.assertEqual(result['integrity'], 'ok')
        self.assertNotIn('score', result)
        self.assertTrue(result['next_steps'])
        self.source.unlink()
        result = json.loads(self.cli('health', '--json', success=False).stdout)
        self.assertEqual(result['integrity'], 'needs_repair')
        self.assertTrue(any('missing reference' in e for e in result['errors']))

    def test_history_shows_wording_permission_sources_and_dependencies(self):
        t = self.fixture; t.start(); t.choices({'evidence_atoms/E_STORY_1': 'accept'}, publication='private'); t.publish()
        t.put('data/selections/example.json', {'candidate_ids': ['E_STORY_1']})
        state = json.loads(self.cli('history', 'E_STORY_1').stdout)
        self.assertEqual(len(state['changes']), 2)
        self.assertEqual(state['changes'][-1]['review']['reviewed_by'], 'Fictional Person')
        self.assertTrue(state['changes'][-1]['sources'])
        self.assertTrue(any(r['kind'] == 'strength' for r in state['dependencies']))
        self.assertTrue(any(r.get('path') == 'data/selections/example.json' for r in state['dependencies']))
        self.cli('history', 'E_STORY_1', '--output', 'outputs/history.html')
        self.assertIn('Original sources and answers', (self.root / 'outputs/history.html').read_text())

    def test_backup_restore_preserves_partial_review_byte_for_byte(self):
        t = self.fixture; t.start(); t.choices({'evidence_atoms/E_STORY_1': 'accept', 'evidence_atoms/E_STORY_2': 'later'}); t.publish('partial')
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file() and p.name != '.pack-write.lock'}
        archive = backup_workspace('backups/private.zip', self.root)
        restored = restore_workspace(archive, self.root / 'restored', self.root)
        for name, value in before.items(): self.assertEqual((restored / name).read_bytes(), value, name)
        state = json.loads(self.cli('review', 'resume', '--session', t.session, root=restored).stdout)
        self.assertEqual(state['summary']['reviewed_items'], 1)
        self.assertTrue((restored / 'CAREER-OVERVIEW.html').exists())
        self.assertEqual(archive.stat().st_mode & 0o777, 0o600)

    def test_backup_audits_plan_selection_and_predecessor_references(self):
        from hashlib import sha256
        t = self.fixture
        t.put('data/selections/selection.json', {})
        selection = self.root / 'data/selections/selection.json'
        pin = {'path': 'data/selections/selection.json', 'sha256': sha256(selection.read_bytes()).hexdigest()}
        t.put('data/plans/plan.json', {'selection': pin})
        self.assertFalse(reference_audit(self.root)['errors'])
        original = selection.read_bytes(); selection.write_text('{"changed": true}')
        with self.assertRaisesRegex(ValueError, 'changed reference'):
            backup_workspace('backups/changed-plan.zip', self.root)
        selection.write_bytes(original)
        t.put('data/plans/plan.json', {'selection': pin, 'supersedes': {'path': 'data/plans/missing.json', 'sha256': '0' * 64}})
        self.assertTrue(any('missing reference' in e for e in reference_audit(self.root)['errors']))
        t.put('data/plans/plan.json', {'selection': pin}); selection.unlink()
        with self.assertRaisesRegex(ValueError, 'missing reference'):
            backup_workspace('backups/missing-plan.zip', self.root)

    def test_backup_preserves_and_audits_paused_startup_sources(self):
        source = self.root / 'data/sources/first.md'
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text('A fictional resume selected only in the startup wizard.')
        self.fixture.put('data/private/start-answers.json', {
            'route': {'state': 'answered', 'origin': 'user', 'value': 'existing'},
            'sources': {'state': 'answered', 'origin': 'user', 'value': [
                {'path': 'data/sources/first.md', 'purpose': 'career_evidence'}]}})
        started = json.loads(self.cli('start', 'create', '--id', 'backup-test',
                                     '--answers', 'data/private/start-answers.json').stdout)
        paused = json.loads(self.cli('start', 'pause', '--session', started['session']).stdout)
        saved = (self.root / paused['session']).read_bytes()
        archive = backup_workspace('backups/startup.zip', self.root)
        restored = restore_workspace(archive, self.root / 'restored-startup', self.root)
        self.assertEqual((restored / paused['session']).read_bytes(), saved)
        self.assertEqual((restored / 'data/sources/first.md').read_bytes(), source.read_bytes())
        source.write_text('Changed after selection')
        with self.assertRaisesRegex(ValueError, 'changed reference'):
            backup_workspace('backups/changed-startup.zip', self.root)
        source.unlink()
        with self.assertRaisesRegex(ValueError, 'missing reference'):
            backup_workspace('backups/missing-startup.zip', self.root)

    def test_restore_rejects_missing_plan_dependency_even_with_consistent_inventory(self):
        from hashlib import sha256
        self.fixture.put('data/selections/selection.json', {})
        dependency = 'data/selections/selection.json'
        self.fixture.put('data/plans/plan.json', {'selection': {
            'path': dependency, 'sha256': sha256((self.root / dependency).read_bytes()).hexdigest()}})
        archive = backup_workspace('backups/complete.zip', self.root)
        incomplete = self.root / 'incomplete.zip'
        with zipfile.ZipFile(archive) as source, zipfile.ZipFile(incomplete, 'w') as target:
            inventory = json.loads(source.read('backup-manifest.json')); inventory['files'].pop(dependency)
            for entry in source.infolist():
                if entry.filename == dependency: continue
                content = json.dumps(inventory).encode() if entry.filename == 'backup-manifest.json' else source.read(entry.filename)
                target.writestr(entry, content)
        with self.assertRaisesRegex(ValueError, 'missing reference'):
            restore_workspace(incomplete, self.root / 'incomplete-restore', self.root)
        self.assertFalse((self.root / 'incomplete-restore').exists())

    def test_backup_preserves_plan_history_and_reports_stale_policy(self):
        from hashlib import sha256
        policy = self.root / 'docs/policies/resume-authoring.json'; policy.parent.mkdir(parents=True, exist_ok=True)
        policy.write_text('{"version": 1}')
        pin = {'path': 'docs/policies/resume-authoring.json', 'sha256': sha256(policy.read_bytes()).hexdigest()}
        self.fixture.put('data/plans/historical.json', {'policy': pin})
        policy.write_text('{"version": 2}')
        audit = reference_audit(self.root)
        self.assertFalse(audit['errors']); self.assertTrue(any('changed reference' in w for w in audit['warnings']))
        archive = backup_workspace('backups/plan-history.zip', self.root)
        restored = restore_workspace(archive, self.root / 'restored-plan-history', self.root)
        self.assertEqual((restored / 'data/plans/historical.json').read_bytes(), (self.root / 'data/plans/historical.json').read_bytes())
        self.assertEqual(reference_audit(restored), audit)
        policy.unlink()
        self.assertTrue(any('missing reference' in e for e in reference_audit(self.root)['errors']))

    def test_restore_refuses_overwrite_corruption_and_traversal(self):
        archive = backup_workspace('backups/private.zip', self.root)
        with self.assertRaises(ValueError): restore_workspace(archive, self.root, self.root)
        for name, content in [('data/packs/base.json', b'changed'), ('../outside', b'escape')]:
            bad = self.root / 'bad.zip'
            with zipfile.ZipFile(archive) as src, zipfile.ZipFile(bad, 'w') as dest:
                for entry in src.infolist():
                    dest.writestr(entry, content if entry.filename == name else src.read(entry.filename))
                if name == '../outside': dest.writestr(name, content)
            with self.assertRaises(ValueError): restore_workspace(bad, self.root / 'invalid-restore', self.root)
            self.assertFalse((self.root / 'invalid-restore').exists())

    def test_backup_refuses_missing_sources_symlinks_and_overwrite(self):
        archive = backup_workspace('backups/private.zip', self.root)
        with self.assertRaises(FileExistsError): backup_workspace(archive, self.root)
        (self.root / 'data/link').symlink_to(self.source)
        with self.assertRaises(ValueError): backup_workspace('backups/link.zip', self.root)
        (self.root / 'data/link').unlink(); self.source.unlink()
        with self.assertRaises(ValueError): backup_workspace('backups/missing.zip', self.root)

    def test_merge_requires_joint_review_and_preserves_old_ids(self):
        t = self.fixture
        atom = copy.deepcopy(t.pack['evidence_atoms'][0]); atom['id'] = 'E_MERGED'
        t.put('data/private/replacement.json', {'atoms': [atom]})
        self.cli('maintain', 'merge', '--input', 'data/private/replacement.json', '--from', 'E_STORY_1', 'E_STORY_2', '--reason', 'Two accounts of one project', '--output', 'data/candidates/merge.json')
        t.proposed = json.loads((self.root / 'data/candidates/merge.json').read_text())
        self.assertEqual(len(list((self.root / 'data/packs').glob('*.json'))), 1)
        t.start(); t.choices({'evidence_atoms/E_MERGED': 'accept'})
        t.publish('invalid', success=False)
        t.choices({k: 'accept' for k in ('field/metadata', 'evidence_atoms/E_STORY_1', 'evidence_atoms/E_STORY_2', 'evidence_atoms/E_MERGED')})
        accepted = t.publish('merged')
        old = next(a for a in accepted['evidence_atoms'] if a['id'] == 'E_STORY_1')
        self.assertEqual(old['evidence_status'], 'declined'); self.assertFalse(old['external_safe'])
        history = json.loads(self.cli('history', 'E_STORY_1').stdout)
        self.assertEqual(history['relationships'][0]['to_ids'], ['E_MERGED'])

    def test_split_and_refresh_preserve_history_and_new_sources(self):
        t = self.fixture
        for operation in ('split', 'refresh'):
            with self.subTest(operation=operation):
                atoms = [copy.deepcopy(t.pack['evidence_atoms'][0])]
                if operation == 'split':
                    atoms[0]['id'] = 'E_PART_A'; atoms.append(dict(copy.deepcopy(atoms[0]), id='E_PART_B'))
                else:
                    source = {'source_id': 'SRC_UPDATE', 'source_type': 'person', 'path': 'reviews/update.md', 'retrieved': '2026-09-11', 'independent': False}
                    (self.root / 'reviews/update.md').write_text('My clarified contribution.')
                    atoms[0]['source_refs'].append({'source_id': 'SRC_UPDATE', 'excerpt': 'My clarified contribution.'})
                t.put('data/private/' + operation + '.json', {'atoms': atoms, 'source_records': [source] if operation == 'refresh' else []})
                self.cli('maintain', operation, '--input', 'data/private/' + operation + '.json', '--from', 'E_STORY_1', '--reason', 'My clarification', '--output', 'data/candidates/' + operation + '.json')
                candidate = json.loads((self.root / ('data/candidates/' + operation + '.json')).read_text())
                self.assertIn('E_STORY_1', [a['id'] for a in candidate['evidence_atoms']])
                self.assertEqual(candidate['metadata']['evidence_maintenance'][0]['operation'], operation)
        self.assertEqual(len(list((self.root / 'data/packs').glob('*.json'))), 1)

    def test_disconnected_or_cyclic_history_is_reported_without_silent_reset(self):
        p = copy.deepcopy(self.fixture.pack); p['metadata']['supersedes'] = 'data/packs/base.json'
        self.fixture.put('data/packs/cycle.json', p)
        self.fixture.pack['metadata']['supersedes'] = 'data/packs/cycle.json'; self.fixture.put('data/packs/base.json', self.fixture.pack)
        result = json.loads(self.cli('health', '--json', success=False).stdout)
        self.assertTrue(any('cycle' in e for e in result['errors']))


if __name__ == '__main__': unittest.main(verbosity=2)
