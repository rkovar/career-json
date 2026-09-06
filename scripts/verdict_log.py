#!/usr/bin/env python3
"""Append screen verdicts to a log, and show whether artefacts are improving.

A screen sidecar is overwritten on every regeneration, so the workspace could tell
you today's verdict and never whether the corroboration work was paying off. The
log is append-only and keyed by artefact, date, and pack hash, so re-running is
safe and a regeneration against the same pack does not create a false data point.

    python3 scripts/verdict_log.py            # record current sidecars
    python3 scripts/verdict_log.py --trend
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from current_pack import ROOT  # noqa: E402

LOG = ROOT / "reviews" / "verdicts.jsonl"
RANK = {"reject": 0, "borderline": 1, "advance": 2}


def existing():
    if not LOG.exists():
        return []
    return [json.loads(line) for line in LOG.read_text().splitlines() if line.strip()]


def record():
    # The verdict is part of the identity. Keyed on artefact, date and pack alone,
    # a screen re-run the same day that changed its verdict added nothing, so the
    # trend lost exactly the changes it exists to show. Identical re-runs still
    # dedupe.
    seen = {(e["artifact"], e["screened"], e.get("pack_sha256"), e.get("verdict"))
            for e in existing()}
    added = []
    for path in sorted((ROOT / "outputs").glob("*-screen.json")):
        data = json.loads(path.read_text())
        entry = {
            "artifact": data["artifact"],
            "target_role": data["target_role"],
            "screened": data["screened"],
            "verdict": data["verdict"],
            "reason": data["reason"],
            "pack_sha256": (data.get("run") or {}).get("pack_sha256"),
            "needs_new_evidence": len(data.get("needs_new_evidence", [])),
            "fix_in_document": len(data.get("fix_in_document", [])),
        }
        key = (entry["artifact"], entry["screened"], entry["pack_sha256"], entry["verdict"])
        if key in seen:
            continue
        added.append(entry)
        seen.add(key)
    if added:
        LOG.parent.mkdir(exist_ok=True)
        with LOG.open("a") as handle:
            for entry in added:
                handle.write(json.dumps(entry) + "\n")
    return added


def trend():
    entries = existing()
    if not entries:
        print("no verdicts recorded yet; run without --trend after a screen")
        return
    by_role = {}
    for entry in entries:
        by_role.setdefault(entry["target_role"], []).append(entry)
    for role, rows in sorted(by_role.items()):
        rows.sort(key=lambda r: r["screened"])
        path = " -> ".join(f"{r['verdict']} ({r['screened']})" for r in rows)
        print(f"{role}\n  {path}")
        if len(rows) > 1:
            delta = RANK[rows[-1]["verdict"]] - RANK[rows[0]["verdict"]]
            direction = "improving" if delta > 0 else "unchanged" if delta == 0 else "worse"
            gap = rows[-1]["needs_new_evidence"] - rows[0]["needs_new_evidence"]
            print(f"  {direction}; open evidence gaps {rows[0]['needs_new_evidence']} -> "
                  f"{rows[-1]['needs_new_evidence']} ({gap:+d})")
        else:
            print(f"  one screen so far; {rows[0]['needs_new_evidence']} evidence gaps open")


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--trend", action="store_true")
    args = parser.parse_args(argv[1:])
    if args.trend:
        trend()
        return 0
    added = record()
    print(f"recorded {len(added)} new verdict(s) in {LOG.relative_to(ROOT)}"
          if added else "no new verdicts to record")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
