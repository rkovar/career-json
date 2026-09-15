#!/usr/bin/env python3
"""Plan a resume, explain selection, and inspect revision losses without changing facts."""
import argparse
import html
import json
import re
import sys
from difflib import SequenceMatcher
from itertools import combinations

from current_pack import ROOT
from editorial import checked, read, pin, pin_errors, write_new, local, validate_record, generation_view, digest

POLICY = 'docs/policies/resume-authoring.json'


def default_application(market='unspecified', review_mode='automatic', audience='named_recipient'):
    values = {'workflow_version': 2, 'market': market,
              'document_type': 'standard_cv' if market == 'UK' else 'standard_resume',
              'submission_channel': 'public' if audience == 'public' else 'unspecified',
              'contact_mode': 'public' if audience == 'public' else 'standard',
              'paper_size': 'Letter' if market == 'US' else 'A4', 'page_limit': None,
              'required_exports': ['pdf', 'txt', 'docx'], 'review_mode': review_mode,
              'employer_instructions': ''}
    values['setting_sources'] = {key: {'origin': 'inferred', 'reason': 'Workflow default; replace with explicit instructions when available.'}
                                for key in values if key != 'workflow_version'}
    return values


def application_errors(brief):
    app = brief.get('application')
    if app is None:
        return []
    errors = []
    if app['page_limit'] is not None and app['page_limit'] < 1:
        errors.append('page_limit must be positive or null')
    if set(app['required_exports']) != {'pdf', 'txt', 'docx'}:
        errors.append('resume delivery requires PDF, TXT, and DOCX')
    fields = set(app) - {'workflow_version', 'setting_sources'}
    if set(app['setting_sources']) != fields:
        errors.append('every application setting needs its origin and reason')
    if brief['audience'] == 'public' and app['contact_mode'] == 'standard':
        errors.append('a public brief cannot request private contact details')
    if app['contact_mode'] == 'public' and brief['audience'] != 'public':
        errors.append('public contact mode requires public audience')
    if app['submission_channel'] == 'public' and brief['audience'] != 'public':
        errors.append('public submission requires public audience')
    return errors


def selected_ids(selection):
    return {row['evidence_id'] for row in selection['recommendations'] if row['disposition'] == 'recommended'}


def overlaps(atoms):
    """Possible duplication, never an automatic decision that two claims are identical."""
    findings = []
    for left, right in combinations(atoms, 2):
        reasons = []
        a, b = left.get('star', {}), right.get('star', {})
        if a.get('result') and a.get('result') == b.get('result'):
            reasons.append('same recorded result; check whether it is a shared outcome')
        if left.get('title') == right.get('title'):
            reasons.append('same achievement title')
        if a.get('action') and b.get('action') and SequenceMatcher(None, a['action'].lower(), b['action'].lower()).ratio() > .86:
            reasons.append('similar recorded contribution')
        if reasons:
            findings.append({'evidence_ids': [left['id'], right['id']], 'reason': '; '.join(reasons),
                             'handling': 'Review whether to combine, distinguish, or omit; do not add shared totals.'})
    return findings


def prepare_plan(selection_path, plan_id):
    selection = checked(selection_path, 'selection')
    view = generation_view(selection_path, for_review=True)
    brief = read(selection['brief']['path'])
    impressions = [{'id': 'I_' + strength['id'], 'message': strength['interpretation'],
                    'basis': 'direct', 'evidence_ids': strength['evidence_ids'],
                    'strength_ids': [strength['id']], 'limitation': '; '.join(strength.get('limitations', []))}
                   for strength in view['editorial']['strengths']]
    requirements = []
    if selection.get('role'):
        from select_evidence import linked_ids
        for req in read(selection['role']['path'])['requirements']:
            support = sorted(set(linked_ids(req, confirmed_only=True)) & selected_ids(selection))
            requirements.append({'requirement': req['text'], 'assessment': 'direct' if support else 'missing',
                                 'evidence_ids': support,
                                 'explanation': 'Review every component of this requirement; a recorded link alone is not proof.' if support else
                                                'No confirmed selected support. Review transferable evidence or report the gap.'})
    for index, impression in enumerate(impressions):
        impression['prominence'] = 'leading' if index == 0 else 'supporting'
    plan = {'plan_id': plan_id, 'selection': pin(selection_path), 'policy': pin(POLICY), 'status': 'proposed',
            'impressions': impressions, 'requirements': requirements,
            'sections': [{'heading': 'Experience', 'purpose': 'Establish contribution, context, and progression.',
                          'evidence_ids': [a['id'] for a in view['atoms']],
                          'space_reason': 'Provisional allocation; curate for distinct contribution, preserving relevant older work.'}],
            'summary': {'include': False, 'reason': 'Decide after drafting experience whether a summary adds understanding.'},
            'overlap_groups': overlaps(view['atoms']),
            'tradeoffs': [{'subject_id': sid, 'reason': 'Not available as a safe complete strength in this selection; review disposition.'}
                         for sid in brief['strength_ids'] if sid not in {s['id'] for s in view['editorial']['strengths']}]}
    plan['privacy_reviews'] = [{'impression_id': i['id'], 'strength_id': s['id'],
                                'disposition': 'pending', 'reason': ''}
                               for i in impressions for s in restricted_strengths(plan)]
    return plan


def restricted_strengths(plan):
    """Private review context only; never expose this through plan_view."""
    pack = read(read(plan['selection']['path'])['pack']['path'])
    return [s for s in pack.get('strengths_profile', [])
            if not s.get('external_safe') or s.get('status') != 'confirmed']


def guidance_fingerprint(plan, brief):
    return digest({'guidance': drafting_guidance(plan, brief),
                   'privacy_reviews': plan.get('privacy_reviews', []),
                   'restricted_strengths': restricted_strengths(plan)})


def privacy_errors(plan):
    restricted = restricted_strengths(plan)
    expected = {(i['id'], s['id']) for i in plan['impressions'] for s in restricted}
    rows = plan.get('privacy_reviews', [])
    actual = [(r['impression_id'], r['strength_id']) for r in rows]
    errors = []
    if len(actual) != len(set(actual)) or set(actual) != expected:
        errors.append('privacy review must compare every impression with every restricted strength; empty strength_ids is not an exemption')
    for row in rows:
        if row['disposition'] == 'pending' or not row['reason'].strip():
            errors.append('privacy comparison needs a reviewed disposition and evidence-based reason')
    from resume_document import normalized
    for impression in plan['impressions']:
        for strength in restricted:
            phrase = normalized(strength['interpretation']).casefold().strip(' .')
            if phrase and phrase in normalized(impression['message']).casefold():
                errors.append('restricted strength interpretation is repeated in drafting guidance: ' + strength['id'])
    return errors


def drafting_guidance(plan, brief):
    """Explicit drafting material; private rationales and tradeoffs stay out."""
    app = brief.get('application', default_application(audience=brief['audience']))
    return {
        'impressions': [{**{k: row[k] for k in ('id', 'message', 'basis', 'evidence_ids', 'strength_ids', 'limitation')},
                         'prominence': row.get('prominence', 'leading' if index == 0 else 'supporting')}
                        for index, row in enumerate(plan['impressions'])],
        'requirements': [{k: row[k] for k in ('requirement', 'assessment', 'evidence_ids', 'explanation')}
                         for row in plan['requirements']],
        'sections': [{'heading': row['heading'], 'evidence_ids': row['evidence_ids']} for row in plan['sections']],
        'summary': {'include': plan['summary']['include']},
        'employer_instructions': app['employer_instructions'],
        'submission_channel': app['submission_channel'],
    }


def plan_errors(plan, ready=False):
    from schema_tools import load, walk
    schema = load('resume-plan.schema.json')
    errors = []
    walk(plan, schema, schema, '', errors)
    if errors:
        return errors
    if ready and plan['status'] != 'ready':
        errors.append('resume plan is proposed; curate it and save a ready revision before generation')
    for item in [plan['selection'], plan['policy']] + ([plan['supersedes']] if plan.get('supersedes') else []):
        errors.extend(pin_errors(item))
    if plan['policy']['path'] != POLICY:
        errors.append('plan must pin the current authoring policy')
    if errors:
        return errors
    try:
        selection = checked(plan['selection']['path'], 'selection')
        _, stale = validate_record('selection', selection)
        errors.extend(stale)
        view = generation_view(plan['selection']['path'], for_review=plan['status'] != 'ready')
        brief = read(selection['brief']['path'])
        if plan['status'] == 'ready':
            errors.extend(privacy_errors(plan))
        if plan['status'] == 'ready' and plan.get('drafting_review_sha256') != guidance_fingerprint(plan, brief):
            errors.append('ready plan needs a current drafting guidance review; inspect guidance and record its drafting_review_sha256')
        safe = {s['id']: set(s['evidence_ids']) for s in view['editorial']['strengths']}
        chosen = selected_ids(selection)
        if plan['status'] == 'ready' and not plan['impressions']:
            errors.append('a ready plan needs at least one supported impression or explicit gap')
        if len({r['id'] for r in plan['impressions']}) != len(plan['impressions']):
            errors.append('duplicate impression id')
        accounted = set()
        for row in plan['impressions']:
            if not set(row['evidence_ids']) <= chosen:
                errors.append('impression support must be selected eligible evidence')
            if row['basis'] == 'gap':
                if row['evidence_ids'] or not row['limitation']:
                    errors.append('gaps need a limitation and cannot claim evidence support')
            elif not row['evidence_ids']:
                errors.append('direct and transferable impressions need evidence')
            if row['basis'] == 'transferable' and not row['limitation']:
                errors.append('transferable impressions must explain their limitation')
            for sid in row['strength_ids']:
                accounted.add(sid)
                if sid not in brief['strength_ids']:
                    errors.append('plan strength is not intended by the brief')
                if row['basis'] != 'gap' and (sid not in safe or not safe[sid] <= set(row['evidence_ids'])):
                    errors.append('strength impression needs its complete safe support')
        accounted.update(t['subject_id'] for t in plan['tradeoffs'])
        if not set(brief['strength_ids']) <= accounted:
            errors.append('account for every intended strength through an impression or tradeoff')
        assigned = set()
        for section in plan['sections']:
            assigned.update(section['evidence_ids'])
        if assigned != chosen:
            errors.append('sections must allocate exactly the selected evidence; revise selection to omit evidence')
        if selection.get('role'):
            expected = [r['text'] for r in read(selection['role']['path'])['requirements']]
            actual = [r['requirement'] for r in plan['requirements']]
            if sorted(expected) != sorted(actual):
                errors.append('plan must assess every role requirement exactly once')
        elif plan['requirements']:
            errors.append('save a role profile before adding requirement assessments')
        for row in plan['requirements']:
            if not set(row['evidence_ids']) <= chosen:
                errors.append('requirement support is outside selected evidence')
            if row['assessment'] in ('direct', 'transferable') and not row['evidence_ids']:
                errors.append('supported requirement assessment needs evidence')
            if row['assessment'] in ('missing', 'withheld') and row['evidence_ids']:
                errors.append('missing or withheld requirements cannot claim selected support')
        for row in plan['overlap_groups']:
            if len(row['evidence_ids']) < 2 or not set(row['evidence_ids']) <= set(selection['candidate_ids']):
                errors.append('overlap group must name at least two selection candidates')
    except (ValueError, KeyError, OSError) as exc:
        errors.append(str(exc))
    return errors


def checked_plan(path, ready=True):
    plan = read(path)
    errors = plan_errors(plan, ready)
    if errors:
        raise ValueError('; '.join(errors))
    return plan


def plan_view(path):
    """Only the exact reviewed drafting guidance enters the generation context."""
    plan = checked_plan(path)
    view = generation_view(plan['selection']['path'])
    brief = read(read(plan['selection']['path'])['brief']['path'])
    view['resume_plan'] = {'plan_id': plan['plan_id'], **drafting_guidance(plan, brief)}
    app = brief.get('application', default_application(audience=brief['audience']))
    view['resume_plan']['format'] = {k: app[k] for k in ('market', 'document_type', 'contact_mode', 'paper_size', 'page_limit', 'required_exports')}
    from resume_employment import employment_groups
    view['resume_plan']['employment_groups'] = employment_groups(view['employment'])
    if app['contact_mode'] == 'anonymous':
        # Contact/name suppression happens before drafting; employer-specific
        # anonymisation of schools or organizations still requires editorial review.
        view['name'] = 'Applicant'
        view['contact'] = {}
    return view


def review_page(plan_path):
    plan = checked_plan(plan_path, ready=False)
    selection = read(plan['selection']['path'])
    pack = read(selection['pack']['path'])
    atoms = {a['id']: a for a in pack['evidence_atoms']}
    e = html.escape
    items = []
    for r in selection['recommendations']:
        a = atoms[r['evidence_id']]
        items.append('<article><h3>' + e(a['title']) + '</h3><p><strong>' + e(r['disposition']) + '</strong></p>' +
                     ''.join('<p><b>' + label + ':</b> ' + e(value) + '</p>' for label, value in
                             [('Contribution', a['star'].get('action') or ''), ('Result or scope', a['star'].get('result') or 'Not recorded'),
                              ('Why include or omit', r['reason']), ('What it adds', r['contribution']),
                              ('Limits', '; '.join(r['limitations'])), ('Replaces', ', '.join(r['replaces']))]) + '</article>')
    impressions = ''.join('<li>' + e(r['message']) + ' (' + e(r['basis']) + ') ' + e(r['limitation']) + '</li>' for r in plan['impressions'])
    gaps = ''.join('<li>' + e(r['requirement'] + ': ' + r['assessment'] + '. ' + r['explanation']) + '</li>' for r in plan['requirements'])
    tradeoffs = ''.join('<li>' + e(t['subject_id'] + ': ' + t['reason']) + '</li>' for t in plan['tradeoffs'])
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><title>Resume choices — private review</title>'
            '<style>body{font:17px/1.6 system-ui;max-width:850px;margin:40px auto;padding:20px}article{border-top:1px solid #aaa;padding:12px 0}</style>'
            '<h1>Your resume choices</h1><p>Private review. Tell the assistant which examples to keep, replace, or correct. '
            'Choices affect this application unless you explicitly choose a wider scope. This page does not save approvals.</p>'
            '<h2>What the reader should understand</h2><ul>' + impressions + '</ul><h2>Requirements and gaps</h2><ul>' + gaps +
            '</ul><h2>Tradeoffs</h2><ul>' + tradeoffs + '</ul><h2>Examples and alternatives</h2>' + ''.join(items) + '</html>')


def revision_findings(before, after, pack):
    from resume_document import document_from_markdown
    old, new = document_from_markdown(before), document_from_markdown(after)
    findings = []
    old_context = [(b['kind'], b['text']) for b in old['blocks'] if not b['evidence_ids']]
    new_context = [(b['kind'], b['text']) for b in new['blocks'] if not b['evidence_ids']]
    if old_context != new_context:
        findings.append({'kind': 'context_changed', 'before': old_context, 'after': new_context,
                         'message': 'Review changes to headings, contact, chronology and uncited role scope against approved records.'})
    new_ids = {aid for b in new['blocks'] for aid in b['evidence_ids']}
    old_ids = {aid for b in old['blocks'] for aid in b['evidence_ids']}
    for aid in sorted(old_ids - new_ids):
        findings.append({'kind': 'evidence_removed', 'evidence_ids': [aid], 'message': 'Evidence removed; check intended strengths and save an omission tradeoff.'})
    qualifiers = re.compile(r'\b(co-designed|co-led|contributed|supported|assisted|prototype|pilot|approximately|jointly|quarterly|weekly)\b', re.I)
    for block in old['blocks']:
        support = set(block['evidence_ids'])
        if not support:
            continue
        if any(b['text'] == block['text'] and set(b['evidence_ids']) == support for b in new['blocks']):
            continue
        replacements = [b['text'] for b in new['blocks'] if support & set(b['evidence_ids'])]
        if replacements and ' '.join(replacements) != block['text']:
            removed = [q for q in qualifiers.findall(block['text']) if q.lower() not in ' '.join(replacements).lower()]
            findings.append({'kind': 'claim_rewritten', 'evidence_ids': sorted(support), 'before': block['text'],
                             'after': replacements, 'removed_qualifiers': removed,
                             'message': 'Review meaning, ownership, method, timeframe and scope; wording comparison cannot establish entailment.'})
    for s in pack.get('strengths_profile', []):
        support = set(s['evidence_ids'])
        if support & old_ids and not support & new_ids:
            findings.append({'kind': 'strength_support_removed', 'strength_id': s['id'], 'message': 'All previously cited support for this strength disappeared.'})
    return findings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    pins = sub.add_parser('pin', help='get an exact path/hash reference for supersedes or provenance')
    pins.add_argument('--path', required=True)
    prepare = sub.add_parser('prepare')
    prepare.add_argument('--selection', required=True); prepare.add_argument('--id', required=True); prepare.add_argument('--output', required=True)
    save = sub.add_parser('save'); save.add_argument('--input', required=True); save.add_argument('--output', required=True)
    for name in ('view', 'review', 'check', 'guidance'):
        p = sub.add_parser(name); p.add_argument('--plan', required=True)
        if name == 'review': p.add_argument('--output', required=True)
    diff = sub.add_parser('compare'); diff.add_argument('--before', required=True); diff.add_argument('--after', required=True); diff.add_argument('--plan', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'pin':
            print(json.dumps(pin(args.path), indent=2))
        elif args.command in ('prepare', 'save'):
            plan = prepare_plan(args.selection, args.id) if args.command == 'prepare' else checked_plan(args.input, ready=False)
            errors = plan_errors(plan)
            if errors: raise ValueError('; '.join(errors))
            if local(args.output).parent != local('data/plans'):
                raise ValueError('resume plans must be saved directly in data/plans')
            for previous in local('data/plans').glob('*.json'):
                if read(previous)['plan_id'] == plan['plan_id']:
                    raise ValueError('plan_id already exists; use a new ID and supersedes')
            print(write_new(args.output, plan))
        elif args.command == 'view':
            print(json.dumps(plan_view(args.plan), indent=2))
        elif args.command == 'guidance':
            # This is a private review preview, not a generation view or approval.
            plan = read(args.plan)
            proposal = dict(plan, status='proposed')
            errors = plan_errors(proposal)
            if errors: raise ValueError('; '.join(errors))
            brief = read(read(plan['selection']['path'])['brief']['path'])
            guidance = drafting_guidance(plan, brief)
            print(json.dumps({'private_review_preview': guidance,
                              'restricted_strengths_for_private_comparison': restricted_strengths(plan),
                              'privacy_reviews': plan.get('privacy_reviews', []),
                              'drafting_review_sha256': guidance_fingerprint(plan, brief)}, indent=2))
        elif args.command == 'review':
            target = local(args.output)
            if not target.is_relative_to(local('reviews')): raise ValueError('private review pages belong under reviews/')
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('x', encoding='utf-8') as handle: handle.write(review_page(args.plan))
            print(target)
        elif args.command == 'check':
            checked_plan(args.plan); print('resume plan is ready and inputs are current')
        else:
            plan = checked_plan(args.plan)
            selection = read(plan['selection']['path'])
            result = revision_findings(local(args.before).read_text(), local(args.after).read_text(), read(selection['pack']['path']))
            print(json.dumps({'findings': result, 'semantic_review_required': True}, indent=2))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print('error: ' + str(exc), file=sys.stderr); return 1


if __name__ == '__main__':
    sys.exit(main())
