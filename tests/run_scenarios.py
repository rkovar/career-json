#!/usr/bin/env python3
"""Behavioural evals: run a skill for real and assert on what it did.

tests/run_tests.py proves the scripts and greps the skills for sentences. It
cannot say whether a model following make-resume asks a question, cites a
withheld atom, or skips the screen. These scenarios can. Each one builds a
throwaway workspace from the fictional pack, invokes one skill through the
Claude Code CLI (`claude -p`), and then asserts with the deterministic scripts
the suite already trusts: the draft validates, nothing withheld is cited, the
screen sidecar says where it was produced.

Spends tokens and takes minutes, so it is `make evals`, never `make check`. Run
it after any material skill edit and paste the summary into tests/scenarios.md.

    python3 tests/run_scenarios.py                 # every scenario
    python3 tests/run_scenarios.py --only 2,13,17  # the cheap ones
    python3 tests/run_scenarios.py --budget 2.00   # per-scenario USD cap
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from run_tests import fixture, ROOT, SCRIPTS  # noqa: E402

WITHHELD = ("E_CX_INTERNAL_TOOL", "E_CX_REVENUE_CLAIM")


def workspace():
    root = Path(tempfile.mkdtemp(prefix="career-json-eval-"))
    shutil.rmtree(root)
    shutil.copytree(fixture(), root)
    # A clean outputs/ so a scenario is judged on what it produced, and the
    # scripts the skills invoke by relative path.
    shutil.rmtree(root / "outputs")
    (root / "outputs").mkdir()
    shutil.copytree(ROOT / "scripts", root / "scripts")
    shutil.copy(ROOT / "Makefile", root / "Makefile")
    return root


def invoke(root, request, budget, model, turns):
    env = dict(os.environ)
    env["CAREER_WORKSPACE"] = str(root)
    cmd = ["claude", "-p", request, "--output-format", "json", "--no-session-persistence",
           "--dangerously-skip-permissions", "--max-turns", str(turns),
           "--max-budget-usd", str(budget), "--model", model, "--add-dir", str(root)]
    proc = subprocess.run(cmd, cwd=root, env=env, capture_output=True, text=True, timeout=1800)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {"result": proc.stdout, "is_error": True, "stderr": proc.stderr[-500:]}
    return payload.get("result") or "", payload


def script(root, name, *args):
    env = dict(os.environ)
    env["CAREER_WORKSPACE"] = str(root)
    return subprocess.run([sys.executable, str(SCRIPTS / name), *map(str, args)],
                          capture_output=True, text=True, env=env)


# --- checks: (root, result_text) -> (ok, detail) ---------------------------------
def drafts(root):
    return sorted((root / "outputs").glob("*-draft.md"))


def produced_a_draft(root, text):
    return bool(drafts(root)), f"drafts: {[d.name for d in drafts(root)]}"


def draft_validates(root, text):
    outs = []
    for d in drafts(root):
        proc = script(root, "validate_artifact.py", d)
        outs.append(proc.stdout[:300])
        if proc.returncode != 0:
            return False, proc.stdout[:400]
    return bool(drafts(root)), " ".join(outs)


def cites_nothing_withheld(root, text):
    for d in drafts(root):
        found = [w for w in WITHHELD if w in d.read_text()]
        if found:
            return False, f"{d.name} cites {found}"
    return True, "no withheld id cited"


def no_question_asked(root, text):
    asks = [l for l in text.splitlines() if l.strip().endswith("?")]
    return not asks, f"question lines: {asks[:3]}"


def asks_for_the_role_only(root, text):
    asks = [l for l in text.splitlines() if l.strip().endswith("?")]
    role_q = any("role" in l.lower() for l in asks)
    return role_q and len(asks) <= 2 and not drafts(root), f"question lines: {asks[:3]}; drafts: {len(drafts(root))}"


def screen_is_fresh(root, text):
    sidecars = sorted((root / "outputs").glob("*-screen.json"))
    if not sidecars:
        return False, "no screen sidecar"
    contexts = [json.loads(s.read_text()).get("context") for s in sidecars]
    return all(c == "fresh" for c in contexts), f"contexts: {contexts}"


def quantities_clean(root, text):
    for d in drafts(root):
        proc = script(root, "quantities.py", d, "--json")
        if proc.returncode == 0 and json.loads(proc.stdout).get("findings"):
            return False, proc.stdout[:400]
    return True, "no unsupported magnitude"


def verdict_is_reject(root, text):
    sidecars = sorted((root / "outputs").glob("*-screen.json"))
    verdicts = [json.loads(s.read_text()).get("verdict") for s in sidecars]
    return verdicts == ["reject"], f"verdicts: {verdicts}"


def one_question_no_list(root, text):
    """One question. A numbered list of *answers* under it is the skill's own
    style (every option with its consequence); a numbered list of *questions*
    is the batch the skill forbids."""
    asks = [l for l in text.splitlines() if l.strip().endswith("?")]
    numbered_questions = [l for l in asks if re.match(r"^\s*\d+[.)]\s", l)]
    return len(asks) == 1 and not numbered_questions, f"{len(asks)} question(s), {len(numbered_questions)} numbered question(s)"


def gap_is_reported(root, text):
    """The essential evidenced only by a withheld atom is named as a gap in the report."""
    return "risk governance" in text.lower() and ("gap" in text.lower() or "withheld" in text.lower()
                                                 or "blocker" in text.lower()), text[:300]


def unsendable_is_said(root, text):
    return bool(drafts(root)) and ("unsendable" in text.lower() or "contact" in text.lower()), text[:300]


def evaluation_pins_the_pack(root, text):
    evals = sorted((root / "outputs").glob("*-evaluation.json"))
    pins = [(json.loads(e.read_text()).get("run") or {}).get("pack_sha256") for e in evals]
    return bool(pins) and all(pins), f"pins: {pins}"


def work_lists_are_split(root, text):
    sidecars = sorted((root / "outputs").glob("*-screen.json"))
    if not sidecars:
        return False, "no sidecar"
    rec = json.loads(sidecars[0].read_text())
    return bool(rec.get("fix_in_document")) and bool(rec.get("needs_new_evidence")), \
        f"fix {len(rec.get('fix_in_document', []))}, evidence {len(rec.get('needs_new_evidence', []))}"


NULL_OPTIONS = ("not measured", "cannot recall", "can't recall", "don't know", "do not know",
                "not sure", "unknown", "narrow", "never measured", "no idea", "leave it")


def question_has_a_null_option(root, text):
    return any(n in text.lower() for n in NULL_OPTIONS), text[:400]


def packs(root):
    return sorted((root / "data" / "packs").glob("*.json"))


def pack_written_and_valid(root, text):
    if not packs(root):
        return False, "no pack written"
    proc = script(root, "validate_pack.py", packs(root)[-1])
    return proc.returncode == 0, proc.stdout[:300]


def everything_self_asserted(root, text):
    """A claim in both the CV and the LinkedIn text is still self_asserted."""
    if not packs(root):
        return False, "no pack"
    pack = json.loads(packs(root)[-1].read_text())
    statuses = {a["evidence_status"] for a in pack.get("evidence_atoms", [])}
    return statuses <= {"self_asserted", "unresolved", "declined"}, f"statuses: {statuses}"


def sources_hashed(root, text):
    if not packs(root):
        return False, "no pack"
    pack = json.loads(packs(root)[-1].read_text())
    ok = []
    for s in pack.get("source_records", []):
        p = root / s.get("path", "")
        ok.append(p.exists() and s.get("sha256") == hashlib.sha256(p.read_bytes()).hexdigest())
    return bool(ok) and all(ok), f"sources: {[s.get('source_id') for s in pack.get('source_records', [])]}"


def contact_was_asked_or_found(root, text):
    if not packs(root):
        return False, "no pack"
    profile = json.loads(packs(root)[-1].read_text()).get("private_profile") or {}
    return bool(profile.get("email") or profile.get("phone")) or "contact" in text.lower(), text[:200]


# --- setups ---------------------------------------------------------------------
def no_role_anywhere(root):
    shutil.rmtree(root / "data" / "roles")
    (root / "data" / "roles").mkdir()
    for p in (root / "data" / "sources").glob("*"):
        p.unlink()


def no_contact_details(root):
    pack_path = root / "data" / "packs" / "pack.json"
    pack = json.loads(pack_path.read_text())
    pack["private_profile"] = {"name": pack["private_profile"]["name"], "location": "London"}
    pack_path.write_text(json.dumps(pack))


def fresh_workspace_one_source(root):
    """No pack, no roles, one fictional CV and one LinkedIn text making the same claim."""
    for p in (root / "data" / "packs").glob("*.json"):
        p.unlink()
    shutil.rmtree(root / "data" / "roles")
    (root / "data" / "roles").mkdir()
    (root / "data" / "sources").mkdir(exist_ok=True)
    for name in ("fictional-cv.txt", "fictional-linkedin.txt"):
        shutil.copy(ROOT / "tests" / "fixtures" / name, root / "data" / "sources" / name)


def weak_draft_without_contact(root):
    (root / "outputs" / "weak-draft.md").write_text(
        "# Morgan Vale\n\n## Experience\n\n### Northwind Systems | Director of Platform Security | 2022 to present\n\n"
        "- Responsible for various security initiatives. <!-- Evidence: E_CX_DETECTION_PROGRAMME -->\n"
        "- Attended many meetings and helped the team. <!-- Evidence: E_CX_ONCALL -->\n")
    script(root, "render.py", root / "outputs" / "weak-draft.md")


def add_a_note_source(root):
    """Between the two runs a new source appears, so the re-run must both skip the
    unchanged files and write a superseding version. Without it a re-run that
    writes nothing is the correct behaviour, and the first run of this eval
    failed a model for being right."""
    (root / "data" / "sources" / "award-note.txt").write_text(
        "Morgan Vale received the Northwind Engineering Excellence Award in 2024 for the fraud detection programme.\n")


SCENARIOS = {
    1: dict(skill="make-resume",
            request="Follow .claude/skills/make-resume/SKILL.md for the role head-of-detection (profile in data/roles/). Produce the document in outputs/.",
            checks=[produced_a_draft, draft_validates, cites_nothing_withheld, no_question_asked,
                    quantities_clean, screen_is_fresh, evaluation_pins_the_pack],
            turns=80),
    2: dict(skill="make-resume",
            request="Follow .claude/skills/make-resume/SKILL.md. Make me a resume.",
            setup=no_role_anywhere, checks=[asks_for_the_role_only], turns=15),
    13: dict(skill="recruiter-screen",
             request="Follow .claude/skills/recruiter-screen/SKILL.md on outputs/weak-draft.md for the role Head of Detection (data/roles/head-of-detection.json). Write the screen and its sidecar.",
             setup=weak_draft_without_contact, checks=[verdict_is_reject, work_lists_are_split], turns=30),
    17: dict(skill="review-evidence",
             request="Follow .claude/skills/review-evidence/SKILL.md in iterative mode against the current pack. Start the session: ask me the first question and stop there.",
             checks=[one_question_no_list, question_has_a_null_option], turns=15),
    3: dict(skill="make-resume",
            request="Follow .claude/skills/make-resume/SKILL.md for the role head-of-detection (profile in data/roles/). Produce the document in outputs/.",
            checks=[produced_a_draft, cites_nothing_withheld, gap_is_reported], turns=80),
    4: dict(skill="make-resume",
            request="Follow .claude/skills/make-resume/SKILL.md for the role head-of-detection (profile in data/roles/). Produce the document in outputs/.",
            setup=no_contact_details, checks=[produced_a_draft, unsendable_is_said], turns=80),
    7: dict(skill="build-career-pack",
            request="Follow .claude/skills/build-career-pack/SKILL.md: build the pack from everything in data/sources/. There is no existing pack. Finish the run and queue the questions; do not wait for answers.",
            setup=fresh_workspace_one_source,
            checks=[pack_written_and_valid, everything_self_asserted, sources_hashed, contact_was_asked_or_found],
            turns=80, then=8),
    8: dict(skill="build-career-pack",
            request="Follow .claude/skills/build-career-pack/SKILL.md again on the same workspace: re-ingest everything in data/sources/ against the current pack. One source is new.",
            setup=add_a_note_source, checks=[], turns=60, after=7),
}


def unchanged_source_skipped(root, text):
    """Said in the report, or provable from the pack: the two original sources keep
    their records and hashes, and the note added between runs got one. The
    report text alone missed a run whose final message was the first review
    question rather than the ingestion report."""
    low = text.lower()
    said = any(k in low for k in ("unchanged", "skipped", "hash-match", "hash match", "already ingested"))
    if not packs(root):
        return False, "no pack"
    pack = json.loads(packs(root)[-1].read_text())
    paths = {s.get("path", "") for s in pack.get("source_records", [])}
    recorded = all(any(name in p for p in paths) for name in ("fictional-cv.txt", "fictional-linkedin.txt", "award-note.txt"))
    return said or recorded, f"said: {said}; recorded: {sorted(paths)}"


def new_version_supersedes(root, text, before):
    """Scenario 11: a new pack file, the previous untouched, supersedes set."""
    now = packs(root)
    newest = json.loads(now[-1].read_text()) if now else {}
    prev_untouched = all(hashlib.sha256(p.read_bytes()).hexdigest() == h for p, h in before.items() if p.exists())
    return (len(now) > len(before) and prev_untouched
            and bool((newest.get("metadata") or {}).get("supersedes"))), \
        f"packs before {len(before)}, after {len(now)}; previous untouched {prev_untouched}"


SCENARIOS[8]["checks"] = [unchanged_source_skipped]


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", help="comma-separated scenario numbers")
    parser.add_argument("--budget", type=float, default=3.0, help="USD cap per scenario")
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--keep", action="store_true", help="keep the workspaces for inspection")
    args = parser.parse_args(argv[1:])
    wanted = [int(x) for x in args.only.split(",")] if args.only else sorted(SCENARIOS)

    report = []
    carried = {}
    for number in wanted:
        spec = SCENARIOS[number]
        if spec.get("after"):
            # Runs on the workspace its predecessor left, after a snapshot of the packs.
            root = carried.get(spec["after"])
            if root is None:
                print(f"SKIP  #{number}: needs #{spec['after']} in the same run")
                continue
            before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in packs(root)}
            if spec.get("setup"):
                spec["setup"](root)
        else:
            root = workspace()
            if spec.get("setup"):
                spec["setup"](root)
        text, payload = invoke(root, spec["request"], args.budget, args.model, spec.get("turns", 40))
        results = [(fn.__name__, *fn(root, text)) for fn in spec["checks"]]
        if spec.get("after"):
            results.append(("new_version_supersedes", *new_version_supersedes(root, text, before)))
        if spec.get("then"):
            carried[number] = root
        passed = all(ok for _, ok, _ in results)
        report.append({"scenario": number, "skill": spec["skill"], "passed": passed,
                       "checks": [{"check": n, "ok": ok, "detail": d} for n, ok, d in results],
                       "result_text": text[:3000],
                       "cost_usd": payload.get("total_cost_usd"), "turns": payload.get("num_turns"),
                       "workspace": str(root) if args.keep else None})
        print(f"{'PASS' if passed else 'FAIL'}  #{number} {spec['skill']}  "
              f"(${payload.get('total_cost_usd') or 0:.2f}, {payload.get('num_turns')} turns)")
        for n, ok, d in results:
            print(f"      {'ok ' if ok else 'BAD'} {n}: {d[:160]}")
        if not passed:
            print("      --- what the model said (first 600 chars) ---")
            for line in text[:600].splitlines():
                print(f"      | {line}")
        if not args.keep and number not in carried:
            shutil.rmtree(root, ignore_errors=True)

    out = ROOT / "outputs" / f"evals-{date.today().isoformat()}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(f"\n{sum(r['passed'] for r in report)}/{len(report)} scenarios passed; written to {out.relative_to(ROOT)}")
    print("\nFor tests/scenarios.md:")
    print(f"| {date.today().isoformat()} | " + ", ".join(f"#{r['scenario']} {'pass' if r['passed'] else 'fail'}" for r in report) + " |")
    return 0 if all(r["passed"] for r in report) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
