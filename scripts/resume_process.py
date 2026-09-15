#!/usr/bin/env python3
"""Private, exact-draft editorial checks and a record-derived continuation handoff.

No command edits a career pack, plan, draft, export or existing review. Preparing
a checklist is not reviewing it. Semantic judgments remain explicit judgments.
"""
import argparse
import json
from pathlib import Path
from urllib.parse import quote

from editorial import read, local, pin, pin_errors, write_new
from resume_document import document_from_markdown, normalized
from resume_workflow import checked_plan, revision_findings, selected_ids
from resume_quality import quality_context, pending_quality, quality_errors, pending_layout, layout_errors


def inputs(artifact, plan_path):
    plan = checked_plan(plan_path)
    selection = read(plan['selection']['path'])
    pack = read(selection['pack']['path'])
    document = document_from_markdown(local(artifact).read_text())
    ids = {i for b in document['blocks'] for i in b['evidence_ids']}
    if not ids <= selected_ids(selection):
        raise ValueError('process review cites evidence outside the selected plan')
    return plan, pack, document


def required_checks(document, pack):
    atoms = {a['id']: a for a in pack['evidence_atoms']}
    checks = []
    for block in document['blocks']:
        specs = []
        if block['evidence_ids']:
            specs += [('ownership', 'Identify the contribution and its object; preserve collaborators, metric basis and limits.'),
                      ('chronology', 'Compare each event timeframe and employment link with the actual heading, not the employer-wide tenure.')]
        elif block['kind'] in ('h2', 'h3', 'h4') or block['kind'] == 'p':
            specs += [('chronology', 'Check dates, role scope and any span claims against approved employment; do not invent a gap or a transition reason.')]
        for kind, source in specs:
            checks.append({'id': block['id'] + ':' + kind, 'block_id': block['id'], 'kind': kind,
                           'evidence_ids': block['evidence_ids'], 'source': source})
        for aid in block['evidence_ids']:
            for index, constraint in enumerate(atoms[aid].get('constraints', [])):
                checks.append({'id': f"{block['id']}:{aid}:constraint:{index}", 'block_id': block['id'],
                               'kind': 'constraint', 'evidence_ids': [aid], 'source': constraint})
    return checks


def review_packet(artifact, plan_path):
    """Private inspection aid, including measured placement and safe sources."""
    from resume_workflow import plan_view
    plan, pack, document = inputs(artifact, plan_path)
    view = plan_view(plan_path)
    offset = 0
    for block in document['blocks']:
        block['word_offset'] = offset
        block['word_count'] = len(block['text'].split())
        offset += block['word_count']
    return {'artifact': pin(artifact), 'plan': pin(plan_path), 'blocks': document['blocks'],
            'selected_evidence': view['atoms'], 'employment': view['employment'],
            'employment_groups': view['resume_plan']['employment_groups'],
            'required_checks': required_checks(document, pack),
            'chronology_findings': chronology_errors(document, pack),
            'quality': quality_context(plan, pack, document),
            'limitation': 'Placement counts are diagnostics. Read the exact claims and sources; this packet does not approve them.'}


from resume_employment import chronology_errors, date_bounds


def feedback_findings(ref):
    """Read recorded work lists; never reinterpret a verdict as hiring evidence."""
    from validate_records import kind_of, load, walk
    errors = pin_errors(ref)
    if errors:
        raise ValueError('; '.join(errors))
    kind, schema_name = kind_of(local(ref['path']))
    if kind not in ('screen', 'evaluation', 'representation'):
        raise ValueError('feedback must be a screen, evaluation or representation record')
    review = read(ref['path']); schema = load(schema_name)
    walk(review, schema, schema, '', errors)
    if errors or not review.get('run', {}).get('artifact_sha256'):
        raise ValueError('feedback needs a valid review shape and exact artifact hash: ' + '; '.join(errors))
    findings = []
    if kind == 'screen':
        for field, category in [('fix_in_document', 'editing'), ('needs_new_evidence', 'new_evidence')]:
            for index, message in enumerate(review[field]):
                findings.append({'source_key': f"{ref['sha256']}:{field}:{index}", 'category': category, 'description': message,
                                 'disposition': 'open', 'reason': 'Imported from the reviewer; inspect and resolve or explicitly defer.'})
    else:
        for index, finding in enumerate(review['findings']):
            if finding['severity'] == 'info':
                continue
            findings.append({'source_key': f"{ref['sha256']}:findings:{index}", 'category': 'editing',
                             'description': finding['message'], 'disposition': 'open', 'reason': finding['remediation']})
    return review['run']['artifact_sha256'], findings


def prepare(artifact, plan_path, previous=None, compression_requested=False, target='', feedback=()):
    plan, pack, document = inputs(artifact, plan_path)
    record = {'process_version': 2,
              'quality': pending_quality(quality_context(plan, pack, document)), 'artifact': pin(artifact), 'plan': pin(plan_path),
              'checks': [dict(c, status='pending', reason='', artifact_excerpt='') for c in required_checks(document, pack)],
              'cold_read': {'context': 'shared', 'impressions': []},
              'prominence': [{'impression_id': i['id'], 'block_ids': [], 'observed': 'missing',
                              'reader_impression_indexes': [], 'status': 'pending', 'reason': ''} for i in plan['impressions']],
              'compression': {'requested': compression_requested, 'target': target,
                              'status': 'pending' if compression_requested else 'not_requested', 'assessment': '', 'meaning_review': []},
              'revision': {'limit': 2, 'budget_origin': 'default', 'budget_reason': 'Default of two editorial revision cycles.',
                           'stop_reason': 'in_progress', 'findings': []}}
    if previous:
        old = read(previous)
        # Keep outstanding findings visible; none becomes resolved just because
        # a new draft was generated. All exact-text checks restart as pending.
        from schema_tools import load, walk
        schema = load('resume-process.schema.json'); errors = []
        walk(old, schema, schema, '', errors)
        if not errors:
            errors.extend(pin_errors(old['artifact']))
            errors.extend(pin_errors(old['plan']))
        if errors:
            raise ValueError('; '.join(errors))
        record['supersedes'] = pin(previous)
        record['review_sources'] = list(old.get('review_sources', []))
        record['revision'] = dict(old['revision'], stop_reason='in_progress', findings=list(old['revision']['findings']))
        if old['artifact']['sha256'] != record['artifact']['sha256']:
            changes = revision_findings(local(old['artifact']['path']).read_text(), local(artifact).read_text(), pack)
            for index, change in enumerate(changes):
                record['revision']['findings'].append({'category': 'editing',
                    'description': f"Revision {old['artifact']['sha256'][:12]} change {index + 1}: " + change['message'],
                    'disposition': 'open', 'reason': 'Inspect the before/after comparison; a citation alone does not prove preserved meaning.'})
        if old['compression']['requested']:
            record['compression'].update(requested=True, status='pending', target=old['compression']['target'])
    refs = record.setdefault('review_sources', [])
    # Automatically carry the previous draft's screen when it exists. Explicit
    # --feedback supports a same-draft screen or other review record as well.
    feedback = list(feedback)
    if previous:
        prior = local(old['artifact']['path'])
        screen = prior.with_name(prior.stem + '-screen.json')
        if screen.exists():
            feedback.append(screen)
    for path in feedback:
        ref = pin(path)
        if ref not in refs:
            _, findings = feedback_findings(ref)
            refs.append(ref); record['revision']['findings'].extend(findings)
    return record


def revision_count(record):
    seen, count, child = set(), 0, record
    while child.get('supersedes'):
        ref = child['supersedes']
        path = str(local(ref['path']))
        if path in seen:
            raise ValueError('cycle in process history')
        seen.add(path)
        errors = pin_errors(ref)
        if errors:
            raise ValueError('; '.join(errors))
        parent = read(ref['path'])
        from schema_tools import load, walk
        schema = load('resume-process.schema.json'); shape = []
        walk(parent, schema, schema, '', shape)
        if shape:
            raise ValueError('invalid process history: ' + '; '.join(shape))
        errors = pin_errors(parent['artifact'])
        if errors:
            raise ValueError('retain immutable prior draft snapshots: ' + '; '.join(errors))
        if child['artifact']['sha256'] != parent['artifact']['sha256']:
            count += 1
        if child['revision']['limit'] != parent['revision']['limit'] and child['revision']['budget_origin'] != 'user':
            raise ValueError('revision budget changes require an explicit user instruction')
        child = parent
    return count


def compression_report(record, pack):
    comp = record['compression']
    before, after = (local(comp[k]['path']).read_text() for k in ('baseline', 'candidate'))
    old, new = document_from_markdown(before), document_from_markdown(after)
    def count(doc):
        return sum(len(b['text'].split()) for b in doc['blocks'])
    return {'before_words': count(old), 'after_words': count(new),
            'findings': revision_findings(before, after, pack),
            'limit': 'Word counts and citation differences do not prove meaning preservation or PDF page count.'}


def process_errors(record, final=True):
    from schema_tools import load, walk
    schema = load('resume-process.schema.json'); errors = []
    walk(record, schema, schema, '', errors)
    if errors:
        return errors
    for key in ('artifact', 'plan'):
        errors.extend(pin_errors(record[key]))
    if errors:
        return errors
    try:
        plan, pack, document = inputs(record['artifact']['path'], record['plan']['path'])
        if record['process_version'] < 2:
            if final: errors.append('legacy process lacks editorial and omission review; prepare a new version')
        elif 'quality' not in record:
            errors.append('process version 2 requires editorial and omission review')
        else:
            errors.extend(quality_errors(record['quality'], quality_context(plan, pack, document), document, final))
        if record.get('quality', {}).get('layout'):
            errors.extend(layout_errors(record['quality']['layout'], record['artifact'], record['plan'], final))
        expected = required_checks(document, pack)
        keys = ('id', 'block_id', 'kind', 'evidence_ids', 'source')
        if [{k: c[k] for k in keys} for c in record['checks']] != expected:
            errors.append('checklist must cover every claim, heading and source constraint exactly; prepare it again')
        blocks = {b['id']: b for b in document['blocks']}
        for row in record['checks']:
            if row['status'] == 'pass':
                if not row['reason'].strip() or not row['artifact_excerpt'].strip():
                    errors.append(row['id'] + ': passed review needs a reason and exact visible excerpt')
                elif normalized(row['artifact_excerpt']) not in normalized(blocks.get(row['block_id'], {}).get('text', '')):
                    errors.append(row['id'] + ': review excerpt is not in its own block')
            if final and row['status'] != 'pass':
                errors.append(row['id'] + ': unresolved ' + row['kind'] + ' review')
        errors.extend(chronology_errors(document, pack) if final else [])
        intended = {i['id']: (i, n) for n, i in enumerate(plan['impressions'])}
        rows = record['prominence']
        if len(rows) != len(intended) or {r['impression_id'] for r in rows} != set(intended):
            errors.append('prominence review must cover every planned impression exactly once')
        for row in rows:
            if not set(row['block_ids']) <= set(blocks):
                errors.append('prominence review refers to a missing block')
            indexes = row['reader_impression_indexes']
            if any(i < 0 or i >= len(record['cold_read']['impressions']) for i in indexes):
                errors.append('prominence review cites a missing reader observation')
            if row['impression_id'] not in intended:
                continue
            impression, position = intended[row['impression_id']]
            target = impression.get('prominence', 'leading' if position == 0 else 'supporting')
            if row['status'] == 'pass' and impression['basis'] != 'gap':
                if not row['block_ids'] or not row['reason'].strip() or row['observed'] == 'missing':
                    errors.append('represented impression needs located proof and a prominence explanation')
                support = {aid for bid in row['block_ids'] if bid in blocks for aid in blocks[bid]['evidence_ids']}
                if not support & set(impression['evidence_ids']):
                    errors.append('prominence locations need the planned evidence')
                if target == 'leading' and (row['observed'] != 'leading' or not indexes):
                    errors.append('a leading impression must emerge in reader observations; presence alone is insufficient')
            if final and row['status'] != 'pass':
                errors.append('unresolved prominence review: ' + row['impression_id'])
        if final and not record['cold_read']['impressions']:
            errors.append('record reader observations before comparing them with intended impressions; label shared context honestly')
        comp = record['compression']
        if comp['requested'] and (not comp['target'].strip() or (final and comp['status'] != 'attempted')):
            errors.append('requested shortening needs a target and an actual compression attempt before stopping')
        if not comp['requested'] and comp['status'] != 'not_requested':
            errors.append('compression status contradicts requested flag')
        if comp['status'] == 'attempted':
            if not comp.get('baseline') or not comp.get('candidate'):
                errors.append('compression attempt needs exact baseline and candidate snapshots')
            else:
                for key in ('baseline', 'candidate'):
                    errors.extend(pin_errors(comp[key]))
                if comp['baseline']['sha256'] == comp['candidate']['sha256']:
                    errors.append('a no-op is not a compression attempt')
                if comp['candidate'] != record['artifact']:
                    errors.append('compression candidate must be this reviewed draft; keep rejected attempts as separate process records')
            dimensions = ['ownership', 'context', 'method', 'timeframe', 'scope', 'strengths']
            if sorted(r['dimension'] for r in comp['meaning_review']) != sorted(dimensions):
                errors.append('compression needs a semantic review of all six preservation dimensions')
            if not comp['assessment'].strip():
                errors.append('compression needs a measured assessment; do not assert that deletion is the only option')
            if final and any(r['status'] != 'pass' for r in comp['meaning_review']):
                errors.append('compression has unresolved meaning losses')
        rev = record['revision']; used = revision_count(record)
        hashes = {record['artifact']['sha256']}; ancestor = record
        while ancestor.get('supersedes'):
            ancestor = read(ancestor['supersedes']['path'])
            hashes.add(ancestor['artifact']['sha256'])
        required_feedback = {}
        for ref in record.get('review_sources', []):
            artifact_hash, findings = feedback_findings(ref)
            if artifact_hash not in hashes:
                errors.append('feedback belongs to a draft outside this revision chain')
            required_feedback.update({f['source_key']: f['description'] for f in findings})
        observed_feedback = [f for f in rev['findings'] if f.get('source_key')]
        if (len(observed_feedback) != len(required_feedback) or
                {f['source_key']: f['description'] for f in observed_feedback} != required_feedback):
            errors.append('every actionable imported review finding must remain in the ledger with its exact source key and description')
        if record.get('supersedes'):
            parent = read(record['supersedes']['path'])
            if any(ref not in record.get('review_sources', []) for ref in parent.get('review_sources', [])):
                errors.append('review sources cannot disappear from revision history')
            carried = {f.get('source_key') or f['description'] for f in rev['findings']}
            for finding in parent['revision']['findings']:
                if finding['disposition'] != 'resolved' and (finding.get('source_key') or finding['description']) not in carried:
                    errors.append('unresolved findings cannot disappear from revision history; resolve or explicitly defer them')
        if rev['limit'] < 0 or (rev['budget_origin'] == 'default' and rev['limit'] != 2):
            errors.append('default budget is two cycles; record explicit user instructions for a different budget')
        if used > rev['limit']:
            errors.append('recorded revisions exceed the budget')
        if rev['stop_reason'] == 'budget_exhausted' and used < rev['limit']:
            errors.append('cannot claim exhausted budget while editorial cycles remain')
        outstanding = [f for f in rev['findings'] if f['disposition'] != 'resolved']
        if rev['stop_reason'] == 'complete' and outstanding:
            errors.append('complete is inconsistent with unresolved findings')
        if rev['stop_reason'] == 'needs_user' and not any(f['category'] == 'user_choice' for f in outstanding):
            errors.append('needs_user requires a concrete unresolved user choice')
        if rev['stop_reason'] == 'needs_evidence' and not any(f['category'] == 'new_evidence' for f in outstanding):
            errors.append('needs_evidence requires a concrete missing fact')
        if final:
            if rev['stop_reason'] == 'in_progress':
                errors.append('process is still in progress')
            if any(f['category'] == 'editing' for f in outstanding):
                errors.append('unresolved editorial findings prevent a publishable result; budget exhaustion does not waive them')
            if any(f['disposition'] == 'open' for f in outstanding):
                errors.append('open user choices or evidence questions must be resolved or explicitly deferred as limitations before publication')
    except (ValueError, KeyError, OSError) as exc:
        errors.append(str(exc))
    return errors


def handoff(process_path, evaluation_path=None):
    record = read(process_path)
    errors = process_errors(record, final=False)
    if errors:
        raise ValueError('; '.join(errors))
    plan, pack, document = inputs(record['artifact']['path'], record['plan']['path'])
    blockers = process_errors(record)
    used = revision_count(record)
    def link(path):
        return '[' + Path(path).name.replace('[', '').replace(']', '') + '](' + quote(str(local(path)), safe='/') + ')'
    lines = ['# Resume continuation — private', '',
             '**Next step:** ' + ('Resolve the outstanding checks below.' if blockers else 'Review delivery status and any recorded user choices below.'), '',
             'Process checks: ' + ('incomplete' if blockers else 'complete') + '. This is not a hiring prediction.',
             f"Editorial cycles: {used}/{record['revision']['limit']} used; {max(0, record['revision']['limit'] - used)} remaining.",
             'Recorded stop reason: `' + record['revision']['stop_reason'] + '`.', '',
             'Draft: ' + link(record['artifact']['path']) + ' · Plan: ' + link(record['plan']['path']) +
             ' · Process record: ' + link(process_path), '', '## Outstanding checks', '']
    lines += ['- ' + e for e in blockers] or ['No outstanding process checks.']
    lines += ['', '## Reviewer judgments and choices', '',
              'These are editorial assessments, not new career facts. Reader context: `' + record['cold_read']['context'] + '`.', '']
    lines += ['- Reader noticed: ' + s for s in record['cold_read']['impressions']]
    for row in record.get('quality', {}).get('omissions', []):
        lines += [f"- Omission review / {row['disposition']}: {row['subject']} — {row['reason']}"]
    lines += ['- Review source: ' + link(ref['path']) for ref in record.get('review_sources', [])]
    lines += [f"- {f['category']} / {f['disposition']}: {f['description']} — {f['reason']}" for f in record['revision']['findings']]
    lines += ['', '## Measured document facts', '',
              f"Visible words: {sum(len(b['text'].split()) for b in document['blocks'])}.",
              f"Cited atoms: {len({i for b in document['blocks'] for i in b['evidence_ids']})}."]
    if record['compression']['status'] == 'attempted':
        report = compression_report(record, pack)
        lines += [f"Compression: {report['before_words']} → {report['after_words']} words.",
                  'Reviewer assessment: ' + record['compression']['assessment'], report['limit']]
    else:
        lines += ['Compression: ' + record['compression']['status'] + '. No claim that shortening is impossible.']
    lines += ['', '## Delivery', '']
    if evaluation_path:
        from validate_records import check
        evaluation = read(evaluation_path)
        kind, failures, warnings = check(local(evaluation_path))
        run = evaluation.get('run', {})
        from manifest import editorial_staleness
        failures.extend(editorial_staleness(run))
        if (kind != 'evaluation' or failures or run.get('process') != pin(process_path)
                or run.get('artifact_sha256') != record['artifact']['sha256']):
            raise ValueError('handoff evaluation must be valid, current and pin this exact process and artifact: ' + '; '.join(failures))
        lines += ['Evaluation: ' + link(evaluation_path) + '. Publishable: ' + str(evaluation['publishable']).lower() + '.']
        lines += ['- Evaluation warning: ' + w for w in warnings]
        if run.get('exports'):
            exported = read(run['exports']['path'])
            lines += ['Export report: ' + link(run['exports']['path'])]
            lines += ['- ' + fmt.upper() + ': ' + row['status'] + (' · ' + link(row['file']['path']) if row.get('file') else '')
                      for fmt, row in exported['formats'].items()]
            lines += ['Visual review: ' + record.get('quality', {}).get('layout', {}).get('status', 'not_recorded'),
                      'DOCX pagination: ' + exported.get('docx_pagination', 'not_verified')]
    else:
        lines += ['No evaluation supplied. Publishability and export verification are not established by this handoff.']
    lines += ['', '## Provenance', '']
    for label, ref in [('Draft', record['artifact']), ('Plan', record['plan']), ('Selection', plan['selection']),
                       ('Pack', read(plan['selection']['path'])['pack']), ('Policy', plan['policy'])]:
        lines += [f"- {label}: {link(ref['path'])} · SHA-256 `{ref['sha256']}`"]
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    for key in ('artifact', 'plan', 'output'):
        prep.add_argument('--' + key, required=True)
    prep.add_argument('--previous'); prep.add_argument('--compression-target', default='')
    prep.add_argument('--feedback', action='append', default=[], help='import a pinned screen, representation or evaluation work list')
    packet = sub.add_parser('packet'); packet.add_argument('--artifact', required=True); packet.add_argument('--plan', required=True)
    check = sub.add_parser('check'); check.add_argument('--process', required=True); check.add_argument('--allow-incomplete', action='store_true')
    layout = sub.add_parser('layout')
    layout.add_argument('--input', required=True); layout.add_argument('--exports', required=True); layout.add_argument('--output', required=True)
    save = sub.add_parser('save'); save.add_argument('--input', required=True); save.add_argument('--output', required=True)
    report = sub.add_parser('handoff'); report.add_argument('--process', required=True); report.add_argument('--evaluation'); report.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'packet':
            print(json.dumps(review_packet(args.artifact, args.plan), indent=2))
        elif args.command == 'check':
            errors = process_errors(read(args.process), final=not args.allow_incomplete)
            if errors:
                raise ValueError('; '.join(errors))
            print('process record is consistent' + ('; incomplete reviews are allowed' if args.allow_incomplete else ' and review checks are complete'))
        else:
            target = local(args.output)
            if target.parent != local('outputs'):
                raise ValueError('private process records and handoffs belong directly under outputs/')
            if args.command == 'handoff':
                text = handoff(args.process, args.evaluation)
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('x', encoding='utf-8') as handle:
                    handle.write(text)
                print(target)
            else:
                if not target.name.endswith('-process.json'):
                    raise ValueError('use outputs/<version>-process.json')
                record = prepare(args.artifact, args.plan, args.previous, bool(args.compression_target), args.compression_target, args.feedback) if args.command == 'prepare' else read(args.input)
                if args.command == 'layout':
                    if record.get('process_version') != 2 or 'quality' not in record:
                        raise ValueError('prepare a version 2 process review first')
                    record['quality']['layout'] = pending_layout(args.exports)
                errors = process_errors(record, final=False)
                if errors:
                    raise ValueError('; '.join(errors))
                print(write_new(target, record))
        return 0
    except (ValueError, KeyError, OSError) as exc:
        print('error: ' + str(exc)); return 1


if __name__ == '__main__':
    raise SystemExit(main())
