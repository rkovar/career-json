"""Page geometry diagnostics; findings request visual judgment, never auto-fix.

Coordinates are in each extractor's page units, with a top-left origin. Block
matching ignores whitespace for diagnostics only; export content verification
remains a separate, stricter check.
"""
import re
import unicodedata
from resume_document import normalized


def compact(text):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', text)).replace('\u2022', '')


def poppler_geometry(xml):
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml[xml.index('<?xml'):])
    return [{'page': int(p.get('number')), 'width': float(p.get('width')), 'height': float(p.get('height')),
             'lines': [{'text': ''.join(t.itertext()), 'x': float(t.get('left')), 'y': float(t.get('top')),
                        'width': float(t.get('width')), 'height': float(t.get('height'))} for t in p.findall('text')]}
            for p in root.findall('page')]


def diagnostics(document, geometry, plan=None):
    limit = 'Page geometry and text placement are diagnostics, not visual approval, ATS compatibility or DOCX pagination.'
    if not geometry:
        return {'status': 'unavailable', 'pages': [], 'blocks': [], 'findings': [], 'limitation': limit}
    stream, spans, pages = '', [], []
    for page in geometry:
        height = page['height']
        intervals = []
        for line in page['lines']:
            text = compact(line['text'])
            if not text: continue
            start = len(stream); stream += text
            spans.append((start, len(stream), page['page']))
            intervals.append((max(0, line['y']), min(height, line['y'] + line['height'])))
        intervals.sort()
        merged = []
        for a, b in intervals:
            if not merged or a > merged[-1][1]: merged.append([a, b])
            else: merged[-1][1] = max(merged[-1][1], b)
        pages.append({'page': page['page'], 'width': page['width'], 'height': height,
                      'text_band_fraction': round(sum(b-a for a, b in merged) / height, 3) if height else 0,
                      'text_characters': sum(len(compact(l['text'])) for l in page['lines'])})
    blocks, findings, cursor = [], [], 0
    def finding(kind, ids, nums, message):
        findings.append({'id': kind + ':' + ':'.join(ids or [str(n) for n in nums]),
                         'kind': kind, 'block_ids': ids, 'pages': nums, 'message': message})
    for block in document['blocks']:
        text = compact(block['text']); start = stream.find(text, cursor)
        if start < 0:
            blocks.append({'block_id': block['id'], 'pages': [], 'status': 'unmatched'})
            finding('unmatched_block', [block['id']], [], 'Could not locate this block reliably; inspect the PDF. This is not evidence of missing text.')
            continue
        end = start + len(text); cursor = end
        nums = sorted({page for a, b, page in spans if a < end and b > start})
        blocks.append({'block_id': block['id'], 'pages': nums, 'status': 'located'})
        if len(nums) > 1 and block['kind'] in ('li', 'p'):
            finding('split_prose', [block['id']], nums, 'Prose crosses a page boundary; assess whether the break interrupts the achievement or short role description.')
    locations = {b['block_id']: b['pages'] for b in blocks}
    for index, block in enumerate(document['blocks'][:-1]):
        if block['kind'] not in ('h2', 'h3', 'h4') and block.get('employment_part') != 'position': continue
        following = document['blocks'][index + 1]
        here, after = locations[block['id']], locations[following['id']]
        if here and after and here[-1] != after[0]:
            finding('separated_heading', [block['id'], following['id']], [here[-1], after[0]], 'Heading or position line is separated from the following content; inspect the grouping.')
    if len(pages) > 1:
        last, earlier = pages[-1], pages[:-1]
        if last['text_band_fraction'] < .30 and any(p['text_band_fraction'] > .55 for p in earlier):
            finding('uneven_final_page', [], [p['page'] for p in pages], 'The final page has few text bands following denser pages; consider redistributing content. These fractions are diagnostics, not page-fill targets.')
    for impression in (plan or {}).get('impressions', []):
        if impression.get('prominence') != 'leading' or impression.get('basis') == 'gap': continue
        proof = [b['id'] for b in document['blocks'] if set(b['evidence_ids']) & set(impression['evidence_ids'])]
        nums = sorted({n for bid in proof for n in locations[bid]})
        if nums and nums[0] > 1:
            finding('late_leading_evidence', proof, nums, 'Evidence supporting a planned leading impression first appears after page one; assess actual prominence without imposing a universal first-page rule.')
    return {'status': 'measured' if all(b['status'] == 'located' for b in blocks) else 'partial',
            'pages': pages, 'blocks': blocks, 'findings': findings, 'limitation': limit}
