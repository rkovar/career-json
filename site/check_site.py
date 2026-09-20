#!/usr/bin/env python3
"""Check the generated public site's local links and publication boundaries."""
import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.ids, self.links, self.images = set(), [], []
        self.has_title = False
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            self.ids.add(attrs['id'])
        if tag == 'title':
            self.has_title = True
        for key in ('href', 'src'):
            if attrs.get(key):
                self.links.append(attrs[key])
        if tag == 'img':
            self.images.append(attrs)


def check(base):
    base = Path(base).resolve()
    errors, count = [], 0
    pages = {path: Page(path.read_text()) for path in base.rglob('*.html')}
    for path, page in pages.items():
        if not page.has_title:
            errors.append(f'{path.relative_to(base)}: missing title')
        for href in page.links:
            url = urlsplit(href)
            if url.scheme or url.netloc:
                continue
            name = unquote(url.path)
            target = (base / name.lstrip('/') if name.startswith('/') else path.parent / name).resolve() if name else path
            if not target.is_relative_to(base):
                errors.append(f'{path.relative_to(base)}: link escapes site: {href}')
                continue
            if target.is_dir():
                target = target / 'index.html'
            if not target.is_file():
                errors.append(f'{path.relative_to(base)}: missing {href}')
            elif url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:
                errors.append(f'{path.relative_to(base)}: missing anchor {href}')
            count += 1
        if not path.relative_to(base).as_posix().startswith('examples/'):
            for image in page.images:
                if 'alt' not in image:
                    errors.append(f'{path.relative_to(base)}: image needs alt text')
    inventory = json.loads((base / 'public-build.json').read_text())
    for name in ('data', 'reviews', 'outputs', 'backups', 'archive', 'archives', '.git', 'node_modules', '.claude'):
        if (base / name).exists():
            errors.append('Unexpected non-website output: ' + name)
    for name in inventory['source_files']:
        if not name.startswith(('docs/', 'graphics/', 'examples/first-pack/')):
            errors.append('Unexpected publication source: ' + name)
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print(f'PASS: {len(pages)} HTML pages, {count} local links, image labels and public publication boundaries.')
    return 0


if __name__ == '__main__':
    sys.exit(check(sys.argv[1]))
