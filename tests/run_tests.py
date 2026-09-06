#!/usr/bin/env python3
"""Regression suite for the workspace.

Two kinds of check, and the difference matters:

  Deterministic  - the scripts are pure functions, so they get real assertions.
  Skill contract - a lint over SKILL.md files asserting that load-bearing
                   invariants are still stated. Not a behavioural eval, but it
                   catches the drift class that actually occurs: a rule quietly
                   disappearing or its vocabulary going stale during an edit.

Behavioural evals need a model in the loop and live in tests/scenarios.md.

    python3 tests/run_tests.py
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
SKILLS = ROOT / ".claude" / "skills"
EXAMPLE = ROOT / "examples" / "career.example.json"

RESULTS = []


def check(name, condition, detail=""):
    RESULTS.append((name, bool(condition), detail))


def run(script, *args, workspace=None):
    env = dict(os.environ)
    if workspace:
        env["CAREER_WORKSPACE"] = str(workspace)
    proc = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                          capture_output=True, text=True, env=env)
    return proc.returncode, proc.stdout, proc.stderr


def sandbox():
    """A throwaway workspace, so a test never touches the user's real notes.

    Previously test_capture backed up and restored the live notes.jsonl; a crash
    between the two lost real captured work.
    """
    root = Path(tempfile.mkdtemp())
    (root / "data" / "capture").mkdir(parents=True)
    (root / "data" / "packs").mkdir(parents=True)
    (root / "outputs").mkdir()
    shutil.copy(EXAMPLE,
                root / "data" / "packs" / "pack.json")
    return root


def broken(pack, mutate):
    data = json.loads(EXAMPLE.read_text())
    mutate(data)
    path = Path(tempfile.mkdtemp()) / pack
    path.write_text(json.dumps(data))
    return path


# --- pack validation ------------------------------------------------------
def test_pack_validation():
    code, _, _ = run("validate_pack.py", EXAMPLE)
    check("example pack validates", code == 0)

    cases = {
        "missing private_profile is an error": lambda d: d.pop("private_profile"),
        "missing external_safe is an error": lambda d: d["evidence_atoms"][0].pop("external_safe"),
        "unknown atom field is an error": lambda d: d["evidence_atoms"][0].update({"evidence_stauts": "x"}),
        "bad status enum is an error": lambda d: d["evidence_atoms"][0].update({"evidence_status": "verified"}),
        "missing star is an error": lambda d: d["evidence_atoms"][0].pop("star"),
        "wrong schema_version is an error": lambda d: d.update({"schema_version": "1.0"}),
        "source_ref to unknown source is an error":
            lambda d: d["evidence_atoms"][0]["source_refs"].append({"source_id": "SRC_NOPE"}),
    }
    for name, mutate in cases.items():
        code, _, _ = run("validate_pack.py", broken("p.json", mutate))
        check(name, code == 1)

    def fake_verified(d):
        for atom in d["evidence_atoms"]:
            if atom["id"] == "E_EXAMPLE_PLATFORM_COST":
                atom["evidence_status"] = "externally_verified"
    code, out, _ = run("validate_pack.py", broken("p.json", fake_verified))
    check("externally_verified needs an independent source", code == 1 and "independent" in out)


# --- selection view -------------------------------------------------------
def test_selection_view():
    code, out, _ = run("select_evidence.py")
    check("selection view runs", code == 0)
    if code != 0:
        return
    view = json.loads(out)
    ids = {a["id"] for a in view["atoms"]}
    code2, out2, _ = run("select_evidence.py", "--excluded")
    excluded = {row["id"] for row in json.loads(out2)["excluded"]}
    check("ineligible atoms never enter the view", not (ids & excluded),
          f"leaked {ids & excluded}")
    check("something was actually excluded", bool(excluded))
    check("view carries no address", "address" not in view["contact"])
    check("view carries no photo_reference", "photo_reference" not in view["contact"])

    order = [a["outcome_type"] for a in view["atoms"]]
    rank = {"business_outcome": 0, "output": 1, "activity": 2, None: 3}
    check("outcomes sort before activity", order == sorted(order, key=lambda o: rank[o]))

    # Regression: --audience=public silently returned the FULL contact block,
    # so a privacy flag failed open on exactly the artefact meant to be published.
    for form in (["--audience", "public"], ["--audience=public"]):
        code3, out3, _ = run("select_evidence.py", *form)
        public = json.loads(out3)["contact"] if code3 == 0 else {}
        check(f"public audience drops email via {' '.join(form)}", "email" not in public)
        check(f"public audience drops phone via {' '.join(form)}", "phone" not in public)
    code4, _, err4 = run("select_evidence.py", "--audience", "publik")
    check("invalid audience is rejected, not downgraded", code4 != 0 and "invalid choice" in err4)
    code5, _, _ = run("select_evidence.py", "public")
    check("stray positional argument is rejected", code5 != 0)


# --- renderer -------------------------------------------------------------
def test_renderer():
    md = ("# Jane Doe\n\nLondon | jane@example.com | +44 20 7946 0000\n\n"
          "## Role\n\nSummary line. <!-- Evidence: E_ONE -->\n\n"
          "## Experience\n\n### Employer | Title | 2020 - 2024\n\n"
          "- Did a thing with *emphasis*. <!-- Evidence: E_TWO -->\n"
          "- Did another & thing. <!-- Evidence: E_THREE -->\n")
    tmp = Path(tempfile.mkdtemp()) / "d.md"
    tmp.write_text(md)
    code, _, _ = run("render.py", tmp)
    html = tmp.with_suffix(".html").read_text()
    check("renderer runs", code == 0)
    check("evidence ids preserved", all(i in html for i in ("E_ONE", "E_TWO", "E_THREE")))
    check("evidence hidden from readers", 'class="evidence"' in html and ".evidence { display: none; }" in html)
    check("ampersand escaped", "&amp;" in html and "& thing" not in html)
    check("emphasis converted", "<em>emphasis</em>" in html)
    check("render is stable under repeat", render_twice(tmp))

    # Regression: a greedy single-* rule chewed through ** pairs and produced
    # "<em>*bold</em><em> text and a </em>term*", corrupting the visible document.
    bold = Path(tempfile.mkdtemp()) / "b.md"
    bold.write_text("# N\n\nLondon\n\n## R\n\nWith **bold** and *slant* together.\n")
    run("render.py", bold)
    bold_html = bold.with_suffix(".html").read_text()
    check("bold renders as strong", "<strong>bold</strong>" in bold_html)
    check("emphasis survives alongside bold", "<em>slant</em>" in bold_html)
    check("no stray asterisks left in output", "*" not in re.sub(r"<style>.*?</style>", "", bold_html, flags=re.S))

    # Regression: contact styling was keyed on an "@", so a public artefact with
    # no email silently lost it.
    pub = Path(tempfile.mkdtemp()) / "p.md"
    pub.write_text("# N\n\nLondon, United Kingdom\n\n## Head of Thing\n\nSummary.\n")
    run("render.py", pub)
    pub_html = pub.with_suffix(".html").read_text()
    check("public artefact keeps contact styling", 'class="contact"' in pub_html)
    check("title pairs name and role", "<title>N - Head of Thing</title>" in pub_html)
    check("contact line classed", 'class="contact"' in html)
    check("list rendered", html.count("<li>") == 2)
    check("render is idempotent", render_twice(tmp))


def render_twice(path):
    run("render.py", path)
    first = path.with_suffix(".html").read_text()
    run("render.py", path)
    return first == path.with_suffix(".html").read_text()


# --- artefact validation --------------------------------------------------
def test_artifact_validation():
    tmp = Path(tempfile.mkdtemp()) / "a.md"
    tmp.write_text("# X\n\n## Role\n\n- A claim. <!-- Evidence: E_JPMC_SCALE -->\n")
    run("render.py", tmp)
    code, out, _ = run("validate_artifact.py", tmp)
    check("clean artefact passes", code == 0, out)

    tmp2 = Path(tempfile.mkdtemp()) / "b.md"
    tmp2.write_text("# X\n\n## Role\n\n- A claim. <!-- Evidence: E_SPLUNK_BOTS_REVENUE -->\n")
    run("render.py", tmp2)
    code, out, _ = run("validate_artifact.py", tmp2)
    check("citing an ineligible atom fails", code == 1 and "external_safe" in out)

    tmp3 = Path(tempfile.mkdtemp()) / "c.md"
    tmp3.write_text("# X\n\n## Role\n\n- A claim. <!-- Evidence: E_JPMC_SCALE -->\n\n"
                    "**Draft status:** not publishable.\n")
    run("render.py", tmp3)
    code, out, _ = run("validate_artifact.py", tmp3)
    check("status banner in the artefact fails", code == 1 and "internal vocabulary" in out)

    tmp4 = Path(tempfile.mkdtemp()) / "d.md"
    tmp4.write_text("# X\n\n## Role\n\n- A claim. <!-- Evidence: E_JPMC_SCALE -->\n")
    run("render.py", tmp4)
    tmp4.write_text("# X\n\n## Role\n\n- A claim. <!-- Evidence: E_JPMC_TURNAROUND -->\n")
    code, out, _ = run("validate_artifact.py", tmp4)
    check("markdown/html drift fails", code == 1 and "different evidence sets" in out)


# --- provenance -----------------------------------------------------------
def test_private_brief():
    """Regression: make-interview-brief instructs citing external_safe: false atoms,
    and validate_artifact.py called that an error. The two contracts contradicted."""
    tmp = Path(tempfile.mkdtemp()) / "role-interview-brief.md"
    tmp.write_text("# Brief\n\nPrivate.\n\n## Do not discuss\n\n"
                   "- Governance. <!-- Evidence: E_JPMC_AI_GOVERNANCE -->\n")
    run("render.py", tmp)
    code, out, _ = run("validate_artifact.py", "--private", tmp)
    check("private brief may cite ineligible evidence", code == 0, out)
    code, out, _ = run("validate_artifact.py", tmp)
    check("a sent artefact still may not", code == 1 and "external_safe" in out, out)


def test_pack_pinning():
    """Regression: manifest.py pinned the pack and validate_artifact.py ignored it."""
    import shutil
    tmp = Path(tempfile.mkdtemp())
    md = tmp / "role-draft.md"
    md.write_text("# X\n\nLondon\n\n## Role\n\n- A claim. <!-- Evidence: E_JPMC_SCALE -->\n")
    run("render.py", md)
    pack = resolve_pack()
    manifest = json.loads(run("manifest.py", "Role")[1])
    (tmp / "role-evaluation.json").write_text(json.dumps({"run": manifest}))
    code, out, _ = run("validate_artifact.py", md)
    check("validator reads the pinned pack",
          code == 0 and Path(manifest["pack"]).name in out, out)

    manifest["pack_sha256"] = "0" * 64
    (tmp / "role-evaluation.json").write_text(json.dumps({"run": manifest}))
    code, out, _ = run("validate_artifact.py", md)
    check("changed pack is reported as stale", "stale" in out, out)


def test_manifest():
    code, out, _ = run("manifest.py", "Some Role")
    check("manifest runs", code == 0)
    if code != 0:
        return
    m = json.loads(out)
    check("manifest pins the pack hash", len(m.get("pack_sha256") or "") == 64)
    check("manifest pins every skill", set(m["skill_versions"]) ==
          {p.parent.name for p in SKILLS.glob("*/SKILL.md")})

    code, out, _ = run("current_pack.py", "--json")
    check("pack resolver runs", code == 0)
    if code == 0:
        check("resolver reports a private_profile", json.loads(out)["has_private_profile"])


# --- skill contracts ------------------------------------------------------
def test_records():
    code, out, _ = run("validate_records.py")
    check("existing records validate", code == 0, out)

    import shutil
    tmp = Path(tempfile.mkdtemp())
    src = ROOT / "outputs" / "head-of-ai-security-draft-screen.json"
    if src.exists():
        rec = json.loads(src.read_text())
        bad = dict(rec, verdict="maybe")
        (tmp / "x-screen.json").write_text(json.dumps(bad))
        code, out, _ = run("validate_records.py", tmp / "x-screen.json")
        check("invalid verdict rejected", code == 1 and "not in" in out, out)

        bad2 = dict(rec)
        bad2.pop("top_changes")
        (tmp / "y-screen.json").write_text(json.dumps(bad2))
        code, out, _ = run("validate_records.py", tmp / "y-screen.json")
        check("missing required field rejected", code == 1 and "top_changes" in out, out)

    ev = ROOT / "outputs" / "head-of-ai-security-evaluation.json"
    if ev.exists():
        rec = json.loads(ev.read_text())
        bad3 = dict(rec, publishable=True)
        (tmp / "z-evaluation.json").write_text(json.dumps(bad3))
        code, out, _ = run("validate_records.py", tmp / "z-evaluation.json")
        check("publishable with a blocker is rejected", code == 1 and "blocker" in out, out)


def test_corroboration_plan():
    code, out, _ = run("corroboration_plan.py")
    check("corroboration plan runs", code == 0)
    if code != 0:
        return
    data = json.loads(out)
    ids = [r["id"] for r in data["plan"]]
    check("corroboration warnings are off by default",
          "no corroborator" not in run("validate_pack.py")[1])
    check("--strict opts back in",
          "no corroborator" in run("validate_pack.py", "--strict")[1])
    check("plan excludes externally_verified atoms",
          all(r["evidence_status"] != "externally_verified" for r in data["plan"]))
    check("plan is sorted by score",
          [r["score"] for r in data["plan"]] == sorted([r["score"] for r in data["plan"]], reverse=True))
    check("every entry carries a specific ask", all(len(r["ask"]) > 20 for r in data["plan"]))
    check("summary counts every atom",
          sum(data["summary"]["by_status"].values()) == data["summary"]["atoms"])
    check("unresolved atoms get their open question in the ask",
          all("Answer it or retire it" in r["ask"]
              for r in data["plan"] if r["evidence_status"] == "unresolved"))
    code, out, _ = run("corroboration_plan.py", "--markdown")
    check("markdown plan renders", code == 0 and "## Work list" in out)


def test_index_and_diff():
    code, out, _ = run("artifact_index.py", "--json")
    check("index runs", code == 0)
    if code == 0:
        rows = json.loads(out)
        check("index finds artefacts", len(rows) > 0)
        check("index reports staleness", all("stale" in r for r in rows))
    drafts = sorted((ROOT / "outputs").glob("*-draft.md"))
    if len(drafts) >= 2:
        code, out, _ = run("diff_artifact.py", drafts[0], drafts[1])
        check("semantic diff runs", code == 0 and "outcome mix" in out)


def test_employment():
    """Employment is what a background check tests, and it lived nowhere in the pack."""
    code, out, _ = run("validate_pack.py", EXAMPLE)
    check("example pack has employment and validates", code == 0, out)

    cases = {
        "pack without employment is an error": lambda d: d.pop("employment"),
        "employment missing a start is an error": lambda d: d["employment"][0].pop("start"),
        "end before start is an error": lambda d: d["employment"][0].update({"start": "2022-03", "end": "2019-01"}),
        "unknown employment field is an error": lambda d: d["employment"][0].update({"salary": 1}),
        "bad date format is an error": lambda d: d["employment"][0].update({"start": "March 2022"}),
        "duplicate employment_id is an error":
            lambda d: d["employment"].append(dict(d["employment"][0])),
        "atom pointing at a missing role is an error":
            lambda d: d["evidence_atoms"][0].update({"employment_id": "EMP_NOPE"}),
        "unknown parent_employment_id is an error":
            lambda d: d["employment"][0].update({"parent_employment_id": "EMP_NOPE"}),
    }
    for name, mutate in cases.items():
        code, _, _ = run("validate_pack.py", broken("p.json", mutate))
        check(name, code == 1)

    view = json.loads(run("select_evidence.py")[1])
    check("selection view carries employment", view["summary"]["employment_records"] > 0)
    check("selection view computes the career span", isinstance(view["career_span_years"], int))

    # Artefact side: a date or employer that traces to nothing must fail.
    tmp = Path(tempfile.mkdtemp()) / "e-draft.md"
    tmp.write_text("# X\n\nLondon\n\n## Role\n\n"
                   "### Nowhere Ltd | Some Title | 1987 - 1990\n\n"
                   "- A claim. <!-- Evidence: E_JPMC_SCALE -->\n")
    run("render.py", tmp)
    code, out, _ = run("validate_artifact.py", "--current", tmp)
    check("unsourced employer fails", code == 1 and "no employment record" in out, out)
    check("unsourced year fails", "matches no employment record" in out, out)

    tmp2 = Path(tempfile.mkdtemp()) / "f-draft.md"
    tmp2.write_text("# X\n\nLondon\n\n## Role\n\nTwelve years across things.\n\n"
                    "- A claim. <!-- Evidence: E_JPMC_SCALE -->\n")
    run("render.py", tmp2)
    code, out, _ = run("validate_artifact.py", "--current", tmp2)
    check("a wrong career-span claim fails", code == 1 and "years of experience" in out, out)


def test_role_fit():
    code, out, _ = run("role_fit.py")
    check("role fit runs", code == 0, out)
    if code != 0:
        return
    roles = json.loads(out)["roles"]
    check("every profile is scored", len(roles) >= 1)
    check("results are ranked", [r["score"] for r in roles] == sorted([r["score"] for r in roles], reverse=True))
    check("an unevidenced essential makes a role unsupported",
          all(r["verdict"] == "not supported" for r in roles if r["essential_gaps"]))
    check("scores are percentages", all(0 <= r["score"] <= 100 for r in roles))
    code, out, _ = run("role_fit.py", "--markdown")
    check("role fit renders markdown", code == 0 and "| Role |" in out)


def test_verdict_log():
    code, _, _ = run("verdict_log.py")
    check("verdict log runs", code == 0)
    code, out, _ = run("verdict_log.py")
    check("recording twice adds nothing", code == 0 and "no new verdicts" in out, out)
    code, out, _ = run("verdict_log.py", "--trend")
    check("trend renders", code == 0)


def test_capture():
    """Capture must never require a pack write: that friction is what stops it."""
    root = sandbox()
    pack = root / "data" / "packs" / "pack.json"
    before = pack.read_text()

    code, out, _ = run("capture.py", "a test capture note", "--tag", "testing", workspace=root)
    check("capture runs", code == 0 and "captured" in out, out)
    check("capture did not touch the pack", pack.read_text() == before)
    check("capture wrote its own log", (root / "data" / "capture" / "notes.jsonl").exists())

    code, out, _ = run("capture.py", "--list", workspace=root)
    check("captured note is listed", code == 0 and "a test capture note" in out)

    code, _, _ = run("capture.py", "--promote", "N0001", "--atom", "E_TEST", workspace=root)
    check("promotion marks the note", code == 0)
    code, out, _ = run("capture.py", "--list", workspace=root)
    check("promoted notes drop off the list", "N0001" not in out)
    code, out, _ = run("capture.py", "--list", "--all", workspace=root)
    check("--all still shows promoted notes", "N0001" in out)

    code, _, _ = run("capture.py", "--promote", "N9999", "--atom", "E_X", workspace=root)
    check("promoting an unknown note fails", code == 1)

    # Regression: gap-filling ids could repoint an atom's capture.note_id.
    notes_file = root / "data" / "capture" / "notes.jsonl"
    run("capture.py", "second", workspace=root)
    kept = [line for line in notes_file.read_text().splitlines() if '"N0001"' not in line]
    notes_file.write_text("\n".join(kept) + "\n")
    run("capture.py", "third", workspace=root)
    ids = [json.loads(line)["note_id"] for line in notes_file.read_text().splitlines() if line.strip()]
    check("note ids are never reused", len(ids) == len(set(ids)) and "N0001" not in ids, str(ids))
    shutil.rmtree(root, ignore_errors=True)


def resolve_pack():
    from pathlib import Path as P
    packs = sorted((ROOT / "data" / "packs").glob("*.json"))
    superseded = set()
    for p in packs:
        try:
            meta = json.loads(p.read_text()).get("metadata") or {}
        except json.JSONDecodeError:
            continue
        if meta.get("supersedes"):
            superseded.add((ROOT / meta["supersedes"]).resolve())
    live = [p for p in packs if p.resolve() not in superseded]
    return live[0] if live else None


def test_no_hardcoded_year():
    """A frozen current year silently drifts the career span and its artefact check."""
    for name in ("find.py", "select_evidence.py", "validate_artifact.py"):
        text = (SCRIPTS / name).read_text()
        body = "\n".join(line for line in text.splitlines()
                          if not line.strip().startswith("#") and "scripts/" not in line)
        check(f"{name} has no hardcoded year", not re.search(r"\b20[2-9][0-9]\b", body),
              next((l for l in body.splitlines() if re.search(r"\b20[2-9][0-9]\b", l)), ""))
    view = json.loads(run("select_evidence.py")[1])
    from datetime import date
    check("career span is computed from today", view["career_span_years"] is not None)
    check("span tracks the real year",
          view["career_span_years"] == date.today().year - 1999)


def test_view_carries_time_and_tags():
    """occurred and tags were added to the pack and never reached generation."""
    view = json.loads(run("select_evidence.py")[1])
    atoms = view["atoms"]
    check("view exposes occurred", all("occurred" in a for a in atoms))
    check("view exposes tags", all("tags" in a for a in atoms))
    rank = {"business_outcome": 0, "output": 1, "activity": 2, None: 3}
    check("outcomes still sort first",
          [rank[a["outcome_type"]] for a in atoms] == sorted(rank[a["outcome_type"]] for a in atoms))
    outputs = [a for a in atoms if a["outcome_type"] == "output"]
    ends = [(a.get("occurred") or {}).get("end") or "0000" for a in outputs]
    ends = ["9999" if e == "ongoing" else e for e in ends]
    check("within a tier, recent work sorts first", ends == sorted(ends, reverse=True), str(ends))


def test_role_aware_selection():
    """Sending the whole pack and asking a model to curate does not survive scale."""
    full = json.loads(run("select_evidence.py")[1])
    code, out, _ = run("select_evidence.py", "--role", "head-of-ai-security", "--limit", "5")
    check("role selection runs", code == 0, out)
    if code != 0:
        return
    scoped = json.loads(out)
    check("shortlist is limited", len(scoped["atoms"]) == 5)
    check("shortlist is smaller than the full view", len(scoped["atoms"]) < len(full["atoms"]))
    check("shortlist reports what it dropped", len(scoped["not_shortlisted"]) ==
          len(full["atoms"]) - 5)
    check("shortlist is ranked", [a["role_score"] for a in scoped["atoms"]] ==
          sorted((a["role_score"] for a in scoped["atoms"]), reverse=True))
    check("every selection is explained", all(a["why_selected"] for a in scoped["atoms"]))
    check("role and central requirement are carried", scoped["role"] and scoped["central_requirement"])
    # Regression: a local named `profile` shadowed the role profile and the
    # contact block silently replaced it.
    check("contact block survives role selection", "name" in scoped["contact"])
    check("contact is not the role profile", "role_id" not in scoped["contact"])
    code, _, err = run("select_evidence.py", "--role", "no-such-role")
    check("unknown role fails loudly", code != 0 and "Available" in err)


def test_capture_edit_delete():
    root = sandbox()
    run("capture.py", "original text", workspace=root)
    code, out, _ = run("capture.py", "--edit", "N0001", "corrected text", workspace=root)
    check("edit rewrites a note", code == 0 and "corrected text" in out, out)
    code, out, _ = run("capture.py", "--edit", "N0001", "--tag", "later", workspace=root)
    check("edit can amend flags only", code == 0 and "corrected text" in out, out)
    code, _, _ = run("capture.py", "--edit", "N9999", "x", workspace=root)
    check("editing an unknown note fails", code == 1)
    code, out, _ = run("capture.py", "--delete", "N0001", workspace=root)
    check("delete removes a note", code == 0 and "deleted" in out, out)
    code, out, _ = run("capture.py", "--list", workspace=root)
    check("deleted note is gone", "N0001" not in out)
    run("capture.py", "after deletion", workspace=root)
    code, out, _ = run("capture.py", "--list", workspace=root)
    check("ids stay monotonic after a delete", "N0002" in out, out)
    code, _, _ = run("capture.py", "--delete", "N9999", workspace=root)
    check("deleting an unknown note fails", code == 1)
    shutil.rmtree(root, ignore_errors=True)


def test_coverage():
    code, out, _ = run("coverage.py", "--json")
    check("coverage runs", code == 0, out)
    if code != 0:
        return
    data = json.loads(out)
    check("coverage builds a timeline", len(data["span"]) > 5)
    check("coverage counts atoms by year", sum(data["by_year"].values()) > 0)
    check("coverage reports inferred dates", isinstance(data["inferred"], list))
    check("coverage finds gaps in a sparse record", isinstance(data["gaps"], list))
    check("timeline ends this year", data["span"][-1] == __import__("datetime").date.today().year)
    code, out, _ = run("coverage.py")
    check("coverage renders a timeline", code == 0 and "Timeline" in out)


def test_resume_json_export():
    """career.json is the superset; resume.json is a lossy, publishable projection."""
    code, out, _ = run("export_resume_json.py")
    check("export runs", code == 0, out)
    if code != 0:
        return
    resume = json.loads(out)
    check("emits JSON Resume top-level sections",
          {"basics", "work", "skills"} <= set(resume))
    check("declares the schema it targets", "jsonresume" in resume.get("$schema", ""))
    check("records that it is a projection", resume["meta"]["canonical"] == "career.json")
    check("dates are ISO 8601",
          all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", w["startDate"]) for w in resume["work"]))
    check("a current role has no endDate",
          any("endDate" not in w for w in resume["work"]))
    check("promotions collapse into their parent role",
          len(resume["work"]) < len(json.loads(resolve_pack().read_text())["employment"]))

    pack = json.loads(resolve_pack().read_text())
    banned = {a["id"] for a in pack["evidence_atoms"]
              if not a["external_safe"] or a["evidence_status"] in ("unresolved", "declined")}
    blob = json.dumps(resume)
    leaked = [a["id"] for a in pack["evidence_atoms"] if a["id"] in banned
              and (a.get("star") or {}).get("result")
              and (a["star"]["result"] or "")[:40] in blob]
    check("unpublishable evidence never reaches the export", not leaked, str(leaked))

    code, out, _ = run("export_resume_json.py", "--audience", "public")
    public = json.loads(out)
    check("public export drops email", "email" not in public["basics"])
    check("public export drops phone", "phone" not in public["basics"])

    code, out, _ = run("export_resume_json.py", "--role", "head-of-ai-security", "--limit", "5")
    scoped = json.loads(out)
    check("role export records the role", scoped["meta"]["role"] == "head-of-ai-security")
    total = sum(len(w.get("highlights", [])) for w in scoped["work"])
    check("role export shortlists highlights", total <= 5, str(total))


def test_find():
    code, out, _ = run("find.py", "--skill", "threat modeling")
    check("alias spelling finds the canonical skill", code == 0 and "THREAT_MODELING" in out, out)
    code, out, _ = run("find.py", "--employer", "Splunk")
    check("employer search works", code == 0 and "SPLUNK" in out, out)
    code, out, _ = run("find.py", "--outcome", "business_outcome", "--json")
    check("outcome filter runs", code == 0)
    code, out, _ = run("find.py", "--since", "2024", "--json")
    if code == 0:
        check("date filter excludes older atoms",
              all((a.get("occurred") or {}).get("end", "9999") >= "2024"
                  or (a.get("occurred") or {}).get("end") == "ongoing"
                  for a in json.loads(out)))
    code, _, _ = run("find.py", "zzzznotarealterm")
    check("no match exits non-zero", code == 1)


def test_dedupe():
    code, out, _ = run("dedupe.py", "--text",
                       "Cleared a cross-team controls backlog stalled eight months, in two weeks")
    check("a reworded existing claim is flagged", code == 0 and "E_JPMC_TURNAROUND" in out, out)
    code, out, _ = run("dedupe.py", "--text", "Trained a pet hamster to play the trumpet")
    check("an unrelated claim is not flagged", code == 0 and "looks new" in out, out)
    code, out, _ = run("dedupe.py", "--json")
    check("dedupe emits json", code == 0)


def test_occurred():
    pack = json.loads(resolve_pack().read_text())
    atoms = pack["evidence_atoms"]
    check("every atom has an occurred field", all("occurred" in a for a in atoms))
    dated = [a for a in atoms if a.get("occurred")]
    check("most atoms are dated", len(dated) >= len(atoms) * 0.6)
    check("inferred dates are marked as inferred",
          all("inferred" in a["occurred"] for a in dated))
    check("pack carries a skill vocabulary", bool(pack.get("skill_vocabulary")))
    for name, mutate in {
        "bad occurred format is an error":
            lambda d: d["evidence_atoms"][0].update({"occurred": {"start": "March 2020"}}),
        "unknown capture method is an error":
            lambda d: d["evidence_atoms"][0].update({"capture": {"method": "telepathy"}}),
    }.items():
        code, _, _ = run("validate_pack.py", broken("p.json", mutate))
        check(name, code == 1)


INVARIANTS = {
    "capture-work": ["Do not interrogate", "never in the pack", "notes are cheap",
                     "capture.py", "dedupe.py", "--edit", "--delete"],
    "make-interview-brief": ["inverts that rule", "Never publish this", "whole pack",
                            "external_safe: false", "Never invent"],
    "make-resume": ["Ask no questions", "never appears inside the artefact",
                    "business_outcome", "role_fit_notes", "recruiter-screen",
                    "Cover letter", "central_requirement", "employment", "career_span_years",
                    "--role"],
    "build-career-pack": ["private_profile", "business_outcome", "one batch",
                          "validate_pack.py", "optional and off by default",
                          "employer_of_record", "annual write-up", "dedupe.py",
                          "review_period"],
    "review-evidence": ["self_asserted", "corroborated", "externally_verified",
                        "Repetition is not corroboration", "not a requirement",
                        "Never chase them"],
    "evaluate-output": ["external_safe", "contact block", "recruiter-screen",
                        "Background-check exposure", "employment", "employer_of_record",
                        "LinkedIn About"],
    "recruiter-screen": ["Do not praise", "default is to reject", "advance", "borderline",
                         "reject", "screen-record.schema.json"],
    "ingest-career-materials": ["self_asserted", "extract_text.sh", "independent",
                               "employment", "employer_of_record"],
    "generate-resume": ["outcome_type", "role_fit_notes", "contact block"],
}
FORBIDDEN = ["user_asserted", "`verified`"]


def flat(text):
    """Skill files are hard-wrapped, so a phrase can straddle a newline."""
    return " ".join(text.lower().split())


def test_skill_contracts():
    for skill, phrases in INVARIANTS.items():
        path = SKILLS / skill / "SKILL.md"
        if not path.exists():
            check(f"{skill} exists", False)
            continue
        text = flat(path.read_text())
        for phrase in phrases:
            check(f"{skill} still states {phrase!r}", flat(phrase) in text)
    for path in SKILLS.glob("*/SKILL.md"):
        text = flat(path.read_text())
        for term in FORBIDDEN:
            check(f"{path.parent.name} free of stale term {term!r}", flat(term) not in text)


WALKTHROUGH = ROOT / "examples" / "walkthrough"


def test_walkthrough():
    """The committed end-to-end example must stay true, or it teaches a lie.

    A README that links to a walkthrough is making a claim about the pipeline.
    These assertions are what keep that claim honest when the pack, the schemas,
    or the renderer move underneath it.
    """
    records = [WALKTHROUGH / "head-of-platform-engineering-evaluation.json",
               WALKTHROUGH / "head-of-platform-engineering-screen.json",
               WALKTHROUGH / "roles" / "head-of-platform-engineering.json"]
    code, out, err = run("validate_records.py", *records)
    check("walkthrough records validate", code == 0, out + err)

    evaluation = json.loads(records[0].read_text())
    pack_sha = hashlib.sha256(EXAMPLE.read_bytes()).hexdigest()
    check("walkthrough evaluation pins the example pack",
          evaluation["run"]["pack_sha256"] == pack_sha,
          "regenerate the walkthrough: the example pack has changed")

    resume = WALKTHROUGH / "resume.md"
    for atom in ("E_EXAMPLE_REVENUE_CLAIM", "E_EXAMPLE_PRIOR_EMPLOYER_DETAIL"):
        check(f"walkthrough resume omits ineligible {atom}", atom not in resume.read_text())

    workspace = sandbox()
    shutil.copy(resume, workspace / "outputs" / "resume.md")
    code, out, err = run("render.py", workspace / "outputs" / "resume.md", workspace=workspace)
    check("walkthrough resume renders", code == 0, out + err)
    code, out, err = run("validate_artifact.py", workspace / "outputs" / "resume.md",
                         "--html", workspace / "outputs" / "resume.html", workspace=workspace)
    check("walkthrough resume validates against the example pack", code == 0, out + err)
    shutil.rmtree(workspace, ignore_errors=True)


NUMBER_WORDS = {7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve"}


def test_docs_match_reality():
    """Counts stated in prose drift silently, and this project cannot afford it.

    architecture.md claimed seven skills when there were nine, and 220 assertions
    when there were 232. In a workspace whose whole pitch is that unverified
    claims are the problem, a reader who checks two numbers and finds both wrong
    stops trusting the rest.
    """
    arch = (ROOT / "docs" / "architecture.md").read_text()
    found = len(list(SKILLS.glob("*/SKILL.md")))
    match = re.search(r"judgement: the (\w+) skills", arch)
    check("architecture.md states a skill count", match is not None)
    if match:
        check("architecture.md skill count is current",
              match.group(1) == NUMBER_WORDS.get(found),
              f"doc says {match.group(1)!r}, workspace has {found} skills")


def check_documented_assertion_count():
    """Last check to run: the documented total against the real one.

    It counts itself, so the number in the doc is the number the suite prints.
    """
    arch = (ROOT / "docs" / "architecture.md").read_text()
    stated = {int(n) for n in re.findall(r"(\d+) assertions", arch)}
    total = len(RESULTS) + 1
    check("architecture.md documents the real assertion count",
          stated == {total},
          f"doc states {sorted(stated) or 'nothing'}, suite has {total}")


def main():
    for test in (test_pack_validation, test_selection_view, test_renderer,
                 test_artifact_validation, test_private_brief, test_pack_pinning, test_manifest,
                 test_records, test_corroboration_plan, test_index_and_diff,
                 test_employment, test_role_fit, test_verdict_log,
                 test_capture, test_find, test_dedupe, test_occurred,
                 test_no_hardcoded_year, test_view_carries_time_and_tags,
                 test_role_aware_selection, test_capture_edit_delete, test_coverage,
                 test_resume_json_export,
                 test_skill_contracts, test_docs_match_reality,
                 test_walkthrough):
        test()
    check_documented_assertion_count()
    failed = [r for r in RESULTS if not r[1]]
    for name, ok, detail in RESULTS:
        if not ok:
            print(f"FAIL  {name}" + (f"\n      {detail.strip()[:200]}" if detail else ""))
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
