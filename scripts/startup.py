"""Shared private startup sessions; immutable revisions, no career approval."""
import argparse
import copy
from datetime import datetime, timezone
import html
import json
import re
import sys

from current_pack import ROOT, resolve
from pack_io import local, read, pin, pin_errors, write_new, workspace_lock
from schema_tools import load, walk

STATES = ('answered', 'none', 'not_applicable', 'later', 'skipped')
ORIGINS = ('user', 'saved', 'inferred')
FLOW_LABELS = {'career': 'Build my career pack', 'resume': 'Create a resume'}


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', value):
        raise ValueError('ID must contain only letters, numbers, hyphens and underscores')
    return value


def text_value(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('expected nonempty text; use none, later or skipped for an empty answer')


def object_value(value, allowed, required=()):
    if not isinstance(value, dict) or set(value) - set(allowed) or not set(required) <= set(value):
        raise ValueError('invalid answer fields; allowed: ' + ', '.join(allowed))


def string_list(value):
    if not isinstance(value, list):
        raise ValueError('expected a list of strings')
    for item in value:
        text_value(item)
    if len(set(value)) != len(value):
        raise ValueError('duplicate entries')


def source_path(path):
    text_value(path)
    result = local(path)
    if not result.is_relative_to(local('data/sources')):
        raise ValueError('source choices must stay inside data/sources')
    return result


def context():
    inventory = []
    directory = local('data/sources')
    for path in sorted(directory.rglob('*')):
        if (path.is_file() and path.resolve().is_relative_to(directory)
                and not any(p.startswith('.') for p in path.relative_to(directory).parts)):
            inventory.append({'path': str(path.relative_to(ROOT.resolve())),
                              'bytes': path.stat().st_size})
    issue = None
    try:
        current = resolve()
    except SystemExit as exc:
        current, issue = None, str(exc)
    pack = read(current) if current else {}
    return {'inventory': inventory, 'pack': pin(current) if current else None,
            'pack_issue': issue, 'evidence_count': len(pack.get('evidence_atoms', [])),
            'pack_reviews': [str(p.relative_to(ROOT.resolve())) for p in
                             sorted(local('reviews/pack-reviews').glob('*/session.json'))]}


def answer(session, question, default=None):
    row = session['answers'].get(question, {})
    return row['value'] if row.get('state') == 'answered' else default


def validate(session, adapter):
    schema = load('startup-session.schema.json')
    errors = []
    walk(session, schema, schema, '', errors)
    if errors:
        raise ValueError('; '.join(errors))
    if not 1 <= session['revision'] <= 999999 or session['flow'] != adapter.FLOW:
        raise ValueError('invalid session revision or wrong workflow')
    for question, row in session['answers'].items():
        if question not in adapter.QUESTIONS:
            raise ValueError('unknown question: ' + question)
        if row['state'] == 'answered':
            adapter.validate_answer(question, row['value'])
        elif row['value'] is not None:
            raise ValueError('empty/deferred answers must have null value')


def path_for(session):
    return local('reviews/startup/{}/{}/{:06d}.json'.format(
        session['flow'], identifier(session['session_id']), session['revision']))


def latest(path, adapter):
    session = read(path)
    validate(session, adapter)
    expected = path_for(session)
    revisions = sorted(expected.parent.glob('[0-9][0-9][0-9][0-9][0-9][0-9].json'))
    if local(path) != expected or not revisions or expected != revisions[-1]:
        raise ValueError('use the latest saved session revision (run list)')
    return session


def list_sessions(adapter):
    result = []
    for folder in sorted(local('reviews/startup/' + adapter.FLOW).glob('*')):
        paths = sorted(folder.glob('[0-9][0-9][0-9][0-9][0-9][0-9].json'))
        if paths:
            row = latest(paths[-1], adapter)
            result.append({'session': str(paths[-1].relative_to(ROOT.resolve())),
                           'id': row['session_id'], 'status': row['status']})
    return result


def choose(path, adapter):
    if path:
        return local(path)
    choices = [s for s in list_sessions(adapter) if s['status'] != 'handed_off']
    if len(choices) != 1:
        raise ValueError('choose a session from list; {} unfinished starts found'.format(len(choices)))
    return local(choices[0]['session'])


def questions(session, adapter):
    if session['status'] != 'active':
        return []
    return [{'id': q, **adapter.QUESTIONS[q]} for q in adapter.active_questions(session)
            if q not in session['answers']][:5]


def continue_prompt(session):
    name = json.dumps(session['session_id'], ensure_ascii=False)
    if session['status'] == 'handed_off':
        action = 'building my career pack' if session['flow'] == 'career' else 'creating my resume'
        return 'Continue {} from saved setup named {}.'.format(action, name)
    target = 'career pack' if session['flow'] == 'career' else 'resume'
    return 'Continue my {} setup named {}.'.format(target, name)


def saved_summary(session):
    if (session.get('handoff') or {}).get('brief'):
        return 'Your resume brief and setup choices are saved for the next stage.'
    if session['answers']:
        return 'Your setup choices are saved, including answers and anything you left for later.'
    return 'Your setup session is saved. No questions have been answered yet.'


def report(session, adapter):
    return {**session, 'session': str(path_for(session).relative_to(ROOT.resolve())),
            'summary': str(path_for(session).with_suffix('.html').relative_to(ROOT.resolve())),
            'questions': questions(session, adapter), 'next': adapter.next_step(session),
            'saved': saved_summary(session), 'continue_prompt': continue_prompt(session)}


def render(session, adapter):
    esc = lambda v: html.escape(str(v), quote=True)
    rows = []
    for key, row in session['answers'].items():
        content = adapter.answer_text(key, row['value'], session) if row['state'] == 'answered' else row['state'].replace('_', ' ').capitalize()
        origin = {'user': 'Your answer', 'saved': 'Saved preference', 'inferred': 'Assistant suggestion'}[row['origin']]
        rows.append('<section><h2>{}</h2><p class="answer">{}</p><small>{}</small></section>'.format(
            esc(adapter.QUESTIONS[key]['label']), esc(content), esc(origin)))
    remaining = ''.join('<li>{}</li>'.format(esc(q['prompt'])) for q in questions(session, adapter))
    return """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title><style>
body{{margin:0;background:#f4f6f7;color:#172b37;font:17px/1.55 system-ui,sans-serif}}
main{{max-width:760px;margin:auto;padding:28px 20px 60px}}h1{{font-size:2rem;line-height:1.2}}
h2{{font-size:1.1rem;margin:0 0 8px}}section,.next{{background:#fff;padding:18px;margin:16px 0;border:1px solid #d3dce0;border-radius:10px}}
.answer,pre{{white-space:pre-wrap;overflow-wrap:anywhere}}small{{color:#4e626e}}pre{{font-size:.8rem}}li{{margin:12px 0}}
</style></head><body><main><p>Private setup summary · {status}</p><h1>{title}</h1>
<p>These choices guide the work. Career facts and permission to use them externally are reviewed separately.</p>
<div class="next"><h2>What is saved</h2><p>{saved}</p><h2>What happens next</h2><p>{next}</p>
<h2>Continue when you are ready</h2><p>Copy this into your conversation in this project:</p><pre class="answer">{continue_prompt}</pre>
<p>You can also run <code>make start</code> and choose <strong>Continue saved work</strong>.</p></div>{rows}{remaining}
<p>Answer in the conversation. You can say “change my answer”, “later” or “pause”. Use the newest summary after an edit.</p>
<details><summary>Source inventory and saved file references</summary><pre>{details}</pre></details>
<small>Session {sid} · revision {revision}. This is a private snapshot; use the newest link after an edit.</small>
</main></body></html>""".format(
        title=esc(adapter.TITLE), saved=esc(saved_summary(session)), continue_prompt=esc(continue_prompt(session)),
        status={'active': 'In progress', 'paused': 'Paused', 'handed_off': 'Setup complete'}[session['status']],
        next=esc(adapter.next_step(session)), rows=''.join(rows),
        remaining='<h2>Still open</h2><ul>'+remaining+'</ul>' if remaining else '',
        details=esc(json.dumps({'context': session['context'], 'handoff': session['handoff']}, indent=2, ensure_ascii=False)),
        sid=esc(session['session_id']), revision=session['revision'])


def apply_answers(session, changes, adapter):
    if not isinstance(changes, dict):
        raise ValueError('answers must be an object keyed by question ID')
    for key, row in changes.items():
        if (key not in adapter.QUESTIONS or not isinstance(row, dict)
                or set(row) != {'state', 'origin', 'value'}
                or row['state'] not in STATES or row['origin'] not in ORIGINS):
            raise ValueError('each known question requires state, origin and value')
        session['answers'][key] = copy.deepcopy(row)
    validate(session, adapter)
    adapter.after_answers(session, changes)


def persist(session, adapter, artifact=None):
    validate(session, adapter)
    path = path_for(session)
    page = path.with_suffix('.html')
    targets = [path, page] + ([local(artifact[0])] if artifact else [])
    if len(set(targets)) != len(targets) or any(p.exists() for p in targets):
        raise ValueError('destination already exists; use a new ID/revision')
    created = []
    try:
        if artifact:
            created.append(write_new(artifact[0], artifact[1]))
            session['handoff']['brief'] = pin(artifact[0])
        # The JSON session is committed last. A partial write is cleaned up under the lock.
        page.parent.mkdir(parents=True, exist_ok=True)
        with page.open('x') as handle:
            created.append(page)
            handle.write(render(session, adapter))
        created.append(write_new(path, session))
    except BaseException:
        for item in reversed(created):
            item.unlink(missing_ok=True)
        raise
    return report(session, adapter)


def run_cli(adapter, argv=None):
    parser = argparse.ArgumentParser(description=adapter.TITLE + ' guided start (assistant-operated)')
    sub = parser.add_subparsers(dest='command', required=True)
    create = sub.add_parser('create')
    create.add_argument('--id', required=True)
    create.add_argument('--answers', help='JSON answers already supplied in conversation')
    adapter.create_args(create)
    sub.add_parser('list')
    for name in ('show', 'answer', 'back', 'pause', 'resume', 'refresh', 'handoff'):
        item = sub.add_parser(name)
        item.add_argument('--session', help='latest JSON revision; optional with one unfinished start')
        if name == 'answer':
            item.add_argument('--input', required=True)
        if name == 'back':
            item.add_argument('--question', choices=tuple(adapter.QUESTIONS), required=True)
        if name == 'handoff':
            adapter.handoff_args(item)
    args = parser.parse_args(argv)
    try:
        with workspace_lock():
            if args.command == 'list':
                result = list_sessions(adapter)
            elif args.command == 'create':
                identifier(args.id)
                if local('reviews/startup/{}/{}'.format(adapter.FLOW, args.id)).exists():
                    raise ValueError('start already exists; resume it or use a new ID')
                session = {'version': 1, 'flow': adapter.FLOW, 'session_id': args.id,
                           'revision': 1, 'updated_at': datetime.now(timezone.utc).isoformat(),
                           'status': 'active', 'context': context(), 'answers': {},
                           'previous': None, 'handoff': None}
                adapter.initialize(session, args)
                if args.answers:
                    apply_answers(session, read(args.answers), adapter)
                result = persist(session, adapter)
            else:
                path = choose(args.session, adapter)
                session = latest(path, adapter)
                if args.command == 'show':
                    result = report(session, adapter)
                else:
                    if session['status'] == 'handed_off' and args.command not in ('back', 'refresh'):
                        raise ValueError('setup was handed off; use back or refresh for a new revision')
                    if session['status'] == 'paused' and args.command not in ('resume', 'back', 'refresh'):
                        raise ValueError('setup is paused; resume before continuing')
                    session = copy.deepcopy(session)
                    session.update(revision=session['revision']+1, previous=pin(path), handoff=None,
                                   updated_at=datetime.now(timezone.utc).isoformat())
                    artifact = None
                    if args.command == 'answer':
                        apply_answers(session, read(args.input), adapter)
                    elif args.command == 'back':
                        session['answers'].pop(args.question, None)
                        adapter.after_answers(session, {args.question: None})
                        session['status'] = 'active'
                    elif args.command == 'pause':
                        session['status'] = 'paused'
                    elif args.command in ('resume', 'refresh'):
                        session['status'] = 'active'
                        if args.command == 'refresh':
                            session['context'].update(context())
                    else:
                        session['handoff'], artifact = adapter.handoff(session, args)
                        session['status'] = 'handed_off'
                    result = persist(session, adapter, artifact)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
    except (ValueError, KeyError, OSError) as exc:
        print('error: ' + str(exc), file=sys.stderr)
        return 1
