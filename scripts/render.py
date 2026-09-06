#!/usr/bin/env python3
"""Render an artefact Markdown draft to HTML, deterministically.

Rendering was previously improvised in-session, differently each time, which is
how the Markdown and HTML drifted apart and how evidence IDs went missing from one
of them. One template, one code path, no drift.

Evidence comments (<!-- Evidence: E_A, E_B -->) become hidden spans, so both
formats carry the same claim-to-evidence mapping and neither shows it to a reader.

    python3 scripts/render.py outputs/draft.md              # writes outputs/draft.html
    python3 scripts/render.py outputs/draft.md -o other.html
"""
import html as htmllib
import re
import sys
from pathlib import Path

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    @page {{ size: A4; margin: 15mm 17mm; }}
    :root {{ color: #17202a; font-family: Georgia, "Times New Roman", serif; }}
    body {{ margin: 0; background: #eeeae3; }}
    main {{ max-width: 210mm; margin: 0 auto; background: #fff; padding: 15mm 17mm; box-sizing: border-box; }}
    h1 {{ margin: 0; font-size: 26pt; }}
    h2 {{ margin: 18px 0 8px; border-bottom: 1px solid #a44d2f; color: #a44d2f; font-size: 11pt; letter-spacing: .08em; text-transform: uppercase; }}
    h3 {{ margin: 13px 0 4px; font-size: 10.5pt; }}
    p, li {{ font-size: 9.5pt; line-height: 1.35; }}
    .contact {{ margin: 5px 0 16px; color: #59636e; font: 9pt Arial, sans-serif; }}
    ul {{ margin-top: 6px; padding-left: 18px; }}
    li {{ margin-bottom: 7px; }}
    .skills {{ line-height: 1.55; }}
    .evidence {{ display: none; }}
    @media print {{ body {{ background: #fff; }} main {{ max-width: none; padding: 0; }} }}
    @media screen {{ main {{ margin: 20px auto; box-shadow: 0 2px 12px #0002; }} }}
    @media screen and (max-width: 700px) {{ main {{ padding: 28px 22px; }} p, li {{ font-size: 10.5pt; line-height: 1.45; }} }}
  </style>
</head>
<body>
<main>
{body}
</main>
</body>
</html>
"""

EVIDENCE = re.compile(r"\s*<!--\s*Evidence:\s*(.+?)\s*-->")


def inline(text):
    match = EVIDENCE.search(text)
    ids = match.group(1) if match else None
    text = EVIDENCE.sub("", text).strip()
    text = htmllib.escape(text, quote=False)
    # Bold first: a greedy single-asterisk rule would otherwise chew through ** pairs
    # and silently mangle the visible text.
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)
    if ids:
        text += f' <span class="evidence">[{htmllib.escape(ids, quote=False)}]</span>'
    return text


def render(markdown):
    name, role = None, None
    out, in_list = [], False
    lines = markdown.splitlines()
    # The line after the H1 is the contact block, whatever it contains.
    contact_index = None
    for i, line in enumerate(lines):
        if line.startswith("# "):
            for j in range(i + 1, len(lines)):
                if lines[j].strip():
                    contact_index = j
                    break
            break

    for index, line in enumerate(lines):
        if line.startswith("- "):
            if not in_list:
                out.append("    <ul>")
                in_list = True
            out.append(f"      <li>{inline(line[2:])}</li>")
            continue
        if in_list:
            out.append("    </ul>")
            in_list = False
        if line.startswith("### "):
            out.append(f"    <h3>{inline(line[4:])}</h3>")
        elif line.startswith("## "):
            heading = EVIDENCE.sub("", line[3:]).strip()
            if role is None:
                role = heading
            out.append(f"    <h2>{inline(line[3:])}</h2>")
        elif line.startswith("# "):
            name = EVIDENCE.sub("", line[2:]).strip()
            out.append(f"    <h1>{inline(line[2:])}</h1>")
        elif line.strip() and not line.startswith("---"):
            stripped = line.strip()
            if index == contact_index:
                cls = ' class="contact"'
            elif stripped.count("|") > 6:
                cls = ' class="skills"'
            else:
                cls = ""
            out.append(f"    <p{cls}>{inline(stripped)}</p>")
    if in_list:
        out.append("    </ul>")
    title = " - ".join(part for part in (name, role) if part) or "Artefact"
    return TEMPLATE.format(title=htmllib.escape(title, quote=False), body="\n".join(out))


def main(argv):
    if len(argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    source = Path(argv[1])
    target = Path(argv[argv.index("-o") + 1]) if "-o" in argv else source.with_suffix(".html")
    target.write_text(render(source.read_text()))
    print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
