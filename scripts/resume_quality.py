"""Editorial questions and omission diagnostics derived from approved inputs.

Preparation never evaluates prose. Answers are private application judgments;
none of these functions updates facts, user preferences, or source confidence.
"""
from resume_document import normalized
from select_evidence import view, role_score, canonical, recency
from evidence_rules import linked_ids


def editorial_specs(document, pack):
    atoms = {a['id']: a for a in pack.get('evidence_atoms', [])}
    blocks = document['blocks']
    prose = [b for b in blocks if b['evidence_ids'] or (b['kind'] == 'li')]
    from render import header
    role_index, contact_index, summary_indexes = header([(b['kind'], b['text']) for b in blocks])
    language_blocks = [b for i, b in enumerate(blocks) if b['kind'] in ('li', 'p') and i not in (role_index, contact_index) and not b.get('employment_part')]
    in_experience = False
    for b in blocks:
        if b['kind'] == 'h2': in_experience = False
        if b['kind'] == 'h3': in_experience = True
        if in_experience and b['kind'] == 'p' and not b.get('employment_part') and b not in prose: prose.append(b)
    opening = [blocks[i] for i in summary_indexes]
    summary_section = False
    for b in blocks:
        if b['kind'] == 'h3': break
        if b['kind'] == 'h2':
            summary_section = b['text'].strip().casefold() in ('summary', 'profile', 'professional summary', 'professional profile')
        elif b['kind'] == 'p' and summary_section and b not in opening:
            opening.append(b)
    prose = [b for b in blocks if b in prose or b in opening]
    first_proof = prose[:1]
    specs = []
    def add(key, dimension, relevant, question):
        specs.append({'id': key, 'dimension': dimension, 'block_ids': [b['id'] for b in relevant], 'question': question})
    add('opening', 'opening', (opening + [b for b in prose if b not in opening]) if opening else first_proof or blocks[:1],
        'What distinct professional contribution does the opening establish? If a summary is present, explain what it adds and locate its support in the body; if absent, assess the first substantive evidence. Compare with the role after recording the cold read.')
    add('language', 'language', language_blocks or blocks,
        'Does the wording make actions understandable without generic praise, unnecessary third-person biography or unexplained jargon? Respect explicit voice preferences. Cite representative passages; inspect all prose, not just the excerpt.')
    for b in prose:
        add(b['id'] + ':focus', 'focus', [b],
            'State the principal achievement. Do competing stories, repetition or supporting details obscure it? Length alone is not a verdict.')
        add(b['id'] + ':contribution', 'contribution', [b],
            'Identify personal contribution, relevant context or method, and supported change, output or scope. Is this responsibility-only wording despite stronger available evidence? Do not invent an outcome.')
        if any(atoms.get(a, {}).get('metrics') for a in b['evidence_ids']):
            add(b['id'] + ':metric_value', 'metric_value', [b],
                'What does each visible number establish for this role: adoption, capability, scope, effort, visibility or commercial impact? Explain its value and basis; a large number or financial measure is not inherently better. If source metrics are unused, assess that choice.')
    return specs


def omission_specs(pack, plan, document, profile=None, excluded=()):
    # Only allowlisted, eligible evidence enters this application review packet.
    pool = view(pack, audience='public')['atoms']
    available = {a['id']: a for a in pool}
    excluded = set(excluded)
    used = {aid for b in document['blocks'] for aid in b['evidence_ids']}
    canon = canonical(pack)
    def ordered(ids):
        candidates = [available[i] for i in sorted(ids) if i in available and i not in excluded and i not in used]
        candidates.sort(key=recency, reverse=True)
        candidates.sort(key=lambda a: -role_score(a, profile or {}, canon)[0])
        return [a['id'] for a in candidates[:3]]
    specs = []
    def add(key, kind, subject, ids):
        ids = set(ids)
        support = sorted(ids & used)
        candidates = ordered(ids)
        if candidates: state = 'available_omission'
        elif support: state = 'represented'
        elif ids & excluded: state = 'excluded_by_decision'
        elif ids and not ids & set(available): state = 'unavailable'
        else: state = 'unmapped'
        specs.append({'id': key, 'kind': kind, 'subject': subject, 'support_in_draft': support,
                      'candidate_ids': candidates, 'availability': state,
                      'question': 'Assess whether the draft misses a consequential contribution. Inspect candidate facts and the eligible pool, not just matching terms. Distinguish overlooked evidence, an explicit omission choice, and a real evidence gap. Keep relevant older work. Do not infer missing career experience from missing links.'})
    for index, req in enumerate((profile or {}).get('requirements', [])):
        ids = linked_ids(req)
        if not used & set(ids): add('requirement:' + str(index), 'requirement', req['text'], ids)
    for impression in plan.get('impressions', []):
        if impression.get('basis') != 'gap' and not used & set(impression['evidence_ids']):
            add('impression:' + impression['id'], 'impression', impression['message'], impression['evidence_ids'])
    employment = view(pack, audience='public')['employment']
    if employment:
        def end(role): return '9999' if role.get('end') == 'present' else role.get('end') or role.get('start') or ''
        latest = max(end(r) for r in employment)
        # Include concurrent latest roles. A newly started role may legitimately
        # have little evidence; this is a review question, not a recency quota.
        for role in employment:
            if end(role) == latest:
                ids = [a['id'] for a in pool if a.get('employment_id') == role['employment_id']]
                add('recent:' + role['employment_id'], 'recent_work', role['employer'] + ' | ' + role['title'], ids)
    return specs


def quality_context(plan, pack, document):
    from editorial import read, effective_decisions
    selection = read(plan['selection']['path'])
    brief = read(selection['brief']['path'])
    decisions = effective_decisions(brief)
    excluded = {sid for (kind, sid), action in decisions.items() if kind == 'atom' and action in ('omit', 'reserve')}
    profile = read(selection['role']['path']) if selection.get('role') else None
    pool = view(pack, audience='public')['atoms']
    # Respect explicit person choices in the alternative pool. Private decision
    # reasons and unsafe evidence must not be copied into application guidance.
    return {'editorial': editorial_specs(document, pack),
            'omissions': omission_specs(pack, plan, document, profile, excluded),
            'eligible_alternatives': [a for a in pool if a['id'] not in excluded],
            'limitation': 'Candidates and links are review aids, not proof of role fit or missing experience. Questions for the person are optional and only useful after the available evidence has been inspected.'}


def pending_quality(context):
    return {'editorial': [dict(s, status='pending', reason='', passages=[]) for s in context['editorial']],
            'omissions': [dict(s, disposition='pending', reason='') for s in context['omissions']]}


def quality_errors(quality, context, document, final=True):
    errors = []
    blocks = {b['id']: b for b in document['blocks']}
    for category, keys in (('editorial', ('id', 'dimension', 'block_ids', 'question')),
                           ('omissions', ('id', 'kind', 'subject', 'support_in_draft', 'candidate_ids', 'availability', 'question'))):
        expected = context[category]
        rows = quality.get(category, [])
        if [{k: r.get(k) for k in keys} for r in rows] != expected:
            errors.append('quality ' + category + ' must cover the exact current review questions and alternatives; prepare again')
        for row in rows:
            if category == 'editorial':
                if row['status'] == 'pass':
                    if not row['reason'].strip() or not row['passages']:
                        errors.append(row['id'] + ': editorial assessment needs reasoning and visible passages')
                    for passage in row['passages']:
                        block = blocks.get(passage['block_id'])
                        if (not block or passage['block_id'] not in row['block_ids'] or not passage['text'].strip()
                                or normalized(passage['text']) not in normalized(block['text'])):
                            errors.append(row['id'] + ': editorial passage is not in its reviewed block')
                if final and row['status'] != 'pass': errors.append(row['id'] + ': unresolved editorial quality review')
            else:
                if row['disposition'] != 'pending' and not row['reason'].strip():
                    errors.append(row['id'] + ': omission decision needs a reason')
                if row['disposition'] == 'needs_evidence' and row['availability'] != 'unmapped':
                    errors.append(row['id'] + ': inspect available evidence or existing decisions before requesting new facts')
                if final and row['disposition'] in ('pending', 'revise_selection'):
                    errors.append(row['id'] + ': unresolved omission review')
    return errors


def pending_layout(exports_path):
    from editorial import pin, read
    from export_resume import validate_export_report
    errors = validate_export_report(exports_path)
    if errors: raise ValueError('; '.join(errors))
    report = read(exports_path)
    layout = report['formats']['pdf'].get('layout')
    if not layout: raise ValueError('export lacks page diagnostics; create a new export bundle')
    return {'exports': pin(exports_path), 'status': 'pending', 'observations': '',
            'findings': [dict(f, status='pending', reason='') for f in layout['findings']]}


def layout_errors(review, artifact, plan, final=True):
    from editorial import read, pin_errors
    errors = pin_errors(review['exports'])
    if errors: return errors
    expected = pending_layout(review['exports']['path'])
    report = read(review['exports']['path'])
    if report['artifact'] != artifact or report.get('plan') != plan:
        errors.append('visual review exports must match the exact draft and plan')
    keys = ('id', 'kind', 'block_ids', 'pages', 'message')
    if [{k: r[k] for k in keys} for r in review['findings']] != [{k: r[k] for k in keys} for r in expected['findings']]:
        errors.append('visual review must account for every measured layout finding')
    for row in review['findings']:
        if row['status'] == 'accepted' and not row['reason'].strip():
            errors.append('accepted layout finding needs a reason after inspecting the PDF')
        if final and row['status'] != 'accepted': errors.append('unresolved layout finding: ' + row['id'])
    if review['status'] == 'reviewed' and not review['observations'].strip():
        errors.append('visual review needs actual observations of the final PDF')
    if final and review['status'] != 'reviewed': errors.append('inspect final PDF and record visual observations')
    return errors


def delivery_quality_errors(process, exports_pin):
    review = process.get('quality', {}).get('layout')
    if not review: return ['publishable resume needs a recorded visual review of its exported PDF']
    if review['exports'] != exports_pin: return ['visual review does not match the submitted export bundle']
    return layout_errors(review, process['artifact'], process['plan'])
