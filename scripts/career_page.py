#!/usr/bin/env python3
"""Render the current pack as a designed, private reading page.

This read-only view presents roles, achievements, strengths, preferences, education,
skills and publications, including withheld content. It is private working
material written to outputs/. The profile contact block is omitted; excerpts may
still contain personal information. Use the JSON export for the complete record.

    python3 scripts/career_page.py                        # outputs/career-record.html
    python3 scripts/career_page.py --pack data/packs/x.json -o outputs/x.html
"""
import argparse
import html as H
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from current_pack import resolve, metric_text, metric_basis, ROOT  # noqa: E402
from pack_io import local
from career_profile import profile_state

MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
STATUS = {"externally_verified": ("Independently verified", "ok"),
          "corroborated": ("Corroborated", "ok"),
          "self_asserted": ("Own account", "own"),
          "unresolved": ("Unresolved", "warn"),
          "declined": ("Restricted", "stop")}
OUTCOME = {"business_outcome": "Outcome", "output": "Output", "activity": "Activity"}


def e(v):
    return H.escape(str(v), quote=True)


def ym(s):
    if not s:
        return ""
    if s in ("present", "ongoing"):
        return "present"
    parts = s.split("-")
    if len(parts) > 1 and parts[1].isdigit() and 1 <= int(parts[1]) <= 12:
        return f"{MONTHS[int(parts[1])]} {parts[0]}"
    return s


def span(start, end):
    if end and end == start:
        return ym(start)
    return f"{ym(start) if start else 'start not recorded'} – {ym(end) if end else 'end not recorded'}"


def linked_title(title, url):
    """Link recorded web URLs only; escape display text and inert invalid targets."""
    if url:
        try:
            parts = urlsplit(url)
            valid = parts.scheme.lower() in ('https', 'http') and parts.hostname and not any(
                ch.isspace() or ord(ch) < 32 for ch in url)
        except ValueError:
            valid = False
        if valid:
            return f'<a href="{e(url)}">{e(title)}</a>'
    return e(title)


def employment_chains(records):
    """Include every descendant in a tenure, rejecting cycles and missing parents."""
    by_id = {r["employment_id"]: r for r in records}
    groups = defaultdict(list)
    for role in records:
        seen, cursor = set(), role
        while cursor.get("parent_employment_id"):
            rid = cursor["employment_id"]
            if rid in seen:
                raise ValueError("cycle in employment parents")
            seen.add(rid)
            parent = cursor["parent_employment_id"]
            if parent not in by_id:
                raise ValueError("unknown employment parent: " + parent)
            cursor = by_id[parent]
        groups[cursor["employment_id"]].append(role)
    return sorted((sorted(chain, key=lambda r: r.get("start") or "") for chain in groups.values()),
                  key=lambda chain: max(r.get("start") or "" for r in chain), reverse=True)


def pill(text, kind=""):
    return f'<span class="pill {kind}">{e(text)}</span>'


def star_html(atom):
    st = atom.get("star") or {}
    out = []
    for k, label in (("situation", "Situation"), ("task", "Task"), ("action", "Action"), ("result", "Result")):
        v = st.get(k)
        if v:
            out.append(f'<p class="star"><span class="lbl">{label}</span>{e(v)}</p>')
    return "".join(out)


def metrics_html(atom):
    ms = atom.get("metrics") or []
    if not ms:
        return ""
    rows = []
    for m in ms:
        basis = metric_basis(m)
        measured = isinstance(m, dict) and m.get("measured")
        how = "measured" if measured is True else "estimate" if measured is False else "stated"
        rows.append(f'<tr><td class="mv">{e(metric_text(m))}</td><td class="mh">{how}</td>'
                    f'<td class="mb">{e(basis) if basis else "<i>no basis recorded</i>"}</td></tr>')
    return ('<table class="metrics"><thead><tr><th>Figure</th><th>How</th><th>Basis</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>')


def supporting_detail(record):
    """Keep material qualifications visible, with provenance available on demand."""
    parts = []
    if record.get('constraints'):
        parts.append('<div class="handle"><span class="lbl">Handling</span><ul>' +
                     ''.join(f'<li>{e(c)}</li>' for c in record['constraints']) + '</ul></div>')
    if record.get('notes'):
        parts.append('<details class="sources"><summary>Recorded context</summary><p>' + e(record['notes']) + '</p></details>')
    refs = record.get('source_refs') or []
    if refs:
        items = ''.join('<li><span class="mono src">' + e(r['source_id']) + '</span>'
                        + (f'<span class="loc">{e(r["locator"])}</span>' if r.get('locator') else '')
                        + (f'<blockquote>{e(r["excerpt"])}</blockquote>' if r.get('excerpt') else '<p>No excerpt recorded.</p>')
                        + '</li>' for r in refs)
        parts.append(f'<details class="sources"><summary>{len(refs)} source reference{"s" if len(refs) != 1 else ""}</summary><ul>{items}</ul></details>')
    return ''.join(parts)


def atom_html(atom):
    status, kind = STATUS.get(atom.get("evidence_status"), (atom.get("evidence_status"), ""))
    pills = [pill(status, kind)]
    oc = atom.get("outcome_type")
    if oc:
        pills.append(pill(OUTCOME[oc], "oc-" + oc))
    if not atom.get("external_safe"):
        pills.append(pill("Private", "stop"))
    occ = atom.get("occurred") or {}
    when = (span(occ.get("start"), occ["end"]) if occ.get("end") else ym(occ.get("start"))) if occ else "undated"
    if occ.get("inferred"):
        when += " · inferred"
    parts = [f'<article class="entry{"" if atom.get("external_safe") else " private"}" id="{e(atom["id"])}">',
             f'<header><div class="when mono">{e(when)}</div><h4>{e(atom["title"])}</h4>'
             f'<div class="pills">{"".join(pills)}</div></header>',
             star_html(atom), metrics_html(atom)]
    parts.append(supporting_detail(atom))
    if atom.get("role_fit_notes"):
        parts.append(f'<p class="fit"><span class="lbl">Role relevance</span>{e(atom["role_fit_notes"])}</p>')
    if atom.get("open_questions"):
        parts.append('<p class="open"><span class="lbl">Open</span>' + e(" ".join(atom["open_questions"])) + "</p>")
    parts.append("</article>")
    return "".join(parts)


def publications_html(pack):
    """Read only canonical publication records; raw sources require normal intake."""
    pubs = pack.get("publications") or []
    if not pubs:
        return '<p class="none">No publication records saved. Add source material through career intake to propose them for review.</p>'
    order = ["keynote", "talk", "book", "book_contribution", "report", "paper", "article", "blog_post", "podcast", "video", "course", "software", "dataset", "committee", "other"]
    labels = {"keynote": "Keynotes", "talk": "Conference talks", "book": "Books", "book_contribution": "Book contributions", "report": "Reports", "paper": "Papers",
              "article": "Articles", "blog_post": "Blog posts", "podcast": "Podcasts and webcasts", "video": "Video interviews", "course": "Courses",
              "software": "Software", "dataset": "Datasets", "committee": "Committees and boards", "other": "Other"}
    groups = defaultdict(list)
    for pub in pubs:
        groups[pub["kind"]].append(pub)
    out = []
    for kind in order + sorted(set(groups) - set(order)):
        items = sorted(groups.get(kind, []), key=lambda x: x.get("date") or "", reverse=True)
        if not items:
            continue
        rows = []
        for i in items:
            status, skind = STATUS.get(i.get("evidence_status"), (i.get("evidence_status"), ""))
            head = linked_title(i["title"], i.get("url"))
            meta = " · ".join(x for x in [i.get("venue"), (i.get("role") or "").replace("_", " ") or None,
                                          ("with " + ", ".join(i["collaborators"])) if i.get("collaborators") else None] if x)
            rows.append('<li' + ("" if i.get("external_safe") else ' class="private"') + f'><div class="pub-head">{head}<span class="mono">{e(ym(i.get("date")) if i.get("date") and len(i["date"]) <= 7 else (i.get("date") or "undated"))}</span></div>'
                        f'<div class="pub-meta"><span class="mono">{e(meta)}</span> {pill(status, skind)}{"" if i.get("external_safe") else pill("Private", "stop")}</div>'
                        + (f'<p>{e(i["description"])}</p>' if i.get("description") else "") + supporting_detail(i) + "</li>")
        out.append(f'<div class="pubgroup"><h3>{e(labels.get(kind, kind.replace("_", " ").title()))} <span class="count mono">{len(items)}</span></h3><ul class="pubs">{"".join(rows)}</ul></div>')
    return "".join(out)


def build(pack, pack_path):
    atoms = pack["evidence_atoms"]
    employment = pack.get("employment", [])
    chains = employment_chains(employment)
    by_emp = defaultdict(list)
    for a in atoms:
        by_emp[a.get("employment_id")].append(a)
    for lst in by_emp.values():
        lst.sort(key=lambda a: (a.get("occurred") or {}).get("start", "0"), reverse=True)

    first = min((x.get("start") or "" for x in employment), default="")
    n_ver = sum(a["evidence_status"] == "externally_verified" for a in atoms)
    n_out = sum(a.get("outcome_type") == "business_outcome" for a in atoms)

    nav, blocks = [], []
    for chain in chains:
        root = chain[0]
        ids = [x["employment_id"] for x in chain]
        entries = [a for i in ids for a in by_emp.get(i, [])]
        entries.sort(key=lambda a: (a.get("occurred") or {}).get("start", "0"), reverse=True)
        ends = [x.get("end") for x in chain]
        end = "present" if "present" in ends else None if None in ends else max(ends)
        anchor = e(root["employment_id"])
        nav.append(f'<a href="#{anchor}"><span class="mono">{e(root["start"][:4])}</span>{e(root["employer"])}</a>')
        from career_state import uncertainty
        titles = "".join(f'<li><span class="mono">{e(span(x["start"], x["end"]))}</span>{e(x["title"])}'
                         + (f'<p class="open">{e(uncertainty(x))}</p>' if uncertainty(x) else '') + '</li>' for x in reversed(chain))
        scope = (chain[-1].get("scope") or {})
        scope_rows = "".join(f'<div><dt>{e(k.replace("_", " "))}</dt><dd>{e(v)}</dd></div>'
                             for k, v in (("remit", scope.get("remit")), ("team", scope.get("team_size")),
                                          ("reports", scope.get("direct_reports")), ("budget", scope.get("budget")),
                                          ("organisation", scope.get("org_size")), ("geography", scope.get("geography"))) if v)
        blocks.append(
            f'<section class="role" id="{anchor}">'
            f'<div class="rail"><span class="dot"></span></div>'
            f'<div class="role-body"><div class="role-head"><div class="mono span">{e(span(root["start"], end))}</div>'
            f'<h2>{e(root["employer"])}</h2><ul class="titles">{titles}</ul>'
            + (f'<dl class="scope">{scope_rows}</dl>' if scope_rows else "")
            + (f'<p class="loc mono">{e(chain[-1].get("location") or "")}</p>' if chain[-1].get("location") else "")
            + '</div>'
            + "".join(atom_html(a) for a in entries)
            + (f'<p class="none">No achievements recorded for this role.</p>' if not entries else "")
            + '</div></section>')

    known_ids = {r["employment_id"] for r in employment}
    loose = [a for a in atoms if a.get("employment_id") not in known_ids]
    if loose:
        nav.append('<a href="#independent"><span class="mono">—</span>Other recorded work</a>')
        blocks.append('<section class="role" id="independent"><div class="rail"><span class="dot"></span></div><div class="role-body">'
                      '<div class="role-head"><h2>Other recorded work</h2><p class="lede">Achievements without a recorded link to a displayed role.</p></div>'
                      + "".join(atom_html(a) for a in loose) + '</div></section>')

    edu = "".join(f'<div class="edu"><div class="mono">{e(span(x.get("start"), x.get("end")))}</div><h3>{e(x["qualification"])}{", " + e(x["field"]) if x.get("field") else ""}</h3>'
                  f'<p>{e(x["institution"])}{" · " + e(x["grade"]) if x.get("grade") else ""}{" · " + e(x["location"]) if x.get("location") else ""}</p></div>'
                  for x in pack.get("education", []))

    titles_by_id = {a["id"]: a["title"] for a in atoms}
    strengths = "".join(
        f'<article class="strength"><div class="pills">{pill(profile_state(s, pack).replace("_", " ").capitalize(), "ok" if profile_state(s, pack) == "confirmed" else "")}'
        f'{pill(s["basis"].replace("_", " "))}{"" if s.get("external_safe") else pill("Private", "stop")}</div><h3>{e(s["interpretation"])}</h3>'
        f'<p class="lbl">Supported by</p><ul class="support">' + "".join(f'<li><a href="#{e(i)}">{e(titles_by_id.get(i, i))}</a></li>' for i in s["evidence_ids"]) + "</ul>"
        + (f'<p class="lbl">Limits</p><ul class="limits">' + "".join(f"<li>{e(l)}</li>" for l in s["limitations"]) + "</ul>" if s.get("limitations") else "")
        + "</article>" for s in pack.get("strengths_profile", []))
    prefs = "".join(f'<li><span class="mono">{e(p["kind"].replace("_", " "))}</span>{e(p["text"])} '
                    f'{pill(p.get("status", "not recorded").capitalize())}'
                    f'{"" if p.get("external_safe") else pill("Private", "stop")}</li>'
                    for p in pack.get("positioning_preferences", []))
    skills = "".join(f'<div class="skillgroup"><h4>{e(g)}</h4><p>{e(", ".join(v))}</p></div>' for g, v in (pack.get("skills") or {}).items())

    return TEMPLATE.format(
        name=e(pack.get("name", "Career record")), first=e(first[:4] or "not recorded"), today=e(date.today().isoformat()),
        pack=e(str(pack_path)), n_atoms=len(atoms), n_roles=len(chains), n_ver=n_ver, n_out=n_out,
        nav="".join(nav), blocks="".join(blocks), edu=edu, strengths=strengths, prefs=prefs, skills=skills, pubs=publications_html(pack),
        location=e((pack.get("private_profile") or {}).get("location") or ""))


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name} · Career Record</title>
<style>
:root {{
  --paper:#F5F7F9; --surface:#FFFFFF; --ink:#141A22; --text:#3B4653; --muted:#6B7683; --line:#D9DFE6; --line-soft:#E8ECF0;
  --accent:#1D4ED8; --accent-soft:#E4ECFF; --ok:#1E7F4F; --ok-soft:#DFF3E7; --own:#9A6700; --own-soft:#FBF0D3;
  --stop:#A32D2D; --stop-soft:#F8E1E1; --rail:#C9D2DC;
  --display:"Spectral", Georgia, "Times New Roman", serif; --body:"Public Sans", "Helvetica Neue", Arial, sans-serif; --mono:"JetBrains Mono", "SFMono-Regular", Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --paper:#0F141A; --surface:#161C24; --ink:#EEF2F6; --text:#C3CCD6; --muted:#8A96A3; --line:#2A333E; --line-soft:#1F2731;
  --accent:#7FA4FF; --accent-soft:#1B2A4A; --ok:#5FCB8E; --ok-soft:#153324; --own:#E3B341; --own-soft:#3A2E10; --stop:#F08A8A; --stop-soft:#3F1B1B; --rail:#2E3947;
}} }}
:root[data-theme="dark"] {{
  --paper:#0F141A; --surface:#161C24; --ink:#EEF2F6; --text:#C3CCD6; --muted:#8A96A3; --line:#2A333E; --line-soft:#1F2731;
  --accent:#7FA4FF; --accent-soft:#1B2A4A; --ok:#5FCB8E; --ok-soft:#153324; --own:#E3B341; --own-soft:#3A2E10; --stop:#F08A8A; --stop-soft:#3F1B1B; --rail:#2E3947;
}}
* {{ box-sizing:border-box; }}
html {{ scroll-behavior:smooth; }}
@media (prefers-reduced-motion: reduce) {{ html {{ scroll-behavior:auto; }} }}
body {{ margin:0; background:var(--paper); color:var(--text); font-family:var(--body); font-size:16px; line-height:1.55; }}
a {{ color:var(--accent); text-decoration:none; }} a:hover, a:focus-visible {{ text-decoration:underline; }}
:focus-visible {{ outline:2px solid var(--accent); outline-offset:2px; }}
.mono {{ font-family:var(--mono); font-size:0.78rem; letter-spacing:0.01em; font-variant-numeric:tabular-nums; color:var(--muted); }}
.lbl {{ display:block; font-family:var(--mono); font-size:0.68rem; text-transform:uppercase; letter-spacing:0.12em; color:var(--muted); margin:0 0 0.15rem; }}
h1,h2,h3,h4 {{ font-family:var(--display); color:var(--ink); text-wrap:balance; margin:0; font-weight:600; }}

.masthead {{ border-bottom:1px solid var(--line); background:var(--surface); }}
.masthead .inner {{ max-width:1180px; margin:0 auto; padding:2.4rem 2rem 1.8rem; display:grid; grid-template-columns:1fr auto; gap:2rem; align-items:end; }}
.masthead h1 {{ font-size:clamp(2.2rem,4vw,3.2rem); line-height:1.05; letter-spacing:-0.01em; }}
.masthead .sub {{ margin:0.6rem 0 0; font-size:1.05rem; color:var(--text); max-width:60ch; }}
.masthead .kicker {{ font-family:var(--mono); font-size:0.72rem; text-transform:uppercase; letter-spacing:0.14em; color:var(--accent); margin-bottom:0.8rem; }}
.ledger {{ display:grid; grid-auto-flow:column; gap:0; border:1px solid var(--line); border-radius:4px; overflow:hidden; }}
.ledger div {{ padding:0.7rem 1.1rem; border-left:1px solid var(--line); }} .ledger div:first-child {{ border-left:0; }}
.ledger b {{ display:block; font-family:var(--display); font-size:1.7rem; color:var(--ink); line-height:1; font-variant-numeric:tabular-nums; }}
.ledger span {{ font-family:var(--mono); font-size:0.66rem; text-transform:uppercase; letter-spacing:0.1em; color:var(--muted); }}
.ledger .ok b {{ color:var(--ok); }}

.page {{ max-width:1180px; margin:0 auto; padding:2rem; display:grid; grid-template-columns:220px minmax(0,1fr); gap:3rem; }}
nav.side {{ position:sticky; top:1.5rem; align-self:start; }}
nav.side .lbl {{ margin-bottom:0.6rem; }}
nav.side a {{ display:grid; grid-template-columns:3.2rem 1fr; gap:0.4rem; padding:0.35rem 0; color:var(--text); border-top:1px solid var(--line-soft); font-size:0.9rem; }}
nav.side a:hover {{ color:var(--accent); text-decoration:none; }}
nav.side .jump {{ margin-top:1.4rem; display:flex; flex-direction:column; gap:0.2rem; }}
nav.side .jump a {{ grid-template-columns:1fr; border:0; padding:0.2rem 0; }}

main {{ min-width:0; overflow-wrap:anywhere; }}
.role {{ display:grid; grid-template-columns:1.6rem minmax(0,1fr); gap:1rem; }}
.rail {{ position:relative; }} .rail::before {{ content:""; position:absolute; left:0.55rem; top:0.9rem; bottom:-1rem; width:2px; background:var(--rail); }}
.rail .dot {{ position:absolute; left:0.15rem; top:0.5rem; width:0.85rem; height:0.85rem; border-radius:50%; background:var(--accent); border:3px solid var(--paper); box-shadow:0 0 0 1px var(--rail); }}
.role:last-of-type .rail::before {{ bottom:auto; height:2rem; }}
.role-body {{ padding-bottom:2.6rem; display:flex; flex-direction:column; gap:1rem; }}
.role-head {{ padding-bottom:0.4rem; }}
.role-head h2 {{ font-size:1.9rem; line-height:1.15; }}
.role-head .span {{ color:var(--accent); margin-bottom:0.3rem; }}
.titles {{ list-style:none; margin:0.5rem 0 0; padding:0; display:flex; flex-direction:column; gap:0.15rem; font-size:0.95rem; color:var(--ink); }}
.titles li {{ display:grid; grid-template-columns:11rem 1fr; gap:0.6rem; }}
.scope {{ margin:0.9rem 0 0; display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,15rem),1fr)); gap:0.5rem 1.4rem; font-size:0.88rem; }}
.scope dt {{ font-family:var(--mono); font-size:0.66rem; text-transform:uppercase; letter-spacing:0.1em; color:var(--muted); }}
.scope dd {{ margin:0; color:var(--text); }}
.lede {{ margin:0.4rem 0 0; max-width:60ch; }}
.loc {{ margin:0.4rem 0 0; }}

.entry {{ background:var(--surface); border:1px solid var(--line); border-radius:4px; padding:1.1rem 1.3rem 1rem; max-width:76ch; }}
.entry.private {{ border-style:dashed; border-color:var(--stop); }}
.entry header {{ display:flex; flex-direction:column; gap:0.35rem; margin-bottom:0.7rem; }}
.entry h4 {{ font-size:1.18rem; line-height:1.3; }}
.pills {{ display:flex; flex-wrap:wrap; gap:0.35rem; }}
.pill {{ font-family:var(--mono); font-size:0.66rem; text-transform:uppercase; letter-spacing:0.08em; padding:0.18rem 0.5rem; border-radius:2px; background:var(--line-soft); color:var(--text); }}
.pill.ok {{ background:var(--ok-soft); color:var(--ok); }} .pill.own {{ background:var(--own-soft); color:var(--own); }}
.pill.stop {{ background:var(--stop-soft); color:var(--stop); }} .pill.warn {{ background:var(--own-soft); color:var(--own); }}
.pill.oc-business_outcome {{ background:var(--accent-soft); color:var(--accent); }}
p.star {{ margin:0 0 0.45rem; font-size:0.95rem; }} p.star .lbl {{ display:inline; margin-right:0.5rem; }}
table.metrics {{ width:100%; border-collapse:collapse; margin:0.7rem 0 0.3rem; font-size:0.86rem; }}
table.metrics th {{ text-align:left; font-family:var(--mono); font-size:0.64rem; text-transform:uppercase; letter-spacing:0.1em; color:var(--muted); font-weight:500; padding:0.3rem 0.5rem 0.3rem 0; border-bottom:1px solid var(--line); }}
table.metrics td {{ padding:0.4rem 0.5rem 0.4rem 0; border-bottom:1px solid var(--line-soft); vertical-align:top; }}
td.mv {{ color:var(--ink); font-weight:500; white-space:nowrap; }} td.mh {{ font-family:var(--mono); font-size:0.72rem; color:var(--muted); white-space:nowrap; }} td.mb {{ color:var(--text); }}
.handle {{ margin-top:0.7rem; padding:0.6rem 0.8rem; background:var(--paper); border-left:3px solid var(--own); font-size:0.86rem; }}
.handle ul {{ margin:0; padding-left:1.1rem; }} .handle li + li {{ margin-top:0.25rem; }}
p.fit, p.open {{ font-size:0.86rem; margin:0.6rem 0 0; }} p.fit .lbl, p.open .lbl {{ display:inline; margin-right:0.5rem; }}
details.sources {{ margin-top:0.7rem; font-size:0.86rem; }} details.sources summary {{ cursor:pointer; color:var(--accent); font-family:var(--mono); font-size:0.74rem; }}
details.sources ul {{ list-style:none; margin:0.5rem 0 0; padding:0; display:flex; flex-direction:column; gap:0.6rem; }}
details.sources .src {{ color:var(--accent); }} details.sources .loc {{ margin-left:0.6rem; font-size:0.78rem; color:var(--muted); }}
details.sources blockquote {{ margin:0.2rem 0 0; padding:0.4rem 0.8rem; border-left:2px solid var(--line); color:var(--text); font-family:var(--display); font-style:italic; white-space:pre-line; }}
.none {{ color:var(--muted); font-style:italic; }}

.section {{ margin-top:1rem; padding-top:2rem; border-top:1px solid var(--line); }}
.section > h2 {{ font-size:1.9rem; margin-bottom:0.3rem; }} .section > .lede {{ margin-bottom:1.4rem; }}
.strengths {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(min(100%,20rem),1fr)); gap:1rem; }}
.strength {{ background:var(--surface); border:1px solid var(--line); border-radius:4px; padding:1.1rem 1.3rem; display:flex; flex-direction:column; gap:0.5rem; }}
.strength h3 {{ font-size:1.15rem; line-height:1.3; }}
.strength ul {{ margin:0; padding-left:1.1rem; font-size:0.86rem; }} .strength .support a {{ color:var(--ink); }} .strength .limits {{ color:var(--muted); }}
.prefs {{ list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:0.5rem; max-width:72ch; }}
.prefs li {{ display:grid; grid-template-columns:8rem 1fr; gap:0.8rem; }}
.edu {{ max-width:72ch; margin-bottom:1rem; }} .edu h3 {{ font-size:1.15rem; }} .edu p {{ margin:0.2rem 0 0; }}
.skills {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(min(100%,18rem),1fr)); gap:0.8rem 2rem; }}
.skillgroup h4 {{ font-family:var(--mono); font-size:0.68rem; text-transform:uppercase; letter-spacing:0.12em; color:var(--muted); font-weight:500; margin-bottom:0.2rem; }}
.skillgroup p {{ margin:0; font-size:0.9rem; }}
.pubgroup {{ margin-bottom:1.8rem; max-width:76ch; }} .pubgroup h3 {{ font-size:1.25rem; margin-bottom:0.2rem; }} .pubgroup .count {{ margin-left:0.5rem; }}
.src-note {{ margin:0 0 0.6rem; font-size:0.84rem; color:var(--muted); }}
ul.posts {{ margin:0; padding-left:1.1rem; columns:2; column-gap:2rem; font-size:0.9rem; }} ul.posts li {{ break-inside:avoid; margin-bottom:0.25rem; }}
ul.pubs {{ list-style:none; margin:0.4rem 0 0; padding:0; display:flex; flex-direction:column; gap:0.7rem; }}
ul.pubs li {{ padding-bottom:0.7rem; border-bottom:1px solid var(--line-soft); }}
.pub-head {{ display:flex; justify-content:space-between; gap:1rem; align-items:baseline; font-size:0.98rem; color:var(--ink); }} .pub-head a {{ color:var(--ink); }} .pub-head .mono {{ white-space:nowrap; }}
.pub-meta {{ margin-top:0.2rem; display:flex; gap:0.5rem; align-items:center; flex-wrap:wrap; }} ul.pubs li.private {{ border-left:2px dashed var(--stop); padding-left:0.6rem; }} ul.pubs p {{ margin:0.25rem 0 0; font-size:0.88rem; }}
@media (max-width: 860px) {{ ul.posts {{ columns:1; }} }}
footer {{ max-width:1180px; margin:0 auto; padding:1.5rem 2rem 3rem; border-top:1px solid var(--line); }}
@media (max-width: 860px) {{ .page {{ grid-template-columns:1fr; gap:1.5rem; }} nav.side {{ position:static; }} .masthead .inner {{ grid-template-columns:1fr; }} .ledger {{ grid-auto-flow:row; grid-template-columns:repeat(2,1fr); }} .ledger div {{ border-left:0; border-top:1px solid var(--line); }} .titles li {{ grid-template-columns:1fr; gap:0; }} td.mv {{ white-space:normal; }} }}
</style>
</head>
<body>
<header class="masthead"><div class="inner">
  <div><div class="kicker">Career record · private · {location}</div>
  <h1>{name}</h1>
  <p class="sub">Recorded achievements and their available source excerpts. Evidence labels reflect the saved pack; this reading view does not verify or approve claims.</p></div>
  <div class="ledger"><div><b>{n_roles}</b><span>tenures · first date {first}</span></div><div><b>{n_atoms}</b><span>achievements</span></div><div class="ok"><b>{n_ver}</b><span>independently verified</span></div><div><b>{n_out}</b><span>business outcomes</span></div></div>
</div></header>
<div class="page">
<nav class="side"><span class="lbl">Timeline</span>{nav}
  <div class="jump"><span class="lbl">Sections</span><a href="#strengths">Strengths</a><a href="#direction">Direction</a><a href="#publications">Publications</a><a href="#education">Education</a><a href="#skills">Capabilities</a></div></nav>
<main>
{blocks}
<section class="section" id="strengths"><h2>Strengths</h2><p class="lede">Recorded interpretations, their current review state, supporting achievements and limitations. Changed support is marked stale.</p><div class="strengths">{strengths}</div></section>
<section class="section" id="direction"><h2>Direction</h2><p class="lede">Recorded preferences and their review state. Rejected or proposed preferences are not confirmed direction.</p><ul class="prefs">{prefs}</ul></section>
<section class="section" id="publications"><h2>Publications, talks and media</h2><p class="lede">Publication records with their saved evidence status and external-use permission.</p>{pubs}</section>
<section class="section" id="education"><h2>Education</h2>{edu}</section>
<section class="section" id="skills"><h2>Capabilities</h2><div class="skills">{skills}</div></section>
</main>
</div>
<footer><span class="mono">Rendered {today} from {pack}. Private working view: includes restricted records. The profile contact block is omitted; source excerpts may contain personal information.</span></footer>
</body>
</html>
"""


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pack")
    ap.add_argument("-o", "--output", default="outputs/career-record.html")
    args = ap.parse_args(argv)
    try:
        path = local(args.pack) if args.pack else resolve()
        if not path:
            raise ValueError("no current pack")
        path = local(path)
        out = local(args.output)
        if not out.is_relative_to(local("outputs")) or out.suffix.lower() != ".html":
            raise ValueError("private reading pages belong under outputs/ with an .html extension")
        from career_markdown import refresh
        refresh(path, out)
        print(out.relative_to(ROOT.resolve()))
        print('outputs/career.md')
        return 0
    except (ValueError, KeyError, OSError) as exc:
        print("error: " + str(exc), file=sys.stderr)
        return 1



if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
