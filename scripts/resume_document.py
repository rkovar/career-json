"""Small derived resume document shared by all submission renderers.

Markdown remains the editable, cited draft. Only supported Markdown structure is
accepted; exports must not silently reinterpret arbitrary HTML or layout tables.
"""
import html
from html.parser import HTMLParser
import re
import unicodedata
import render
from resume_links import source_links
from resume_employment import date_range


class Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def plain_fragment(text):
    parser = Text(); parser.feed(render.inline(text))
    return ''.join(parser.parts)


def inline_with_links(text):
    text = re.sub(r'<!--.*?-->', '', text, flags=re.S).strip()
    found = source_links(text)
    marker = '\ue000LINK'
    while marker in text:
        marker += '_'
    pieces, offset = [], 0
    for index, link in enumerate(found):
        pieces.extend([text[offset:link['start']], marker + str(index) + '\ue001'])
        offset = link['end']
    pieces.append(text[offset:])
    # Flatten formatting once over the whole block, preserving spaces and
    # emphasis that crosses a hyperlink boundary.
    flattened = plain_fragment(''.join(pieces))
    visible, links, offset = '', [], 0
    for index, link in enumerate(found):
        token = marker + str(index) + '\ue001'
        position = flattened.index(token, offset)
        visible += flattened[offset:position]
        start = len(visible)
        label = plain_fragment(link['label']) if link['label'] is not None else link['target']
        visible += label if label == link['target'] else label + ' (' + link['target'] + ')'
        links.append({'start': start, 'end': len(visible), 'target': link['target']})
        offset = position + len(token)
    visible += flattened[offset:]
    return visible, links


def plain_inline(text):
    return inline_with_links(text)[0]


def document_from_markdown(markdown, paper_size='A4'):
    if paper_size not in ('A4', 'Letter'):
        raise ValueError('paper_size must be A4 or Letter')
    without_comments = re.sub(r'<!--.*?-->', '', markdown, flags=re.S)
    if re.search(r'^\s*(?:```|~~~|> |\|.*\||#{5,} |\d+[.)] )|!\[|<\s*/?[A-Za-z][^>]*>', without_comments, re.M):
        raise ValueError('unsupported resume markup; use headings, paragraphs, ordinary bullets and inline links/emphasis')
    blocks, employer_group = [], False
    for index, (kind, text) in enumerate(render.blocks(markdown)):
        ids = sorted(set(re.findall(r'\bE_[A-Z0-9_]+\b', ' '.join(m.group(0) for m in render.EVIDENCE.finditer(text)))))
        visible, links = inline_with_links(text)
        if not visible:
            if ids:
                raise ValueError('orphan evidence comment; attach it to its claim')
            continue
        if re.search(r'\bE_[A-Z0-9_]+\b|PRIVATE_CANARY|external_safe|evidence_status', visible):
            raise ValueError('internal evidence or review metadata appears in submission text')
        parts = [s.strip() for s in visible.split('|')]
        if kind in ('h1', 'h2', 'h3'):
            employer_group = kind == 'h3' and len(parts) >= 2 and date_range(parts[1]) is not None
        block = {'id': f'b{index + 1}', 'kind': kind, 'text': visible, 'evidence_ids': ids, 'links': links}
        if employer_group and kind == 'p' and len(parts) >= 2 and date_range(parts[1]):
            block['employment_part'] = 'position'
        blocks.append(block)
    if not blocks:
        raise ValueError('empty resume')
    return {'document_version': 2, 'paper_size': paper_size, 'blocks': blocks}


def paragraphs(document):
    return [b['text'] for b in document['blocks']]


def plain_text(document):
    return '\n\n'.join(('- ' if b['kind'] == 'li' else '') + b['text'] for b in document['blocks']) + '\n'


def normalized(text):
    # Collapse line wrapping and spacing, but preserve boundaries between words.
    text = re.sub(r'(?m)^\s*[-•]\s+', '', text)
    return ' '.join(unicodedata.normalize('NFKC', text).split())


def pdf_wrapping_matches(expected, recovered):
    """Match only physical newline wraps inside expected hyphens or URLs.

    Word boundaries are never removed globally. TXT/DOCX do not use this
    tolerance, and a space inside an ordinary word remains a content failure.
    """
    line_break = r'(?:[ \t]*\r?\n[ \t]*)?'
    tokens = []
    for token in normalized(expected).split(' '):
        # Link labels are expanded as `label (https://...)` in the document.
        url = re.search(r'(?:https?://|mailto:)[^\s]+', token)
        chars = []
        for index, char in enumerate(token):
            chars.append(re.escape(char))
            if index < len(token) - 1 and (char == '-' or (url and index >= url.start())):
                chars.append(line_break)
        tokens.append(''.join(chars))
    recovered = unicodedata.normalize('NFKC', recovered)
    recovered = re.sub(r'(?m)^\s*[-•]\s+', '', recovered)
    return re.fullmatch(r'\s*' + r'\s+'.join(tokens) + r'\s*', recovered) is not None


def submission_html(document):
    out, listing = [], False
    for block in document['blocks']:
        kind = block['kind']
        if kind == 'li' and not listing:
            out.append('<ul>'); listing = True
        elif kind != 'li' and listing:
            out.append('</ul>'); listing = False
        parts, offset = [], 0
        for link in block.get('links', []):
            parts.append(html.escape(block['text'][offset:link['start']]))
            parts.append('<a href="' + html.escape(link['target'], quote=True) + '">' +
                         html.escape(block['text'][link['start']:link['end']]) + '</a>')
            offset = link['end']
        parts.append(html.escape(block['text'][offset:]))
        text = ''.join(parts)
        attrs = ' class="position"' if block.get('employment_part') == 'position' else ''
        out.append(f'<{kind}{attrs}>{text}</{kind}>')
    if listing: out.append('</ul>')
    page = render.TEMPLATE.format(title='Resume', body='\n'.join(out))
    page = page.replace('size: A4', 'size: ' + document['paper_size'])
    # CSS case conversion changes extracted PDF text, unlike DOCX/TXT.
    page = page.replace('text-transform: uppercase;', 'text-transform: none;')
    page = page.replace('</style>', 'a { color: inherit; text-decoration: none; overflow-wrap: anywhere; }</style>')
    if document['paper_size'] == 'Letter':
        page = page.replace('210mm', '215.9mm')
    # No hidden metadata, external resources, or browser-supplied header/footer.
    page = page.replace('    .evidence { display: none; }\n', '')
    page = page.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">')
    return page
