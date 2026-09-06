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


# --- setups ---------------------------------------------------------------------
def no_role_anywhere(root):
    shutil.rmtree(root / "data" / "roles")
    (root / "data" / "roles").mkdir()
    for p in (root / "data" / "sources").glob("*"):
        p.unlink()


def weak_draft_without_contact(root):
    (root / "outputs" / "weak-draft.md").write_text(
        "# Morgan Vale\n\n## Experience\n\n### Northwind Systems | Director of Platform Security | 2022 to present\n\n"
        "- Responsible for various security initiatives. <!-- Evidence: E_CX_DETECTION_PROGRAMME -->\n"
        "- Attended many meetings and helped the team. <!-- Evidence: E_CX_ONCALL -->\n")
    script(root, "render.py", root / "outputs" / "weak-draft.md")


SCENARIOS = {
    1: dict(skill="make-resume",
            request="Follow .claude/skills/make-resume/SKILL.md for the role head-of-detection (profile in data/roles/). Produce the document in outputs/.",
            checks=[produced_a_draft, draft_validates, cites_nothing_withheld, no_question_asked,
                    quantities_clean, screen_is_fresh],
            turns=80),
    2: dict(skill="make-resume",
            request="Follow .claude/skills/make-resume/SKILL.md. Make me a resume.",
            setup=no_role_anywhere, checks=[asks_for_the_role_only], turns=15),
    13: dict(skill="recruiter-screen",
             request="Follow .claude/skills/recruiter-screen/SKILL.md on outputs/weak-draft.md for the role Head of Detection (data/roles/head-of-detection.json). Write the screen and its sidecar.",
             setup=weak_draft_without_contact, checks=[verdict_is_reject], turns=30),
    17: dict(skill="review-evidence",
             request="Follow .claude/skills/review-evidence/SKILL.md in iterative mode against the current pack. Start the session: ask me the first question and stop there.",
             checks=[one_question_no_list], turns=15),
}


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", help="comma-separated scenario numbers")
    parser.add_argument("--budget", type=float, default=3.0, help="USD cap per scenario")
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--keep", action="store_true", help="keep the workspaces for inspection")
    args = parser.parse_args(argv[1:])
    wanted = [int(x) for x in args.only.split(",")] if args.only else sorted(SCENARIOS)

    report = []
    for number in wanted:
        spec = SCENARIOS[number]
        root = workspace()
        if spec.get("setup"):
            spec["setup"](root)
        text, payload = invoke(root, spec["request"], args.budget, args.model, spec.get("turns", 40))
        results = [(fn.__name__, *fn(root, text)) for fn in spec["checks"]]
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
        if not args.keep:
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
