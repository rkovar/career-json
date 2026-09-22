"""Guide resume setup into the existing typed brief and evidence-planning workflow."""
import copy
import sys

import startup as flow
from pack_io import local, read, pin, pin_errors
from schema_tools import load, walk
from resume_workflow import default_application

FLOW = 'resume'
TITLE = flow.FLOW_LABELS['resume']
QUESTIONS = {
    'target': {'label': 'Target', 'prompt': 'Do you have a job description, a type of role in mind, or would you like help choosing a direction?',
               'choices': ['job_description', 'role', 'explore']},
    'focus': {'label': 'Desired impression', 'prompt': 'What should the reader remember about you? Name qualities to highlight, or ask me to suggest strengths from your pack.'},
    'achievements': {'label': 'Examples to feature', 'prompt': 'Any achievements to include or give less space? I can suggest a ranked selection and explain each choice.'},
    'constraints': {'label': 'Application requirements', 'prompt': 'Which market and any employer instructions or length limits? Unknown is fine; PDF, TXT, DOCX and Markdown are included.'},
    'review_mode': {'label': 'How to work together', 'prompt': 'Review the proposed evidence selection before writing, or let me generate and review automatically?',
                    'choices': ['interactive', 'automatic']},
}
CONSTRAINTS = ('market', 'document_type', 'submission_channel', 'contact_mode', 'paper_size',
               'page_limit', 'employer_instructions', 'length', 'audience', 'setting_sources')


def create_args(parser):
    parser.add_argument('--brief', help='reuse a named brief; never guess the latest application')


def handoff_args(parser):
    parser.add_argument('--id', required=True, help='new immutable brief ID')
    parser.add_argument('--application', required=True)
    parser.add_argument('--output-id')
    parser.add_argument('--role', help='profile derived from the chosen job description')


def initialize(session, args):
    if not args.brief:
        return
    from editorial import checked
    brief = checked(args.brief, 'brief')
    if brief['format'] != 'resume':
        raise ValueError('resume setup can reuse resume briefs only')
    session['context']['base_brief'] = pin(args.brief)
    # A brief alone cannot encode a deferred answer or the original JD before a
    # role profile exists. Recover that context from its exact recorded handoff.
    previous = []
    for path in local('reviews/startup/resume').glob('*/*.json'):
        saved = read(path)
        if (saved.get('handoff') or {}).get('brief') == session['context']['base_brief']:
            flow.validate(saved, sys.modules[__name__])
            previous.append(saved)
    if len(previous) > 1:
        raise ValueError('multiple startup handoffs claim this brief; resume a specific session')
    if previous:
        saved = previous[0]
        # Preserve pinned source bytes: reusing a brief must not silently
        # acknowledge changes to its job description.
        session['answers'] = copy.deepcopy(saved['answers'])
        session['context']['job_description'] = copy.deepcopy(saved['context'].get('job_description'))
        session['context']['target_value'] = copy.deepcopy(flow.answer(session, 'target'))
        return
    app = brief.get('application', default_application(audience=brief['audience']))
    constraints = {k: copy.deepcopy(app[k]) for k in CONSTRAINTS if k in app}
    constraints['setting_sources'] = {k: v for k, v in app['setting_sources'].items()
                                     if k in CONSTRAINTS and k != 'setting_sources'}
    constraints.update(length=brief['length'], audience=brief['audience'])
    values = {'focus': {'text': brief['instructions'], 'strength_ids': brief['strength_ids']},
              'achievements': {'include_ids': brief['priority_evidence_ids']},
              'constraints': constraints, 'review_mode': app['review_mode']}
    if brief.get('role_id') or brief.get('role_family'):
        values['target'] = {'mode': 'role', 'description': brief.get('role_family') or brief['role_id'],
                            'role_id': brief.get('role_id'), 'role_family': brief.get('role_family')}
    flow.apply_answers(session, {q: {'state': 'answered', 'value': v, 'origin': 'saved'}
                                for q, v in values.items()}, sys.modules[__name__])


def validate_answer(question, value):
    if question == 'target':
        flow.object_value(value, ('mode', 'description', 'path', 'role_id', 'role_family'), ('mode',))
        if value['mode'] not in ('job_description', 'role', 'explore'):
            raise ValueError('target mode must be job_description, role or explore')
        if value['mode'] == 'job_description':
            flow.source_path(value.get('path'))
        elif value['mode'] == 'role':
            flow.text_value(value.get('description'))
        if 'description' in value:
            flow.text_value(value['description'])
        for key in ('role_id', 'role_family'):
            if value.get(key) is not None:
                spec = load('output-brief.schema.json')['properties'][key]
                errors = []
                walk(value[key], spec, spec, key, errors)
                if errors:
                    raise ValueError('; '.join(errors))
        if value['mode'] != 'job_description' and 'path' in value:
            raise ValueError('source path requires job_description mode')
        if value['mode'] == 'explore' and (value.get('role_id') or value.get('role_family')):
            raise ValueError('save a chosen direction as role mode')
    elif question == 'focus':
        flow.object_value(value, ('text', 'strength_ids', 'suggest'))
        if not value:
            raise ValueError('describe an impression or ask for suggestions')
        if 'text' in value and not isinstance(value['text'], str):
            raise ValueError('focus must be text')
        if 'strength_ids' in value:
            flow.string_list(value['strength_ids'])
        if 'suggest' in value and not isinstance(value['suggest'], bool):
            raise ValueError('suggest must be true or false')
    elif question == 'achievements':
        flow.object_value(value, ('include_ids', 'deemphasize_ids', 'notes'))
        for key in ('include_ids', 'deemphasize_ids'):
            if key in value:
                flow.string_list(value[key])
        if set(value.get('include_ids', [])) & set(value.get('deemphasize_ids', [])):
            raise ValueError('an achievement cannot be both included and de-emphasised')
        if 'notes' in value:
            flow.text_value(value['notes'])
    elif question == 'constraints':
        flow.object_value(value, CONSTRAINTS)
        brief = load('output-brief.schema.json')['properties']
        properties = dict(brief['application']['properties'])
        properties.update({k: brief[k] for k in ('length', 'audience')})
        spec = {'type': 'object', 'properties': properties, 'additionalProperties': False}
        errors = []
        walk(value, spec, spec, 'constraints', errors)
        if errors:
            raise ValueError('; '.join(errors))
        if value.get('page_limit') is not None and value['page_limit'] < 1:
            raise ValueError('page limit must be positive')
        if set(value.get('setting_sources', {})) - (set(value) - {'length', 'audience', 'setting_sources'}):
            raise ValueError('setting provenance must refer to supplied application settings')
    elif value not in ('automatic', 'interactive'):
        raise ValueError('review mode must be automatic or interactive')


def after_answers(session, changes):
    if 'constraints' in changes and changes['constraints'] is not None:
        session['context'].pop('constraints_to_review', None)
    if 'target' in changes:
        target = flow.answer(session, 'target', {})
        previous = session['context'].get('target_value')
        jd = pin(target['path']) if target.get('mode') == 'job_description' else None
        changed = previous is not None and (target != previous or jd != session['context'].get('job_description'))
        constraints = flow.answer(session, 'constraints', {})
        employer_rules = bool(constraints.get('employer_instructions')) or any(
            r['origin'] == 'employer' for r in constraints.get('setting_sources', {}).values())
        if changed and employer_rules and 'constraints' not in changes:
            # Keep the prior values available, but do not apply another
            # employer's requirements to a new target without reassessment.
            session['context']['constraints_to_review'] = session['answers'].pop('constraints')
        session['context']['job_description'] = jd
        session['context']['target_value'] = copy.deepcopy(target)


def active_questions(session):
    if not flow.answer(session, 'target'):
        return ['target']
    return ['focus', 'achievements', 'constraints', 'review_mode']


def answer_text(question, value, session):
    def labels(ids, collection, field):
        record = (session.get('handoff') or {}).get('pack') or session['context'].get('pack')
        pack = read(record['path']) if record and not pin_errors(record) else {}
        names = {row['id']: row.get(field, row['id']) for row in pack.get(collection, [])}
        return ', '.join(names.get(i, i) for i in ids)

    if question == 'target':
        if value['mode'] == 'job_description':
            return 'Job description: ' + value['path']
        return value.get('description', 'Suggest directions from my career evidence.')
    if question == 'focus':
        rows = [value.get('text', '')]
        if value.get('suggest'):
            rows.append('Suggest strengths supported by the pack.')
        if value.get('strength_ids'):
            rows.append('Chosen strengths: ' + labels(value['strength_ids'], 'strengths_profile', 'interpretation'))
        return '\n'.join(r for r in rows if r) or 'Use the available evidence.'
    if question == 'achievements':
        rows = [value.get('notes', '')]
        for key, label in (('include_ids', 'Include'), ('deemphasize_ids', 'Give less space')):
            if value.get(key):
                rows.append(label + ': ' + labels(value[key], 'evidence_atoms', 'title'))
        return '\n'.join(r for r in rows if r) or 'Suggest complementary examples from the pack.'
    if question == 'constraints':
        return '\n'.join('{}: {}'.format(k.replace('_', ' ').capitalize(), v)
                         for k, v in value.items() if k != 'setting_sources') + '\nExports: PDF, TXT, DOCX and Markdown.'
    return 'Review the selection before writing.' if value == 'interactive' else 'Generate and review automatically.'


def next_step(session):
    if session['status'] == 'paused':
        return 'Paused. Your target and preferences are saved.'
    if session['handoff']:
        if session['handoff']['action'] == 'build_pack_then_resume':
            return 'Build and review your career pack, then continue with your saved target and preferences.'
        return 'Rank evidence with reasons and alternatives, prepare a resume plan, and follow the chosen review mode. Deliver PDF, TXT, DOCX and Markdown.'
    if flow.answer(session, 'target', {}).get('mode') == 'explore':
        return 'Suggest a few directions from available career evidence, explain support and gaps, then save the chosen direction before drafting.'
    if session['context'].get('constraints_to_review'):
        return 'The target changed. Review the saved application requirements and keep only those that still apply; the previous answers remain available.'
    if not session['context'].get('pack'):
        return 'Save the resume brief, then build and review a career pack. Your target and preferences will be kept.'
    return 'Create the brief, propose a complementary evidence selection, then plan the resume.'


def handoff(session, args):
    target = flow.answer(session, 'target', {})
    if not target or target['mode'] == 'explore':
        raise ValueError('choose a target before handoff; keep this setup while exploring')
    if session['context'].get('constraints_to_review'):
        raise ValueError('target changed; review the previous employer constraints or explicitly clear them')
    current = flow.context()
    if current['pack_issue']:
        raise ValueError(current['pack_issue'])
    for name in ('base_brief', 'job_description'):
        if session['context'].get(name):
            errors = pin_errors(session['context'][name])
            if errors:
                raise ValueError('; '.join(errors) + '; review the changed input before continuing')
    base = read(session['context']['base_brief']['path']) if session['context'].get('base_brief') else {}
    constraints = flow.answer(session, 'constraints', {})
    audience = constraints.get('audience', 'named_recipient')
    mode = flow.answer(session, 'review_mode', 'automatic')
    app = default_application(constraints.get('market', 'unspecified'), mode, audience)
    origin = session['answers'].get('constraints', {}).get('origin', 'inferred')
    for key, value in constraints.items():
        if key not in ('length', 'audience', 'setting_sources'):
            app[key] = copy.deepcopy(value)
            app['setting_sources'][key] = constraints.get('setting_sources', {}).get(key, {
                'origin': 'user' if origin in ('user', 'saved') else 'inferred',
                'reason': 'Recorded in resume setup ' + session['session_id'] + '.'})
    mode_origin = session['answers'].get('review_mode', {}).get('origin', 'inferred')
    if mode_origin == 'saved' and base.get('application'):
        app['setting_sources']['review_mode'] = copy.deepcopy(base['application']['setting_sources']['review_mode'])
    elif mode_origin == 'user' and flow.answer(session, 'review_mode'):
        app['setting_sources']['review_mode'] = {'origin': 'user', 'reason': 'Explicit setup choice.'}
    role_id = args.role or target.get('role_id')
    if target['mode'] == 'job_description' and current['pack'] and not role_id:
        raise ValueError('prepare a role profile from the saved job description and supply --role')
    if target.get('role_id') and args.role and args.role != target['role_id']:
        raise ValueError('role differs from the saved target; change the target answer first')
    if role_id:
        profile = read('data/roles/' + flow.identifier(role_id) + '.json')
        schema = load('role-profile.schema.json')
        errors = []
        walk(profile, schema, schema, 'role', errors)
        if errors:
            raise ValueError('; '.join(errors))
        if profile['role_id'] != role_id:
            raise ValueError('role profile ID does not match its filename')
        if target['mode'] == 'job_description':
            if not profile.get('source') or local(profile['source']) != flow.source_path(target['path']):
                raise ValueError('role profile must reference the saved job description')
    focus = flow.answer(session, 'focus', {})
    choices = flow.answer(session, 'achievements', {})
    notes = []
    if target.get('description'):
        notes.append('Target direction (preference, not career fact): ' + target['description'])
    if focus.get('text'):
        notes.append('Desired impression / private guidance: ' + focus['text'])
    if focus.get('suggest'):
        notes.append('Suggest strengths from eligible evidence; this request is not a career fact.')
    if choices.get('notes'):
        notes.append('Selection preferences: ' + choices['notes'])
    if choices.get('deemphasize_ids'):
        notes.append('Give less space to: ' + ', '.join(choices['deemphasize_ids']) + '. Explain material tradeoffs during selection.')
    brief = {'brief_id': flow.identifier(args.id), 'output_id': args.output_id or args.id,
             'application_id': flow.identifier(args.application), 'role_id': role_id,
             'role_family': target.get('role_family'), 'format': 'resume', 'audience': audience,
             'length': constraints.get('length', 'concise; allocate space by relevant evidence'),
             'strength_ids': focus.get('strength_ids', []), 'preference_ids': base.get('preference_ids', []),
             'priority_evidence_ids': choices.get('include_ids', []), 'instructions': '\n'.join(notes),
             'external_safe': False, 'created_by': 'system', 'application': app}
    schema = load('output-brief.schema.json')
    errors = []
    walk(brief, schema, schema, '', errors)
    if not errors:
        from editorial import validate_record
        errors, _ = validate_record('brief', brief)
    if errors:
        raise ValueError('; '.join(errors))
    pack = read(current['pack']['path']) if current['pack'] else {}
    if set(choices.get('deemphasize_ids', [])) - {a['id'] for a in pack.get('evidence_atoms', [])}:
        raise ValueError('de-emphasised achievements contain unknown IDs')
    for path in local('data/briefs').glob('*.json'):
        if read(path).get('brief_id') == brief['brief_id']:
            raise ValueError('brief ID already exists; use a new revision ID')
    return {'action': 'prepare_selection' if current['pack'] else 'build_pack_then_resume',
            'pack': current['pack'], 'job_description': session['context'].get('job_description'),
            'review_mode': mode, 'required_exports': ['pdf', 'txt', 'docx', 'md']}, (
                'data/briefs/' + brief['brief_id'] + '.json', brief)


def main(argv=None):
    return flow.run_cli(sys.modules[__name__], argv)


if __name__ == '__main__':
    sys.exit(main())
