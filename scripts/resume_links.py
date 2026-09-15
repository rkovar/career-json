"""Source URL spans and strict comparison of PDF hyperlink destinations.

No destinations are fetched. A correct embedded target does not establish that
the website is available or that its content is still current.
"""
import re
from urllib.parse import quote, urlsplit, urlunsplit


def canonical_url(target):
    """Allow normal browser URI serialization, not changed paths or queries."""
    if re.search(r'[\s\x00-\x1f\x7f<>"\\]', target):
        raise ValueError('URL contains whitespace or unsafe characters; use a complete encoded URL')
    if re.search(r'%(?![0-9a-fA-F]{2})', target):
        raise ValueError('URL has invalid percent encoding')
    parts = urlsplit(target)
    scheme = parts.scheme.lower()
    if scheme not in ('http', 'https', 'mailto'):
        raise ValueError('unsupported link target; use a recorded public HTTP(S) or mailto URL')
    if scheme == 'mailto':
        if not parts.path or parts.netloc:
            raise ValueError('mailto URL needs an address')
        result = urlunsplit((scheme, '', parts.path, parts.query, parts.fragment))
    else:
        if not parts.hostname:
            raise ValueError('HTTP(S) URL needs a hostname')
        host = parts.hostname.encode('idna').decode('ascii').lower()
        if ':' in host:
            host = '[' + host + ']'
        port = parts.port
        if port is not None and port != {'http': 80, 'https': 443}[scheme]:
            host += ':' + str(port)
        if '@' in parts.netloc:
            host = parts.netloc.rsplit('@', 1)[0] + '@' + host
        result = urlunsplit((scheme, host, parts.path or '/', parts.query, parts.fragment))
    # urlunsplit omits empty query/fragment delimiters; retain source semantics.
    if '?' in target.split('#', 1)[0] and not parts.query:
        head, sep, fragment = result.partition('#')
        result = head + '?' + sep + fragment
    if target.endswith('#'):
        result += '#'
    # Encode Unicode while preserving existing escapes and reserved delimiters.
    result = quote(result, safe="/:?#[]@!$&'()*+,;=%-._~")
    return re.sub(r'%[0-9a-fA-F]{2}', lambda m: m.group().upper(), result)


BARE_URL = re.compile(r'(?i)(?:https?://|mailto:)[^\s<>"]+')
MARKDOWN_LINK = re.compile(r'(?<!\\)\[([^\]\n]+)\]\(')


def source_links(text):
    """Locate explicit Markdown links and full bare URLs without guessing hosts.

    Explicit targets retain terminal punctuation and balanced parentheses. Bare
    URLs exclude ordinary sentence punctuation and unmatched closing brackets.
    Use Markdown links to disambiguate a target ending in punctuation.
    """
    explicit, offset = [], 0
    while match := MARKDOWN_LINK.search(text, offset):
        start, index, depth = match.end(), match.end(), 1
        while index < len(text) and depth:
            if text[index] == '\\' and index + 1 < len(text):
                index += 2
                continue
            if text[index] == '(':
                depth += 1
            elif text[index] == ')':
                depth -= 1
            index += 1
        if depth:
            raise ValueError('unclosed Markdown link; use [label](complete-URL)')
        target = text[start:index - 1].replace('\\(', '(').replace('\\)', ')')
        canonical_url(target)
        explicit.append({'start': match.start(), 'end': index, 'label': match.group(1), 'target': target})
        offset = index

    def bare(start, end):
        result = []
        for match in BARE_URL.finditer(text, start, end):
            target = match.group()
            prefix = text[:match.start()]
            while target:
                if target[-1] in '.,;!?:':
                    target = target[:-1]
                elif target.endswith('**') and len(re.findall(r'(?<!\\)\*\*', prefix)) % 2:
                    target = target[:-2]
                elif target.endswith('*') and len(re.findall(r'(?<!\\)\*', prefix.replace('**', ''))) % 2:
                    target = target[:-1]
                elif any(target.endswith(close) and target.count(close) > target.count(opening)
                         for opening, close in [('(', ')'), ('[', ']'), ('{', '}')]):
                    target = target[:-1]
                else:
                    break
            canonical_url(target)
            result.append({'start': match.start(), 'end': match.start() + len(target), 'label': None, 'target': target})
        return result

    found, offset = [], 0
    for link in explicit:
        found.extend(bare(offset, link['start'])); found.append(link); offset = link['end']
    found.extend(bare(offset, len(text)))
    return found


def expected_links(document):
    return [{'target': link['target'], 'text': block['text'][link['start']:link['end']]}
            for block in document['blocks'] for link in block.get('links', [])]


def validate_pdf_links(document, annotations):
    """Match every logical link to its consecutive clickable PDF fragments.

    A wrapped link may have several annotations. Text coverage disambiguates it
    from separate occurrences of the same destination, so a missing repeated
    link cannot hide behind another link's wrap fragments.
    """
    from resume_document import normalized, pdf_wrapping_matches
    if not isinstance(annotations, list) or any(not isinstance(a, dict) or not isinstance(a.get('target'), str)
                                               or not isinstance(a.get('text'), str) for a in annotations):
        raise ValueError('PDF hyperlink annotations were not inspected')
    expected = expected_links(document)
    actual_targets = [canonical_url(a['target']) for a in annotations]
    expected_targets = [canonical_url(a['target']) for a in expected]
    # Dynamic programming permits multiple physical fragments per logical link.
    positions = {0}
    for link, target in zip(expected, expected_targets):
        following = set()
        for start in positions:
            fragments = []
            for end in range(start, len(annotations)):
                if actual_targets[end] != target:
                    break
                fragments.append(annotations[end]['text'].strip())
                recovered = '\n'.join(fragments)
                if normalized(link['text']) == normalized(recovered) or pdf_wrapping_matches(link['text'], recovered):
                    following.add(end + 1)
        positions = following
        if not positions:
            break
    if len(annotations) not in positions:
        raise ValueError('PDF hyperlinks differ from source URLs or clickable text: missing, changed, extra, or incomplete link fragments')
    return {'status': 'verified', 'expected_links': len(expected), 'annotation_fragments': len(annotations),
            'checks': ['source_destinations', 'clickable_text_coverage'], 'website_availability': 'not_checked'}
