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
    p, li {{ font-size: 10.5pt; line-height: 1.35; orphans: 2; widows: 2; }}
    h2, h3 {{ break-after: avoid; page-break-after: avoid; }}
    h3 + p, h3 + p + p {{ break-after: avoid; page-break-after: avoid; }}
    li {{ break-inside: avoid; page-break-inside: avoid; }}
    .role {{ margin: 4px 0 8px; border: 0; color: #17202a; font: bold 12pt Arial, sans-serif; letter-spacing: 0; text-transform: none; }}
    .dates {{ white-space: nowrap; font-weight: normal; }}
    .contact {{ margin: 5px 0 12px; color: #59636e; font: 9.5pt Arial, sans-serif; }}
    a {{ color: inherit; text-decoration-color: #a44d2f; overflow-wrap: anywhere; }}
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
            "languages", "interests", "references", "speaking", "recognition", "volunteering",
            "hands", "selected", "earlier", "technical", "professional"}


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


def header(parts):
    """Locate the role, contact and summary without confusing a title for contact.

    New drafts use an H2 role before the contact paragraph. Accept the previous
    contact-then-H2 convention too, and legacy paragraph titles when followed by
    an identifiable contact block. Location-only public contacts need no email.
    The first real section ends the header; later headings cannot rename a CV.
    """
    role, contact, paragraphs = None, None, []
    for index, (kind, text) in enumerate(parts):
        if kind in ("h3", "li") or (kind == "h2" and is_section(text)):
            break
        if kind == "h2" and role is None:
            role = index
        elif kind == "p":
            paragraphs.append(index)
    if paragraphs:
        contact = paragraphs[0]
        if role is None and len(paragraphs) >= 2:
            first, second = (parts[i][1] for i in paragraphs[:2])
            contact_marker = r"@|linkedin\.com/|\+\d[\d .()-]{6,}"
            if (len(first.split()) <= 12 and not EVIDENCE.search(first)
                    and not re.search(contact_marker, first)
                    and re.search(contact_marker, second)):
                role, contact = paragraphs[:2]
    summary = [i for i in paragraphs if i not in (role, contact)]
    return role, contact, summary


def render(markdown):
    name, role = None, None
    out, in_list = [], False
    parts = blocks(markdown)
    role_index, contact_index, _ = header(parts)

    for index, (kind, text) in enumerate(parts):
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
            # Keep an employment date range together even when the long official
            # employer/title wraps. Other H3 headings remain ordinary Markdown.
            fields = text.rsplit("|", 1)
            if len(fields) == 2 and re.match(r"\s*\d{4}\b", fields[1]):
                body = f'{inline(fields[0])} | <span class="dates">{inline(fields[1])}</span>'
            else:
                body = inline(text)
            out.append(f"    <h3>{body}</h3>")
        elif kind == "h2":
            heading = EVIDENCE.sub("", text).strip()
            if index == role_index:
                role = heading
            cls = ' class="role"' if index == role_index else ""
            out.append(f"    <h2{cls}>{inline(text)}</h2>")
        elif kind == "h1":
            name = EVIDENCE.sub("", text).strip()
            out.append(f"    <h1>{inline(text)}</h1>")
        else:
            if index == role_index:
                role = EVIDENCE.sub("", text).strip()
                cls = ' class="role"'
            elif index == contact_index:
                cls = ' class="contact"'
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
