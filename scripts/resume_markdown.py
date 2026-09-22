"""Structured inline formatting and clean, deterministic resume Markdown."""
from html.parser import HTMLParser
import re
import string
import unicodedata

import render
from resume_links import source_links


class Inline(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.nodes = []
        self.stack = [self.nodes]

    def handle_data(self, text):
        self.stack[-1].append({'kind': 'text', 'text': text})

    def handle_starttag(self, tag, attrs):
        if tag not in ('strong', 'em'):
            raise ValueError('unsupported inline formatting: ' + tag)
        node = {'kind': tag, 'children': []}
        self.stack[-1].append(node)
        self.stack.append(node['children'])

    def handle_endtag(self, tag):
        if tag not in ('strong', 'em') or len(self.stack) == 1:
            raise ValueError('invalid inline formatting')
        self.stack.pop()


def formatted(text):
    parser = Inline()
    parser.feed(render.inline(text))
    return parser.nodes


def inline_nodes(text):
    text = re.sub(r'<!--.*?-->', '', text, flags=re.S).strip()
    links = source_links(text)
    marker = '\ue000LINK'
    while marker in text:
        marker += '_'
    pieces, offset = [], 0
    replacements = {}
    for index, link in enumerate(links):
        token = marker + str(index) + '\ue001'
        pieces.extend([text[offset:link['start']], token])
        replacements[token] = {'kind': 'link', 'target': link['target'],
                               'children': formatted(link['label']) if link['label'] is not None
                               else [{'kind': 'text', 'text': link['target']}]}
        offset = link['end']
    pieces.append(text[offset:])

    def expand(nodes):
        result = []
        for node in nodes:
            if node['kind'] != 'text':
                result.append({**node, 'children': expand(node['children'])})
            else:
                for part in re.split('(' + re.escape(marker) + r'\d+\ue001)', node['text']):
                    if part:
                        result.append(replacements.get(part, {'kind': 'text', 'text': part}))
        return result
    return expand(formatted(''.join(pieces)))


def visible(nodes):
    result = ''
    for node in nodes:
        if node['kind'] == 'text':
            result += node['text']
        else:
            label = visible(node['children'])
            if node['kind'] == 'link' and label != node['target']:
                label += ' (' + node['target'] + ')'
            result += label
    return result


def escape(text):
    # Backslash-escaped ASCII punctuation is literal in CommonMark. Escape angle
    # brackets too, so text cannot become an HTML tag or an automatic link.
    return re.sub(r'([\\`*_{}\[\]()#+.!|>~<&-])', r'\\\1', text)


def serialize(nodes):
    out, emphasis = [], []
    for node in nodes:
        kind = node['kind']
        if kind == 'text':
            out.append(escape(node['text']))
        elif kind in ('strong', 'em'):
            marker = '**' if kind == 'strong' else '*'
            inner = serialize(node['children'])
            # CommonMark does not recognize emphasis with whitespace just inside
            # its delimiters. Keep that whitespace outside without changing text.
            leading = inner[:len(inner) - len(inner.lstrip())]
            trailing = inner[len(inner.rstrip()):]
            core = inner.strip()
            if core:
                start = sum(map(len, out)) + len(leading)
                emphasis.append((start, start + len(marker) + len(core), marker, core))
            out.append(leading + marker + core + marker + trailing if core else inner)
        elif kind == 'link':
            target = node['target'].replace('(', r'\(').replace(')', r'\)')
            out.append('[' + serialize(node['children']) + '](' + target + ')')
        else:
            raise ValueError('unsupported inline node: ' + kind)
    result = ''.join(out)
    def punctuation(char):
        return char in string.punctuation or unicodedata.category(char).startswith('P')
    for start, end, marker, core in emphasis:
        before = result[start - 1] if start else '\n'
        after = result[end + len(marker):end + len(marker) + 1] or '\n'
        body = core.strip('*') or core
        # The draft's older inline renderer accepts punctuation-only intraword
        # emphasis that CommonMark renders literally. Fail instead of exporting
        # extra asterisks as if the content comparison had verified them.
        if ((punctuation(body[0]) and not (before.isspace() or punctuation(before))) or
                (punctuation(body[-1]) and not (after.isspace() or punctuation(after)))):
            raise ValueError('unsupported Markdown emphasis boundary; separate emphasis from adjacent words')
    return result


def submission_markdown(document):
    blocks = []
    for block in document['blocks']:
        nodes = block['inline']
        if visible(nodes) != block['text']:
            raise ValueError('Markdown inline content differs from shared text')
        kind = block['kind']
        prefix = {'p': '', 'li': '- ', 'h1': '# ', 'h2': '## ', 'h3': '### ', 'h4': '#### '}[kind]
        blocks.append(prefix + serialize(nodes))
    return '\n\n'.join(blocks) + '\n'


def validate_markdown(document, text):
    """Require exact canonical structure as well as the model's visible content.

    This deliberately rejects even formatting-only changes to a pinned export.
    It also checks link labels, destinations and inline emphasis, which a plain
    text comparison alone cannot establish.
    """
    if text != submission_markdown(document):
        raise ValueError('Markdown content, structure or links differ from the shared document')
    return '\n\n'.join(visible(block['inline']) for block in document['blocks']) + '\n'
