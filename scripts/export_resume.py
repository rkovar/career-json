#!/usr/bin/env python3
"""Export one cited draft to PDF, UTF-8 TXT, editable DOCX and clean Markdown; verify recovered content.

TXT/DOCX use Python's standard library. PDF requires Chrome/Chromium plus Poppler
or macOS Swift/PDFKit for verification. Missing tools are reported as failures,
never treated as verified exports. Submission files and private diagnostics are
separate. Existing export directories are never overwritten.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
import zipfile

from current_pack import ROOT, sha256
from editorial import local, pin, read, pin_errors
from resume_layout import diagnostics as layout_diagnostics, poppler_geometry
from resume_markdown import submission_markdown, validate_markdown
from resume_document import document_from_markdown, paragraphs, plain_text, submission_html, normalized, pdf_wrapping_matches
from resume_links import validate_pdf_links

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
ET.register_namespace('w', W)
ET.register_namespace('r', R)


def element(parent, name, attrs=None, text=None):
    child = ET.SubElement(parent, '{' + W + '}' + name,
                          {'{' + W + '}' + key: str(value) for key, value in (attrs or {}).items()})
    if text is not None: child.text = text
    return child


def xml_bytes(root):
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def write_docx(document, target):
    root = ET.Element('{' + W + '}document')
    body = element(root, 'body')
    for block in document['blocks']:
        p = element(body, 'p'); props = element(p, 'pPr')
        style = {'h1': 'Title', 'h2': 'Heading1', 'h3': 'Heading2', 'h4': 'Heading3', 'li': 'ListParagraph'}.get(block['kind'], 'Normal')
        if block.get('employment_part') == 'position': style = 'Position'
        element(props, 'pStyle', {'val': style})
        if block['kind'] == 'li':
            num = element(props, 'numPr'); element(num, 'ilvl', {'val': 0}); element(num, 'numId', {'val': 1})
        if block['kind'] in ('h1', 'h2', 'h3', 'h4') or style == 'Position': element(props, 'keepNext')
        element(props, 'keepLines')
        run = element(p, 'r'); text = element(run, 't', text=block['text'])
        text.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    section = element(body, 'sectPr')
    width, height = (11906, 16838) if document['paper_size'] == 'A4' else (12240, 15840)
    element(section, 'pgSz', {'w': width, 'h': height})
    element(section, 'pgMar', {'top': 850, 'bottom': 850, 'left': 964, 'right': 964, 'header': 0, 'footer': 0, 'gutter': 0})

    styles = ET.Element('{' + W + '}styles')
    for name, size, bold in [('Normal', 21, False), ('Title', 48, True), ('Heading1', 23, True), ('Heading2', 21, True), ('Heading3', 21, True), ('Position', 20, False), ('ListParagraph', 21, False)]:
        style = element(styles, 'style', {'type': 'paragraph', 'styleId': name})
        if name == 'Normal': style.set('{' + W + '}default', '1')
        element(style, 'name', {'val': name})
        if name != 'Normal': element(style, 'basedOn', {'val': 'Normal'})
        props = element(style, 'pPr'); element(props, 'spacing', {'after': 30 if name == 'Position' else 120, 'line': 300, 'lineRule': 'auto'})
        if name in ('Heading1', 'Heading2', 'Heading3'):
            element(props, 'outlineLvl', {'val': {'Heading1': 0, 'Heading2': 1, 'Heading3': 2}[name]})
            element(props, 'keepNext')
        rprops = element(style, 'rPr'); element(rprops, 'rFonts', {'ascii': 'Georgia', 'hAnsi': 'Georgia'})
        element(rprops, 'sz', {'val': size})
        if bold: element(rprops, 'b')
    numbering = ET.Element('{' + W + '}numbering')
    abstract = element(numbering, 'abstractNum', {'abstractNumId': 0})
    level = element(abstract, 'lvl', {'ilvl': 0})
    element(level, 'start', {'val': 1}); element(level, 'numFmt', {'val': 'bullet'}); element(level, 'lvlText', {'val': '•'})
    pp = element(level, 'pPr'); element(pp, 'ind', {'left': 360, 'hanging': 180})
    num = element(numbering, 'num', {'numId': 1}); element(num, 'abstractNumId', {'val': 0})
    contents = b'''<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/><Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/></Types>'''
    rels = b'''<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'''
    docrels = b'''<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/></Relationships>'''
    payload = {'[Content_Types].xml': contents, '_rels/.rels': rels, 'word/_rels/document.xml.rels': docrels,
               'word/document.xml': xml_bytes(root), 'word/styles.xml': xml_bytes(styles), 'word/numbering.xml': xml_bytes(numbering)}
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(payload.items()):
            entry = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0)); entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, data)


def docx_text(path):
    with zipfile.ZipFile(path) as archive:
        doc = ET.fromstring(archive.read('word/document.xml'))
        return '\n'.join(''.join(t.text or '' for t in p.iter('{' + W + '}t')) for p in doc.iter('{' + W + '}p'))


def chrome_binary():
    for name in ('chromium', 'chromium-browser', 'google-chrome', 'google-chrome-stable'):
        found = shutil.which(name)
        if found: return found
    path = Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    return str(path) if path.exists() else None


def run(command, timeout=55, env=None):
    # Browser helpers can inherit pipes after the parent exits. File-backed
    # output avoids waiting indefinitely on a descendant's open pipe.
    with tempfile.TemporaryFile(mode='w+') as stdout, tempfile.TemporaryFile(mode='w+') as stderr:
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr, env=env, start_new_session=True)
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise
        stdout.seek(0); stderr.seek(0)
        if process.returncode:
            raise ValueError(Path(command[0]).name + f' failed ({process.returncode}): ' + stderr.read()[-1500:])
        return stdout.read()


def write_pdf(html_path, target):
    browser = chrome_binary()
    if not browser: raise ValueError('PDF export requires Chrome or Chromium')
    with tempfile.TemporaryDirectory(prefix='career-pdf-browser-') as temp:
        printed = Path(temp) / 'printed.pdf'
        command = [browser, '--headless', '--disable-gpu', '--disable-background-networking', '--no-first-run',
                   '--no-default-browser-check', '--disable-extensions', '--no-pdf-header-footer',
                   '--user-data-dir=' + str(Path(temp) / 'profile'), '--print-to-pdf=' + str(printed), html_path.resolve().as_uri()]
        with tempfile.TemporaryFile(mode='w+') as log:
            process = subprocess.Popen(command, stdout=log, stderr=log, start_new_session=True)
            deadline, previous, stable = time.monotonic() + 50, None, 0
            try:
                # Some browser versions keep helpers running after printing.
                # Observe a complete, stable file rather than requiring UI exit.
                while time.monotonic() < deadline:
                    data = printed.read_bytes() if printed.exists() else b''
                    signature = (len(data), hashlib.sha256(data).digest())
                    stable = stable + 1 if signature == previous else 0
                    previous = signature
                    if data.startswith(b'%PDF-') and data.rstrip().endswith(b'%%EOF') and stable >= 3:
                        break
                    if process.poll() is not None and not data:
                        log.seek(0)
                        raise ValueError('PDF browser exited without output: ' + log.read()[-1500:])
                    time.sleep(.2)
                else:
                    raise ValueError('PDF browser did not finish printing within 50 seconds')
            finally:
                try: os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError: pass
                try: process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL); process.wait()
            shutil.copyfile(printed, target)
    if not target.is_file() or not target.read_bytes().startswith(b'%PDF-'):
        raise ValueError('browser did not produce a PDF')
    return Path(browser).name


def pdf_details(path):
    if all(shutil.which(name) for name in ('pdftotext', 'pdfinfo', 'pdftohtml')):
        text = run(['pdftotext', '-enc', 'UTF-8', str(path), '-'])
        info = run(['pdfinfo', str(path)])
        pages = re.search(r'^Pages:\s+(\d+)', info, re.M)
        if not pages: raise ValueError('PDF page count unavailable')
        # XML preserves the clickable text fragments and their destinations.
        # No -p flag: that option rewrites .pdf destinations to .html.
        xml = run(['pdftohtml', '-xml', '-stdout', '-i', '-hidden', '-enc', 'UTF-8', str(path.resolve())])
        return {'text': text, 'pages': int(pages.group(1)), 'extractor': 'Poppler', 'links': poppler_links(xml), 'geometry': poppler_geometry(xml)}
    if sys.platform == 'darwin' and shutil.which('swift'):
        with tempfile.TemporaryDirectory(prefix='career-pdf-check-') as temp:
            script = Path(temp) / 'inspect.swift'
            script.write_text('''import Foundation
import PDFKit
guard let doc = PDFDocument(url: URL(fileURLWithPath: CommandLine.arguments[1])) else { exit(1) }
var links: [[String: Any]] = []
var geometry: [[String: Any]] = []
for index in 0..<doc.pageCount {
    guard let page = doc.page(at: index) else { continue }
    let bounds = page.bounds(for: .mediaBox)
    let selection = page.selection(for: bounds)
    let lines: [[String: Any]] = (selection?.selectionsByLine() ?? []).map { line in
        let rect = line.bounds(for: page)
        return ["text": line.string ?? "", "x": rect.minX - bounds.minX, "y": bounds.maxY - rect.maxY,
                "width": rect.width, "height": rect.height]
    }
    geometry.append(["page": index + 1, "width": bounds.width, "height": bounds.height, "lines": lines])
    for annotation in page.annotations where annotation.type == "Link" {
        let action = annotation.action as? PDFActionURL
        links.append(["page": index + 1, "target": action?.url?.absoluteString ?? "",
                      "text": page.selection(for: annotation.bounds)?.string ?? ""])
    }
}
let result: [String: Any] = ["text": doc.string ?? "", "pages": doc.pageCount, "extractor": "PDFKit", "links": links, "geometry": geometry]
let data = try JSONSerialization.data(withJSONObject: result)
print(String(data: data, encoding: .utf8)!)
''')
            env = {**os.environ, 'CLANG_MODULE_CACHE_PATH': str(Path(temp) / 'cache')}
            return json.loads(run(['swift', str(script), str(path)], env=env))
    raise ValueError('PDF text and hyperlink verification requires Poppler (pdftotext, pdfinfo and pdftohtml) or macOS Swift/PDFKit')


def poppler_links(xml):
    try:
        root = ET.fromstring(xml[xml.index('<?xml'):])
    except (ValueError, ET.ParseError) as exc:
        raise ValueError('Poppler hyperlink XML could not be read') from exc
    return [{'page': int(page.get('number', '0')), 'target': anchor.get('href', ''),
             'text': ''.join(anchor.itertext())}
            for page in root.findall('page') for anchor in page.iter('a')]


def validate_content(document, recovered, *, pdf=False):
    expected = normalized('\n'.join(paragraphs(document)))
    actual = normalized(recovered)
    if expected != actual:
        if pdf and pdf_wrapping_matches(expected, recovered):
            return 'expected_text_with_physical_pdf_wraps'
        raise ValueError('extracted content differs from the shared document: missing, added, or misordered text')
    return 'exact_normalized_text'


def validate_export_report(report_path):
    report = read(report_path)
    errors = pin_errors(report['artifact'])
    if report.get('plan'):
        errors.extend(pin_errors(report['plan']))
        if not errors:
            from resume_workflow import checked_plan
            try: checked_plan(report['plan']['path'])
            except ValueError as exc: errors.append(str(exc))
    if not report.get('complete'):
        errors.append('required exports are incomplete or failed validation')
    version = report.get('export_version', 1)
    if type(version) is not int or version not in (1, 2, 3, 4):
        errors.append('unsupported export report version')
        return errors
    required = {'pdf', 'txt', 'docx', 'md'} if version >= 4 else {'pdf', 'txt', 'docx'}
    if version < 2:
        errors.append('legacy export did not verify PDF hyperlinks; create a new export bundle')
    if set(report.get('formats', {})) != required:
        errors.append('export report must account for ' + ', '.join(sorted(required)))
    for fmt, result in report.get('formats', {}).items():
        if result.get('status') != 'verified': errors.append(fmt + ' is not verified')
        if result.get('file'): errors.extend(pin_errors(result['file']))
        else: errors.append(fmt + ' has no file pin')
    if not errors:
        document = document_from_markdown(local(report['artifact']['path']).read_text(encoding='utf-8'))
        if version >= 4:
            try:
                md = report['formats']['md']
                validate_markdown(document, local(md['file']['path']).read_text(encoding='utf-8'))
                if not {'markdown_structure', 'hyperlink_targets'} <= set(md.get('checks', [])):
                    errors.append('Markdown structure/link verification is missing')
            except ValueError as exc:
                errors.append(str(exc))
        pdf = report['formats']['pdf']
        if version >= 3:
            plan = read(report['plan']['path']) if report.get('plan') else None
            if pdf.get('layout') != layout_diagnostics(document, pdf.get('geometry'), plan):
                errors.append('PDF layout diagnostics are missing or inconsistent')
        try:
            links = validate_pdf_links(document, pdf.get('links'))
            if pdf.get('hyperlinks') != links or 'hyperlink_targets' not in pdf.get('checks', []):
                errors.append('PDF hyperlink verification is missing or inconsistent')
        except ValueError as exc:
            errors.append(str(exc))
    return errors


def export(artifact, destination, plan_path=None, paper_size=None, page_limit=None):
    artifact, destination = local(artifact), local(destination)
    if not destination.is_relative_to(local('outputs')):
        raise ValueError('exports belong under outputs/')
    if destination.exists(): raise ValueError('export destination exists; choose a new version directory')
    report = {'export_version': 4, 'artifact': pin(artifact), 'formats': {}, 'complete': False,
              'visual_review': 'not_recorded', 'docx_pagination': 'not_verified_in_Word',
              'accessibility': 'semantic HTML and native DOCX structure; assistive-technology review not performed',
              'ats_compatibility': 'not_tested_against_an_employer_ATS'}
    plan = None
    if plan_path:
        from resume_workflow import checked_plan, default_application, selected_ids
        plan = checked_plan(plan_path)
        selection = read(plan['selection']['path']); brief = read(selection['brief']['path'])
        app = brief.get('application', default_application(audience=brief['audience']))
        if paper_size is not None and paper_size != app['paper_size']:
            raise ValueError('paper size contradicts the pinned brief; revise the brief first')
        if page_limit is not None and page_limit != app['page_limit']:
            raise ValueError('page limit contradicts the pinned brief; revise the brief first')
        paper_size, page_limit = app['paper_size'], app['page_limit']
        report['plan'] = pin(plan_path)
    if page_limit is not None and page_limit < 1: raise ValueError('page limit must be positive')
    document = document_from_markdown(artifact.read_text(encoding='utf-8'), paper_size or 'A4')
    if plan_path:
        cited = {aid for b in document['blocks'] for aid in b['evidence_ids']}
        if not cited <= selected_ids(selection): raise ValueError('draft cites evidence outside its selected plan')
        from validate_artifact import check
        errors, _ = check(artifact, None, read(selection['pack']['path']), audience=brief['audience'], application=app)
        if errors:
            raise ValueError('artifact validation failed: ' + '; '.join(errors))
    report['paper_size'], report['page_limit'] = document['paper_size'], page_limit
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.resume-export-', dir=destination.parent) as temp:
        staging = Path(temp); files = staging / 'files'; files.mkdir()
        review = staging / 'review'; review.mkdir()
        html_path = review / 'preview.html'; html_path.write_text(submission_html(document), encoding='utf-8')
        (review / 'document.json').write_text(json.dumps(document, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        for fmt in ('md', 'txt', 'docx', 'pdf'):
            path = files / ('resume.' + fmt)
            result = {'status': 'failed'}
            try:
                if fmt == 'md':
                    path.write_text(submission_markdown(document), encoding='utf-8')
                    recovered = validate_markdown(document, path.read_text(encoding='utf-8'))
                elif fmt == 'txt':
                    path.write_text(plain_text(document), encoding='utf-8')
                    recovered = path.read_text(encoding='utf-8')
                elif fmt == 'docx':
                    write_docx(document, path); recovered = docx_text(path)
                else:
                    result['renderer'] = write_pdf(html_path, path)
                    details = pdf_details(path); recovered = details.pop('text'); result.update(details)
                    result['hyperlinks'] = validate_pdf_links(document, details.get('links'))
                    result['layout'] = layout_diagnostics(document, details.get('geometry'), plan)
                    if page_limit is not None and details['pages'] > page_limit:
                        raise ValueError(f"PDF has {details['pages']} pages; limit is {page_limit}. Revise content or layout, then re-export.")
                result['content_comparison'] = validate_content(document, recovered, pdf=fmt == 'pdf')
                result['status'] = 'verified'
                result['checks'] = ['text_content', 'reading_order', 'internal_metadata_excluded']
                if fmt == 'pdf': result['checks'].append('hyperlink_targets')
                if fmt == 'md': result['checks'].extend(['markdown_structure', 'hyperlink_targets'])
            except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
                result['error'] = str(exc)
            if path.exists():
                result['file'] = {'path': str((destination / 'files' / path.name).relative_to(ROOT.resolve())), 'sha256': sha256(path)}
            report['formats'][fmt] = result
        report['complete'] = all(row['status'] == 'verified' for row in report['formats'].values())
        if sha256(artifact) != report['artifact']['sha256']:
            raise ValueError('draft changed during export; rerun against stable input')
        if plan_path:
            if pin_errors(report['plan']): raise ValueError('plan changed during export')
            checked_plan(plan_path)
        (review / 'export-report.json').write_text(json.dumps(report, indent=2) + '\n')
        # Exclusive publication protects older bundles and avoids partial writes.
        destination.mkdir()
        try:
            for part in staging.iterdir(): shutil.move(str(part), str(destination / part.name))
        except Exception:
            shutil.rmtree(destination); raise
    return report, destination / 'review/export-report.json'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifact', nargs='?'); parser.add_argument('--output')
    parser.add_argument('--plan'); parser.add_argument('--paper-size', choices=('A4', 'Letter'))
    parser.add_argument('--page-limit', type=int); parser.add_argument('--check', help='verify hashes and completeness of a saved export report')
    args = parser.parse_args(argv)
    try:
        if args.check:
            errors = validate_export_report(args.check)
            if errors: raise ValueError('; '.join(errors))
            print('all required export files match their verified content and inputs'); return 0
        if not args.artifact or not args.output: parser.error('artifact and --output are required for export')
        report, path = export(args.artifact, args.output, args.plan, args.paper_size, args.page_limit)
        for fmt, row in report['formats'].items(): print(fmt.upper() + ': ' + row['status'] + (': ' + row['error'] if row.get('error') else ''))
        print('Report: ' + str(path))
        return 0 if report['complete'] else 1
    except (OSError, ValueError, KeyError) as exc:
        print('error: ' + str(exc), file=sys.stderr); return 1


if __name__ == '__main__':
    sys.exit(main())
