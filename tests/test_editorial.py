#!/usr/bin/env python3
"""Editorial persistence tests in fictional, disposable workspaces only."""
import copy
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
import editorial
import current_pack
import manifest
import select_evidence
import validate_pack
import validate_records


class EditorialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='career-editorial-test-')
        self.root = Path(self.temp.name)
        for folder in ('data/packs', 'data/roles', 'data/briefs', 'data/private', 'data/selections', 'reviews/decisions', 'outputs'):
            (self.root / folder).mkdir(parents=True)
        shutil.copytree(ROOT / 'schemas', self.root / 'schemas')
        shutil.copytree(ROOT / '.claude', self.root / '.claude')
        self.saved = []
        for module, attr, value in (
            (editorial, 'ROOT', self.root), (current_pack, 'ROOT', self.root),
            (manifest, 'ROOT', self.root), (manifest, 'SKILLS', self.root / '.claude/skills'),
            (select_evidence, 'ROOT', self.root), (select_evidence, 'ROLES', self.root / 'data/roles'),
            (validate_pack, 'ROOT', self.root), (validate_pack, 'SCHEMA', self.root / 'schemas/career.schema.json'),
            (validate_records, 'ROOT', self.root), (validate_records, 'SCHEMAS', self.root / 'schemas')):
            self.saved.append((module, attr, getattr(module, attr)))
            setattr(module, attr, value)
        # resolve's default argument is bound at import; replace callers as well.
        for module in (editorial, manifest, validate_records):
            self.saved.append((module, 'resolve', module.resolve))
            module.resolve = lambda: current_pack.resolve(self.root / 'data/packs')
        self.pack = json.loads((ROOT / 'examples/career.complex.example.json').read_text())
        self.pack['schema_version'] = '1.4'
        self.pack['metadata'] = {}
        self.pack['source_records'].append({'source_id': 'SRC_EDITORIAL', 'source_type': 'person',
                                            'path': 'reviews/answers.md', 'retrieved': '2026-09-08', 'independent': False})
        self.ref = {'source_id': 'SRC_EDITORIAL', 'excerpt': 'This describes my contribution accurately.'}
        (self.root / 'reviews/answers.md').write_text(self.ref['excerpt'])
        self.aid = 'E_CX_PLATFORM_MIGRATION'
        self.other = 'E_CX_FRAUD_LOSS'
        self.private = 'E_CX_INTERNAL_TOOL'
        self.pack['strengths_profile'] = [self.strength('S_DEPTH', [self.aid])]
        self.pack['positioning_preferences'] = [{'id': 'P_DIRECTION', 'kind': 'direction',
            'text': 'More technical design work', 'status': 'active', 'external_safe': True, 'source_refs': [self.ref]}]
        self.pack_path = self.put('data/packs/pack.json', self.pack)
        self.brief = {'brief_id': 'resume-a', 'application_id': 'application-a', 'role_id': None,
                      'role_family': 'technical', 'format': 'resume', 'audience': 'named_recipient',
                      'length': 'two A4 pages', 'strength_ids': ['S_DEPTH'], 'preference_ids': ['P_DIRECTION'],
                      'priority_evidence_ids': [], 'instructions': '', 'external_safe': False, 'created_by': 'system'}
        self.brief_path = self.put('data/briefs/resume-a-brief.json', self.brief)

    def tearDown(self):
        for module, attr, value in reversed(self.saved):
            setattr(module, attr, value)
        self.temp.cleanup()

    def put(self, path, record):
        path = self.root / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=2) + '\n')
        return path

    def strength(self, sid, ids):
        atoms = editorial.atoms_by_id(self.pack)
        return {'id': sid, 'interpretation': 'Designs dependable technical systems', 'evidence_ids': ids,
                'evidence_fingerprints': {i: editorial.digest(atoms[i]) for i in ids}, 'status': 'confirmed',
                'basis': 'single_achievement' if len(ids) == 1 else 'recurring_pattern',
                'limitations': ['One documented project'], 'timeframe': 'Historical project',
                'external_safe': True, 'source_refs': [self.ref], 'question_status': 'answered'}

    def decision(self, sid=None, action='omit', scope='application', scope_id='application-a', author='system', **extra):
        return {'decision_id': extra.pop('decision_id', 'D_ONE'), 'scope': {'kind': scope, 'id': scope_id},
                'subject': {'kind': 'atom', 'id': sid or self.aid}, 'action': action, 'reason': 'Other evidence better serves this audience.',
                'made_by': author, 'on': '2026-09-08', 'source_refs': [self.ref] if author == 'user' else [], **extra}

    def selection(self, limit=1):
        record = editorial.prepare(self.brief_path, 'selection-a', limit=limit)
        return self.put('data/selections/a-selection.json', record), record

    def cli(self, script, *args):
        return subprocess.run([sys.executable, str(ROOT / 'scripts' / script), *map(str, args)],
                              env={**os.environ, 'CAREER_WORKSPACE': str(self.root)},
                              cwd=self.root, text=True, capture_output=True)

    def test_legacy_migration_preserves_facts_and_archive_validation(self):
        self.pack.pop('strengths_profile'); self.pack.pop('positioning_preferences')
        self.pack['schema_version'] = '1.3'
        self.put('data/packs/pack.json', self.pack)
        before = self.pack_path.read_bytes()
        out = self.cli('editorial.py', 'migrate', '--output', 'data/packs/v2.json')
        self.assertEqual(out.returncode, 0, out.stderr)
        migrated = editorial.read('data/packs/v2.json')
        self.assertEqual(self.pack_path.read_bytes(), before)
        self.assertEqual(migrated['evidence_atoms'], self.pack['evidence_atoms'])
        self.assertEqual(migrated['strengths_profile'], [])
        self.assertEqual(migrated['metadata']['supersedes'], 'data/packs/pack.json')
        self.assertEqual(self.cli('current_pack.py').stdout.strip(), 'data/packs/v2.json')
        for path in ('data/packs/pack.json', 'data/packs/v2.json'):
            out = self.cli('validate_pack.py', path)
            self.assertEqual(out.returncode, 0, out.stdout)
        again = self.cli('editorial.py', 'migrate', '--output', 'data/packs/v2.json')
        self.assertNotEqual(again.returncode, 0)

    def test_fingerprint_invalidation_does_not_change_truth(self):
        self.assertEqual(editorial.profile_state(self.pack['strengths_profile'][0], self.pack), 'confirmed')
        original = self.pack['evidence_atoms'][0]['evidence_status']
        editorial.atoms_by_id(self.pack)[self.aid]['star']['action'] = 'Corrected personal contribution'
        self.assertEqual(editorial.profile_state(self.pack['strengths_profile'][0], self.pack), 'stale')
        self.assertEqual(editorial.safe_strengths(self.pack), [])
        self.assertEqual(self.pack['evidence_atoms'][0]['evidence_status'], original)
        errors, warnings = editorial.validate_profile(self.pack)
        self.assertFalse(errors)
        self.assertTrue(any('changed' in w for w in warnings))

    def test_private_or_partial_support_never_enters_generation(self):
        s = self.strength('S_PRIVATE', [self.aid, self.private])
        s['interpretation'] = 'PRIVATE-CANARY-INTERPRETATION'
        self.pack['strengths_profile'].append(s)
        self.pack['positioning_preferences'][0].update({'external_safe': False, 'text': 'PRIVATE-CANARY-PREFERENCE'})
        self.put('data/packs/pack.json', self.pack)
        self.brief['strength_ids'].append('S_PRIVATE')
        self.brief['instructions'] = 'PRIVATE-CANARY-INSTRUCTION'
        self.brief['audience'] = 'public'
        self.put('data/briefs/resume-a-brief.json', self.brief)
        path, _ = self.selection()
        output = json.dumps(editorial.generation_view(path))
        self.assertNotIn('PRIVATE-CANARY', output)
        self.assertNotIn(self.private, output)
        self.assertNotIn('source_refs', output)
        self.assertNotIn('morgan.vale@example.invalid', output)

    def test_strength_support_survives_small_candidate_limit(self):
        path, record = self.selection()
        self.assertIn(self.aid, record['candidate_ids'])
        self.assertIn('S_DEPTH', next(r['contribution'] for r in record['recommendations'] if r['evidence_id'] == self.aid))
        view = editorial.generation_view(path)
        self.assertIn(self.aid, [a['id'] for a in view['atoms']])
        self.assertEqual(view['editorial']['strengths'][0]['id'], 'S_DEPTH')

    def test_omission_stays_in_its_application(self):
        self.put('reviews/decisions/d-decision.json', self.decision())
        path, record = self.selection()
        self.assertNotIn(self.aid, [a['id'] for a in editorial.generation_view(path)['atoms']])
        self.brief.update({'application_id': 'application-b', 'brief_id': 'resume-b'})
        self.brief_path = self.put('data/briefs/resume-b-brief.json', self.brief)
        path, _ = self.selection()
        self.assertIn(self.aid, [a['id'] for a in editorial.generation_view(path)['atoms']])

    def test_output_choice_survives_brief_revision_but_not_other_formats(self):
        self.brief['output_id'] = 'stable-resume'
        self.put('data/briefs/resume-a-brief.json', self.brief)
        self.put('reviews/decisions/d-decision.json', self.decision(scope='output', scope_id='stable-resume'))
        self.brief['brief_id'] = 'shortened-resume-v2'
        self.brief['length'] = 'one page'
        self.brief_path = self.put('data/briefs/resume-v2-brief.json', self.brief)
        path, _ = self.selection()
        self.assertNotIn(self.aid, [a['id'] for a in editorial.generation_view(path)['atoms']])
        bio = {**self.brief, 'brief_id': 'bio-v1', 'output_id': 'public-bio', 'format': 'biography', 'audience': 'public'}
        self.assertNotIn(('atom', self.aid), editorial.effective_decisions(bio))

    def test_user_choice_precedes_system_and_eligibility_precedes_both(self):
        self.put('reviews/decisions/user-decision.json', self.decision(action='include', author='user'))
        self.put('reviews/decisions/system-decision.json', self.decision(scope='output', scope_id='resume-a', decision_id='D_TWO'))
        path, _ = self.selection()
        self.assertIn(self.aid, [a['id'] for a in editorial.generation_view(path)['atoms']])
        self.put('reviews/decisions/private-decision.json', self.decision(sid=self.private, action='include', author='user', decision_id='D_PRIVATE'))
        path, _ = self.selection()
        self.assertNotIn(self.private, [a['id'] for a in editorial.generation_view(path)['atoms']])

    def test_conflict_needs_explicit_supersession_and_retraction(self):
        first = self.decision()
        self.put('reviews/decisions/one-decision.json', first)
        self.put('reviews/decisions/two-decision.json', self.decision(action='include', decision_id='D_TWO'))
        with self.assertRaisesRegex(ValueError, 'conflicting'):
            editorial.effective_decisions(self.brief)
        second = self.decision(action='include', decision_id='D_TWO', supersedes='D_ONE')
        self.put('reviews/decisions/two-decision.json', second)
        self.assertEqual(editorial.effective_decisions(self.brief)[('atom', self.aid)], 'include')
        self.put('reviews/decisions/three-decision.json', self.decision(action='retract', decision_id='D_THREE', supersedes='D_TWO'))
        self.assertNotIn(('atom', self.aid), editorial.effective_decisions(self.brief))

    def test_bad_supersession_rejected_before_save(self):
        self.put('reviews/decisions/one-decision.json', self.decision(author='user'))
        candidate = self.decision(action='include', decision_id='D_TWO', supersedes='D_ONE')
        self.put('data/private/candidate.json', candidate)
        out = self.cli('editorial.py', 'save', '--kind', 'decision', '--input', 'data/private/candidate.json', '--output', 'reviews/decisions/two-decision.json')
        self.assertNotEqual(out.returncode, 0)
        self.assertIn('cannot supersede', out.stderr)
        self.assertFalse((self.root / 'reviews/decisions/two-decision.json').exists())
        candidate['made_by'] = 'user'; candidate['source_refs'] = [self.ref]
        candidate['scope']['kind'] = 'person'; candidate['scope']['id'] = 'person'
        errors, _ = editorial.validate_record('decision', candidate)
        self.assertTrue(any('scope' in e for e in errors))

    def test_unrelated_decision_does_not_stale_but_new_applicable_one_does(self):
        path, _ = self.selection()
        self.put('reviews/decisions/other-decision.json', self.decision(scope_id='another-app'))
        editorial.generation_view(path)
        self.put('reviews/decisions/relevant-decision.json', self.decision(decision_id='D_TWO'))
        with self.assertRaisesRegex(ValueError, 'decisions changed'):
            editorial.generation_view(path)

    def test_manifest_pins_all_inputs_and_new_decisions_invalidate_it(self):
        path, record = self.selection()
        artifact = self.root / 'outputs/resume-draft.md'
        artifact.write_text('# Fictional person\n')
        run = manifest.manifest('Technical specialist', artifact, path, {'format': 'resume'})
        self.assertFalse(manifest.editorial_staleness(run))
        self.assertEqual(run['editorial_inputs']['brief'], record['brief'])
        self.put('reviews/decisions/relevant-decision.json', self.decision())
        self.assertTrue(manifest.editorial_staleness(run))
        with self.assertRaises(ValueError):
            manifest.manifest('Role', artifact, path)

    def test_changed_brief_role_and_selection_make_reviews_stale(self):
        role = {'role_id': 'technical', 'title': 'Technical specialist', 'central_requirement': 'Technical design',
                'requirements': [{'text': 'Technical design', 'weight': 'essential', 'evidenced_by': [self.aid]}]}
        self.put('data/roles/technical.json', role)
        self.brief['role_id'] = 'technical'; self.put('data/briefs/resume-a-brief.json', self.brief)
        path, _ = self.selection()
        artifact = self.root / 'outputs/resume-draft.md'; artifact.write_text('Fictional output')
        run = manifest.manifest('Role', artifact, path)
        for target in (self.brief_path, path, self.root / 'data/roles/technical.json'):
            before = target.read_bytes()
            target.write_bytes(before + b'\n')
            self.assertTrue(manifest.editorial_staleness(run), target)
            target.write_bytes(before)
        self.assertFalse(manifest.editorial_staleness(run))

    def test_acceptance_requires_answer_but_never_confirms_role_links(self):
        path, record = self.selection()
        record['review_status'] = 'accepted'
        errors, _ = editorial.validate_record('selection', record)
        self.assertTrue(any('answer source' in e for e in errors))
        before = copy.deepcopy(self.pack)
        record['review_source_refs'] = [self.ref]
        errors, _ = editorial.validate_record('selection', record)
        self.assertFalse(errors)
        self.assertEqual(self.pack, before)

    def test_rejected_and_declined_interview_questions_stay_closed(self):
        s = self.pack['strengths_profile'][0]
        s['status'] = 'rejected'; s['question_status'] = 'answered'
        s['review_question'] = 'Would you describe this differently?'
        self.put('data/packs/pack.json', self.pack)
        out = self.cli('editorial.py', 'status')
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertFalse(json.loads(out.stdout)['strengths'][0]['ask'])
        self.assertFalse(editorial.safe_strengths(self.pack))
        s['status'] = 'proposed'; s['question_status'] = 'declined'
        editorial.atoms_by_id(self.pack)[self.aid]['star']['action'] = 'Changed evidence'
        self.put('data/packs/pack.json', self.pack)
        self.assertFalse(json.loads(self.cli('editorial.py', 'status').stdout)['strengths'][0]['ask'])

    def test_profile_validation_requires_real_references_and_person_answers(self):
        self.pack['strengths_profile'][0]['evidence_ids'] = ['E_DOES_NOT_EXIST']
        errors, _ = editorial.validate_profile(self.pack)
        self.assertTrue(any('unknown evidence' in e for e in errors))
        self.pack['positioning_preferences'][0]['source_refs'] = []
        errors, _ = editorial.validate_profile(self.pack)
        self.assertTrue(any('recorded answer' in e for e in errors))

    def test_unsafe_selection_and_path_escape_rejected(self):
        _, record = self.selection()
        record['candidate_ids'].append(self.private)
        errors, _ = editorial.validate_record('selection', record)
        self.assertTrue(any('ineligible' in e for e in errors))
        with self.assertRaisesRegex(ValueError, 'inside CAREER_WORKSPACE'):
            editorial.local('../outside.json')
        with self.assertRaises(FileExistsError):
            editorial.write_new(self.brief_path, {})

    def test_misspelled_scope_cannot_silently_discard_a_decision(self):
        errors, _ = editorial.validate_record('decision', self.decision(scope_id='typo-application'))
        self.assertTrue(any('scope does not resolve' in e for e in errors))

    def test_save_enforces_durable_directory_and_unique_ids(self):
        path, record = self.selection()
        candidate = self.put('data/private/selection.json', record)
        out = self.cli('editorial.py', 'save', '--kind', 'selection', '--input', candidate,
                       '--output', 'data/selections/duplicate-selection.json')
        self.assertNotEqual(out.returncode, 0)
        self.assertIn('selection_id already exists', out.stderr)
        record['selection_id'] = 'selection-b'
        self.put('data/private/selection.json', record)
        out = self.cli('editorial.py', 'save', '--kind', 'selection', '--input', candidate,
                       '--output', 'outputs/lost-selection.json')
        self.assertNotEqual(out.returncode, 0)
        self.assertFalse((self.root / 'outputs/lost-selection.json').exists())

    def test_bind_strength_preserves_candidate_lineage_without_promoting(self):
        before = self.pack_path.read_bytes()
        self.pack['metadata'] = {'supersedes': 'data/packs/pack.json'}
        self.pack['strengths_profile'][0]['status'] = 'proposed'
        self.pack['evidence_atoms'][0]['star']['action'] += ' Updated.'
        candidate = self.put('data/private/candidate.json', self.pack)
        out = self.cli('editorial.py', 'bind-strength', '--pack', candidate, '--strength', 'S_DEPTH',
                       '--output', 'data/packs/v2.json')
        self.assertEqual(out.returncode, 0, out.stderr)
        saved = editorial.read('data/packs/v2.json')
        self.assertEqual(saved['metadata']['supersedes'], 'data/packs/pack.json')
        self.assertEqual(saved['strengths_profile'][0]['status'], 'proposed')
        self.assertEqual(saved['evidence_atoms'], self.pack['evidence_atoms'])
        self.assertEqual(self.pack_path.read_bytes(), before)

    def test_cli_generation_uses_saved_selection_and_rejects_overrides(self):
        path, _ = self.selection()
        out = self.cli('select_evidence.py', '--selection', path)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout)['editorial']['brief_id'], 'resume-a')
        out = self.cli('select_evidence.py', '--selection', path, '--audience', 'public')
        self.assertNotEqual(out.returncode, 0)

    def test_private_words_are_not_mistaken_for_embedded_evidence_ids(self):
        path = self.root / 'outputs/private-interview-brief.md'
        path.write_text('PRIVATE_CANARY describes private fixture material. <!-- Evidence: ' + self.aid + ' -->\n')
        out = self.cli('validate_artifact.py', path, '--private')
        self.assertEqual(out.returncode, 0, out.stdout)

    def representation(self, path, artifact):
        return {'artifact': str(artifact.relative_to(self.root)), 'run': manifest.manifest('Role', artifact, path),
                'reader_impressions': ['Technical design with a dependable migration outcome'],
                'strengths': [{'strength_id': 'S_DEPTH', 'status': 'clearly_represented', 'evidence_ids': [self.aid],
                               'artifact_excerpt': 'Designed the migration', 'reason': 'The wording establishes personal technical design.'}],
                'findings': []}

    def test_representation_checks_support_and_actual_excerpt_not_just_id(self):
        path, _ = self.selection()
        artifact = self.root / 'outputs/resume-draft.md'
        artifact.write_text('Designed the migration. <!-- Evidence: ' + self.aid + ' -->\n')
        rep = self.representation(path, artifact)
        errors, _ = editorial.validate_record('representation', rep)
        self.assertFalse(errors, errors)
        artifact.write_text('Worked on a project. <!-- Evidence: ' + self.aid + ' -->\n')
        # Even a newly pinned review cannot reuse an excerpt lost in shortening.
        rep['run'] = manifest.manifest('Role', artifact, path)
        errors, _ = editorial.validate_record('representation', rep)
        self.assertTrue(any('excerpt' in e for e in errors))
        rep['strengths'] = []
        errors, _ = editorial.validate_record('representation', rep)
        self.assertTrue(any('every intended strength' in e for e in errors))

    def test_publishability_requires_representation_and_resolved_findings(self):
        path, _ = self.selection()
        artifact = self.root / 'outputs/resume-draft.md'; artifact.write_text('Designed the migration. <!-- Evidence: ' + self.aid + ' -->\n')
        rep = self.representation(path, artifact)
        ev = {'artifacts': ['outputs/resume-draft.md'], 'target_role': 'Role', 'publishable': True,
              'evaluation_date': '2026-09-08', 'run': rep['run'], 'findings': [], 'passed_checks': []}
        ev_path = self.put('outputs/resume-evaluation.json', ev)
        self.assertTrue(validate_records.check(ev_path)[1])
        rep['strengths'][0]['status'] = 'inadequately_represented'
        self.put('outputs/resume-draft-representation.json', rep)
        self.assertTrue(any('unresolved representation' in e for e in validate_records.check(ev_path)[1]))
        rep['strengths'][0]['status'] = 'intentionally_omitted'
        rep['strengths'][0]['reason'] = 'Another strength is more useful in the requested short format.'
        omission = self.decision()
        omission['subject'] = {'kind': 'strength', 'id': 'S_DEPTH'}
        self.put('reviews/decisions/omission-decision.json', omission)
        path, _ = self.selection()
        rep['run'] = manifest.manifest('Role', artifact, path)
        ev['run'] = rep['run']
        self.put('outputs/resume-evaluation.json', ev)
        self.put('outputs/resume-draft-representation.json', rep)
        self.assertFalse(validate_records.check(ev_path)[1])

    def test_five_personas_survive_shortening_retargeting_and_correction(self):
        from editorial_fixture import personas, pack_for, brief_for
        for person in personas():
            with self.subTest(person=person['id']):
                self.pack = pack_for(person)
                self.put('data/packs/pack.json', self.pack)
                errors, _ = validate_pack.check(self.pack_path, json.loads(validate_pack.SCHEMA.read_text()))
                self.assertFalse(errors, errors)
                self.brief = brief_for(person)
                self.brief_path = self.put('data/briefs/current-brief.json', self.brief)
                path, before = self.selection(limit=1)
                self.assertIn('E_STORY_1', before['candidate_ids'])
                self.assertNotIn('PRIVATE_CANARY', json.dumps(editorial.generation_view(path)))
                # Shortening changes the brief, not the truth or the support.
                self.brief['length'] = '75 words'
                self.put('data/briefs/current-brief.json', self.brief)
                with self.assertRaises(ValueError):
                    editorial.generation_view(path)
                path, shortened = self.selection(limit=1)
                self.assertIn('E_STORY_1', shortened['candidate_ids'])
                # Retargeting can use the same history and different intent.
                self.brief['application_id'] = person['id'] + '-next-application'
                self.put('data/briefs/current-brief.json', self.brief)
                path, _ = self.selection(limit=1)
                self.assertEqual(editorial.generation_view(path)['editorial']['preferences'][0]['text'], person['direction'])
                # A factual correction invalidates the interpretation without
                # being mistaken for an approval or a new outcome.
                self.pack['evidence_atoms'][0]['star']['action'] += '; correction: shared contribution'
                self.put('data/packs/pack.json', self.pack)
                with self.assertRaises(ValueError):
                    editorial.generation_view(path)
                path, _ = self.selection(limit=1)
                self.assertEqual(editorial.generation_view(path)['editorial']['strengths'], [])
                self.assertTrue(all(a['evidence_status'] == 'self_asserted' for a in self.pack['evidence_atoms']))

    def test_user_strength_omission_preserves_usable_atoms(self):
        decision = self.decision(author='user')
        decision['subject'] = {'kind': 'strength', 'id': 'S_DEPTH'}
        decision['reason'] = 'PRIVATE_REASON_CANARY'
        self.put('reviews/decisions/omit-decision.json', decision)
        path, _ = self.selection(limit=30)
        view = editorial.generation_view(path)
        self.assertEqual(view['editorial']['strengths'], [])
        self.assertIn(self.aid, [a['id'] for a in view['atoms']])
        self.assertNotIn('PRIVATE_REASON_CANARY', json.dumps(view))
        self.brief['application_id'] = 'different-application'
        self.put('data/briefs/resume-a-brief.json', self.brief)
        path, _ = self.selection(limit=30)
        self.assertEqual([s['id'] for s in editorial.generation_view(path)['editorial']['strengths']], ['S_DEPTH'])

    def test_generation_preserves_saved_recommendation_order(self):
        path, record = self.selection(limit=4)
        record['recommendations'].reverse()
        record['recommendations'][1]['disposition'] = 'reserve'
        self.put('data/selections/a-selection.json', record)
        expected = [r['evidence_id'] for r in record['recommendations'] if r['disposition'] == 'recommended']
        self.assertEqual([a['id'] for a in editorial.generation_view(path)['atoms']], expected)

    def test_missing_wrong_and_changed_role_pins_fail(self):
        role = {'role_id': 'technical', 'title': 'Technical specialist', 'central_requirement': 'Technical design',
                'requirements': [{'text': 'Technical design', 'weight': 'essential', 'evidenced_by': [self.aid]}]}
        self.put('data/roles/technical.json', role)
        self.put('data/roles/other.json', role)
        self.brief['role_id'] = 'technical'
        self.put('data/briefs/resume-a-brief.json', self.brief)
        path, original = self.selection()
        artifact = self.root / 'outputs/resume-draft.md'
        artifact.write_text('A fictional artifact')
        run = manifest.manifest('Technical specialist', artifact, path)
        for replacement in (None, editorial.pin('data/roles/other.json')):
            record = copy.deepcopy(original)
            record.pop('role')
            if replacement:
                record['role'] = replacement
            self.put('data/selections/a-selection.json', record)
            with self.assertRaisesRegex(ValueError, 'requires role pin'):
                editorial.generation_view(path)
            with self.assertRaisesRegex(ValueError, 'requires role pin'):
                manifest.manifest('Technical specialist', artifact, path)
            # Older malformed runs must fail even if all their supplied hashes match.
            old = copy.deepcopy(run)
            old['editorial_inputs']['selection'] = editorial.pin(path)
            old['editorial_inputs'].pop('role')
            if replacement:
                old['editorial_inputs']['role'] = replacement
            self.assertTrue(any('requires role pin' in e for e in manifest.editorial_staleness(old)))
        self.put('data/selections/a-selection.json', original)
        role['central_requirement'] = 'Changed role'
        self.put('data/roles/technical.json', role)
        self.assertTrue(manifest.editorial_staleness(run))

    def test_role_pin_without_role_is_rejected(self):
        self.put('data/roles/other.json', {})
        path, record = self.selection()
        record['role'] = editorial.pin('data/roles/other.json')
        self.assertTrue(any('without a role' in e for e in editorial.validate_record('selection', record)[0]))

    def review_inputs(self):
        path, _ = self.selection()
        artifact = self.root / 'outputs/resume-draft.md'
        artifact.write_text('Designed the migration. <!-- Evidence: ' + self.aid + ' -->\n')
        rep = self.representation(path, artifact)
        run = rep.pop('run')
        self.put('data/private/run.json', run)
        self.put('data/private/body.json', rep)
        return run, rep, artifact

    def save_review_cli(self, *extra):
        return self.cli('save_review.py', '--kind', 'representation', '--body', 'data/private/body.json',
                        '--run', 'data/private/run.json', '--output', 'outputs/resume-draft-representation.json', *extra)

    def test_review_assembly_preserves_exact_run_and_replaces_atomically(self):
        run, body, _ = self.review_inputs()
        run['generation_settings'] = {'temperature': 0, 'format': 'resume'}
        self.put('data/private/run.json', run)
        result = self.save_review_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        out = self.root / 'outputs/resume-draft-representation.json'
        self.assertEqual(json.loads(out.read_text())['run'], run)
        self.assertNotEqual(self.save_review_cli().returncode, 0)
        body['reader_impressions'] = ['A revised reader impression']
        self.put('data/private/body.json', body)
        self.assertEqual(self.save_review_cli('--replace').returncode, 0)
        before = out.read_bytes()
        body['run'] = run
        self.put('data/private/body.json', body)
        self.assertNotEqual(self.save_review_cli('--replace').returncode, 0)
        self.assertEqual(out.read_bytes(), before)

    def test_review_assembly_refuses_stale_or_incomplete_manifests(self):
        run, _, artifact = self.review_inputs()
        damaged = copy.deepcopy(run)
        damaged['skill_versions'].pop('review-representation')
        self.put('data/private/run.json', damaged)
        self.assertNotEqual(self.save_review_cli().returncode, 0)
        self.put('data/private/run.json', run)
        artifact.write_text('Changed artifact')
        self.assertNotEqual(self.save_review_cli().returncode, 0)
        self.assertFalse((self.root / 'outputs/resume-draft-representation.json').exists())

    def test_evaluation_assembly_enforces_representation_gate(self):
        run, rep, _ = self.review_inputs()
        rep['strengths'][0]['status'] = 'inadequately_represented'
        self.put('data/private/body.json', rep)
        self.assertEqual(self.save_review_cli().returncode, 0)
        ev = {'artifacts': ['outputs/resume-draft.md'], 'target_role': 'Role', 'publishable': True,
              'evaluation_date': '2026-09-08', 'findings': [], 'passed_checks': []}
        self.put('data/private/evaluation-body.json', ev)
        args = ('--kind', 'evaluation', '--body', 'data/private/evaluation-body.json', '--run',
                'data/private/run.json', '--output', 'outputs/resume-evaluation.json')
        self.assertNotEqual(self.cli('save_review.py', *args).returncode, 0)
        ev['publishable'] = False
        self.put('data/private/evaluation-body.json', ev)
        result = self.cli('save_review.py', *args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(editorial.read('outputs/resume-evaluation.json')['run'], run)

    def test_private_facts_preserve_unknown_and_explicit_measurement_states(self):
        from private_facts import facts, grounding_errors
        atom = editorial.atoms_by_id(self.pack)[self.aid]
        for metric, expected in (([], None), (['an estimate'], 'unknown'),
                                 ([{'value': 'an estimate', 'basis': None}], 'unknown'),
                                 ([{'value': 'an estimate', 'measured': None}], 'unknown'),
                                 ([{'value': 'an estimate', 'measured': True}], 'measured'),
                                 ([{'value': 'an estimate', 'measured': False}], 'not_measured')):
            atom['metrics'] = metric
            row = next(a for a in facts(self.pack)['atoms'] if a['evidence_id'] == self.aid)
            self.assertEqual(row['occurred'], atom.get('occurred'))
            self.assertEqual(row['metrics'][0]['measurement_status'] if metric else None, expected)
            prose = 'The metric “an estimate” was not measured. <!-- Evidence: ' + self.aid + ' -->'
            self.assertEqual(bool(grounding_errors(prose, self.pack)), expected != 'not_measured')
        self.assertTrue(grounding_errors('Turnover was not measured. <!-- Evidence: ' + self.aid + ' -->', self.pack))
        atom['metrics'] = []
        self.assertFalse(grounding_errors('Measurement information is not recorded. <!-- Evidence: ' + self.aid + ' -->', self.pack))
        self.assertTrue(grounding_errors('Everything else: Not measured.', self.pack))

    def test_private_artifact_cli_rejects_fabricated_age_and_measurement(self):
        artifact = self.root / 'outputs/interview-brief.md'
        aid = self.aid
        for prose, expected in (
                ('March 2019, six years ago.', False),
                ('Everything else was not measured.', False),
                ('Recorded in March 2019. Measurement information is not recorded.', True)):
            artifact.write_text('# Private interview preparation\n\n' + prose + ' <!-- Evidence: ' + aid + ' -->\n')
            result = self.cli('validate_artifact.py', artifact, '--private')
            self.assertEqual(result.returncode == 0, expected, result.stdout + result.stderr)

    def test_private_relative_age_uses_stable_recorded_dates(self):
        from private_facts import grounding_errors
        for text in ('March 2019, six years ago', 'March 2019 (6 years ago)', '18 months ago', 'It is six years old'):
            self.assertTrue(grounding_errors(text, self.pack), text)
        self.assertFalse(grounding_errors('The recorded date is March 2019.', self.pack))

    def test_delete_outputs_and_regenerate_three_formats(self):
        records = []
        for fmt, audience in (('resume', 'named_recipient'), ('biography', 'public'), ('interview_brief', 'private')):
            brief = {**self.brief, 'brief_id': fmt, 'format': fmt, 'audience': audience}
            bp = self.put(f'data/briefs/{fmt}-brief.json', brief)
            selection = editorial.prepare(bp, fmt)
            sp = self.put(f'data/selections/{fmt}-selection.json', selection)
            records.append((fmt, sp, copy.deepcopy(selection)))
        (self.root / 'outputs/disposable.md').write_text('Disposable prose is not a new source.')
        shutil.rmtree(self.root / 'outputs')
        for fmt, path, before in records:
            self.assertEqual(editorial.read(path), before)
            if fmt == 'interview_brief':
                with self.assertRaisesRegex(ValueError, 'private interview'):
                    editorial.generation_view(path)
                self.assertIn(self.private, editorial.atoms_by_id(editorial.read(before['pack']['path'])))
            else:
                view = editorial.generation_view(path)
                self.assertIn(self.aid, [a['id'] for a in view['atoms']])
                self.assertEqual(view['editorial']['format'], fmt)
        self.assertEqual(editorial.read(self.pack_path), self.pack)


if __name__ == '__main__':
    unittest.main(verbosity=2)
