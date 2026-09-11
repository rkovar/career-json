#!/usr/bin/env python3
"""Bounded model checks of editorial skills in a fictional temporary workspace.

Separate from make check. Uses the locally configured Claude CLI and explicitly
allowed local editing/validation tools; no permission bypass or live career data.
    python3 tests/run_editorial_scenarios.py --scenario representation --budget 2
    python3 tests/run_editorial_scenarios.py --scenario formats --budget 4
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from editorial_fixture import ROOT, personas, pack_for, brief_for


def save(root, path, record):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record, indent=2) + '\n')
    return target


def script(root, name, *args):
    result = subprocess.run([sys.executable, str(root / 'scripts' / name), *map(str, args)], cwd=root,
                            env={**os.environ, 'CAREER_WORKSPACE': str(root)}, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout


def workspace(scenario, installation='checkout'):
    root = Path(tempfile.mkdtemp(prefix='career-editorial-eval-'))
    if installation == 'core':
        sys.path.insert(0, str(ROOT / 'scripts'))
        from build_release import build
        import zipfile
        with tempfile.TemporaryDirectory(prefix='career-core-eval-build-') as build_dir:
            archive = build('core', Path(build_dir))
            with zipfile.ZipFile(archive) as handle:
                handle.extractall(root)
                for entry in handle.infolist():
                    (root / entry.filename).chmod((entry.external_attr >> 16) & 0o777)
    else:
        for folder in ('scripts', 'schemas', '.claude'):
            shutil.copytree(ROOT / folder, root / folder)
        shutil.copytree(ROOT / 'docs', root / 'docs')
        shutil.copy(ROOT / 'CLAUDE.md', root / 'CLAUDE.md')
    for folder in ('data/packs', 'data/roles', 'data/briefs', 'data/selections', 'data/private', 'outputs', 'reviews/decisions'):
        (root / folder).mkdir(parents=True, exist_ok=True)
    person = next(p for p in personas() if p['id'] == ('specialist' if scenario == 'representation' else 'technical-leader'))
    pack = pack_for(person)
    save(root, 'data/packs/pack.json', pack)
    (root / 'reviews/onboarding.md').write_text(pack['strengths_profile'][0]['source_refs'][0]['excerpt'])
    kinds = () if installation == 'core' else (('resume',) if scenario != 'formats' else ('resume', 'biography', 'interview_brief'))
    for kind in kinds:
        brief = brief_for(person, kind)
        save(root, f'data/briefs/{kind}-brief.json', brief)
        script(root, 'editorial.py', 'prepare', '--brief', f'data/briefs/{kind}-brief.json',
               '--id', kind, '--output', f'data/selections/{kind}-selection.json')
    if scenario == 'representation':
        artifact = root / 'outputs/fixture-draft.md'
        artifact.write_text('# Owen Birch\n\n## Compiler Engineer\n\nLondon, UK · specialist@example.invalid\n\n'
                            'Compiler engineer with experience maintaining compatibility checks. <!-- Evidence: E_STORY_2 -->\n\n'
                            '## Experience\n\n### Fictional Fieldwork Ltd | Compiler Engineer | 2015 to present\n\n'
                            '- Updated routine compatibility checks for language releases. <!-- Evidence: E_STORY_2 -->\n')
        run = json.loads(script(root, 'manifest.py', 'Compiler Engineer', '--selection', 'data/selections/resume-selection.json', '--artifact', artifact))
        save(root, 'data/private/run.json', run)
    if scenario == 'grounding':
        artifact = root / 'outputs/fixture-draft.md'
        artifact.write_text('# Jules Elm\n\n## Head of Engineering\n\ntechnical-leader@example.invalid · London, UK\n\n'
                            '## Experience\n\n### Fictional Fieldwork Ltd | Head of Engineering | January 2018 to present\n\n'
                            '- Designed a deployment rehearsal format and co-built its runner with engineers; two teams adopted rehearsals before deployment. <!-- Evidence: E_STORY_1 -->\n'
                            '- Hired and coached engineers while introducing peer design reviews; the engineering group adopted them. <!-- Evidence: E_STORY_2 -->\n\n'
                            'Teams freely chose these practices; no mandate was imposed. <!-- Evidence: E_STORY_1, E_STORY_2 -->\n')
    if scenario == 'interview':
        pack['strengths_profile'][0].update({'status': 'proposed', 'question_status': 'open',
                                            'review_question': 'Does this interpretation describe your contribution?'})
        save(root, 'data/packs/pack.json', pack)
    return root


REQUESTS = {
    'grounding': 'Use evaluate-output and review-representation to review outputs/fixture-draft.md against the current pack, '
                 'data/briefs/resume-brief.json and data/selections/resume-selection.json. Save outputs/fixture-evaluation.json '
                 'and the representation sidecar with a shared saved manifest. This is review only: leave the artifact and all '
                 'career inputs unchanged, record findings and publishability, and do not run a recruiter screen or PDF export.',
    'representation': 'Use .claude/skills/review-representation/SKILL.md to review outputs/fixture-draft.md. '
                      'The saved brief is data/briefs/resume-brief.json, selection is data/selections/resume-selection.json '
                      'and exact run is data/private/run.json. Write the representation sidecar and validate it. '
                      'This is a review request; leave the artifact, pack, brief and selection unchanged.',
    'interview': 'Use .claude/skills/review-strengths/SKILL.md to start reviewing my career strengths from the current pack. '
                 'Ask the first question and wait for my answer. All data is fictional test material.',
    'formats': 'Use the project workflows to produce a resume, a public biography and a private interview brief from '
               'data/packs/pack.json. Their saved briefs are data/briefs/resume-brief.json, biography-brief.json and '
               'interview_brief-brief.json; selections are under data/selections/. '
               'Use generate-resume for generation and evaluate-output plus review-representation where applicable; '
               'use make-interview-brief for private preparation. This test requests generation and evaluation only, '
               'not a recruiter screen or PDF export. Save outputs/fixture-draft.md, outputs/fixture-biography-draft.md, '
               'outputs/fixture-interview-brief.md and the relevant review records. '
               'Keep the source pack unchanged and use no sources beyond this fictional workspace. '
               'Afterward explain what was preserved and what changed by format. Do not ask questions.'
}


def checks(root, scenario, payload):
    result = []
    def check(name, passed): result.append({'check': name, 'passed': bool(passed)})
    check('model_completed', not payload.get('is_error', True))
    if scenario == 'grounding':
        path = root / 'outputs/fixture-evaluation.json'
        check('evaluation_created', path.exists())
        if path.exists():
            record = json.loads(path.read_text())
            check('unsupported_contrast_blocks_publishability', record.get('publishable') is False and
                  any(f.get('severity') == 'blocker' and any(word in f.get('message', '').lower()
                      for word in ('voluntar', 'mandate', 'freely', 'chose', 'imposed')) for f in record.get('findings', [])))
            try:
                script(root, 'validate_records.py', path)
                check('record_validates', True)
            except RuntimeError:
                check('record_validates', False)
    elif scenario == 'representation':
        path = root / 'outputs/fixture-draft-representation.json'
        check('review_created', path.exists())
        if path.exists():
            rep = json.loads(path.read_text())
            check('lost_strength_identified', any(r.get('strength_id') == 'S_DISTINCTIVE' and
                                                r.get('status') == 'inadequately_represented' for r in rep.get('strengths', [])))
            check('reader_impressions_recorded', bool(rep.get('reader_impressions')))
            check('exact_saved_manifest_preserved', rep.get('run') == json.loads((root / 'data/private/run.json').read_text()))
            try:
                script(root, 'validate_records.py', path)
                check('record_validates', True)
            except RuntimeError:
                check('record_validates', False)
    elif scenario == 'interview':
        text = payload.get('result', '')
        check('one_question', text.count('?') == 1)
        check('existing_evidence_used', 'rehearsal' in text.lower() and 'design review' in text.lower())
        check('does_not_confirm_for_user', json.loads((root / 'data/packs/pack.json').read_text())['strengths_profile'][0]['status'] == 'proposed')
    else:
        outputs = [('fixture-draft.md', []), ('fixture-biography-draft.md', ['--audience', 'public']),
                   ('fixture-interview-brief.md', ['--private'])]
        for name, flags in outputs:
            path = root / 'outputs' / name
            check(name + '_exists', path.exists())
            if not path.exists(): continue
            try:
                script(root, 'validate_artifact.py', path, *flags)
                check(name + '_validates', True)
            except RuntimeError:
                check(name + '_validates', False)
            if not flags or 'public' in flags:
                check(name + '_privacy', 'PRIVATE_CANARY' not in path.read_text() and 'E_PRIVATE' not in path.read_text())
                check(name + '_distinctive_evidence', 'E_STORY_1' in path.read_text())
            check(name + '_representation_record', path.with_name(path.stem + '-representation.json').exists())
        try:
            script(root, 'validate_records.py')
            check('all_records_validate', True)
        except RuntimeError:
            check('all_records_validate', False)
        # These deterministic checks do not grade prose; the report retains all
        # artifacts so a reviewer can compare meaning and choices across formats.
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', choices=tuple(REQUESTS), required=True)
    parser.add_argument('--installation', choices=('checkout', 'core'), default='checkout')
    parser.add_argument('--budget', type=float, default=2)
    parser.add_argument('--report', type=Path, required=True, help='report path; workspace path included for review')
    args = parser.parse_args()
    if args.installation == 'core' and args.scenario != 'interview':
        parser.error('the core-only installation supports the interview scenario; document generation needs the add-on')
    if args.installation == 'core' and not (ROOT / 'scripts/build_release.py').is_file():
        parser.error('building a core-only test archive requires the developer checkout')
    root = workspace(args.scenario, args.installation)
    print('Fictional evaluation workspace: ' + str(root), flush=True)
    original_pack = (root / 'data/packs/pack.json').read_bytes()
    original_artifact = (root / 'outputs/fixture-draft.md').read_bytes() if args.scenario in ('representation', 'grounding') else None
    cmd = ['claude', '-p', REQUESTS[args.scenario], '--output-format', 'json', '--no-session-persistence',
           '--permission-mode', 'acceptEdits', '--tools', 'Read,Write,Edit,Glob,Grep,Bash',
           '--allowedTools', 'Read,Write,Edit,Glob,Grep,Bash(python3 scripts/*)',
           '--max-budget-usd', str(args.budget)]
    try:
        proc = subprocess.run(cmd, cwd=root, env={**os.environ, 'CAREER_WORKSPACE': str(root)},
                              capture_output=True, text=True, timeout=900)
        payload = json.loads(proc.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        payload = {'is_error': True, 'result': str(exc)}
    result = checks(root, args.scenario, payload)
    if args.scenario != 'interview':
        result.append({'check': 'source_pack_unchanged', 'passed': (root / 'data/packs/pack.json').read_bytes() == original_pack})
    if original_artifact is not None:
        result.append({'check': 'reviewed_artifact_unchanged', 'passed': (root / 'outputs/fixture-draft.md').read_bytes() == original_artifact})
    report = {'scenario': args.scenario, 'installation': args.installation, 'workspace': str(root), 'checks': result,
              'cost_usd': payload.get('total_cost_usd'), 'result': payload.get('result'),
              'model_usage': payload.get('modelUsage', {}),
              'permission_denials': payload.get('permission_denials', [])}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    for row in result:
        print(('PASS ' if row['passed'] else 'FAIL ') + row['check'])
    print('Report: ' + str(args.report))
    return 0 if all(r['passed'] for r in result) else 1


if __name__ == '__main__':
    sys.exit(main())
