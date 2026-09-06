#!/usr/bin/env python3
"""Find claims already in the pack, before an import adds them twice.

An annual write-up restates work. Year two's review will describe the same
programme year one already recorded, in different words, and without a check the
pack slowly fills with near-duplicates that split the evidence for one achievement
across three atoms.

Similarity is token overlap over title, STAR text, and metrics. Deliberately
crude and explainable: it is a prompt to look, not a decision.

    scripts/dedupe.py                          # near-duplicates already in the pack
    scripts/dedupe.py --text "cleared the stalled controls backlog in two weeks"
    scripts/dedupe.py --notes                  # check unpromoted capture notes
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from current_pack import resolve, ROOT  # noqa: E402

NOTES = ROOT / "data" / "capture" / "notes.jsonl"
STOP = set("""a an and are as at be by for from has have in into is it its of on or that the
to was were will with we our i my me they their this these those been being do did done
than then them there here also more most very much many any all some such no not only own
same so too can could would should may might must across over under after before during""".split())


def tokens(text):
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower())
            if len(w) > 2 and w not in STOP}


def atom_tokens(atom):
    star = atom.get("star") or {}
    parts = [atom.get("title", "")] + [star.get(k) or "" for k in ("situation", "task", "action", "result")]
    parts += atom.get("metrics", []) + atom.get("skills", [])
    return tokens(" ".join(parts))


def similarity(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--text", help="candidate claim to check before adding it")
    parser.add_argument("--notes", action="store_true", help="check unpromoted capture notes")
    parser.add_argument("--threshold", type=float, default=0.25)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv[1:])

    path = resolve()
    if path is None:
        print("no pack found", file=sys.stderr)
        return 1
    pack = json.loads(path.read_text())
    atoms = pack["evidence_atoms"]
    index = {a["id"]: atom_tokens(a) for a in atoms}
    titles = {a["id"]: a["title"] for a in atoms}

    results = []
    if args.text:
        candidate = tokens(args.text)
        for aid, toks in index.items():
            score = similarity(candidate, toks)
            if score >= args.threshold:
                results.append({"candidate": args.text[:60], "atom": aid,
                                "title": titles[aid], "score": round(score, 2)})
    elif args.notes:
        if not NOTES.exists():
            print("no capture notes")
            return 0
        for line in NOTES.read_text().splitlines():
            note = json.loads(line)
            if note.get("promoted_to"):
                continue
            candidate = tokens(note["text"] + " " + " ".join(note.get("skills", [])))
            for aid, toks in index.items():
                score = similarity(candidate, toks)
                if score >= args.threshold:
                    results.append({"candidate": note["note_id"] + ": " + note["text"][:50],
                                    "atom": aid, "title": titles[aid], "score": round(score, 2)})
    else:
        ids = list(index)
        for i, left in enumerate(ids):
            for right in ids[i + 1:]:
                score = similarity(index[left], index[right])
                if score >= args.threshold:
                    results.append({"candidate": left, "atom": right,
                                    "title": titles[right], "score": round(score, 2)})

    results.sort(key=lambda r: -r["score"])
    if args.json:
        print(json.dumps(results, indent=2))
        return 0
    if not results:
        print(f"nothing above {args.threshold} similarity; looks new")
        return 0
    print(f"{len(results)} possible overlap(s). Look before adding: the same achievement")
    print("split across atoms is worse than one atom stated properly.\n")
    for row in results:
        print(f"  {row['score']:.2f}  {row['candidate']}")
        print(f"        vs {row['atom']}: {row['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
