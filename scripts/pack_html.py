#!/usr/bin/env python3
"""Render the whole pack as one browsable page, for reading and reviewing it.

A pack is the product, and until now the only way to read one was to open the
JSON. That is fine for ten atoms and useless for a hundred, and it makes the one
job the pack most needs, reviewing whether each atom is classified and measured
correctly, harder than it should be.

This is a **private working view**, not an artefact. Like an interview brief it
deliberately includes atoms no document may cite, marked as withheld, because the
point is to see the whole record. It is written to the gitignored `outputs/` and
must never be sent.

Contact details are deliberately not rendered. Reviewing atoms does not need an
email address, and a file that does not contain one cannot leak it.

`render.py` is not reused: its template is A4 print geometry for a resume, and
this is a screen tool. Sharing one would make both worse.

    python3 scripts/pack_html.py                      # outputs/pack.html
    python3 scripts/pack_html.py -o /tmp/review.html
    python3 scripts/pack_html.py --pack data/packs/archive/old.json
"""
import argparse
import html as htmllib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from current_pack import resolve, sha256, metric_text, metric_basis, ROOT  # noqa: E402
from select_evidence import eligible  # noqa: E402

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{
    color-scheme: light dark;
    --bg: #f4f2ee; --card: #fff; --ink: #1b2733; --muted: #5d6b7a;
    --line: #dcd7ce; --accent: #a44d2f; --warn: #8a5a00; --warn-bg: #fdf3e0;
    --stop: #8f2d2d; --stop-bg: #fbeded; --good: #2f6b4f; --good-bg: #eaf4ee;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #14181d; --card: #1c222a; --ink: #e6e9ec; --muted: #97a3b0;
      --line: #2c343d; --accent: #e08a63; --warn: #e3b464; --warn-bg: #2d2617;
      --stop: #e08c8c; --stop-bg: #2e1c1c; --good: #7fc3a1; --good-bg: #17271f;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--bg); color: var(--ink);
         font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }}
  main {{ max-width: 1040px; margin: 0 auto; padding: 24px 20px 80px; }}
  h1 {{ font-size: 24px; margin: 0 0 4px; }}
  h2 {{ font-size: 13px; text-transform: uppercase; letter-spacing: .08em;
        color: var(--accent); border-bottom: 1px solid var(--line);
        padding-bottom: 6px; margin: 34px 0 14px; }}
  .sub {{ color: var(--muted); font-size: 13px; margin: 0 0 18px; }}
  .private {{ background: var(--stop-bg); border: 1px solid var(--stop); color: var(--stop);
              border-radius: 8px; padding: 12px 14px; font-size: 13px; margin: 0 0 22px; }}
  .private strong {{ display: block; margin-bottom: 3px; }}
  .stats {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 18px; }}
  .stat {{ background: var(--card); border: 1px solid var(--line); border-radius: 8px;
           padding: 8px 12px; font-size: 13px; }}
  .stat b {{ font-size: 17px; display: block; }}
  .stat.flag {{ background: var(--warn-bg); border-color: var(--warn); color: var(--warn); }}
  .controls {{ position: sticky; top: 0; z-index: 5; background: var(--bg);
               border-bottom: 1px solid var(--line); padding: 12px 0; margin-bottom: 14px;
               display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }}
  select, input {{ font: inherit; font-size: 13px; padding: 6px 9px; border-radius: 7px;
                   border: 1px solid var(--line); background: var(--card); color: var(--ink); }}
  input {{ flex: 1 1 220px; min-width: 160px; }}
  .count {{ color: var(--muted); font-size: 13px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13.5px;
           background: var(--card); border: 1px solid var(--line); border-radius: 8px; }}
  th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line); }}
  th {{ color: var(--muted); font-weight: 600; font-size: 12px;
        text-transform: uppercase; letter-spacing: .05em; }}
  tr:last-child td {{ border-bottom: none; }}
  .atom {{ background: var(--card); border: 1px solid var(--line); border-left: 3px solid var(--line);
           border-radius: 8px; padding: 14px 16px; margin-bottom: 12px; }}
  .atom.withheld {{ border-left-color: var(--stop); }}
  .atom.outcome {{ border-left-color: var(--good); }}
  .atom h3 {{ margin: 0 0 3px; font-size: 15.5px; }}
  .aid {{ font: 12px ui-monospace, SFMono-Regular, Menlo, monospace; color: var(--muted); }}
  .badges {{ display: flex; flex-wrap: wrap; gap: 5px; margin: 8px 0 10px; }}
  .b {{ font-size: 11.5px; padding: 2px 8px; border-radius: 20px;
        border: 1px solid var(--line); color: var(--muted); }}
  .b.good {{ background: var(--good-bg); border-color: var(--good); color: var(--good); }}
  .b.warn {{ background: var(--warn-bg); border-color: var(--warn); color: var(--warn); }}
  .b.stop {{ background: var(--stop-bg); border-color: var(--stop); color: var(--stop); }}
  .star {{ margin: 0; font-size: 14px; }}
  .star div {{ margin-bottom: 5px; }}
  .star .k {{ display: inline-block; min-width: 74px; color: var(--muted);
              font-size: 11.5px; text-transform: uppercase; letter-spacing: .05em;
              vertical-align: top; }}
  .star .v {{ display: inline-block; max-width: calc(100% - 82px); }}
  .missing {{ color: var(--muted); font-style: italic; }}
  .meta {{ margin-top: 11px; padding-top: 10px; border-top: 1px dashed var(--line);
           font-size: 12.5px; color: var(--muted); }}
  .meta div {{ margin-bottom: 3px; }}
  .basis {{ color: var(--good); }}
  .nobasis {{ color: var(--warn); }}
  .q {{ background: var(--warn-bg); border-left: 3px solid var(--warn); color: var(--warn);
        padding: 8px 11px; border-radius: 0 6px 6px 0; margin-top: 10px; font-size: 13px; }}
  .q ul {{ margin: 5px 0 0; padding-left: 18px; }}
  .note {{ font-size: 12.5px; color: var(--muted); margin-top: 8px; font-style: italic; }}
  footer {{ color: var(--muted); font-size: 12px; margin-top: 40px;
            border-top: 1px solid var(--line); padding-top: 12px; }}
  @media (max-width: 620px) {{
    .star .k {{ display: block; min-width: 0; }}
    .star .v {{ display: block; max-width: none; }}
    table {{ display: block; overflow-x: auto; }}
  }}
</style>
</head>
<body>
<main>
{body}
</main>
<script>
const atoms = Array.from(document.querySelectorAll('.atom'));
const controls = ['f-outcome', 'f-status', 'f-eligible', 'f-employer'].map(id => document.getElementById(id));
const search = document.getElementById('f-search');
const count = document.getElementById('f-count');
function apply() {{
  const term = search.value.trim().toLowerCase();
  let shown = 0;
  for (const atom of atoms) {{
    let ok = controls.every(c => !c.value || atom.dataset[c.dataset.key] === c.value);
    if (ok && term) ok = atom.innerText.toLowerCase().includes(term);
    atom.hidden = !ok;
    if (ok) shown++;
  }}
  count.textContent = shown + ' of ' + atoms.length + ' atoms';
}}
for (const c of controls) c.addEventListener('change', apply);
search.addEventListener('input', apply);
apply();
</script>
</body>
</html>
"""


def esc(value):
    return htmllib.escape(str(value), quote=True)


def badge(text, kind=""):
    return f'<span class="b {kind}">{esc(text)}</span>'


def star_block(atom):
    star = atom.get("star") or {}
    rows = []
    for field in ("situation", "task", "action", "result"):
        value = star.get(field)
        shown = (f'<span class="v">{esc(value)}</span>' if value
                 else '<span class="v missing">not recorded</span>')
        rows.append(f'<div><span class="k">{field}</span>{shown}</div>')
    return '<div class="star">' + "".join(rows) + "</div>"


def metrics_block(atom):
    metrics = atom.get("metrics") or []
    if not metrics:
        return '<div><span class="k">metrics</span><span class="v missing">none</span></div>'
    rows = []
    for metric in metrics:
        text, basis = metric_text(metric), metric_basis(metric)
        unmeasured = isinstance(metric, dict) and metric.get("measured") is False
        line = esc(text)
        if basis:
            line += f' <span class="basis">— measured: {esc(basis)}</span>'
        else:
            line += ' <span class="nobasis">— no measurement basis recorded</span>'
        if unmeasured:
            line += ' <span class="nobasis">(estimate, not measured)</span>'
        rows.append(f"<li>{line}</li>")
    return ('<div><span class="k">metrics</span><span class="v">'
            f'<ul style="margin:0;padding-left:18px">{"".join(rows)}</ul></span></div>')


def when(atom):
    occurred = atom.get("occurred")
    if not occurred:
        return "undated"
    start, end = occurred.get("start"), occurred.get("end")
    span = start if not end else f"{start} to {end}"
    return span + (" (inferred from the employment window)" if occurred.get("inferred") else "")


def atom_html(atom, employers):
    ok, why = eligible(atom)
    outcome = atom.get("outcome_type")
    classes = "atom" + ("" if ok else " withheld") + (" outcome" if outcome == "business_outcome" else "")

    badges = [badge(outcome or "no outcome_type", "good" if outcome == "business_outcome"
                    else "warn" if outcome is None else ""),
              badge(atom.get("evidence_status", "?"),
                    "warn" if atom.get("evidence_status") == "unresolved" else "")]
    if not ok:
        badges.append(badge("withheld: " + (why or ""), "stop"))
    if not atom.get("occurred"):
        badges.append(badge("undated", "warn"))
    elif (atom.get("occurred") or {}).get("inferred"):
        badges.append(badge("date inferred", "warn"))
    if atom.get("role_fit_notes"):
        badges.append(badge("counts against some roles", "warn"))
    if atom.get("corroborators"):
        badges.append(badge(f"{len(atom['corroborators'])} corroborator(s)", "good"))
    unmeasured = [m for m in (atom.get("metrics") or []) if not metric_basis(m)]
    if unmeasured:
        badges.append(badge(f"{len(unmeasured)} metric(s) without a basis", "warn"))

    parts = [f'<div class="{classes}"'
             f' data-outcome="{esc(outcome or "none")}"'
             f' data-status="{esc(atom.get("evidence_status", ""))}"'
             f' data-eligible="{"yes" if ok else "no"}"'
             f' data-employer="{esc(employers.get(atom.get("employment_id"), "none"))}">',
             f'<h3>{esc(atom.get("title", "untitled"))}</h3>',
             f'<div class="aid">{esc(atom.get("id", ""))}</div>',
             '<div class="badges">' + "".join(badges) + "</div>",
             star_block(atom),
             '<div class="star">' + metrics_block(atom) + "</div>"]

    meta = [f"<div><b>when:</b> {esc(when(atom))}</div>",
            f"<div><b>employer:</b> {esc(employers.get(atom.get('employment_id'), 'not linked'))}</div>"]
    if atom.get("skills"):
        meta.append(f"<div><b>skills:</b> {esc(', '.join(atom['skills']))}</div>")
    if atom.get("tags"):
        meta.append(f"<div><b>tags:</b> {esc(', '.join(atom['tags']))}</div>")
    refs = ", ".join(f"{r.get('source_id')}" + (f" ({r['locator']})" if r.get("locator") else "")
                     for r in atom.get("source_refs") or [])
    meta.append(f"<div><b>sources:</b> {esc(refs) or 'none'}</div>")
    if atom.get("role_fit_notes"):
        meta.append(f"<div><b>counts against:</b> {esc(atom['role_fit_notes'])}</div>")
    if atom.get("constraints"):
        meta.append(f"<div><b>constraints:</b> {esc('; '.join(atom['constraints']))}</div>")
    parts.append('<div class="meta">' + "".join(meta) + "</div>")

    if atom.get("open_questions"):
        items = "".join(f"<li>{esc(q)}</li>" for q in atom["open_questions"])
        parts.append(f'<div class="q"><b>Open questions</b><ul>{items}</ul></div>')
    if atom.get("notes"):
        parts.append(f'<div class="note">{esc(atom["notes"])}</div>')
    parts.append("</div>")
    return "".join(parts)


def build(pack, pack_path, digest):
    atoms = pack.get("evidence_atoms", [])
    employment = pack.get("employment", [])
    employers = {r["employment_id"]: r["employer"] for r in employment}

    counts = {"business_outcome": 0, "output": 0, "activity": 0, "none": 0}
    for atom in atoms:
        counts[atom.get("outcome_type") or "none"] += 1
    withheld = [a for a in atoms if not eligible(a)[0]]
    undated = [a for a in atoms if not a.get("occurred")]
    no_basis = sum(1 for a in atoms for m in (a.get("metrics") or []) if not metric_basis(m))

    stats = [("atoms", len(atoms), ""),
             ("business outcome", counts["business_outcome"],
              "flag" if not counts["business_outcome"] else ""),
             ("output", counts["output"], ""),
             ("activity", counts["activity"], ""),
             ("withheld", len(withheld), "flag" if withheld else ""),
             ("undated", len(undated), "flag" if undated else ""),
             ("metrics with no basis", no_basis, "flag" if no_basis else "")]
    stat_html = "".join(f'<div class="stat {c}"><b>{v}</b>{esc(label)}</div>'
                        for label, v, c in stats)

    rows = []
    for rec in sorted(employment, key=lambda r: r["start"], reverse=True):
        parent = rec.get("parent_employment_id")
        eor = rec.get("employer_of_record")
        note = []
        if parent:
            note.append(f"promotion under {parent}")
        if eor and eor != rec["employer"]:
            note.append(f"paid by {eor}")
        rows.append(f"<tr><td>{esc(rec['employer'])}</td><td>{esc(rec['title'])}</td>"
                    f"<td>{esc(rec['start'])} to {esc(rec.get('end') or '?')}</td>"
                    f"<td>{esc('; '.join(note))}</td></tr>")

    def options(name, key, values, label):
        opts = "".join(f'<option value="{esc(v)}">{esc(v)}</option>' for v in values)
        return (f'<select id="{name}" data-key="{key}">'
                f'<option value="">{esc(label)}</option>{opts}</select>')

    controls = (
        '<div class="controls">'
        + options("f-outcome", "outcome", ["business_outcome", "output", "activity", "none"],
                  "any outcome type")
        + options("f-status", "status", sorted({a.get("evidence_status", "") for a in atoms}),
                  "any status")
        + options("f-eligible", "eligible", ["yes", "no"], "withheld or not")
        + options("f-employer", "employer",
                  sorted({employers.get(a.get("employment_id"), "none") for a in atoms}),
                  "any employer")
        + '<input id="f-search" type="search" placeholder="search every field">'
        + '<span class="count" id="f-count"></span></div>')

    body = [
        f"<h1>{esc(pack.get('name') or 'Career pack')}</h1>",
        f'<p class="sub">{esc(pack_path)} · sha256 {esc(digest[:12])}… · '
        f'schema {esc(pack.get("schema_version"))}</p>',
        '<div class="private"><strong>Private working view. Do not send.</strong>'
        'This page shows the whole pack, including atoms marked withheld that no '
        'artefact may cite. Contact details are deliberately not rendered.</div>',
        f'<div class="stats">{stat_html}</div>',
        "<h2>Employment</h2>",
        "<table><tr><th>Employer</th><th>Title</th><th>Dates</th><th></th></tr>"
        + "".join(rows) + "</table>",
        *(["<h2>Education</h2>",
           "<table><tr><th>Institution</th><th>Qualification</th><th>Field</th>"
           "<th>Dates</th><th>Grade</th></tr>"
           + "".join(f"<tr><td>{esc(r['institution'])}</td><td>{esc(r['qualification'])}</td>"
                     f"<td>{esc(r.get('field') or '')}</td>"
                     f"<td>{esc(r.get('start') or '?')} to {esc(r.get('end') or '?')}</td>"
                     f"<td>{esc(r.get('grade') or '')}</td></tr>"
                     for r in sorted(pack.get("education", []),
                                     key=lambda r: r.get("end") or r.get("start") or "", reverse=True))
           + "</table>"] if pack.get("education") else []),
        "<h2>Evidence atoms</h2>",
        controls,
        "".join(atom_html(a, employers) for a in atoms),
        '<footer>Generated by scripts/pack_html.py. Regenerate with <code>make pack-html</code> '
        'after any pack change: this file does not update itself.</footer>',
    ]
    return TEMPLATE.format(title=esc((pack.get("name") or "Career") + " — pack"),
                           body="\n".join(body))


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pack", type=Path, default=None,
                        help="a specific pack; defaults to the current one")
    parser.add_argument("-o", "--output", type=Path, default=None,
                        help="defaults to outputs/pack.html")
    args = parser.parse_args(argv[1:])

    path = args.pack or resolve()
    if path is None:
        print("no pack found", file=sys.stderr)
        return 1
    pack = json.loads(path.read_text())
    try:
        shown = str(path.resolve().relative_to(ROOT))
    except ValueError:
        shown = str(path)

    target = args.output or (ROOT / "outputs" / "pack.html")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(build(pack, shown, sha256(path)))
    print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
