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
COMPLEX = ROOT / "examples" / "career.complex.example.json"

RESULTS = []


def check(name, condition, detail=""):
    RESULTS.append((name, bool(condition), detail))


def run(script, *args, workspace=None):
    """Run a script against a workspace. Never the live one.

    CAREER_WORKSPACE is always set, to the caller's workspace or the shared
    fixture, so no test can reach the owner's data/, outputs/ or reviews/ by
    forgetting a parameter. Sixteen tests used to do exactly that: they read the
    owner's pack, referenced personal evidence ids, and one wrote to the live
    verdict log. A clean checkout's `make check` crashed as a result.
    """
    env = dict(os.environ)
    env["CAREER_WORKSPACE"] = str(workspace or fixture())
    proc = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                          capture_output=True, text=True, env=env)
    return proc.returncode, proc.stdout, proc.stderr


_FIXTURE = None
PRIVATE_DIRS = ("data", "outputs", "reviews")


def _snapshot():
    """Every file under the owner's private directories, with size and mtime, so
    the suite can prove afterwards that it touched none of them."""
    seen = {}
    for name in PRIVATE_DIRS:
        base = ROOT / name
        if base.is_dir():
            for path in base.rglob("*"):
                if path.is_file():
                    stat = path.stat()
                    seen[str(path)] = (stat.st_size, stat.st_mtime_ns)
    return seen


LIVE_BEFORE = _snapshot()


def _run_in(root, script, *args):
    env = dict(os.environ)
    env["CAREER_WORKSPACE"] = str(root)
    return subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                          capture_output=True, text=True, env=env)


def fixture():
    """The workspace tests run against when they do not build their own.

    Built once from the complex fictional pack: a promotion chain, withheld and
    unresolved evidence, undated atoms, an independent source, education, a role
    profile, two rendered drafts with an evaluation and a screen, and an empty
    review log. Everything a script might reach for, none of it real.
    """
    global _FIXTURE
    if _FIXTURE is not None:
        return _FIXTURE
    root = Path(tempfile.mkdtemp(prefix="career-json-fixture-"))
    for sub in ("data/packs", "data/roles", "data/capture", "outputs", "reviews"):
        (root / sub).mkdir(parents=True)
    shutil.copytree(ROOT / "schemas", root / "schemas")
    shutil.copytree(ROOT / "examples", root / "examples")
    # manifest.py hashes the skills under the workspace, so the fixture carries
    # them; they are public and the pin must name every one.
    shutil.copytree(ROOT / ".claude", root / ".claude")
    shutil.copy(COMPLEX, root / "data" / "packs" / "pack.json")
    (root / "data" / "roles" / "head-of-detection.json").write_text(json.dumps({
        "role_id": "head-of-detection", "title": "Head of Detection",
        "central_requirement": "Has run detection engineering as a function.",
        "requirements": [
            {"weight": "essential", "text": "Runs detection engineering",
             "evidenced_by": ["E_CX_DETECTION_PROGRAMME"]},
            {"weight": "essential", "text": "Owns risk governance tooling",
             "evidenced_by": ["E_CX_INTERNAL_TOOL"]},
            {"weight": "important", "text": "Reduces fraud loss",
             "evidenced_by": ["E_CX_FRAUD_LOSS"]}],
        "ats_keywords": ["detection engineering", "fraud"],
        "negative_signals": [], "length": "two A4 pages", "audience": "named_recipient"}))

    head = ("# Morgan Vale\n\nLondon, United Kingdom · morgan.vale@example.invalid · "
            "+44 20 7946 0123\n\n## Experience\n\n"
            "### Northwind Systems | Director of Platform Security | 2022 to present\n\n")
    drafts = {
        "head-of-detection-draft.md": head
            + "- Cut quarterly fraud write-offs by roughly a third with the false-positive rate "
              "unchanged. <!-- Evidence: E_CX_FRAUD_LOSS -->\n"
            + "- Made detection a reviewed, tested practice with 70+ detections under review. "
              "<!-- Evidence: E_CX_DETECTION_PROGRAMME -->\n",
        "generalist-draft.md": head
            + "- Survived a regional outage with zero customer-visible downtime. "
              "<!-- Evidence: E_CX_PLATFORM_MIGRATION -->\n"
            + "- Rebuilt a nine-person on-call rotation. <!-- Evidence: E_CX_ONCALL -->\n",
    }
    for name, text in drafts.items():
        (root / "outputs" / name).write_text(text)
        _run_in(root, "render.py", root / "outputs" / name)

    manifest = json.loads(_run_in(root, "manifest.py", "Head of Detection").stdout)
    walkthrough = ROOT / "examples" / "walkthrough"
    evaluation = json.loads((walkthrough / "head-of-platform-engineering-evaluation.json").read_text())
    evaluation.update({"artifacts": ["outputs/head-of-detection-draft.md"],
                       "target_role": "Head of Detection", "run": manifest})
    (root / "outputs" / "head-of-detection-evaluation.json").write_text(json.dumps(evaluation))
    screen = json.loads((walkthrough / "head-of-platform-engineering-screen.json").read_text())
    screen.update({"artifact": "outputs/head-of-detection-draft.md",
                   "target_role": "Head of Detection", "run": manifest})
    (root / "outputs" / "head-of-detection-draft-screen.json").write_text(json.dumps(screen))
    _FIXTURE = root
    return root


def fixture_pack():
    return json.loads((fixture() / "data" / "packs" / "pack.json").read_text())


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
    # validate_pack.py resolves the schema under CAREER_WORKSPACE, so a sandbox
    # without this cannot run it at all.
    shutil.copytree(ROOT / "schemas", root / "schemas")
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

    # A string "false" was truthy, so a typo could authorise externally_verified.
    def string_false(d):
        d["source_records"][0]["independent"] = "false"
        d["evidence_atoms"][0]["evidence_status"] = "externally_verified"
    code, out, _ = run("validate_pack.py", broken("p.json", string_false))
    check("a non-boolean independent flag is an error", code == 1 and "must be boolean" in out, out)
    check("and a string false cannot support external verification",
          "requires a source_ref to an independent source" in out, out)

    # The supersedes chain decides which pack every script resolves.
    for mutate, why in ((lambda d: d.setdefault("metadata", {}).update({"supersedes": "data/packs/nope.json"}),
                         "does not exist"),
                        (lambda d: d.setdefault("metadata", {}).update({"supersedes": "p.json"}),
                         "itself")):
        root = sandbox()  # the validator loads its schema from the workspace
        data = json.loads(EXAMPLE.read_text())
        mutate(data)
        (root / "p.json").write_text(json.dumps(data))
        code, out, _ = run("validate_pack.py", root / "p.json", workspace=root)
        check(f"supersedes pointing at a pack that {why} is an error", code == 1 and why in out, out)
        shutil.rmtree(root, ignore_errors=True)


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
    tmp.write_text("# X\n\n## Role\n\n- A claim. <!-- Evidence: E_CX_FRAUD_LOSS -->\n")
    run("render.py", tmp)
    code, out, _ = run("validate_artifact.py", tmp)
    check("clean artefact passes", code == 0, out)

    tmp2 = Path(tempfile.mkdtemp()) / "b.md"
    tmp2.write_text("# X\n\n## Role\n\n- A claim. <!-- Evidence: E_CX_REVENUE_CLAIM -->\n")
    run("render.py", tmp2)
    code, out, _ = run("validate_artifact.py", tmp2)
    check("citing an ineligible atom fails", code == 1 and "external_safe" in out)

    tmp3 = Path(tempfile.mkdtemp()) / "c.md"
    tmp3.write_text("# X\n\n## Role\n\n- A claim. <!-- Evidence: E_CX_FRAUD_LOSS -->\n\n"
                    "**Draft status:** not publishable.\n")
    run("render.py", tmp3)
    code, out, _ = run("validate_artifact.py", tmp3)
    check("status banner in the artefact fails", code == 1 and "internal vocabulary" in out)

    tmp4 = Path(tempfile.mkdtemp()) / "d.md"
    tmp4.write_text("# X\n\n## Role\n\n- A claim. <!-- Evidence: E_CX_FRAUD_LOSS -->\n")
    run("render.py", tmp4)
    tmp4.write_text("# X\n\n## Role\n\n- A claim. <!-- Evidence: E_CX_PLATFORM_MIGRATION -->\n")
    code, out, _ = run("validate_artifact.py", tmp4)
    check("markdown/html drift fails", code == 1 and "different evidence sets" in out)


# --- provenance -----------------------------------------------------------
def test_private_brief():
    """Regression: make-interview-brief instructs citing external_safe: false atoms,
    and validate_artifact.py called that an error. The two contracts contradicted."""
    tmp = Path(tempfile.mkdtemp()) / "role-interview-brief.md"
    tmp.write_text("# Brief\n\nPrivate.\n\n## Do not discuss\n\n"
                   "- Governance. <!-- Evidence: E_CX_INTERNAL_TOOL -->\n")
    run("render.py", tmp)
    code, out, _ = run("validate_artifact.py", "--private", tmp)
    check("private brief may cite ineligible evidence", code == 0, out)
    code, out, _ = run("validate_artifact.py", tmp)
    check("a sent artefact still may not", code == 1 and "external_safe" in out, out)

    # Found by running the skill against the real pack. The fixture above dodges
    # the defect by never using the vocabulary a brief exists to state: the skill
    # requires naming which atoms are external_safe: false or unresolved so the
    # candidate knows what not to discuss, and the leak scan failed a real brief
    # on exactly those words. Eligibility was inverted for --private; the leak
    # scan was not.
    real = Path(tempfile.mkdtemp()) / "role-interview-brief.md"
    real.write_text("# Brief\n\n**Private. Do not send.** This brief is not publishable.\n\n"
                    "## Do not discuss\n\n"
                    "- `E_CX_INTERNAL_TOOL` is marked `external_safe: false`. "
                    "<!-- Evidence: E_CX_INTERNAL_TOOL -->\n"
                    "- The revenue claim is `unresolved`. "
                    "<!-- Evidence: E_CX_REVENUE_CLAIM -->\n")
    run("render.py", real)
    code, out, _ = run("validate_artifact.py", "--private", real)
    check("a brief may name the statuses it exists to warn about", code == 0, out)
    code, out, _ = run("validate_artifact.py", real)
    check("the same words still fail a sendable artefact",
          code == 1 and "internal vocabulary" in out, out)

    # A brief cites evidence in prose and tables, not citation comments. Without
    # skipping uncited blocks the quantity check emitted eighty warnings on one
    # real brief, which is the check nobody reads.
    uncited = Path(tempfile.mkdtemp()) / "role-interview-brief.md"
    uncited.write_text("# Brief\n\n| Figure | Source |\n| --- | --- |\n"
                       "| ~33% write-offs | `E_CX_FRAUD_LOSS` |\n"
                       "| 70+ detections | `E_CX_DETECTION_PROGRAMME` |\n\n"
                       "- A cited claim. <!-- Evidence: E_CX_FRAUD_LOSS -->\n")
    code, out, _ = run("quantities.py", uncited)
    check("a block citing nothing raises no magnitude warning",
          code == 0 and "does not carry" not in out, out)


def test_pack_pinning():
    """Regression: manifest.py pinned the pack and validate_artifact.py ignored it."""
    import shutil
    tmp = Path(tempfile.mkdtemp())
    md = tmp / "role-draft.md"
    md.write_text("# X\n\nLondon\n\n## Role\n\n- A claim. <!-- Evidence: E_CX_FRAUD_LOSS -->\n")
    run("render.py", md)
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

    tmp = Path(tempfile.mkdtemp())
    # Unconditional: the records are seeded into the fixture, so a missing file
    # is a failure rather than a silently skipped assertion.
    rec = json.loads((fixture() / "outputs" / "head-of-detection-draft-screen.json").read_text())
    bad = dict(rec, verdict="maybe")
    (tmp / "x-screen.json").write_text(json.dumps(bad))
    code, out, _ = run("validate_records.py", tmp / "x-screen.json")
    check("invalid verdict rejected", code == 1 and "not in" in out, out)

    bad2 = dict(rec)
    bad2.pop("top_changes")
    (tmp / "y-screen.json").write_text(json.dumps(bad2))
    code, out, _ = run("validate_records.py", tmp / "y-screen.json")
    check("missing required field rejected", code == 1 and "top_changes" in out, out)

    # Construct the blocker rather than borrowing one from a live artefact. This
    # test used to take the real evaluation record and flip publishable to true,
    # which silently stopped testing anything the day that artefact was
    # regenerated without a blocker in it.
    rec = json.loads((fixture() / "outputs" / "head-of-detection-evaluation.json").read_text())
    bad3 = dict(rec, publishable=True, findings=[{
        "severity": "blocker", "category": "target_fit",
        "message": "Synthetic blocker for the publishable check.",
        "affected": "whole document", "remediation": "n/a"}])
    (tmp / "z-evaluation.json").write_text(json.dumps(bad3))
    code, out, _ = run("validate_records.py", tmp / "z-evaluation.json")
    check("publishable with a blocker is rejected", code == 1 and "blocker" in out, out)

    # `make resume-json` writes outputs/resume.json, and discovery then failed
    # `make records` on it as an unknown record type. Discovery now takes only
    # recognised records; an explicit path is still judged whatever it is called.
    workspace = Path(tempfile.mkdtemp())
    shutil.copytree(fixture(), workspace, dirs_exist_ok=True)
    (workspace / "outputs" / "resume.json").write_text(json.dumps({"basics": {"name": "x"}}))
    code, out, _ = run("validate_records.py", workspace=workspace)
    check("a resume.json export does not break record discovery", code == 0, out)
    code, out, _ = run("validate_records.py", workspace / "outputs" / "resume.json", workspace=workspace)
    check("an explicit unrecognised file still fails", code == 1 and "not a recognised" in out, out)
    shutil.rmtree(workspace, ignore_errors=True)


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
    check("index runs", code == 0, out)
    rows = json.loads(out) if code == 0 else []
    check("index finds artefacts", len(rows) == 2, str(rows))
    check("index reports staleness", all("stale" in r for r in rows))
    drafts = sorted((fixture() / "outputs").glob("*-draft.md"))
    code, out, _ = run("diff_artifact.py", drafts[0], drafts[1])
    check("semantic diff runs", code == 0 and "outcome mix" in out, out)


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
                   "- A claim. <!-- Evidence: E_CX_FRAUD_LOSS -->\n")
    run("render.py", tmp)
    code, out, _ = run("validate_artifact.py", "--current", tmp)
    check("unsourced employer fails", code == 1 and "no employment record" in out, out)
    check("unsourced year fails", "matches no employment record" in out, out)

    tmp2 = Path(tempfile.mkdtemp()) / "f-draft.md"
    tmp2.write_text("# X\n\nLondon\n\n## Role\n\nForty years across things.\n\n"
                    "- A claim. <!-- Evidence: E_CX_FRAUD_LOSS -->\n")
    run("render.py", tmp2)
    code, out, _ = run("validate_artifact.py", "--current", tmp2)
    check("a wrong career-span claim fails", code == 1 and "years of experience" in out, out)

    # The three parts of a heading are one claim. Separate sets of employers,
    # titles and years let one employer wear another's title and dates.
    def artefact(heading, bullet="- A claim. <!-- Evidence: E_CX_FRAUD_LOSS -->\n", workspace=None):
        path = Path(tempfile.mkdtemp()) / "h-draft.md"
        path.write_text("# X\n\nLondon · x@example.invalid\n\n## Experience\n\n"
                        f"### {heading}\n\n{bullet}")
        run("render.py", path, workspace=workspace)
        return run("validate_artifact.py", "--current", path, workspace=workspace)
    code, out, _ = artefact("Northwind Systems | Senior Systems Engineer | 2013 to 2016")
    check("another employer's title on a heading fails", code == 1 and "belongs to no record" in out, out)
    code, out, _ = artefact("Northwind Systems | Director of Platform Security | 2011 to present")
    check("a year outside the role's span fails", code == 1 and "matches no employment record" in out, out)
    code, out, _ = artefact("Northwind Systems | Director of Platform Security | 2017 to present")
    check("a parent title may carry its promotion chain's years", code == 0, out)

    hidden = sandbox()
    shutil.copy(COMPLEX, hidden / "data" / "packs" / "pack.json")
    pack = json.loads((hidden / "data" / "packs" / "pack.json").read_text())
    for rec in pack["employment"]:
        if rec["employment_id"] == "EMP_CX_CONTOSO":
            rec["external_safe"] = False
    (hidden / "data" / "packs" / "pack.json").write_text(json.dumps(pack))
    code, out, _ = artefact("Contoso Retail | Senior Systems Engineer | 2013 to 2016", workspace=hidden)
    check("withheld employment may not head a role block", code == 1 and "withheld" in out, out)
    shutil.rmtree(hidden, ignore_errors=True)

    # One real citation used to cover the whole document.
    code, out, _ = artefact("Northwind Systems | Director of Platform Security | 2022 to present",
                            bullet="- A claim. <!-- Evidence: E_CX_FRAUD_LOSS -->\n"
                                   "- Personally invented a worldwide computing standard.\n")
    check("an uncited bullet fails even beside a cited one",
          code == 1 and "cites no evidence" in out, out)
    brief = Path(tempfile.mkdtemp()) / "x-interview-brief.md"
    brief.write_text("# Brief\n\n## Attacks\n\n- A question, cited nowhere.\n\n"
                     "- Cited. <!-- Evidence: E_CX_FRAUD_LOSS -->\n")
    run("render.py", brief)
    code, out, _ = run("validate_artifact.py", "--private", brief)
    check("a private brief may carry uncited bullets", "cites no evidence" not in out, out)


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


def test_shortlist_actually_curates():
    """The README claims selection curates as a pack grows past what anyone reads.

    Untested and untestable at fixture size: five atoms, and a real pack of twenty,
    both sit under the default limit of thirty, so not_shortlisted was empty on
    every run ever made. The claim was true prospectively and inert in practice.
    """
    workspace = sandbox()
    (workspace / "data" / "roles").mkdir(parents=True)
    pack = json.loads((workspace / "data" / "packs" / "pack.json").read_text())

    template = dict(pack["evidence_atoms"][0])
    grown = []
    for i in range(40):
        atom = json.loads(json.dumps(template))
        atom["id"] = f"E_GROWN_{i:02d}"
        atom["title"] = f"Grown atom {i}"
        # Vary the score so the ranking has something to sort on.
        atom["outcome_type"] = ("business_outcome", "output", "activity")[i % 3]
        grown.append(atom)
    pack["evidence_atoms"] = grown
    (workspace / "data" / "packs" / "pack.json").write_text(json.dumps(pack))
    (workspace / "data" / "roles" / "grown.json").write_text(json.dumps({
        "role_id": "grown", "title": "Grown", "central_requirement": "c",
        "requirements": [{"weight": "essential", "text": "t", "evidenced_by": ["E_GROWN_00"]}],
        "ats_keywords": ["platform engineering"]}))

    code, out, err = run("select_evidence.py", "--role", "grown", workspace=workspace)
    check("selection runs against a pack larger than the shortlist", code == 0, err)
    if code != 0:
        shutil.rmtree(workspace, ignore_errors=True)
        return
    view = json.loads(out)
    check("a pack larger than the limit is actually shortlisted",
          len(view["atoms"]) == 30, f"kept {len(view['atoms'])}")
    check("what was cut is reported rather than silently dropped",
          len(view["not_shortlisted"]) == 10, str(len(view["not_shortlisted"])))
    kept = min(a["role_score"] for a in view["atoms"])
    cut = max(r["role_score"] for r in view["not_shortlisted"])
    check("the shortlist keeps the higher-scoring atoms", kept >= cut, f"{kept} vs {cut}")

    code, out, _ = run("select_evidence.py", "--role", "grown", "--limit", "5", workspace=workspace)
    check("--limit narrows the shortlist", len(json.loads(out)["atoms"]) == 5, out[:120])
    shutil.rmtree(workspace, ignore_errors=True)


def test_complex_pack_shape():
    """The suite was fixture-shaped, and that is how three defects shipped.

    Every assertion ran against a five-atom pack with one employer, no promotion
    chain, no withheld evidence, no unresolved claim and no undated atoms. Those
    are the shapes a real pack has, and running the scripts against one for the
    first time found a leak-scan contradiction, eighty warnings of noise on one
    document, and a fit score with no eligibility filter. This fixture has that
    shape and is entirely fictional.
    """
    code, out, _ = run("validate_pack.py", COMPLEX)
    check("the complex fixture validates", code == 0, out)
    check("its undated atoms are warned about, not errors",
          "cannot be placed in time" in out, out)

    workspace = Path(tempfile.mkdtemp())
    (workspace / "data" / "packs").mkdir(parents=True)
    (workspace / "data" / "roles").mkdir(parents=True)
    (workspace / "outputs").mkdir()
    shutil.copytree(ROOT / "schemas", workspace / "schemas")
    shutil.copy(COMPLEX, workspace / "data" / "packs" / "pack.json")
    pack = json.loads(COMPLEX.read_text())
    atoms = {a["id"]: a for a in pack["evidence_atoms"]}

    # A pack that does hold business outcomes must not get the pack-level warning.
    code, out, _ = run("validate_pack.py", COMPLEX)
    check("a pack with business outcomes is not told it has none",
          "no atom is typed business_outcome" not in out, out)

    code, out, err = run("select_evidence.py", workspace=workspace)
    check("selection runs against the complex pack", code == 0, err)
    view = json.loads(out) if code == 0 else {"atoms": [], "employment": [], "contact": {}}
    shown = {a["id"] for a in view["atoms"]}
    for withheld in ("E_CX_INTERNAL_TOOL", "E_CX_REVENUE_CLAIM"):
        check(f"{withheld} never reaches the selection view", withheld not in shown)
    check("the unresolved atom is withheld for its status too",
          atoms["E_CX_REVENUE_CLAIM"]["evidence_status"] == "unresolved")
    check("address is stripped from the view", "address" not in view["contact"])
    check("photo_reference is stripped from the view", "photo_reference" not in view["contact"])
    check("the object-form metric reaches generation as text",
          any("~33% reduction" in m for a in view["atoms"] for m in a.get("metrics", [])),
          str([a.get("metrics") for a in view["atoms"]][:3]))

    # A three-deep promotion chain: the shape that makes one employer look like
    # four roles, and the one the small example has no version of.
    chain = [r for r in pack["employment"] if r.get("parent_employment_id") == "EMP_CX_DIR"]
    check("the fixture carries a promotion chain", len(chain) == 2, str(chain))
    check("selection keeps every promotion record", len(view["employment"]) == 5,
          str(len(view["employment"])))
    check("career span spans the whole history", view["career_span_years"] >= 14,
          str(view["career_span_years"]))

    # externally_verified is unreachable without an independent source, and the
    # small example has none, so the earning rule was never exercised end to end.
    talk = atoms["E_CX_CONF_TALK"]
    independent = {r["source_id"] for r in pack["source_records"] if r.get("independent")}
    check("externally_verified is reachable in this fixture",
          talk["evidence_status"] == "externally_verified"
          and {r["source_id"] for r in talk["source_refs"]} & independent)

    for script in ("coverage.py", "dedupe.py", "corroboration_plan.py", "export_resume_json.py"):
        code, out, err = run(script, workspace=workspace)
        check(f"{script} runs against a realistically shaped pack", code == 0, err[:200])

    (workspace / "data" / "roles" / "head-of-detection.json").write_text(json.dumps({
        "role_id": "head-of-detection", "title": "Head of Detection",
        "central_requirement": "Has run detection as a function.",
        "requirements": [
            {"weight": "essential", "text": "Runs detection engineering",
             "evidenced_by": ["E_CX_DETECTION_PROGRAMME"]},
            {"weight": "essential", "text": "Owns risk governance tooling",
             "evidenced_by": ["E_CX_INTERNAL_TOOL"]}],
        "ats_keywords": ["detection engineering"]}))
    code, out, _ = run("role_fit.py", "--markdown", workspace=workspace)
    check("fit reports what no artefact may cite",
          code == 0 and "E_CX_INTERNAL_TOOL" in out, out)
    check("and shows the deliverable score diverging from capability",
          "deliverable" in out, out)

    md = workspace / "outputs" / "d-draft.md"
    md.write_text("# Morgan Vale\n\nLondon · morgan.vale@example.invalid\n\n"
                  "## Experience\n\n"
                  "### Northwind Systems | Director of Platform Security | 2022 to present\n\n"
                  "- Cut quarterly fraud write-offs by roughly a third with the "
                  "false-positive rate unchanged. <!-- Evidence: E_CX_FRAUD_LOSS -->\n")
    run("render.py", md, workspace=workspace)
    code, out, _ = run("validate_artifact.py", md, workspace=workspace)
    check("an artefact from the complex pack validates", code == 0, out)
    check("a promotion-chain heading does not trip the employment check",
          "matches no employment record" not in out, out)

    inflated = workspace / "outputs" / "i-draft.md"
    inflated.write_text("# Morgan Vale\n\nLondon · morgan.vale@example.invalid\n\n"
                        "## Experience\n\n"
                        "### Northwind Systems | Director of Platform Security | 2022 to present\n\n"
                        "- Halved quarterly fraud write-offs. <!-- Evidence: E_CX_FRAUD_LOSS -->\n")
    run("render.py", inflated, workspace=workspace)
    code, out, _ = run("validate_artifact.py", inflated, workspace=workspace)
    check("a third inflated into a half warns on the complex pack too",
          "50 pct" in out, out)
    shutil.rmtree(workspace, ignore_errors=True)


def test_pack_html():
    """The pack browser is a private view: it shows withheld atoms on purpose and
    must not carry contact details, because a file that never contains an email
    cannot leak one."""
    workspace = sandbox()
    shutil.copy(COMPLEX, workspace / "data" / "packs" / "pack.json")
    target = workspace / "outputs" / "pack.html"
    code, out, err = run("pack_html.py", "-o", target, workspace=workspace)
    check("pack_html runs", code == 0, err)
    page = target.read_text() if target.exists() else ""

    check("it is marked private", "Private working view" in page)
    check("every atom is rendered", page.count('class="atom') == 12, str(page.count('class="atom')))
    check("withheld atoms are shown and labelled",
          "E_CX_INTERNAL_TOOL" in page and "withheld:" in page)
    check("an unresolved atom's open questions are shown", "Open questions" in page)
    check("a metric with no basis is flagged",
          "no measurement basis recorded" in page)
    check("a metric with a basis shows it", "measured: write-offs booked" in page)
    check("a promotion chain is visible", "promotion under EMP_CX_DIR" in page)
    check("an employer_of_record difference is visible", "paid by Fabrikam" in page)

    profile = json.loads(COMPLEX.read_text())["private_profile"]
    for field in ("email", "phone", "address", "photo_reference"):
        check(f"{field} is never rendered", profile[field] not in page)

    sys.path.insert(0, str(SCRIPTS))
    from validate_artifact import Tags  # noqa: E402
    parser = Tags()
    parser.feed(page)
    check("the page is well-formed html", not parser.stack and not parser.errors,
          f"unclosed {parser.stack[:3]}, mismatched {parser.errors[:3]}")
    check("nothing is hidden without javascript", " hidden " not in page)

    code, _, err = run("pack_html.py", "-o", target, workspace=Path(tempfile.mkdtemp()))
    check("it refuses when there is no pack", code == 1, err)
    shutil.rmtree(workspace, ignore_errors=True)


def test_education():
    """Education was absent from the schema entirely, so a degree could not be
    recorded and JSON Resume's education section could never be filled.

    It is held to the employment standard rather than the atom standard: a
    qualification is not a STAR achievement, it is a fact a background check
    verifies, and the withheld rule applies to it identically.
    """
    code, out, _ = run("validate_pack.py", COMPLEX)
    check("a pack with education validates", code == 0, out)

    for mutate, why in (
            (lambda d: d["education"][0].pop("qualification"), "missing qualification"),
            (lambda d: d["education"][0].update({"instutition": "typo"}), "unknown field"),
            (lambda d: d["education"][0].update({"end": "not-a-year"}), "must be YYYY"),
            (lambda d: d["education"].append(dict(d["education"][0])), "duplicate education_id"),
            (lambda d: d["education"][0].update({"source_refs": [{"source_id": "SRC_NOPE"}]}),
             "unknown source_id")):
        data = json.loads(COMPLEX.read_text())
        mutate(data)
        path = Path(tempfile.mkdtemp()) / "p.json"
        path.write_text(json.dumps(data))
        code, out, _ = run("validate_pack.py", path)
        check(f"education {why} is an error", code == 1 and why.split()[-1] in out, out)

    workspace = Path(tempfile.mkdtemp())
    (workspace / "data" / "packs").mkdir(parents=True)
    (workspace / "outputs").mkdir()
    shutil.copytree(ROOT / "schemas", workspace / "schemas")
    shutil.copy(COMPLEX, workspace / "data" / "packs" / "pack.json")

    code, out, err = run("select_evidence.py", workspace=workspace)
    view = json.loads(out) if code == 0 else {}
    ids = {r["education_id"] for r in view.get("education", [])}
    check("the selection view carries education", "EDU_CX_MSC" in ids, str(ids))
    check("a withheld qualification never reaches generation", "EDU_CX_WITHHELD" not in ids, str(ids))
    check("the view counts education records", view.get("summary", {}).get("education_records") == 1,
          str(view.get("summary")))

    out_json = workspace / "resume.json"
    code, _, err = run("export_resume_json.py", "-o", out_json, workspace=workspace)
    resume = json.loads(out_json.read_text()) if out_json.exists() else {}
    edu = resume.get("education", [])
    check("resume.json carries an education section", len(edu) == 1, str(edu))
    if edu:
        check("it projects into JSON Resume field names",
              edu[0].get("studyType") == "MSc" and edu[0].get("score") == "Distinction"
              and edu[0].get("institution") == "Fictional University", str(edu[0]))
        check("the withheld qualification is not projected",
              all("Academy" not in e.get("institution", "") for e in edu), str(edu))

    page = workspace / "outputs" / "pack.html"
    run("pack_html.py", "-o", page, workspace=workspace)
    html = page.read_text() if page.exists() else ""
    check("the pack browser shows education", "Distinction" in html and "MSc" in html)
    shutil.rmtree(workspace, ignore_errors=True)


def test_open_questions():
    """The queue of outstanding questions is a pure function over the pack and the
    role profiles, so it is a script. Answering "what is still open?" by grepping
    the pack by hand is how questions get missed and how ordering gets lost.

    The ordering matters more than the content: a batch in pack order is abandoned
    early, the same questions ranked by what each unlocks get answered.
    """
    sys.path.insert(0, str(SCRIPTS))
    import open_questions  # noqa: E402

    pack = json.loads(COMPLEX.read_text())
    profile = {"role_id": "r", "title": "R", "central_requirement": "c",
               "requirements": [{"weight": "essential", "text": "nothing evidences this",
                                 "evidenced_by": []}]}
    qs = open_questions.collect(pack, [profile], cited=set())
    kinds = {q["kind"] for q in qs}

    # Found by the subject spotting a blank role block on a finished resume, which
    # is exactly the kind of thing the queue exists to catch first.
    empty = json.loads(COMPLEX.read_text())
    empty["evidence_atoms"] = [a for a in empty["evidence_atoms"]
                               if a.get("employment_id") != "EMP_CX_UNI"]
    eq = open_questions.collect(empty, [], cited=set())
    check("an employer with no evidence at all is surfaced",
          any(q["kind"] == "empty_role" and q["subject"] == "EMP_CX_UNI" for q in eq),
          str([q["subject"] for q in eq if q["kind"] == "empty_role"]))
    check("and it outranks everything except an unevidenced essential requirement",
          eq[0]["kind"] == "empty_role", str(eq[0]))

    # A promotion with no atoms of its own is not a hole: generation collapses the
    # progression into the parent, so the work renders under the parent's heading.
    promo = json.loads(COMPLEX.read_text())
    promo["evidence_atoms"] = [a for a in promo["evidence_atoms"]
                               if a.get("employment_id") != "EMP_CX_LEAD"]
    pq = open_questions.collect(promo, [], cited=set())
    check("an empty promotion inside a chain that has evidence is not asked about",
          not any(q["kind"] == "empty_role" and q["subject"] == "EMP_CX_LEAD" for q in pq),
          str([q["subject"] for q in pq if q["kind"] == "empty_role"]))

    for kind in ("role_gap", "withheld", "undated", "metric_basis", "recorded"):
        check(f"the queue finds {kind} questions", kind in kinds, str(sorted(kinds)))
    check("an unevidenced essential requirement outranks everything else",
          qs[0]["kind"] == "role_gap", str(qs[0]))
    check("the queue is sorted by what answering unlocks",
          [q["score"] for q in qs] == sorted((q["score"] for q in qs), reverse=True))
    check("a withheld atom is named as withheld rather than missing",
          any(q["kind"] == "withheld" and q["subject"] == "E_CX_INTERNAL_TOOL" for q in qs))
    check("a metric that already records its basis is not asked about again",
          not any(q["kind"] == "metric_basis" and "33%" in q["question"] for q in qs),
          str([q["question"] for q in qs if q["kind"] == "metric_basis"]))
    check("a metric carrying no magnitude is not asked for a baseline",
          not any(q["kind"] == "metric_basis" and "coverage" in q["question"].lower() for q in qs))

    cited = open_questions.collect(pack, [profile], cited={"E_CX_MENTORING"})
    plain = {q["question"]: q["score"] for q in qs}
    raised = [q for q in cited if q["subject"] == "E_CX_MENTORING"
              and q["score"] > plain.get(q["question"], 0)]
    check("a question about a claim that reaches artefacts is ranked higher", bool(raised))

    # A declined atom is a recorded decision. The example pack's declined atom
    # says "do not re-ask" in its own notes and used to receive three questions.
    declined_pack = json.loads(EXAMPLE.read_text())
    dq = open_questions.collect(declined_pack, [], cited=set())
    check("a declined atom receives no questions at all",
          not any(q["subject"] == "E_EXAMPLE_PRIOR_EMPLOYER_DETAIL" for q in dq),
          str([q["kind"] for q in dq if q["subject"] == "E_EXAMPLE_PRIOR_EMPLOYER_DETAIL"]))
    # An unresolved atom's recorded questions are the real ones; asking whether
    # it can be published before they are answered is noise.
    kinds_for_unresolved = {q["kind"] for q in qs if q["subject"] == "E_CX_REVENUE_CLAIM"}
    check("an unresolved atom keeps its recorded questions", "recorded" in kinds_for_unresolved,
          str(kinds_for_unresolved))
    check("but is not asked whether it can be published", "withheld" not in kinds_for_unresolved)

    # The guardrail: movement that cites nothing must be visible.
    d = open_questions.delta(pack, COMPLEX)
    check("the delta reports a verdict", "verdict" in d, str(d))

    for args in ([], ["--markdown"], ["--delta"]):
        code, out, err = run("open_questions.py", *args)
        check(f"open_questions.py {' '.join(args) or '(default)'} runs", code == 0, err)


def test_conversation_is_a_source():
    """An atom created by an answer must say so. This is the difference between a
    review that records what the subject recalled and one that records what a
    persuasive question produced."""
    sys.path.insert(0, str(SCRIPTS))
    schema = json.loads((ROOT / "schemas" / "career.schema.json").read_text())
    check("person is an allowed source_type",
          "person" in schema["$defs"]["sourceRecord"]["properties"]["source_type"]["enum"])

    def with_person_source(d):
        d["source_records"].append({"source_id": "SRC_TALK", "source_type": "person",
                                    "path": "reviews/r.md", "retrieved": "2026-09-06",
                                    "independent": False})
        d["evidence_atoms"][0]["source_refs"] = [{"source_id": "SRC_TALK"}]
    code, out, _ = run("validate_pack.py", broken("p.json", with_person_source))
    check("a person source validates without a sha256", code == 0, out)

    def undated_person(d):
        d["source_records"].append({"source_id": "SRC_TALK", "source_type": "person",
                                    "path": "reviews/r.md", "independent": False})
    code, out, _ = run("validate_pack.py", broken("p.json", undated_person))
    check("a person source without a date is an error",
          code == 1 and "retrieved date" in out, out)

    def sourceless(d):
        d["evidence_atoms"][0]["source_refs"] = []
    code, out, _ = run("validate_pack.py", broken("p.json", sourceless))
    check("an atom citing nothing is warned about, not silently accepted",
          "traces to nothing" in out, out)


def test_metric_measurement_basis():
    """A metric is a claim, and a claim whose denominator nobody recorded cannot
    be defended. The interview brief had to say "no baseline recorded" for the two
    highest-risk figures in the document, because the pack had nowhere to put one.

    The plain-string form stays valid so no pack needs migrating.
    """
    sys.path.insert(0, str(SCRIPTS))
    from current_pack import metric_basis, metric_text  # noqa: E402

    check("a plain string metric still reads", metric_text("67% throughput increase")
          == "67% throughput increase")
    check("a plain string metric has no recorded basis",
          metric_basis("67% throughput increase") is None)
    rich = {"value": "67% throughput increase",
            "basis": "threat models completed per quarter, H1 2024 against H2 2024",
            "measured": True}
    check("an object metric reads its value", metric_text(rich) == "67% throughput increase")
    check("an object metric carries its basis", "H1 2024" in metric_basis(rich))

    def with_rich_metric(d):
        d["evidence_atoms"][0]["metrics"] = [rich, "median build time unchanged"]
    path = broken("p.json", with_rich_metric)
    code, out, _ = run("validate_pack.py", path)
    check("a pack mixing both metric forms validates", code == 0, out)

    for bad, why in ((lambda d: d["evidence_atoms"][0].update({"metrics": [{"basis": "x"}]}),
                      "object form needs a value"),
                     (lambda d: d["evidence_atoms"][0].update(
                         {"metrics": [{"value": "x", "bassis": "typo"}]}),
                      "unknown field")):
        code, out, _ = run("validate_pack.py", broken("p.json", bad))
        check(f"metric {why} is an error", code == 1 and why in out, out)

    # The basis has to reach generation, or it is provenance nothing consumes.
    workspace = sandbox()
    pack_path = workspace / "data" / "packs" / "pack.json"
    pack = json.loads(pack_path.read_text())
    pack["evidence_atoms"][0]["metrics"] = [rich,
                                            {"value": "reported uplift", "measured": False}]
    pack_path.write_text(json.dumps(pack))
    code, out, err = run("select_evidence.py", workspace=workspace)
    view = json.loads(out) if code == 0 else {"atoms": []}
    atom = next((a for a in view["atoms"] if a["id"] == pack["evidence_atoms"][0]["id"]), {})
    check("the selection view carries the metric text", "67% throughput increase"
          in atom.get("metrics", []), str(atom.get("metrics")))
    check("the selection view carries the measurement basis",
          "H1 2024" in (atom.get("metric_basis", {}).get("67% throughput increase") or ""),
          str(atom.get("metric_basis")))
    check("an unmeasured metric is flagged before it reaches a page",
          "reported uplift" in atom.get("unmeasured_metrics", []),
          str(atom.get("unmeasured_metrics")))
    shutil.rmtree(workspace, ignore_errors=True)


def test_withheld_evidence_is_visible():
    """Found by a full run against a real pack, not by this suite.

    role_fit.py applied no eligibility filter, so an atom that no artefact may
    cite scored as if a resume could show it. Linked to a requirement it read
    "supported" on unpublishable material; left unlinked, the same capability
    read as an unevidenced gap. Neither number was true, and telling them apart
    took reading a whole pack by hand.
    """
    sys.path.insert(0, str(SCRIPTS))
    import role_fit  # noqa: E402

    # The complex fixture's withheld atom is a described, self-asserted
    # achievement that happens to be confidential. The small example's only
    # ineligible atom is *declined*, and using that here had this test asserting
    # that a refusal to discuss something counts as capability.
    atoms = {a["id"]: a for a in json.loads(COMPLEX.read_text())["evidence_atoms"]}
    withheld = "E_CX_INTERNAL_TOOL"
    check("the fixture carries a withheld but asserted atom to test with",
          withheld in atoms and not atoms[withheld].get("external_safe")
          and atoms[withheld]["evidence_status"] == "self_asserted")

    profile = {"role_id": "r", "title": "R", "central_requirement": "c",
               "requirements": [{"weight": "essential", "text": "needs the withheld one",
                                 "evidenced_by": [withheld]}]}
    capability = role_fit.score(profile, atoms)
    deliverable = role_fit.score(profile, atoms, deliverable=True)
    check("capability fit counts evidence a document may not carry",
          capability["score"] > 0 and not capability["essential_gaps"], str(capability))
    check("deliverable fit does not",
          deliverable["score"] == 0 and deliverable["essential_gaps"], str(deliverable))

    listed = {r["id"] for r in role_fit.withheld(atoms)}
    check("withheld atoms are named next to the verdict", withheld in listed, str(listed))

    code, out, _ = run("role_fit.py", "--markdown")
    check("the fit report names what no artefact may cite",
          code == 0 and "Withheld from every artefact" in out, out)


def test_empty_role_heading():
    """A role heading with nothing under it reads worse than omitting the role.

    Only a finding when the pack HELD eligible evidence and the document did not
    use it. Where the pack has nothing to say, the gap is in the record and
    open_questions.py owns it; blaming the document would be the wrong altitude,
    the same mistake the business_outcome warning used to make.
    """
    workspace = sandbox()
    md = workspace / "outputs" / "d-draft.md"
    head = ("# X\n\nLondon · a@b.example\n\n## Experience\n\n"
            "### Northwind Systems | Staff Platform Engineer | 2022 to present\n\n")
    md.write_text(head + "### Acme Retail Group | Senior Software Engineer | 2018 to 2022\n\n"
                  "- A claim. <!-- Evidence: E_EXAMPLE_PLATFORM_COST -->\n")
    run("render.py", md, workspace=workspace)
    code, out, _ = run("validate_artifact.py", md, workspace=workspace)
    check("a heading with unused eligible evidence under it is flagged",
          "has no claims under it" in out, out)

    md.write_text(head + "- A claim. <!-- Evidence: E_EXAMPLE_PLATFORM_COST -->\n")
    run("render.py", md, workspace=workspace)
    code, out, _ = run("validate_artifact.py", md, workspace=workspace)
    check("a heading with claims under it is not flagged",
          "has no claims under it" not in out, out)
    shutil.rmtree(workspace, ignore_errors=True)


def test_outcome_warning_altitude():
    """A pack with no business_outcome made every artefact warn forever. That is a
    pack property reported per-document, so it taught nothing and got skipped."""
    workspace = sandbox()
    pack_path = workspace / "data" / "packs" / "pack.json"
    pack = json.loads(pack_path.read_text())
    for atom in pack["evidence_atoms"]:
        if atom.get("outcome_type") == "business_outcome":
            atom["outcome_type"] = "activity"
    pack_path.write_text(json.dumps(pack))

    code, out, _ = run("validate_pack.py", pack_path, workspace=workspace)
    check("a pack with no business outcome says so once, at pack level",
          "no atom is typed business_outcome" in out, out)

    md = workspace / "outputs" / "d-draft.md"
    md.write_text("# X\n\n## Role\n\n- A claim. <!-- Evidence: E_EXAMPLE_ONCALL_REDESIGN -->\n")
    run("render.py", md, workspace=workspace)
    code, out, _ = run("validate_artifact.py", md, workspace=workspace)
    check("and the artefact does not repeat it",
          "business_outcome" not in out, out)
    shutil.rmtree(workspace, ignore_errors=True)


def test_verdict_log():
    # A private copy: recording appends to reviews/, and the shared fixture must
    # not accumulate state between tests.
    workspace = Path(tempfile.mkdtemp())
    shutil.copytree(fixture(), workspace, dirs_exist_ok=True)
    code, out, _ = run("verdict_log.py", workspace=workspace)
    check("verdict log runs", code == 0 and "recorded 1" in out, out)
    code, out, _ = run("verdict_log.py", workspace=workspace)
    check("recording twice adds nothing", code == 0 and "no new verdicts" in out, out)

    # Same artefact, same day, same pack, different verdict: this is the change
    # the trend exists to show, and it used to be deduplicated away.
    screen_path = workspace / "outputs" / "head-of-detection-draft-screen.json"
    screen = json.loads(screen_path.read_text())
    screen["verdict"] = "advance" if screen["verdict"] != "advance" else "reject"
    screen_path.write_text(json.dumps(screen))
    code, out, _ = run("verdict_log.py", workspace=workspace)
    check("a changed verdict on the same day is recorded", code == 0 and "recorded 1" in out, out)
    code, out, _ = run("verdict_log.py", workspace=workspace)
    check("an identical re-run after the change still adds nothing", "no new verdicts" in out, out)

    code, out, _ = run("verdict_log.py", "--trend", workspace=workspace)
    check("trend renders", code == 0)
    shutil.rmtree(workspace, ignore_errors=True)


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
    earliest = min(int(r["start"][:4]) for r in fixture_pack()["employment"])
    check("career span is computed from today", view["career_span_years"] is not None)
    check("span tracks the real year",
          view["career_span_years"] == date.today().year - earliest)


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
    # Import the real sort key rather than restating it. The test used to keep its
    # own copy, the two drifted, and the test then failed a correctly ordered view:
    # it read only `occurred.end`, so a point-in-time atom with a start and no end
    # sorted as though it were undated.
    sys.path.insert(0, str(SCRIPTS))
    from select_evidence import recency  # noqa: E402
    ends = [recency(a) for a in outputs]
    check("within a tier, recent work sorts first", ends == sorted(ends, reverse=True), str(ends))


def test_role_aware_selection():
    """Sending the whole pack and asking a model to curate does not survive scale."""
    full = json.loads(run("select_evidence.py")[1])
    code, out, _ = run("select_evidence.py", "--role", "head-of-detection", "--limit", "5")
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


def test_selection_contract():
    """What generation may see is a contract, not whatever fell through.

    The view dropped employment_id, so overlapping roles were attributed by
    guesswork, and dropped every reviewed constraint, so "do not imply sole
    ownership" vanished before the bullet was written. Meanwhile the whole
    employment record passed through, employer_of_record and operator notes
    included, which data-model.md says never appear in an artefact.
    """
    sys.path.insert(0, str(SCRIPTS))
    import select_evidence as sel

    pack = fixture_pack()
    view = sel.view(pack)
    blob = json.dumps(view)
    atom = next(a for a in view["atoms"] if a["id"] == "E_CX_TEAM_GROWTH")
    check("the view carries employment_id", atom.get("employment_id") == "EMP_CX_DIR", str(atom))
    check("the view carries reviewed constraints",
          any("sole ownership" in c for c in atom.get("constraints", [])), str(atom.get("constraints")))
    check("operator notes on atoms never reach generation", "FY2024 headcount plan" not in blob)
    allowed = {"employment_id", "employer", "title", "start", "end", "location", "parent_employment_id"}
    check("employment is projected through an allowlist",
          all(set(r) <= allowed for r in view["employment"]),
          str([sorted(r) for r in view["employment"]][:1]))
    check("employer_of_record never reaches generation", "Fabrikam" not in blob)
    check("employment notes never reach generation", "reference checks go there" not in blob)

    # Whether a fit note counts against a role is judgement; it is carried, not
    # scored. Codex's probe: a note saying "strong for a head-of role" was
    # penalised 1.5 on head-of roles.
    profile = {"role_id": "r", "title": "R", "central_requirement": "c",
               "requirements": [{"weight": "essential", "text": "grow a function",
                                 "evidenced_by": ["E_CX_TEAM_GROWTH"]}],
               "ats_keywords": []}
    scored = sel.view(pack, profile=profile)["atoms"]
    growth = next(a for a in scored if a["id"] == "E_CX_TEAM_GROWTH")
    check("role_fit_notes is surfaced rather than penalised",
          any("role_fit_notes" in r for r in growth["why_selected"])
          and not any("negative signal" in r for r in growth["why_selected"]), str(growth["why_selected"]))
    check("a noted essential atom still scores its essential weight", growth["role_score"] >= 5.0)

    # Essential coverage survives the limit. Two strong examples of one
    # essential used to push out the only example of another.
    grown = json.loads(json.dumps(pack))
    strong = json.loads(json.dumps(next(a for a in grown["evidence_atoms"] if a["id"] == "E_CX_FRAUD_LOSS")))
    strong.update(id="E_STRONG_A", role_fit_notes=None)
    dup = json.loads(json.dumps(strong)); dup["id"] = "E_STRONG_B"
    unique = json.loads(json.dumps(strong))
    unique.update(id="E_UNIQUE", outcome_type="activity", occurred={"start": "2010", "inferred": False})
    grown["evidence_atoms"] = [strong, dup, unique]
    two = {"role_id": "two", "title": "Two", "central_requirement": "c", "ats_keywords": [],
           "requirements": [{"text": "Build", "weight": "essential", "evidenced_by": ["E_STRONG_A", "E_STRONG_B"]},
                            {"text": "Govern", "weight": "essential", "evidenced_by": ["E_UNIQUE"]}]}
    kept = {a["id"] for a in sel.view(grown, profile=two, limit=2)["atoms"]}
    check("a two-slot shortlist keeps the sole evidence for each essential",
          kept == {"E_STRONG_A", "E_UNIQUE"}, str(kept))

    # Per-requirement coverage tells withheld from missing from cut-by-limit.
    cov_profile = {"role_id": "c", "title": "C", "central_requirement": "c", "ats_keywords": [],
                   "requirements": [
                       {"text": "fraud", "weight": "essential", "evidenced_by": ["E_CX_FRAUD_LOSS"]},
                       {"text": "governance tooling", "weight": "essential", "evidenced_by": ["E_CX_INTERNAL_TOOL"]},
                       {"text": "nothing", "weight": "important", "evidenced_by": []},
                       {"text": "mentoring", "weight": "nice_to_have", "evidenced_by": ["E_CX_MENTORING"]}]}
    cov = {c["text"]: c["status"] for c in sel.view(pack, profile=cov_profile, limit=1)["requirement_coverage"]}
    check("requirement coverage reports covered, withheld, missing and omitted",
          cov == {"fraud": "covered", "governance tooling": "withheld",
                  "nothing": "missing", "mentoring": "omitted"}, str(cov))
    check("a pack with no role profile reports empty coverage", view["requirement_coverage"] == [])


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
          len(resume["work"]) < len(fixture_pack()["employment"]))

    pack = fixture_pack()
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

    code, out, _ = run("export_resume_json.py", "--role", "head-of-detection", "--limit", "5")
    scoped = json.loads(out)
    check("role export records the role", scoped["meta"]["role"] == "head-of-detection")
    total = sum(len(w.get("highlights", [])) for w in scoped["work"])
    check("role export shortlists highlights", total <= 5, str(total))


def test_find():
    code, out, _ = run("find.py", "--skill", "threat modeling")
    check("alias spelling finds the canonical skill",
          code == 0 and "E_CX_DETECTION_PROGRAMME" in out, out)
    code, out, _ = run("find.py", "--employer", "Northwind Systems", "--json")
    found = {a["id"] for a in json.loads(out)} if code == 0 else set()
    check("employer search works", "E_CX_FRAUD_LOSS" in found, out[:200])
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
                       "Rebuilt the fraud scoring pipeline with velocity features and a shadow "
                       "deployment; quarterly fraud write-offs fell by roughly a third with the "
                       "false-positive rate unchanged")
    check("a reworded existing claim is flagged", code == 0 and "E_CX_FRAUD_LOSS" in out, out)
    code, out, _ = run("dedupe.py", "--text", "Trained a pet hamster to play the trumpet")
    check("an unrelated claim is not flagged", code == 0 and "looks new" in out, out)
    code, out, _ = run("dedupe.py", "--json")
    check("dedupe emits json", code == 0)


def test_quantities():
    """Magnitude extraction, table-driven, because the risk is a word list.

    Every rule in quantities.py is hand-maintained English, so the tables below
    are the check on the check. Two classes matter equally and pull against each
    other: noise that must stay silent, and magnitudes that must survive
    suppression. An earlier extractor treated any word before a decimal as a
    version number and silently deleted "33.5%", "1.5 seconds", and every other
    decimal claim, which is a check that reports ok while seeing nothing.
    """
    sys.path.insert(0, str(SCRIPTS))
    import quantities  # noqa: E402

    # Nothing here is a claim about magnitude, so nothing may be extracted.
    for text in ["Led SOC 2 Type II readiness across the estate.",
                 "Remediated Log4j (CVE-2021-44228) in the estate.",
                 "Aligned controls to ISO 27001 and PCI DSS 4.0.",
                 "Migrated services to Python 3.11.2 and Terraform v1.5.",
                 "Ran a 24/7 follow-the-sun rotation.",
                 "Delivered the programme between 2019 and 2022.",
                 "Owned the OWASP Top 10 remediation programme.",
                 "Sold into a Fortune 500 client.",
                 # A period, not a proportion. Found when a generated bullet said
                 # "throughput increased 67% half-year on half-year" and the check
                 # reported an unsupported 50%.
                 "Throughput rose half-year on half-year.",
                 "Reported quarter-hour response times.",
                 "Ran a half-day workshop each quarter-year."]:
        found = quantities.extract(text)
        check(f"no magnitude read from {text[:34]!r}", not found, str(sorted(found)))

    # Each of these asserts a magnitude, in the form the generator actually writes.
    for text, expected in [
            ("Cut CI spend by roughly a third.", (33.3, "pct")),
            ("Halved monthly CI spend.", (50.0, "pct")),
            ("Reduced spend by 33%.", (33.0, "pct")),
            ("Reduced spend by 33.5%.", (33.5, "pct")),
            ("Cut costs by 40 per cent.", (40.0, "pct")),
            ("Doubled deployment frequency.", (100.0, "pct")),
            ("A six-person on-call rotation.", (6.0, "count")),
            ("Defeated 39 ships at Wolf 359.", (39.0, "count")),
            ("Thirty-nine ships lost.", (39.0, "count")),
            ("Grew the team to twenty-five engineers.", (25.0, "count")),
            ("Evacuated 15,000 colonists.", (15000.0, "count")),
            ("Sale valued at roughly $7.4bn.", (7.4e9, "money")),
            ("Saved £250k a year.", (250000.0, "money"))]:
        found = quantities.extract(text)
        check(f"{expected[1]} magnitude read from {text[:34]!r}",
              expected in found, str(sorted(found)))

    # Word and digit forms are the same claim: the walkthrough's bullets spell
    # every number out, so without this the check has no coverage on real output.
    check("a third and 33% are the same magnitude",
          quantities.supported((33.3, "pct"), {(33.0, "pct")}))
    check("rounding does not flag", quantities.supported((7.4e9, "money"), {(7.35e9, "money")}))
    check("six and seven stay distinct", not quantities.supported((6.0, "count"), {(7.0, "count")}))
    check("a third is not a half", not quantities.supported((33.3, "pct"), {(50.0, "pct")}))
    check("kinds are never compared across each other",
          not quantities.supported((33.0, "pct"), {(33.0, "count")}))

    # Lower bounds are everywhere in real resume metrics. Reading them as nothing
    # made the report claim the evidence carried no magnitude when it carried two.
    check("a lower bound is read as a bound",
          (50.0, "count+") in quantities.extract("50+ personnel across the function."))
    check("a bounded percentage is read as a bound",
          (20.0, "pct+") in quantities.extract("Grew adoption by 20+ per cent."))
    check("restating a bound is supported",
          quantities.supported((50.0, "count"), {(50.0, "count+")}))
    check("hardening a bound into a point estimate is not supported",
          not quantities.supported((55.0, "count"), {(50.0, "count+")}))

    # Both citation placements are in live use. Handling only the next-line form
    # compared every bullet against an empty set, so every magnitude in a real
    # draft reported as unsupported.
    inline = quantities.cited_blocks("- Cut spend by a third. <!-- Evidence: E_X -->\n")
    check("an inline citation binds to its bullet", inline == [("Cut spend by a third.", ["E_X"])],
          str(inline))
    following = quantities.cited_blocks("- Cut spend by a third.\n<!-- Evidence: E_X -->\n")
    check("a next-line citation binds to its bullet",
          following == [("Cut spend by a third.", ["E_X"])], str(following))
    para = quantities.cited_blocks("## Summary\n\nLed a team of nine. <!-- Evidence: E_X -->\n")
    check("a cited summary paragraph is a claim too",
          para == [("Led a team of nine.", ["E_X"])], str(para))

    # validate_artifact.py checks span claims against employment records. Two
    # checks over one claim can disagree, so this one stays out of it.
    check("a career-span claim is left to validate_artifact.py",
          not quantities.extract("Twenty-four years across military and financial services."))

    # Scope is the whole atom. Narrowing to metrics and star.result flags
    # "six-person" and "a quarter", which live in situation and action.
    pack = json.loads(EXAMPLE.read_text())
    atoms = {a["id"]: a for a in pack["evidence_atoms"]}
    carried = quantities.extract(quantities.atom_text(atoms["E_EXAMPLE_ONCALL_REDESIGN"]))
    check("whole-atom scope carries a magnitude from star.situation",
          (6.0, "count") in carried, str(sorted(carried)))

    workspace = sandbox()
    shutil.copy(WALKTHROUGH / "resume.md", workspace / "outputs" / "resume.md")
    code, out, err = run("quantities.py", workspace / "outputs" / "resume.md", workspace=workspace)
    check("the committed walkthrough asserts no unsupported magnitude",
          code == 0 and out.startswith("ok"), out + err)

    # The motivating case: the atom records ~33%, the bullet claims a half, and
    # every existing check passes because the cited ID is real and eligible.
    inflated = workspace / "outputs" / "inflated.md"
    inflated.write_text("# X\n\n## Role\n\n- Halved monthly CI spend.\n"
                        "<!-- Evidence: E_EXAMPLE_PLATFORM_COST -->\n")
    code, out, _ = run("quantities.py", inflated, "--strict", workspace=workspace)
    check("a bullet inflating a third into a half is flagged",
          code == 1 and "50 pct" in out, out)
    code, out, _ = run("quantities.py", inflated, workspace=workspace)
    check("reporting mode does not fail the run", code == 0, out)

    faithful = workspace / "outputs" / "faithful.md"
    faithful.write_text("# X\n\n## Role\n\n- Cut monthly CI spend by roughly 33%.\n"
                        "<!-- Evidence: E_EXAMPLE_PLATFORM_COST -->\n")
    code, out, _ = run("quantities.py", faithful, "--strict", workspace=workspace)
    check("a faithful restatement in digits is not flagged", code == 0, out)

    # Wired into validate_artifact.py as a warning, never an error: an unsupported
    # magnitude is worth a look, not worth blocking a document over.
    run("render.py", inflated, workspace=workspace)
    code, out, _ = run("validate_artifact.py", inflated, workspace=workspace)
    check("an unsupported magnitude warns rather than fails",
          code == 0 and "warn" in out and "50 pct" in out, out)
    run("render.py", faithful, workspace=workspace)
    code, out, _ = run("validate_artifact.py", faithful, workspace=workspace)
    check("a faithful magnitude produces no warning from validate_artifact",
          code == 0 and "does not carry" not in out, out)

    code, out, _ = run("quantities.py", inflated, "--json", workspace=workspace)
    check("quantities emits json", code == 0 and json.loads(out)["findings"], out)
    shutil.rmtree(workspace, ignore_errors=True)


def test_occurred():
    pack = fixture_pack()
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
                    "at the end of the claim's own line",
                    "business_outcome", "role_fit_notes", "recruiter-screen",
                    "Cover letter", "central_requirement", "employment", "career_span_years",
                    "--role"],
    "build-career-pack": ["private_profile", "business_outcome", "one batch",
                          "validate_pack.py", "optional and off by default",
                          "employer_of_record", "annual write-up", "dedupe.py",
                          "review_period"],
    "review-evidence": ["self_asserted", "corroborated", "externally_verified",
                        "Repetition is not corroboration", "not a requirement",
                        "Never chase them",
                        # The iterative review mode. Every one of these is a rule
                        # that stops the method becoming an inflation engine.
                        "Ask one question. Wait.", "genuine null option",
                        "written into `star.result`", "An answer is a source",
                        "Close an unanswerable question", "open_questions.py",
                        "indistinguishable from a coaching one"],
    "evaluate-output": ["external_safe", "contact block", "recruiter-screen",
                        "Background-check exposure", "employment", "employer_of_record",
                        "LinkedIn About"],
    "recruiter-screen": ["Do not praise", "default is to reject", "advance", "borderline",
                         "reject", "screen-record.schema.json"],
    "ingest-career-materials": ["self_asserted", "extract_text.sh", "independent",
                               "employment", "employer_of_record"],
    "generate-resume": ["outcome_type", "role_fit_notes", "contact block", "constraints"],
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


FUN = ROOT / "examples" / "fun"


def test_fun_packs():
    """The parody packs are committed, so they must validate and stay labelled.

    Two of the three describe real people. The label is the thing that keeps a
    committed file from reading as a genuine record, so it is asserted rather
    than trusted.
    """
    packs = sorted(FUN.glob("*.career.json"))
    check("parody packs present", len(packs) == 3, f"found {[p.name for p in packs]}")
    for path in packs:
        code, out, err = run("validate_pack.py", path)
        check(f"{path.name} validates", code == 0, out + err)
        pack = json.loads(path.read_text())
        check(f"{path.name} marked example_only",
              pack.get("metadata", {}).get("status") == "example_only")
        check(f"{path.name} carries a warning",
              bool(pack.get("metadata", {}).get("warning")))
        check(f"{path.name} uses no real contact details",
              all("example." in (pack["private_profile"].get(f) or "example.")
                  for f in ("email",))
              and not pack["private_profile"].get("phone")
              and not pack["private_profile"].get("address"))
        check(f"{path.name} keeps second-hand claims out of artefacts",
              all(a.get("external_safe") is False
                  for a in pack["evidence_atoms"]
                  if a.get("evidence_status") == "unresolved"))


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


def check_live_tree_untouched():
    """The claim in architecture.md is that tests never touch live data. Assert it
    rather than trust it: every file under data/, outputs/ and reviews/ must have
    the size and mtime it had when the suite started. On a clean checkout those
    directories are empty or absent and this passes trivially."""
    after = _snapshot()
    changed = sorted(set(LIVE_BEFORE) ^ set(after)) + \
        sorted(p for p in LIVE_BEFORE if p in after and LIVE_BEFORE[p] != after[p])
    check("the suite left the owner's data/, outputs/ and reviews/ untouched",
          not changed, "\n".join(changed[:5]))


def check_documented_assertion_count():
    """Last check to run: the documented total against the real one.

    It counts itself, so the number in the doc is the number the suite prints.
    """
    arch = (ROOT / "docs" / "architecture.md").read_text()
    stated = {int(n) for n in re.findall(r"(\d+) assertions", arch)}
    total = len(RESULTS) + 1  # this check counts itself
    check("architecture.md documents the real assertion count",
          stated == {total},
          f"doc states {sorted(stated) or 'nothing'}, suite has {total}")


def main():
    for test in (test_pack_validation, test_selection_view, test_renderer,
                 test_artifact_validation, test_private_brief, test_pack_pinning, test_manifest,
                 test_records, test_corroboration_plan, test_index_and_diff,
                 test_employment, test_role_fit, test_shortlist_actually_curates,
                 test_metric_measurement_basis, test_open_questions,
                 test_conversation_is_a_source, test_complex_pack_shape, test_pack_html,
                 test_education,
                 test_withheld_evidence_is_visible,
                 test_outcome_warning_altitude, test_empty_role_heading,
                 test_verdict_log,
                 test_capture, test_find, test_dedupe, test_quantities, test_occurred,
                 test_no_hardcoded_year, test_view_carries_time_and_tags,
                 test_role_aware_selection, test_selection_contract, test_capture_edit_delete, test_coverage,
                 test_resume_json_export,
                 test_skill_contracts, test_docs_match_reality,
                 test_walkthrough, test_fun_packs):
        test()
    check_live_tree_untouched()
    check_documented_assertion_count()
    failed = [r for r in RESULTS if not r[1]]
    for name, ok, detail in RESULTS:
        if not ok:
            print(f"FAIL  {name}" + (f"\n      {detail.strip()[:200]}" if detail else ""))
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
