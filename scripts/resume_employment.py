"""Employer-level resume structure derived from approved employment dates."""
import re

MONTHS = {name: index for index, name in enumerate(
    ('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'), 1)}
DATE = r'(?:[A-Za-z]+\s+\d{4}|\d{4}(?:-(?:0[1-9]|1[0-2]))?|present|ongoing)'
RANGE = re.compile(r'^\s*(' + DATE + r')\s*(?:to|through|[–—-])\s*(' + DATE + r')\s*$', re.I)


def date_bounds(value):
    if value in ('present', 'ongoing'):
        return (999999, 999999)
    if not value:
        return None
    parts = value.split('-')
    year = int(parts[0]) * 100
    return (year + int(parts[1]), year + int(parts[1])) if len(parts) > 1 else (year + 1, year + 12)


def date_range(text):
    match = RANGE.fullmatch(text)
    if not match:
        return None
    def parse(value):
        value = value.lower()
        if value in ('present', 'ongoing') or value[0].isdigit():
            return value
        month, year = value.split()
        if month[:3] not in MONTHS:
            raise ValueError('unrecognized employment month: ' + month)
        return year + '-' + str(MONTHS[month[:3]]).zfill(2)
    return tuple(parse(v) for v in match.groups())


def next_month(value):
    return (value // 100 + 1) * 100 + 1 if value % 100 == 12 else value + 1


def employment_groups(records):
    """Group one employer's overlapping/adjacent roles, retaining every title.

    Definite breaks create separate tenures. Unknown ends are not invented.
    Dates at year precision remain year-precision data. Grouping does not infer
    promotions, reporting lines, or the reason for a change of role.
    """
    by_employer = {}
    for record in records:
        by_employer.setdefault(record['employer'], []).append(record)
    groups = []
    for employer, roles in by_employer.items():
        ordered = sorted(roles, key=lambda r: date_bounds(r['start'])[0])
        chunks, chunk, end = [], [], None
        for role in ordered:
            start = date_bounds(role['start'])[0]
            if chunk and (end is None or start > next_month(end)):
                chunks.append(chunk); chunk = []
            chunk.append(role)
            role_end = date_bounds(role.get('end'))
            end = max(date_bounds(r['end'])[1] for r in chunk) if role_end and all(r.get('end') for r in chunk) else None
        if chunk:
            chunks.append(chunk)
        for chunk in chunks:
            first = min(chunk, key=lambda r: date_bounds(r['start'])[0])
            last = max(chunk, key=lambda r: date_bounds(r.get('end') or r['start'])[1])
            groups.append({'employer': employer, 'start': first['start'],
                           'end': last['end'] if all(r.get('end') for r in chunk) else None,
                           'roles': sorted(chunk, key=lambda r: date_bounds(r['start'])[0], reverse=True),
                           'employment_ids': [r['employment_id'] for r in chunk]})
    return sorted(groups, key=lambda g: date_bounds(g.get('end') or g['start'])[1], reverse=True)


def matches_range(shown, start, end):
    if not shown or not end:
        return False
    # A displayed year can summarize a known month; it cannot invent a month
    # when the source knows only a year.
    for display, source in zip(shown, (start, end)):
        displayed, actual = date_bounds(display), date_bounds(source)
        if not (displayed[0] <= actual[0] and actual[1] <= displayed[1]):
            return False
    return True


def heading_contexts(blocks, records):
    """Return dated source scope for each block plus structural/date failures."""
    groups = employment_groups(records)
    contexts, errors, flat_groups = {}, [], {}
    employer_group, current = None, None
    shown_roles = []
    role_heading, role_content = None, False

    def finish_role():
        if role_heading is not None and not role_content:
            errors.append(role_heading + ': empty position subsection; show positions without dedicated achievements as compact timeline rows')

    def finish_group():
        if employer_group is not None:
            expected = set(employer_group['employment_ids'])
            if set(shown_roles) != expected or len(shown_roles) != len(expected):
                errors.append('grouped employer must show each position and its dates exactly once: ' + employer_group['employer'])
            else:
                starts = {r['employment_id']: date_bounds(r['start'])[0] for r in employer_group['roles']}
                shown_starts = [starts[rid] for rid in shown_roles]
                if shown_starts != sorted(shown_starts, reverse=True):
                    errors.append('show positions in reverse chronological order within ' + employer_group['employer'])

    def scope(roles, title):
        return {'title': title, 'records': roles,
                'low': min(date_bounds(r['start'])[0] for r in roles),
                'high': max(date_bounds(r.get('end') or r['start'])[1] for r in roles),
                'ids': {r['employment_id'] for r in roles}}

    for block in blocks:
        kind, text = block['kind'], block['text']
        parts = [p.strip() for p in text.split('|')]
        position_row = employer_group is not None and kind == 'p' and len(parts) >= 2
        if kind in ('h1', 'h2', 'h3', 'h4') or position_row:
            finish_role(); role_heading, role_content = None, False
        elif role_heading is not None:
            role_content = True
        if kind in ('h1', 'h2', 'h3'):
            finish_group(); employer_group, current, shown_roles = None, None, []
        if kind == 'h3' and len(parts) >= 2:
            shown = date_range(parts[1])
            if shown:
                candidates = [g for g in groups if g['employer'] == parts[0]
                              and matches_range(shown, g['start'], g['end'])]
                if len(candidates) != 1:
                    errors.append(block['id'] + ': employer tenure does not match a recorded continuous group; preserve breaks and date precision')
                else:
                    employer_group = candidates[0]
            elif len(parts) >= 3:
                employer, title, dates = parts[:3]  # optional location is a fourth field
                same = [r for r in records if r['employer'] == employer]
                if title == 'Career highlights':
                    candidates = [g for g in groups if g['employer'] == employer
                                  and matches_range(date_range(dates), g['start'], g['end'])]
                    matched = candidates[0]['roles'] if len(candidates) == 1 else []
                else:
                    matched = [r for r in same if r['title'] == title and matches_range(date_range(dates), r['start'], r.get('end'))]
                if not matched:
                    errors.append(block['id'] + ': heading dates or title do not match this role; an employer promotion chain cannot extend its title tenure')
                else:
                    current = scope(matched, title)
                    for group in groups:
                        if current['ids'] <= set(group['employment_ids']) and title != 'Career highlights':
                            key = tuple(group['employment_ids'])
                            flat_groups.setdefault(key, []).append(block['id'])
        elif employer_group is not None and kind in ('p', 'h4'):
            if kind == 'h4' and text == 'Career highlights':
                current = scope(employer_group['roles'], 'Career highlights')
            elif len(parts) >= 2:
                matched = [r for r in employer_group['roles'] if r['title'] == parts[0]
                           and matches_range(date_range(parts[1]), r['start'], r.get('end'))]
                if len(matched) != 1:
                    errors.append(block['id'] + ': position title/dates do not match this employer tenure')
                    current = None
                else:
                    shown_roles.append(matched[0]['employment_id'])
                    # Compact timeline rows are not headings for the following
                    # bullets; only an explicit role or highlights subsection is.
                    current = scope(matched, parts[0]) if kind == 'h4' else None
                    if kind == 'h4': role_heading = block['id']
            elif kind == 'h4':
                errors.append(block['id'] + ': use a dated role heading or Career highlights within the employer group')
                current = None
        elif kind == 'h4':
            errors.append(block['id'] + ': a position subsection needs an employer heading with tenure dates')
            current = None
        if employer_group is not None and block.get('evidence_ids') and not current:
            errors.append(block['id'] + ': grouped achievements need an explicit role or Career highlights subsection')
        contexts[block['id']] = current
    finish_group()
    finish_role()
    for headings in flat_groups.values():
        if len(headings) > 1:
            errors.append('related positions repeat employer headings (' + ', '.join(headings) + '); group the tenure under one employer heading')
    return contexts, errors


def chronology_errors(document, pack):
    records = [r for r in pack.get('employment', []) if r.get('external_safe')
               and r.get('evidence_status') not in ('unresolved', 'declined')]
    atoms = {a['id']: a for a in pack.get('evidence_atoms', [])}
    contexts, errors = heading_contexts(document['blocks'], records)
    for block in document['blocks']:
        current = contexts[block['id']]
        if current is None:
            continue
        for aid in block.get('evidence_ids', []):
            if aid not in atoms:
                continue
            atom = atoms[aid]
            if atom.get('employment_id') and atom['employment_id'] not in current['ids']:
                errors.append(f"{block['id']}: {aid} is linked to a different employment record; correct the grouping or route the career-record correction through Core")
            occurred = atom.get('occurred') or {}
            if occurred and not occurred.get('inferred'):
                start, end = date_bounds(occurred['start']), date_bounds(occurred.get('end') or occurred['start'])
                if start[1] < current['low'] or end[0] > current['high']:
                    errors.append(f"{block['id']}: {aid} spans dates outside {current['title']}; use an accurate role or explicit company-wide Career highlights section")
    return errors
