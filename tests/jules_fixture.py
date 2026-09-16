"""Authored, entirely fictional career and source material for Jules's walkthrough.

Separate from the small editorial personas: this example exercises a career over
time, including deliberately imperfect proposals. It is not an extraction eval.
"""
import hashlib

from editorial_fixture import fingerprint


ROLES = [
    ('EMP_CIVIC', 'Fictional Civic Atlas', 'Software Engineer', '2010-09', '2014-06', None,
     'Software Engineer at Fictional Civic Atlas, September 2010 to June 2014. Built data-import tools with a service-delivery team.'),
    ('EMP_NORTH', 'Fictional North Quay Systems', 'Senior Software Engineer', '2014-07', '2017-12', None,
     'Senior Software Engineer at Fictional North Quay Systems, July 2014 to December 2017. Worked on service operations and shared platform tools.'),
    ('EMP_STAFF', 'Fictional Fieldwork Ltd', 'Staff Engineer', '2018-01', '2022-06', None,
     'Staff Engineer at Fictional Fieldwork Ltd, January 2018 to June 2022. Supported several product teams without line-management responsibility.'),
    ('EMP_CURRENT', 'Fictional Fieldwork Ltd', 'Head of Engineering', '2022-07', 'present', 'EMP_STAFF',
     'Head of Engineering at Fictional Fieldwork Ltd, July 2022 to present. Leads a group of 18 engineers through three engineering managers; partners with product and operations. London.'),
]

STORIES = [
    ('E_IMPORT_VALIDATION', 'Made data imports easier to recover', 'EMP_CIVIC', '2012-04',
     'Import failures were discovered after staff had started processing records.',
     'Make failures visible before processing and leave a recovery path for operators.',
     'Built validation checks and a rejected-record queue with the service-delivery team.',
     'Operators used the checks across 18 recurring data feeds.', ['data engineering', 'service operations']),
    ('E_OPERATIONS_RUNBOOK', 'Handed routine recovery to operations', 'EMP_CIVIC', '2013-09',
     'Routine recovery depended on an engineer remembering undocumented steps.',
     'Help the operations team own routine recovery safely.',
     'Paired with operators to write recovery runbooks and rehearse failure cases.',
     'Operations maintained the runbooks and performed routine recovery; no response-time baseline was recorded.', ['knowledge transfer', 'service operations']),
    ('E_QUEUE_VISIBILITY', 'Made a shared queue visible to service teams', 'EMP_NORTH', '2016-03',
     'Service teams could not distinguish a quiet queue from a stalled consumer.',
     'Expose queue age and ownership without replacing the messaging platform.',
     'Designed a queue-age dashboard and paired with service owners to set alert thresholds.',
     'Five services adopted the dashboard and ownership alerts.', ['observability', 'cross-team collaboration']),
    ('E_INCIDENT_EXERCISES', 'Practised incident decisions across teams', 'EMP_NORTH', '2017-10',
     'Teams had recovery instructions but had not practised making decisions together.',
     'Help service owners and support staff rehearse escalation decisions.',
     'Facilitated four incident exercises with service owners and support staff.',
     'The group clarified escalation owners and recorded gaps in recovery instructions; outage reduction was not measured.', ['incident management', 'facilitation']),
    ('E_STORY_1', 'Created a deployment rehearsal tool', 'EMP_STAFF', '2019-03',
     'Product teams needed to test deployment steps before changing production.',
     'Make deployment practice repeatable without taking delivery ownership from the teams.',
     'Designed the rehearsal format and co-built its runner with engineers.',
     'Two teams adopted rehearsals before deployment.', ['platform engineering', 'cross-team collaboration']),
    ('E_SERVICE_BOUNDARIES', 'Agreed a gradual service separation', 'EMP_STAFF', '2021-02',
     'Product and operations disagreed about replacing a shared service in one release.',
     'Make the migration tradeoffs explicit and agree a sequence the teams could support.',
     'Mapped failure boundaries with both groups and authored a staged separation proposal.',
     'The teams chose a staged separation and retained a rollback path; product teams implemented the changes.', ['software architecture', 'stakeholder communication']),
    ('E_PLATFORM_ADOPTION', 'Chose an adoption plan within team capacity', 'EMP_CURRENT', '2023-05',
     'Four product teams requested different platform improvements from the same small group.',
     'Agree priorities and ownership within the available engineering capacity.',
     'Worked with engineering managers and product leads to compare support burden and migration effort.',
     'The group agreed a two-quarter platform adoption plan and named an owner for each migration; revenue impact was not measured.', ['engineering leadership', 'prioritization']),
    ('E_PRIVATE_REVIEW', 'Led a sensitive supplier review', 'EMP_CURRENT', '2024-11',
     'A supplier arrangement needed a confidential technical review.',
     'Give procurement a technical assessment without disclosing internal contract details.',
     'Coordinated engineering and procurement input and wrote the technical tradeoff assessment.',
     'Procurement used the assessment in its supplier review; commercial terms and the final decision remain private.', ['technical due diligence', 'stakeholder communication']),
]

REHEARSAL = ('In March 2019 I designed a deployment rehearsal format and co-built its runner with engineers. '
             'Two teams adopted rehearsals before deployment.')
COACHING_OLD = ('In February 2025 I hired and coached engineers while introducing peer design reviews. '
                'The engineering group adopted peer design reviews.')
COACHING_REVIEW = ('Jules sponsored the peer design-review pilot and coached three engineering managers. '
                   'Engineers Mara Vale and Theo Reed designed the review format together. '
                   'Hiring was shared with the managers. The engineering group adopted peer design reviews; '
                   'we have not collected feedback about which coaching was most useful.')
QUEUE_NOTE = ('The March 2016 queue-age dashboard and the "service health dashboard" in the resume '
              'are the same project. Jules designed the dashboard and worked with the five service owners '
              'on alert thresholds. This is not a second delivery.')
SPEED_NOTE = ('A draft February 2025 review estimated that design-review queues became 35% shorter. '
              'The original baseline and measurement period were not retained. The percentage must not '
              'be treated as an established outcome.')
TALK = ('Community Systems Forum, June 2021: "Practising deployments before production". '
        'Co-presenters: Jules Elm and Mara Vale, Fictional Fieldwork Ltd. '
        'The programme establishes the shared talk title and speaker listing, not audience size or impact.')
COACHING_ANSWER = ('I sponsored the peer design-review pilot and coached three managers. Mara and Theo '
                   'designed the format, and the managers shared hiring responsibility. Please keep that '
                   'division of work explicit. I still cannot say which part of my coaching helped most.')
STRENGTH_ANSWER = ('Yes: helping teams adopt practical engineering approaches describes my contribution. '
                  'It includes coaching and creating space for engineers to design the solution; it does '
                  'not mean I built everything myself. Keep this interpretation private for now.')
DIRECTION_ANSWER = ('I want technical leadership work that keeps me close to system design and helps '
                    'other engineers develop. I am open to Staff Engineer or engineering leadership '
                    'roles; a larger reporting organization is not my main goal.')
EDUCATION = 'BSc in Computer Science, Fictional Eastbank University, September 2006 to June 2010. No grade supplied.'
NOTE = ('Helped operations and product agree a phased customer-data migration. I wrote the rollback '
        'decision guide; operations ran the rehearsal. Capture this for my next review.')
UPDATE = ('August 2026: product wanted a single customer-data migration while operations wanted a '
          'rehearsed fallback. Jules facilitated the planning discussion and wrote a rollback decision '
          'guide. Operations ran the rehearsal, and product owners agreed to migrate in phases. '
          'The migration had not yet run; no claim about a successful launch, time saved or reduced '
          'incidents is established.')


def source_record(sid, path, text, independent=False, kind='markdown'):
    record = {'source_id': sid, 'source_type': kind, 'path': path, 'independent': independent,
              'sha256': hashlib.sha256(text.encode()).hexdigest(), 'character_count': len(text)}
    if kind == 'person':
        record['retrieved'] = '2026-09-16'
    return record


def ref(sid, text):
    return {'source_id': sid, 'excerpt': text}


def atom(aid, title, role, when, situation, task, action, result, skills, refs, status='self_asserted'):
    return {'id': aid, 'title': title, 'employment_id': role,
            'occurred': {'start': when, 'end': when, 'inferred': False},
            'star': {'situation': situation, 'task': task, 'action': action, 'result': result},
            'metrics': [], 'skills': skills, 'source_refs': refs, 'evidence_status': status,
            'external_safe': False, 'outcome_type': 'output', 'corroborators': [], 'constraints': []}


def strength(sid, text, ids, atoms, limitation):
    return {'id': sid, 'interpretation': text, 'evidence_ids': ids,
            'evidence_fingerprints': {a['id']: fingerprint(a) for a in atoms if a['id'] in ids},
            'status': 'proposed', 'basis': 'recurring_pattern', 'limitations': [limitation],
            'timeframe': 'Dates of the supporting achievements', 'external_safe': False,
            'source_refs': [], 'question_status': 'open', 'review_question': 'Does this describe your contribution?'}


def initial():
    resume = ['# Jules Elm — fictional resume',
              'Entirely fictional source for reviewing a career pack. London. Updated March 2026.',
              '## Employment', *[r[-1] for r in reversed(ROLES)], '## Education', EDUCATION, '## Selected work']
    atoms = []
    for story in STORIES:
        aid, title, role, when, situation, task, action, result, skills = story
        excerpt = REHEARSAL if aid == 'E_STORY_1' else f'{when}: {situation} {task} {action} {result}'
        resume.append(excerpt)
        atoms.append(atom(*story, [ref('SRC_SUBJECT', excerpt)]))
    resume.extend([COACHING_OLD,
                   'March 2016: built a service health dashboard adopted by five services.'])
    source_texts = {
        'data/sources/resume.md': '\n\n'.join(resume) + '\n',
        'data/sources/manager-review-2025.md': '# Fictional manager review — February 2025\n\n' + COACHING_REVIEW + '\n',
        'data/sources/project-notes.md': '# Fictional project notes — retained for context\n\n' + QUEUE_NOTE + '\n\n' + SPEED_NOTE + '\n',
        'data/sources/conference-programme.md': '# Fictional conference programme\n\n' + TALK + '\n',
    }
    records = [source_record(sid, path, source_texts[path], independent) for sid, path, independent in [
        ('SRC_SUBJECT', 'data/sources/resume.md', False),
        ('SRC_MANAGER', 'data/sources/manager-review-2025.md', True),
        ('SRC_NOTES', 'data/sources/project-notes.md', False),
        ('SRC_TALK', 'data/sources/conference-programme.md', True),
    ]]
    atoms.extend([
        atom('E_STORY_2', 'Built an engineering practice', 'EMP_CURRENT', '2025-02',
             'The group was trying a shared approach to design reviews.', 'Help engineers learn from each other.',
             'Personally designed the peer review format, hired the engineers and coached every engineer.',
             'The engineering group adopted peer design reviews.', ['coaching', 'engineering leadership'],
             [ref('SRC_SUBJECT', COACHING_OLD), ref('SRC_MANAGER', COACHING_REVIEW)]),
        atom('E_QUEUE_DUPLICATE', 'Built a service health dashboard', 'EMP_NORTH', '2016-03',
             'Services needed visibility of their queues.', 'Make service health visible.',
             'Built a service health dashboard.', 'Five services adopted it.', ['observability'],
             [ref('SRC_SUBJECT', resume[-1]), ref('SRC_NOTES', QUEUE_NOTE)]),
        atom('E_REVIEW_SPEED', 'Shortened design-review queues by 35%', 'EMP_CURRENT', '2025-02',
             'The group wanted to reduce waiting for design reviews.', 'Understand the effect of the new review practice.',
             'Compared review queues informally.', 'Estimated that review queues became 35% shorter.',
             ['engineering leadership'], [ref('SRC_NOTES', SPEED_NOTE)], status='unresolved'),
        atom('E_TALK', 'Shared deployment practice with peers', 'EMP_STAFF', '2021-06',
             'A community event invited practitioners to discuss deployment practice.',
             'Share the approach with peers.', 'Co-presented with Mara Vale at Community Systems Forum.',
             'The programme lists both speakers and the shared talk; audience impact was not measured.',
             ['public speaking', 'knowledge transfer'], [ref('SRC_TALK', TALK)]),
    ])
    next(a for a in atoms if a['id'] == 'E_STORY_2')['open_questions'] = ['What part of coaching was most useful to the engineers?']
    next(a for a in atoms if a['id'] == 'E_REVIEW_SPEED')['open_questions'] = ['Can the baseline and measurement period be recovered?']
    next(a for a in atoms if a['id'] == 'E_PRIVATE_REVIEW')['constraints'] = ['Private supplier and employer context; do not reuse in external documents.']
    employment = [{'employment_id': rid, 'employer': employer, 'employer_of_record': employer,
                   'title': title, 'start': start, 'end': end, 'parent_employment_id': parent,
                   'location': 'London', 'source_refs': [ref('SRC_SUBJECT', text)],
                   'external_safe': False, 'evidence_status': 'self_asserted', 'corroborators': []}
                  for rid, employer, title, start, end, parent, text in ROLES]
    employment[-1]['scope'] = {'team_size': '18 engineers', 'direct_reports': '3 engineering managers',
                              'source_refs': [ref('SRC_SUBJECT', ROLES[-1][-1])]}
    strengths = [
        strength('S_DISTINCTIVE', 'Helps teams adopt practical engineering approaches', ['E_STORY_1', 'E_STORY_2'], atoms,
                 'Shared ownership matters; the coaching description needs correction.'),
        strength('S_TRANSLATION', 'Makes technical tradeoffs understandable across teams', ['E_SERVICE_BOUNDARIES', 'E_PLATFORM_ADOPTION'], atoms,
                 'These examples show planning and agreement, not measured commercial outcomes.'),
        strength('S_ENTERPRISE', 'Transforms engineering organizations at enterprise scale', ['E_PLATFORM_ADOPTION', 'E_STORY_2'], atoms,
                 'Deliberately overbroad proposed interpretation: the record covers a focused engineering group.'),
    ]
    pack = {'schema_version': '1.4', 'name': 'Jules Elm',
            'purpose': 'Entirely fictional career-review demonstration; never use as personal evidence.',
            'private_profile': {'name': 'Jules Elm', 'location': 'London'},
            'employment': employment, 'source_records': records, 'evidence_atoms': atoms,
            'education': [{'education_id': 'EDU_BSC', 'institution': 'Fictional Eastbank University',
                           'qualification': 'BSc', 'field': 'Computer Science', 'start': '2006-09', 'end': '2010-06',
                           'grade': None, 'evidence_status': 'self_asserted', 'external_safe': False,
                           'source_refs': [ref('SRC_SUBJECT', EDUCATION)]}],
            'publications': [{'publication_id': 'PUB_DEPLOYMENT_TALK', 'title': 'Practising deployments before production',
                              'kind': 'talk', 'venue': 'Community Systems Forum', 'date': '2021-06',
                              'role': 'co_speaker', 'collaborators': ['Mara Vale'], 'employment_id': 'EMP_STAFF',
                              'evidence_id': 'E_TALK', 'source_refs': [ref('SRC_TALK', TALK)],
                              'evidence_status': 'self_asserted', 'external_safe': False, 'url': None}],
            'strengths_profile': strengths, 'positioning_preferences': []}
    return pack, source_texts
