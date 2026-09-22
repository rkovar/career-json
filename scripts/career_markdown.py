#!/usr/bin/env python3
"""Export the complete saved career pack as a private Markdown snapshot.

    python3 scripts/career_markdown.py
    python3 scripts/career_markdown.py --pack data/packs/example.json -o outputs/example.md
"""
import argparse
import hashlib
import html
import json
import re
import sys

from current_pack import ROOT, resolve
from pack_io import local, write_view
from schema_tools import walk


def escape(value):
    """Literal recorded text, including raw HTML and Markdown-looking excerpts."""
    text = html.escape(str(value), quote=False)
    return re.sub(r'([\\`*_{}\[\]()#+.!|>~-])', r'\\\1', text)


def fields(value, indent=0):
    """Lossless recursive presentation, including schema-permitted extensions.

    Every object key and array entry is visited; no truthiness filter can discard
    false permissions, zero metrics, empty values or null dates.
    """
    rows = []
    items = value.items() if isinstance(value, dict) else enumerate(value, 1)
    for key, item in items:
        prefix = '  ' * indent + '- **' + escape(key) + ':**'
        if isinstance(item, (dict, list)) and item:
            rows.append(prefix)
            rows.extend(fields(item, indent + 1))
        else:
            literal = item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)
            lines = escape(literal).split('\n')
            rows.append(prefix + ' ' + lines[0])
            rows.extend('  ' * (indent + 1) + line for line in lines[1:])
    return rows


def build(pack, pack_path, source_hash):
    from career_page import employment_chains
    out = ['# Career record: ' + escape(pack.get('name', '')), '',
           '**Personal record — includes private and restricted information.**', '',
           'This snapshot contains the saved pack, including contact details, notes and evidence. '
           'It does not grant permission to share restricted content. Recorded acceptance, '
           'evidence confidence and external-use permission are separate states.', '',
           'JSON is authoritative. Edits to this Markdown do not sync back. Separate pending '
           'capture notes, review proposals, historical packs and source files are not included.', '',
           'Source pack: ' + escape(pack_path), '', 'Source SHA-256: ' + source_hash, '',
           'Schema version: ' + escape(pack['schema_version']), '']

    def section(title, value):
        out.extend(['## ' + title, ''])
        if isinstance(value, (dict, list)) and value:
            out.extend(fields(value))
        else:
            out.extend(fields({'value': value}))
        out.append('')

    handled = {'employment', 'evidence_atoms'}
    for key, title in [('name', 'Name'), ('purpose', 'Purpose'), ('private_profile', 'Private profile')]:
        if key in pack:
            section(title, pack[key]); handled.add(key)
    roles = pack.get('employment', [])
    atoms = pack.get('evidence_atoms', [])
    known = {r['employment_id'] for r in roles}
    for atom in atoms:
        if atom.get('employment_id') and atom['employment_id'] not in known:
            raise ValueError('unknown employment reference: ' + atom['employment_id'])
    out.extend(['## Employment and achievements', ''])
    for chain in employment_chains(roles):
        out.extend(['### ' + escape(chain[0].get('employer', 'Employer')), ''])
        for role in chain:
            out.extend(['#### ' + escape(role.get('title', role['employment_id'])), ''])
            out.extend(fields(role)); out.append('')
            for atom in atoms:
                if atom.get('employment_id') == role['employment_id']:
                    out.extend(['##### ' + escape(atom.get('title', atom['id'])), ''])
                    out.extend(fields(atom)); out.append('')
    other = [a for a in atoms if not a.get('employment_id')]
    if other:
        section('Other recorded work', other)
    titles = {'source_records': 'Supporting sources', 'skills': 'Skills',
              'skill_vocabulary': 'Skill vocabulary', 'education': 'Education',
              'strengths_profile': 'Strengths (recorded states)',
              'positioning_preferences': 'Positioning preferences', 'publications': 'Publications',
              'metadata': 'Record metadata', 'schema_version': 'Schema'}
    for key, value in pack.items():
        if key not in handled:
            section(titles.get(key, escape(key)), value)
    return '\n'.join(out).rstrip() + '\n'


def prepare(path, raw=None):
    """Validate and pin the same bytes used for rendering, without reading sources."""
    from validate_pack import check
    path = local(path)
    raw = path.read_bytes() if raw is None else raw
    pack = json.loads(raw)
    if not isinstance(pack, dict):
        raise ValueError('career pack must be an object')
    schema_path = ('schemas/archive/career-1.3.schema.json' if pack.get('schema_version') == '1.3'
                   else 'schemas/career.schema.json')
    schema = json.loads(local(schema_path).read_text())
    errors = []
    walk(pack, schema, schema, 'pack', errors)
    if errors:
        raise ValueError('; '.join(errors))
    errors, _ = check(path, schema, root=ROOT)
    if errors:
        raise ValueError('; '.join(errors))
    text = build(pack, path.relative_to(ROOT.resolve()), hashlib.sha256(raw).hexdigest())
    if path.read_bytes() != raw:
        raise ValueError('pack changed during export; retry against a stable pack')
    return text


def export(path, destination='outputs/career.md'):
    out = local(destination)
    if not out.is_relative_to(local('outputs')) or out.suffix.lower() != '.md':
        raise ValueError('private Markdown records belong under outputs/ with an .md extension')
    text = prepare(path)
    write_view(out, text)
    return out


def refresh(path, destination='outputs/career-record.html'):
    """Prepare both saved views from one snapshot before replacing either file."""
    from career_page import build as reading_page
    path, out = local(path), local(destination)
    if not out.is_relative_to(local('outputs')) or out.suffix.lower() != '.html':
        raise ValueError('private reading pages belong under outputs/ with an .html extension')
    raw = path.read_bytes()
    markdown = prepare(path, raw)
    marker = '<!-- career-pack-sha256: ' + hashlib.sha256(raw).hexdigest() + ' -->\n'
    page = marker + reading_page(json.loads(raw), path.relative_to(ROOT.resolve()))
    if path.read_bytes() != raw:
        raise ValueError('pack changed during refresh; retry against a stable pack')
    write_view(local('outputs/career.md'), markdown)
    write_view(out, page)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack')
    parser.add_argument('-o', '--output', default='outputs/career.md')
    args = parser.parse_args(argv)
    try:
        path = local(args.pack) if args.pack else resolve()
        if path is None:
            raise ValueError('no current pack')
        print(export(path, args.output).relative_to(ROOT.resolve()))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print('error: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
