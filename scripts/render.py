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
LINK = re.compile(r"\[(.+?)\]\((.+?)\)")
# A link target must be one of these, or the text is rendered without the link.
# Anything else (javascript:, data:, a bare quote that closes the attribute) is
# untrusted content reaching an attribute, which is exactly where escaping with
# quote=False stops being enough.
SAFE_SCHEMES = ("http://", "https://", "mailto:")
# Section headings that name a part of the document rather than the role it
# targets. The first H2 that is not one of these names the page title.
SECTIONS = {"experience", "employment", "education", "skills", "summary", "profile",
            "certifications", "publications", "teaching", "research", "awards", "projects",
            "languages", "interests", "references", "speaking", "recognition", "volunteering"}


def is_section(heading):
    """A heading whose first word names a part of a resume ("Teaching, research
    and standing") rather than a role. Judged on the first word so the list stays
    generic instead of enumerating one person's headings."""
    words = re.findall(r"[a-z]+", heading.lower())
    return bool(words) and words[0] in SECTIONS


def link(match):
    text, target = match.group(1), htmllib.unescape(match.group(2))
    if not target.lower().startswith(SAFE_SCHEMES):
        return text
    return f'<a href="{htmllib.escape(target, quote=True)}">{text}</a>'


def inline(text):
    # Every citation in the block, not the first: a summary paragraph with an
    # inline comment and an end comment lost the second set in the HTML, so the
    # Markdown and the HTML cited different evidence.
    found = [m.group(1) for m in EVIDENCE.finditer(text)]
    ids = ", ".join(found) if found else None
    text = EVIDENCE.sub("", text).strip()
    text = htmllib.escape(text, quote=False)
    # Bold first: a greedy single-asterisk rule would otherwise chew through ** pairs
    # and silently mangle the visible text.
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", text)
    text = LINK.sub(link, text)
    if ids:
        text += f' <span class="evidence">[{htmllib.escape(ids, quote=False)}]</span>'
    return text


def blocks(markdown):
    """Group source lines into blocks the way Markdown reads them: a heading or
    list item is its own block; consecutive text lines are one paragraph until a
    blank line; a line indented under a list item continues that item.

    The renderer used to emit every physical line as a paragraph, so a summary
    soft-wrapped at eighty columns became five paragraphs and its evidence
    comment, on a line of its own, a sixth. The Markdown said one thing and the
    HTML another, which is the drift this script exists to prevent."""
    out, para = [], []

    def flush():
        if para:
            out.append(("p", " ".join(para)))
            para.clear()

    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("---"):
            flush()
            continue
        if line.startswith("- "):
            flush()
            out.append(("li", line[2:].strip()))
        elif line[:1].isspace() and out and out[-1][0] == "li" and not para:
            out[-1] = ("li", out[-1][1] + " " + stripped)
        elif line.startswith("### "):
            flush()
            out.append(("h3", line[4:].strip()))
        elif line.startswith("## "):
            flush()
            out.append(("h2", line[3:].strip()))
        elif line.startswith("# "):
            flush()
            out.append(("h1", line[2:].strip()))
        else:
            para.append(stripped)
    flush()
    return out


def render(markdown):
    name, role = None, None
    out, in_list = [], False
    # The first paragraph after the H1 is the contact block, whatever it contains.
    contact_pending = False

    for kind, text in blocks(markdown):
        if kind == "li":
            if not in_list:
                out.append("    <ul>")
                in_list = True
            out.append(f"      <li>{inline(text)}</li>")
            continue
        if in_list:
            out.append("    </ul>")
            in_list = False
        if kind == "h3":
            out.append(f"    <h3>{inline(text)}</h3>")
        elif kind == "h2":
            heading = EVIDENCE.sub("", text).strip()
            if role is None and not is_section(heading):
                role = heading
            out.append(f"    <h2>{inline(text)}</h2>")
        elif kind == "h1":
            name = EVIDENCE.sub("", text).strip()
            contact_pending = True
            out.append(f"    <h1>{inline(text)}</h1>")
        else:
            if contact_pending:
                cls = ' class="contact"'
                contact_pending = False
            elif text.count("|") > 6:
                cls = ' class="skills"'
            else:
                cls = ""
            out.append(f"    <p{cls}>{inline(text)}</p>")
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
