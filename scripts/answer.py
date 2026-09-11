#!/usr/bin/env python3
"""Record an answer the moment it is given, verbatim, where the pack can cite it.

A review session asks a question, the subject answers in the conversation, and
the answer used to reach the review record later as narrative written by the
reviewer, or not at all. Three atoms were found citing a record that did not
contain the answers they rest on. The transcript held them; the workspace did
not. What the subject actually said is the source, so it is written down at the
moment it is said, in their words, and the pack cites it by excerpt.

Appends one row to the review record's answer table (creating the table on
first use), atomically, and prints the source_ref to attach to the atom.

    scripts/answer.py reviews/session-2026-09-06.md \\
        --atom E_JPMC_AI_FUNCTION \\
        --question "How many people work on AI security under you?" \\
        --answer "3-5, mixed direct and matrixed"
    scripts/answer.py reviews/session.md --list
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from current_pack import ROOT  # noqa: E402

HEADING = "## Answers, verbatim, as given"
TABLE = ("| Time | Question | Answer, verbatim | Atom |\n"
         "| --- | --- | --- | --- |\n")


def cell(text):
    """A table cell cannot hold a pipe or a newline; the words are otherwise untouched."""
    return " ".join(str(text).replace("|", "│").split())


def append(record, atom, question, answer, source_id=None, now=None):
    now = now or datetime.now()
    text = record.read_text() if record.exists() else f"# Review record\n\n"
    if HEADING not in text:
        text = text.rstrip("\n") + f"\n\n{HEADING}\n\nRecorded by scripts/answer.py at the moment each answer was given. Spelling as typed.\n\n{TABLE}"
    row = f"| {now.strftime('%Y-%m-%d %H:%M')} | {cell(question)} | {cell(answer)} | {cell(atom)} |\n"
    text = text.rstrip("\n") + "\n" + row
    record.parent.mkdir(parents=True, exist_ok=True)
    tmp = record.with_name(record.name + ".tmp")
    with tmp.open("w") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, record)
    try:
        shown = str(record.resolve().relative_to(ROOT))
    except ValueError:
        shown = str(record)
    return {"source_id": source_id or "SRC_SUBJECT_REVIEW_<date>",
            "locator": f"answer at {now.strftime('%H:%M')}: {cell(question)[:60]}",
            "excerpt": cell(answer),
            "_record": shown}


def rows(record):
    out = []
    if not record.exists():
        return out
    seen_heading = False
    for line in record.read_text().splitlines():
        if line.startswith(HEADING):
            seen_heading = True
            continue
        if seen_heading and line.startswith("|") and not line.startswith("| ---") \
                and not line.startswith("| Time"):
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) == 4:
                out.append(dict(zip(("time", "question", "answer", "atom"), parts)))
    return out


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("record", type=Path, help="the review record for this session")
    subject = parser.add_mutually_exclusive_group()
    subject.add_argument("--atom", help="the atom this answer bears on")
    subject.add_argument("--subject", help="strength or preference ID; does not create an evidence atom")
    parser.add_argument("--question")
    parser.add_argument("--answer", help="the subject's words, unedited")
    parser.add_argument("--source", help="the person source_id to cite; printed as a placeholder otherwise")
    parser.add_argument("--list", action="store_true", help="show the answers recorded so far")
    args = parser.parse_args(argv[1:])

    if args.list:
        recorded = rows(args.record)
        print(json.dumps(recorded, indent=2) if recorded else "no answers recorded")
        return 0
    target = args.atom or args.subject
    if not (target and args.question and args.answer):
        parser.error("--atom or --subject, --question and --answer are all required")
    ref = append(args.record, target, args.question, args.answer, args.source)
    record = ref.pop("_record")
    print(f"recorded in {record}; cite it from {target} with:")
    print(json.dumps(ref, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
