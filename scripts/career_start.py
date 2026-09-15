"""Choose career material, gather sources, or start with a conversational account."""
import sys
import startup as flow
from pack_io import pin, pin_errors

FLOW = 'career'
TITLE = 'Career pack'
PURPOSES = ('career_evidence', 'job_context', 'writing_reference', 'defer')
CATEGORIES = {
    'resumes': 'Current and older resumes',
    'linkedin': 'LinkedIn PDF or export',
    'reviews': 'Performance reviews and promotion submissions',
    'public_work': 'Talks, publications, podcasts and courses',
    'projects': 'Project notes, architecture decisions and selected repository files',
    'feedback': 'Awards, recognition and useful feedback',
    'qualifications': 'Education, certifications and training',
}
QUESTIONS = {
    'route': {'label': 'Starting point', 'prompt': 'Use material already here, help gather sources, or start by describing your career?',
              'choices': ['existing', 'gather', 'conversation']},
    'sources': {'label': 'Material to use now', 'prompt': 'Which files should we use now? I can inspect everything here and separate career evidence from job descriptions and writing advice.'},
    'materials': {'label': 'Sources to gather', 'prompt': 'What do you have: resumes, LinkedIn, reviews, public work, project notes, feedback, or qualifications? None, not applicable and later are valid for each.'},
    'career_story': {'label': 'Your starting account', 'prompt': 'Tell me about a role and one contribution you want recorded. Rough notes are enough; we can fill gaps later.'},
    'missing_work': {'label': 'Work documents may miss', 'prompt': 'Anything these sources might overlook: technical decisions, mentoring, incidents, informal leadership, or something you built? You can skip this.'},
    'restrictions': {'label': 'Handling preferences', 'prompt': 'Anything to leave out or handle privately? The first pack stays private by default.'},
}


def create_args(parser):
    pass


def handoff_args(parser):
    pass


def initialize(session, args):
    pass


def validate_answer(question, value):
    if question == 'route':
        if value not in ('existing', 'gather', 'conversation'):
            raise ValueError('choose existing, gather or conversation')
    elif question == 'sources':
        if not isinstance(value, list) or not value:
            raise ValueError('select source entries, or use none/later')
        paths = []
        for row in value:
            flow.object_value(row, ('path', 'purpose', 'note'), ('path', 'purpose'))
            paths.append(str(flow.source_path(row['path'])))
            if row['purpose'] not in PURPOSES:
                raise ValueError('each source needs a purpose: ' + ', '.join(PURPOSES))
            if 'note' in row:
                flow.text_value(row['note'])
        if len(paths) != len(set(paths)):
            raise ValueError('duplicate source choice')
    elif question == 'materials':
        flow.object_value(value, CATEGORIES)
        if not value:
            raise ValueError('record a category or use none/later')
        for row in value.values():
            flow.object_value(row, ('state', 'detail'), ('state',))
            if row['state'] not in flow.STATES:
                raise ValueError('invalid material state')
            if 'detail' in row:
                flow.text_value(row['detail'])
    else:
        flow.text_value(value)


def after_answers(session, changes):
    if 'sources' in changes:
        session['context']['source_pins'] = [
            pin(row['path']) for row in flow.answer(session, 'sources', [])
            if row['purpose'] != 'defer']


def active_questions(session):
    route = flow.answer(session, 'route')
    if not route:
        return ['route']
    first = {'existing': 'sources', 'gather': 'materials', 'conversation': 'career_story'}[route]
    return [first, 'missing_work', 'restrictions']


def answer_text(question, value, session):
    if question == 'route':
        return {'existing': 'Use existing material', 'gather': 'Help me gather sources',
                'conversation': 'Start by describing my career'}[value]
    if question == 'sources':
        labels = {'career_evidence': 'Career evidence', 'job_context': 'Job context only',
                  'writing_reference': 'Writing advice only', 'defer': 'Later'}
        return '\n'.join('{} — {}{}'.format(row['path'], labels[row['purpose']],
                        ': ' + row['note'] if row.get('note') else '') for row in value)
    if question == 'materials':
        return '\n'.join('{}: {}{}'.format(CATEGORIES[key], row['state'].replace('_', ' '),
                        ' — ' + row['detail'] if row.get('detail') else '') for key, row in value.items())
    return str(value)


def next_step(session):
    if session['status'] == 'paused':
        return 'Paused. Source choices and deferrals are saved; resume when you are ready.'
    if session['handoff']:
        if session['handoff']['action'] == 'gather_sources':
            return 'Bring any convenient source into data/sources, then continue this setup. One source is enough.'
        return 'Next, I will prepare a proposed career pack from your chosen material and account. You will review its wording before any career facts are saved as accepted.'
    route = flow.answer(session, 'route')
    if route == 'gather':
        return 'Save a short source checklist. Bring one item now and leave the rest for later.'
    if route == 'conversation':
        return 'Save your account as a source, propose career evidence, then review the wording together.'
    return 'Choose the material to use. Job descriptions and writing advice stay separate from career evidence.'


def handoff(session, args):
    route = flow.answer(session, 'route')
    if not route:
        raise ValueError('choose a starting route before handoff')
    if flow.context().get('pack_issue'):
        raise ValueError('resolve ambiguous pack history before intake')
    rows = flow.answer(session, 'sources', []) if route != 'conversation' else []
    pins = session['context'].get('source_pins', []) if rows else []
    expected = {str(flow.source_path(r['path'])) for r in rows if r['purpose'] != 'defer'}
    if {str(flow.source_path(p['path'])) for p in pins} != expected:
        raise ValueError('source pins do not match choices; save the source answer again')
    for record in pins:
        errors = pin_errors(record)
        if errors:
            raise ValueError('; '.join(errors) + '; review and save the source choices again')
    accounts = []
    for key in ('career_story', 'missing_work'):
        row = session['answers'].get(key, {})
        if key == 'career_story' and route != 'conversation':
            continue
        if row.get('state') == 'answered' and row.get('origin') in ('user', 'saved'):
            accounts.append({'question': key, 'text': row['value'], 'origin': row['origin']})
    sources = [pin(row['path']) for row in rows if row['purpose'] == 'career_evidence']
    if not sources and not accounts and route != 'gather':
        raise ValueError('no career material selected; choose a source, describe a role, or switch to gather')
    return {'action': 'ingest_candidates' if sources or accounts else 'gather_sources',
            'career_sources': sources, 'user_accounts': accounts,
            'context_sources': [dict(pin(row['path']), purpose=row['purpose']) for row in rows
                                if row['purpose'] in ('job_context', 'writing_reference')],
            'deferred_sources': [row['path'] for row in rows if row['purpose'] == 'defer'],
            'materials': session['answers'].get('materials'),
            'restrictions': session['answers'].get('restrictions'),
            'external_safe_default': False}, None


def main(argv=None):
    return flow.run_cli(sys.modules[__name__], argv)


if __name__ == '__main__':
    sys.exit(main())
