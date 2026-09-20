"""Read-only state shared by navigation, summaries and recovery."""
import json
import re
from pathlib import Path

from current_pack import ROOT, resolve
from pack_io import local, pin, read, write_view


def uncertainty(record):
    notes = record.get('notes') or ''
    if record.get('evidence_status') == 'unresolved':
        return 'Unresolved: ' + (notes or 'Confirm the recorded alternatives before asserting a definite value.')
    if re.search(r'\b(?:date|month)\b.*\b(?:unknown|uncertain|unresolved|not recalled|cannot recall)\b', notes, re.I):
        return 'Date uncertainty: ' + notes
    if re.search(r'\b(?:end date|start date|promotion month)\b', notes, re.I):
        return 'Recorded date context: ' + notes
    return ''


def dates(record):
    text = str(record.get('start') or 'Start not recorded') + ' – ' + str(record.get('end') or 'End not recorded')
    return text + (' · ' + uncertainty(record) if uncertainty(record) else '')


def question_summary(pack, root=ROOT):
    from open_questions import career_questions
    rows = career_questions(pack, optional=True, include_closed=True, root=root)
    counts = {s: sum(r.get('state', 'open') == s for r in rows) for s in ('open', 'answered', 'deferred', 'declined', 'superseded')}
    return {'items': rows, **counts,
            'required': sum(r.get('state', 'open') == 'open' and not r.get('optional') for r in rows),
            'optional': sum(r.get('state', 'open') == 'open' and r.get('optional', False) for r in rows)}


def reading_state(current, root=ROOT):
    page = local('outputs/career-record.html', root)
    if not current: return {'path': None, 'state': 'absent'}
    if not page.is_file(): return {'path': None, 'state': 'not_rendered'}
    marker = '<!-- career-pack-sha256: ' + pin(current, root)['sha256'] + ' -->'
    return {'path': str(page.relative_to(root.resolve())),
            'state': 'current' if page.read_text().startswith(marker) else 'stale'}


def history_errors(current, root=ROOT):
    """Fast chain check; legacy recall can still read the known head."""
    seen = set()
    while current:
        path = local(current, root)
        if path in seen:
            return ['Saved career history contains a cycle.']
        seen.add(path)
        previous = read(path, root).get('metadata', {}).get('supersedes')
        if not previous:
            return []
        target = local(previous, root)
        if not target.is_file() or not target.is_relative_to((root / 'data/packs').resolve()):
            return ['Saved career history needs repair: predecessor is missing or outside data/packs: ' + str(previous)]
        current = target
    return []


def summary(root=ROOT):
    from pack_review import session_catalog
    root = Path(root).resolve()
    errors, sessions = [], []
    try:
        path = resolve(root/'data/packs', root)
        pack = read(path, root) if path else {}
        errors.extend(history_errors(path, root))
    except (SystemExit, ValueError, OSError, KeyError) as exc:
        path, pack = None, {}; errors.append(str(exc))
    for row in session_catalog(root):
        if row.get('superseded_by'): continue
        if row.get('error'): errors.append(row['error']); continue
        try:
            # Review helpers operate in the configured workspace. External roots
            # use a subprocess so dependency paths never resolve against this repo.
            if root == ROOT.resolve():
                from pack_review import status
                state = status(row['path'])
            else:
                import os, subprocess, sys
                result = subprocess.run([sys.executable, '-B', str(Path(__file__).with_name('pack_review.py')),
                                         'status', '--session', row['path']],
                                        env={**os.environ, 'CAREER_WORKSPACE': str(root)}, capture_output=True, text=True)
                if result.returncode: raise ValueError(result.stderr.strip())
                state = json.loads(result.stdout)
            sessions.append(dict(row, summary=state['summary'], actionable=bool(state['summary']['pending_items'])))
        except (ValueError, OSError, KeyError) as exc:
            errors.append(row['path'] + ': ' + str(exc))
    try: questions = question_summary(pack, root)
    except (ValueError, OSError, KeyError) as exc:
        questions = {'items': [], 'required': 0, 'optional': 0}; errors.append(str(exc))
    return {'current_pack': pin(path, root) if path else None,
            'state': 'needs_repair' if errors else 'saved' if path else 'new',
            'reading_page': reading_state(path, root), 'questions': questions, 'reviews': sessions,
            'saved': {'roles': len(pack.get('employment', [])), 'achievements': len(pack.get('evidence_atoms', []))},
            'errors': errors,
            'next': 'Repair the reported workspace issue.' if errors else 'Continue your saved review.' if any(s['actionable'] for s in sessions)
                    else 'Your saved career record is ready to view or update.' if path else 'Bring one source or describe your work.'}


def recover(root=ROOT):
    """Expose valid saved proposals even when a model never returns a response."""
    root = Path(root).resolve()
    state = summary(root)
    reviews = []
    for session in state['reviews']:
        try:
            import os, subprocess, sys
            rid = session['review_id']
            page = 'outputs/review-' + rid + '.html'
            proc = subprocess.run([sys.executable, '-B', str(Path(__file__).with_name('pack_review.py')),
                                   'render', '--session', session['path'], '--output', page],
                                  env={**os.environ, 'CAREER_WORKSPACE': str(root)}, capture_output=True, text=True)
            if proc.returncode: raise ValueError(proc.stderr.strip())
            reviews.append({'review': session['path'], 'page': page,
                            'continue': 'Continue my career-pack review named ' + json.dumps(rid) + '.'})
        except (ValueError, OSError) as exc:
            state['errors'].append(str(exc))
    lines = ['# Saved career work', '', state['next'], '',
             'A saved proposal is not an approved career pack. No approval has been inferred.', '']
    for row in reviews:
        lines.extend(['- [Open saved review](' + row['page'].removeprefix('outputs/') + ')', row['continue'], ''])
    if not reviews: lines.append('No valid staged review was recovered. Inspect the retained run diagnostics before retrying.')
    lines.extend('Issue: ' + e for e in state['errors'])
    path = write_view('outputs/career-handoff.md', '\n'.join(lines).rstrip()+'\n', root)
    return {'handoff': str(path.relative_to(root)), 'reviews': reviews, 'errors': state['errors'], 'model_completed': False}
