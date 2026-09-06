#!/usr/bin/env python3
"""Record something you did, in seconds, without touching the pack.

The workspace could only ever capture what you had already remembered: ingestion
reads documents you sat down and wrote. Nobody writes a document when they clear a
stalled backlog; eighteen months later it is gone.

Notes are appended to data/capture/notes.jsonl. Deliberately not the pack: making
a thirty-second note require a new pack version is exactly the friction that stops
people capturing at all. A later pass promotes notes into evidence atoms, which is
the natural thing to do while writing an annual review.

    scripts/capture.py "cleared the controls backlog in two weeks, no formal authority"
    scripts/capture.py "shipped X" --tag scaling --skill "platform engineering"
    scripts/capture.py --list                # everything not yet promoted
    scripts/capture.py --list --since 2026-01
    scripts/capture.py --edit N0001 "corrected text"
    scripts/capture.py --delete N0001
    scripts/capture.py --promote NOTE_ID --atom E_SOMETHING
"""
import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(os.environ.get("CAREER_WORKSPACE", Path(__file__).resolve().parent.parent))
NOTES = ROOT / "data" / "capture" / "notes.jsonl"
SEQ = ROOT / "data" / "capture" / ".seq"


def load():
    if not NOTES.exists():
        return []
    return [json.loads(line) for line in NOTES.read_text().splitlines() if line.strip()]


def _write_atomically(path, text):
    """Write to a sibling temp file and replace. write_text() truncates before it
    writes, so an interruption mid-save left the log empty: the one file this
    product exists to keep. os.replace is atomic on the same filesystem."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def save_all(notes):
    _write_atomically(NOTES, "".join(json.dumps(n) + "\n" for n in notes))


def next_id(notes):
    """Monotonic and never reused: a deleted note's id may already be cited by an
    atom's capture.note_id, and handing it out again would silently repoint that
    link at unrelated work.

    Deriving the next id from surviving notes alone is not enough, because
    deleting the newest note (or all of them) resets the counter. The high-water
    mark is persisted beside the log.
    """
    highest = 0
    for note in notes:
        match = re.fullmatch(r"N(\d+)", note.get("note_id", ""))
        if match:
            highest = max(highest, int(match.group(1)))
    if SEQ.exists():
        try:
            highest = max(highest, int(SEQ.read_text().strip()))
        except ValueError:
            pass
    nxt = highest + 1
    _write_atomically(SEQ, str(nxt))
    return f"N{nxt:04d}"


def add(text, tags, skills, occurred):
    notes = load()
    note = {
        "note_id": next_id(notes),
        "text": text,
        "captured": date.today().isoformat(),
        "occurred": occurred or date.today().strftime("%Y-%m"),
        "tags": tags,
        "skills": skills,
        "promoted_to": None,
    }
    notes.append(note)
    save_all(notes)
    return note


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("text", nargs="*", help="what you did, in one line")
    parser.add_argument("--tag", action="append", default=[], dest="tags")
    parser.add_argument("--skill", action="append", default=[], dest="skills")
    parser.add_argument("--occurred", help="YYYY or YYYY-MM; defaults to this month")
    parser.add_argument("--list", action="store_true", help="show notes not yet promoted")
    parser.add_argument("--all", action="store_true", help="with --list, include promoted notes")
    parser.add_argument("--since", help="with --list, only notes occurring on or after YYYY-MM")
    parser.add_argument("--edit", metavar="NOTE_ID",
                        help="rewrite a note; pass the new text, or only flags to amend those")
    parser.add_argument("--delete", metavar="NOTE_ID", help="remove a note entirely")
    parser.add_argument("--promote", help="note id to mark as promoted")
    parser.add_argument("--atom", help="the atom id it became")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv[1:])

    if args.delete:
        notes = load()
        remaining = [n for n in notes if n["note_id"] != args.delete]
        if len(remaining) == len(notes):
            print(f"no note {args.delete}", file=sys.stderr)
            return 1
        gone = next(n for n in notes if n["note_id"] == args.delete)
        if gone.get("promoted_to"):
            print(f"{args.delete} was promoted to {gone['promoted_to']}; deleting the note does "
                  f"not remove that atom", file=sys.stderr)
        save_all(remaining)
        # Ids are monotonic, so a deleted id is never handed out again.
        print(f"deleted {args.delete}: {gone['text'][:60]}")
        return 0

    if args.edit:
        notes = load()
        for note in notes:
            if note["note_id"] != args.edit:
                continue
            if args.text:
                note["text"] = " ".join(args.text)
            if args.tags:
                note["tags"] = args.tags
            if args.skills:
                note["skills"] = args.skills
            if args.occurred:
                note["occurred"] = args.occurred
            save_all(notes)
            print(f"{args.edit}  {note['occurred']}  {note['text']}")
            return 0
        print(f"no note {args.edit}", file=sys.stderr)
        return 1

    if args.promote:
        if not args.atom:
            print("--promote needs --atom", file=sys.stderr)
            return 2
        notes = load()
        for note in notes:
            if note["note_id"] == args.promote:
                note["promoted_to"] = args.atom
                save_all(notes)
                print(f"{args.promote} -> {args.atom}")
                return 0
        print(f"no note {args.promote}", file=sys.stderr)
        return 1

    if args.list:
        notes = [n for n in load() if args.all or not n["promoted_to"]]
        if args.since:
            notes = [n for n in notes if n["occurred"] >= args.since]
        notes.sort(key=lambda n: n["occurred"])
        if args.json:
            print(json.dumps(notes, indent=2))
            return 0
        if not notes:
            print("no unpromoted notes")
            return 0
        print(f"{len(notes)} note(s) awaiting promotion into the pack:\n")
        for note in notes:
            meta = []
            if note["tags"]:
                meta.append("tags: " + ", ".join(note["tags"]))
            if note["skills"]:
                meta.append("skills: " + ", ".join(note["skills"]))
            print(f"  {note['note_id']}  {note['occurred']}  {note['text']}")
            if meta:
                print(f"          {' | '.join(meta)}")
        return 0

    if not args.text:
        parser.print_help()
        return 2
    note = add(" ".join(args.text), args.tags, args.skills, args.occurred)
    print(f"{note['note_id']} captured ({note['occurred']}). "
          f"{sum(1 for n in load() if not n['promoted_to'])} awaiting promotion.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
