#!/usr/bin/env python3
"""Choose a career workflow and open its existing conversational wizard."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from check_components import check
from current_pack import ROOT, resolve
from startup import FLOW_LABELS, continue_prompt

PROMPTS = {
    'career': 'Walk me through the career-pack wizard.',
    'update': 'Help me update my career pack. Save a quick note as supplied, or inspect the new material I specify and review only meaningful additions and changes.',
    'resume': 'Walk me through the resume wizard.',
    'view': 'Show my current saved career record. Refresh its reading page from the accepted pack if needed.',
}
STATUSES = {'active': 'In progress', 'paused': 'Paused', 'handed_off': 'Setup complete'}


def label(value):
    """Keep saved names readable on one terminal line."""
    return ''.join(c for c in ' '.join(str(value).split()) if c.isprintable())[:100]


def resume_available(root):
    if not (root / 'components/resume/component.json').exists():
        return False, 'Create a resume is available with the Resume Application add-on. See docs/releases.md.'
    try:
        check(root, require='resume')
        for name in ('scripts/editorial.py', '.claude/skills/make-resume/SKILL.md'):
            if not (root / name).is_file():
                raise ValueError('Resume Application installation is incomplete')
        return True, None
    except (ValueError, KeyError, OSError) as exc:
        return False, 'Resume setup is unavailable: ' + str(exc)


def saved_work(root, include_resume, history=False):
    """Read current setup names and review names without creating or changing data."""
    root = Path(root).resolve()
    result, unreadable = [], 0
    flows = ('career', 'resume') if include_resume else ('career',)
    for kind in flows:
        base = root / 'reviews/startup' / kind
        for folder in sorted(base.glob('*')):
            paths = sorted(folder.glob('[0-9][0-9][0-9][0-9][0-9][0-9].json'))
            if not paths:
                continue
            try:
                path = paths[-1]
                if not path.resolve().is_relative_to(root):
                    raise ValueError('session outside workspace')
                row = json.loads(path.read_text())
                if (row['version'] != 1 or row['flow'] != kind
                        or row['session_id'] != folder.name
                        or not re.fullmatch(r'[A-Za-z0-9_-]+', row['session_id'])
                        or type(row['revision']) is not int
                        or path.stem != '{:06d}'.format(row['revision'])
                        or row['status'] not in STATUSES):
                    raise ValueError('invalid saved setup')
                if row['status'] == 'handed_off' and not history:
                    continue
                result.append({
                    'label': '{} — {} ({})'.format(FLOW_LABELS[kind], label(row['session_id']), STATUSES[row['status']]),
                    'prompt': continue_prompt(row),
                    'updated': label(row.get('updated_at', '')),
                })
            except (ValueError, KeyError, TypeError, OSError):
                unreadable += 1
    from pack_review import session_catalog
    # The shared projection knows which complete review sessions have actionable
    # work. Older incomplete headers remain discoverable for diagnosis.
    from career_state import summary
    current_reviews = {r['review_id']: r for r in summary(root)['reviews']}
    for row in session_catalog(root):
        if row.get('error'):
            unreadable += 1
        elif history or not row['superseded_by']:
            if not history and row['review_id'] in current_reviews and not current_reviews[row['review_id']]['actionable']:
                continue
            result.append({'label': 'Career-pack review — ' + label(row['label']),
                           'prompt': 'Continue my career-pack review named {}.'.format(json.dumps(row['review_id'])),
                           'updated': label(row['created'])})
    return sorted(result, key=lambda row: (row['updated'], row['label']), reverse=True), unreadable


def choose(title, choices):
    print('\n' + title)
    for i, row in enumerate(choices, 1):
        print('  {}. {}'.format(i, row['label']))
    print('  q. Quit')
    while True:
        try:
            value = input('\nChoose a number: ').strip().lower()
        except EOFError:
            return None
        if value in ('q', 'quit'):
            return None
        if value.isascii() and value.isdigit() and 1 <= int(value) <= len(choices):
            return choices[int(value) - 1]
        print('Choose 1–{} or q.'.format(len(choices)))


def main(argv=None, root=ROOT):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--flow', choices=('career', 'update', 'resume', 'continue', 'view'))
    parser.add_argument('--history', action='store_true', help='include completed setup and review work')
    parser.add_argument('--print-prompt', action='store_true', help='show the conversation prompt without opening Claude Code')
    args = parser.parse_args(argv)
    root = Path(root).resolve()
    try:
        check(root)
        has_resume, note = resume_available(root)
        saved, unreadable = saved_work(root, has_resume, args.history)
        choices = [{'label': FLOW_LABELS['career'], 'flow': 'career'}]
        try:
            current = resolve(root / 'data/packs', root)
        except SystemExit as exc:
            raise ValueError('The saved career history needs repair; it is not an empty workspace. ' + str(exc)) from exc
        from career_state import history_errors
        problems = history_errors(current, root)
        if problems:
            raise ValueError('; '.join(problems))
        if current:
            choices.insert(0, {'label': 'Update my career pack', 'flow': 'update'})
            choices.insert(1, {'label': 'View my saved career record', 'flow': 'view'})
        if has_resume:
            choices.append({'label': FLOW_LABELS['resume'], 'flow': 'resume'})
        if saved:
            choices.append({'label': 'Continue saved work', 'flow': 'continue'})
        print('Start here')
        print('Build a private career record, or turn it into a resume.')
        print('Unsure? Start with your career pack. One old resume is enough.')
        if note:
            print('\n' + note)
        if unreadable:
            print('\n{} saved item(s) could not be read. Ask the assistant to check workspace health.'.format(unreadable))
        interactive = sys.stdin.isatty() and sys.stdout.isatty()
        if not args.flow and not interactive:
            print('\nOpen this project in Claude Code and use one of these prompts:')
            for row in choices:
                if row['flow'] == 'continue':
                    print('  Continue saved work: run make start in a terminal to choose a saved setup or review.')
                else:
                    print('  {}: {}'.format(row['label'], PROMPTS[row['flow']]))
            return 0
        selected = next((r for r in choices if r['flow'] == args.flow), None) if args.flow else choose(
            'What would you like to do?', choices)
        if selected is None:
            if args.flow:
                raise ValueError('that path is not available in this workspace')
            print('No workflow started.')
            return 0
        if selected['flow'] == 'continue':
            if len(saved) == 1:
                work = saved[0]
            elif not interactive:
                print('\nChoose one saved item and paste its prompt into Claude Code:')
                for item in saved:
                    print('\n' + item['label'] + '\n' + item['prompt'])
                return 0
            else:
                work = choose('Which saved work would you like to continue?', saved)
            if work is None:
                print('No workflow started.')
                return 0
            prompt = work['prompt']
        else:
            prompt = PROMPTS[selected['flow']]
        print('\n' + prompt, flush=True)
        if args.print_prompt or not interactive or os.environ.get('CLAUDECODE'):
            print('\nPaste this prompt into your conversation in this project.')
            return 0
        claude = shutil.which('claude')
        if claude is None:
            print('\nClaude Code was not found on PATH. Open this project in Claude Code and paste the prompt above.')
            return 1
        print('\nOpening Claude Code. Continue by answering in the conversation.', flush=True)
        return subprocess.run([claude, prompt], cwd=root).returncode
    except KeyboardInterrupt:
        print('\nStopped.')
        return 130
    except (ValueError, KeyError, OSError) as exc:
        print('start: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
