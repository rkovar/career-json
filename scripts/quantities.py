#!/usr/bin/env python3
"""Report magnitudes a bullet asserts that its cited evidence does not support.

Generation is instructed to preserve the meaning of a Result. Nothing checked it.
An atom recording "~33% CI spend reduction" and a bullet claiming "halved
infrastructure costs" both cite the same evidence ID, and every existing check
passes: the ID exists, the atom is eligible, the employer and years match.

This is deliberately *not* a fidelity check, and is not named as one. Whether a
bullet preserves the meaning of a Result is entailment, and is not decidable from
the pack. What is decidable is narrower and worth having on its own: a magnitude
asserted in the bullet either traces to one in the cited atom, or it does not.

Two design decisions carry the whole thing.

**Only confident magnitude shapes are extracted.** The obvious approach, take
every numeral and denylist the proper nouns, loses. That denylist is unbounded:
SOC 2, ISO 27001, PCI DSS 4.0, CVE-2021-44228, Python 3.11, 24/7, Black Hat 2023.
Seven of ten realistic bullets emit numerals carrying no claim at all. So the
burden is inverted: percentages, proportional words, currency, and numbers bound
to a counted noun are extracted, and everything else is ignored. Under-flagging is
the correct failure direction, because a check that is overridden routinely is
worse than no check.

**The comparison scope is the whole atom.** Scoping to `metrics` and `star.result`
flags two of the three bullets in the committed walkthrough: "six-person" lives in
`star.situation` and "a quarter" in `star.action`. A bullet legitimately draws on
the whole atom.

Word and digit forms are normalised together, because the generator writes prose.
The walkthrough's bullets contain no digits at all: "roughly a third" has to match
"~33%" or this check has no coverage on real output.

    scripts/quantities.py outputs/head-of-platform-draft.md
    scripts/quantities.py outputs/draft.md --strict     # exit 1 on unsupported
    scripts/quantities.py --text "Halved CI spend." --atom E_EXAMPLE_PLATFORM_COST
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from current_pack import resolve, metric_text, ROOT  # noqa: E402

EVIDENCE_ID = re.compile(r"E_[A-Z0-9_]+")

# Proportional and multiplicative language, normalised to a percentage. This is a
# hand-maintained lexicon and is the honest limit of the check: it is confident on
# what it lists and blind to what it does not.
PROPORTION = {
    "a third": 33.3, "one third": 33.3, "two thirds": 66.7,
    "a quarter": 25.0, "one quarter": 25.0, "three quarters": 75.0,
    "a half": 50.0, "one half": 50.0, "half": 50.0, "halved": 50.0, "halving": 50.0,
    "a fifth": 20.0, "a tenth": 10.0, "an order of magnitude": 900.0,
    "doubled": 100.0, "doubling": 100.0, "tripled": 200.0, "tripling": 200.0,
    "quadrupled": 300.0,
}

UNITS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
         "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
         "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
         "seventeen": 17, "eighteen": 18, "nineteen": 19}
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
        "seventy": 70, "eighty": 80, "ninety": 90}
SCALE = {"k": 1e3, "m": 1e6, "bn": 1e9, "b": 1e9,
         "thousand": 1e3, "million": 1e6, "billion": 1e9}

# Structural noise: shapes that look numeric and never carry a magnitude claim.
# Matched by named vocabulary and by form, never by "a word followed by a number".
# That broader rule was tried first and ate real magnitudes, swallowing the number
# in both "spend 33%" and "defeated 39 ships". A narrower version of the same
# mistake, treating any word before a decimal as a version, then silently removed
# every decimal claim: "33.5%", "1.5 seconds", "2.5 points". Suppression and
# extraction pull against each other here, and suppression must give way: a missed
# magnitude is a check that says nothing, a suppressed one is a check that lies.
NOISE = re.compile(r"""(
      cve-\d{4}-\d+
    | \b(?:iso|iec|nist|sp|pci\s?dss|soc|sox|hipaa|fedramp|gdpr|ieee|rfc|cis|owasp)\s?\d+[\w.:-]*
    | \bv\d+(?:\.\d+)*\b                  # v2, v1.5
    | \b\d+\.\d+\.\d+\b                   # three-part versions: 3.11.2
    | \b(?:top|fortune)\s+\d+\b           # OWASP Top 10, Fortune 500
    | \btype\s+[ivx]+\b
    | \b(?:half|quarter)[\s-](?:year|day|hour|week|month|term)s?\b   # a period, not a proportion
    | \b[\w-]+\s+years?\b                  # span claims: validate_artifact.py owns these
    | \b\d{1,2}\s?/\s?\d{1,2}\b           # 24/7
    | \b(?:19|20)\d{2}\b                  # years: already checked against employment
)""", re.X | re.I)

# A number followed by one of these is not counting anything.
NOT_A_NOUN = {"and", "the", "but", "for", "from", "with", "per", "was", "were",
              "that", "which", "into", "onto", "over", "under", "than", "then",
              "out", "off", "who", "not", "nor", "yet", "its"}

# Rounding and hedged approximation have to survive: "~33%" and "roughly a third"
# are the same claim. Relative, with a floor so that six and seven stay distinct.
TOLERANCE_REL = 0.05
TOLERANCE_ABS = 0.5


def _blank(text, start, end):
    """Consume a matched span so a later, looser pattern cannot re-read it."""
    return text[:start] + " " * (end - start) + text[end:]


def _word_number(text):
    """twenty-five -> 25. Returns None when the phrase is not a number."""
    total = 0
    for part in re.split(r"[\s-]+", text.strip().lower()):
        if part in TENS:
            total += TENS[part]
        elif part in UNITS:
            total += UNITS[part]
        else:
            return None
    return float(total)


def base_kind(kind):
    return kind.rstrip("+")


def extract(text):
    """Magnitudes asserted by this text, as a set of (value, kind).

    kind is one of pct, money, count. Kinds are never compared across each other:
    a 33% reduction and 33 engineers are not the same claim.

    A trailing "+" marks a lower bound. Resume metrics are full of them ("50+
    personnel", "70+ tasks") and reading them as nothing left the report claiming
    the evidence carried no magnitude when it carried two. A bound is compared on
    its value, so a bullet may restate "50+" but hardening it into a precise 55 is
    a magnitude the evidence does not carry.
    """
    if not text:
        return set()
    found = set()
    work = NOISE.sub(lambda m: " " * len(m.group(0)), text.lower())

    for match in re.finditer(r"(\d+(?:\.\d+)?)\s*(\+?)\s*(?:%|per\s?cent)", work):
        found.add((round(float(match.group(1)), 1), "pct" + match.group(2)))
        work = _blank(work, *match.span())

    for phrase, value in PROPORTION.items():
        for match in re.finditer(r"\b" + re.escape(phrase) + r"\b", work):
            found.add((value, "pct"))
            work = _blank(work, *match.span())

    for match in re.finditer(
            r"[£$€]\s?(\d+(?:[.,]\d+)*)\s*(k|m|bn|b|thousand|million|billion)?(\+?)", work):
        value = float(match.group(1).replace(",", ""))
        found.add((value * SCALE.get(match.group(2) or "", 1), "money" + match.group(3)))
        work = _blank(work, *match.span())

    words = "|".join(sorted(list(UNITS) + list(TENS), key=len, reverse=True))
    pattern = (r"\b(?:(\d[\d,]*(?:\.\d+)?)|((?:%s)(?:[\s-](?:%s))?))"
               r"\s*(k|m|bn|thousand|million|billion)?(\+?)[\s-]+([a-z]{2,})" % (words, words))
    for match in re.finditer(pattern, work):
        digits, spelled, scale, bound, noun = match.groups()
        if noun in NOT_A_NOUN:
            continue
        value = float(digits.replace(",", "")) if digits else _word_number(spelled)
        if value is None:
            continue
        found.add((value * SCALE.get(scale or "", 1), "count" + bound))

    return found


def supported(quantity, available):
    """Is this magnitude within tolerance of one the evidence actually carries?"""
    value, kind = quantity
    for other, other_kind in available:
        if base_kind(kind) != base_kind(other_kind):
            continue
        if abs(value - other) <= max(TOLERANCE_ABS, TOLERANCE_REL * max(abs(value), abs(other))):
            return True
    return False


def atom_text(atom):
    """Everything the atom asserts. Narrowing this to metrics and star.result
    produces false positives on the workspace's own canonical example."""
    star = atom.get("star") or {}
    parts = [atom.get("title", "")]
    parts += [metric_text(m) for m in atom.get("metrics", [])]
    parts += [star.get(field) or "" for field in ("situation", "task", "action", "result")]
    return " ".join(parts)


CITATION = re.compile(r"<!--\s*Evidence:\s*(.+?)\s*-->")


def cited_blocks(markdown):
    """Claims paired with the evidence IDs they cite.

    Both citation placements are in live use and only handling one is worse than
    handling neither, because the bullet is then compared against an empty set and
    every magnitude in it reports as unsupported. Run against real drafts, the
    next-line-only parser flagged every bullet in both of them.

        - Cleared the backlog. <!-- Evidence: E_X -->
        - Cleared the backlog.
          <!-- Evidence: E_X -->

    A cited summary paragraph is a claim too, so blocks are not restricted to
    bullets.
    """
    found, current = [], []

    def flush(ids):
        text = " ".join(current).strip()
        current.clear()
        if text:
            found.append((text, ids))

    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            flush([])
            continue
        inline = CITATION.search(stripped)
        if inline and CITATION.sub("", stripped).strip():
            body = CITATION.sub("", stripped).strip()
            if body.startswith(("- ", "* ")):
                flush([])
                body = body[2:]
            current.append(body)
            flush(EVIDENCE_ID.findall(inline.group(1)))
        elif inline:
            flush(EVIDENCE_ID.findall(inline.group(1)))
        elif stripped.startswith(("- ", "* ")):
            flush([])
            current.append(stripped[2:])
        elif not stripped:
            flush([])
        else:
            current.append(stripped)
    flush([])
    return found


def check(markdown, pack):
    """One row per bullet that asserts a magnitude its evidence does not carry."""
    atoms = {a["id"]: a for a in pack.get("evidence_atoms", [])}
    rows = []
    for text, ids in cited_blocks(markdown):
        # Nothing to compare against. An interview brief cites evidence in prose
        # and tables rather than in citation comments, so without this every
        # number in it reported as unsupported: eighty warnings on one document,
        # which is the "check everyone learns to skip" failure exactly.
        if not ids:
            continue
        claimed = extract(text)
        if not claimed:
            continue
        known = set()
        missing = []
        for aid in ids:
            if aid in atoms:
                known |= extract(atom_text(atoms[aid]))
            else:
                missing.append(aid)
        unsupported = sorted(q for q in claimed if not supported(q, known))
        if unsupported or missing:
            rows.append({
                "bullet": text,
                "cites": ids,
                "unknown_ids": missing,
                "unsupported": [{"value": v, "kind": k} for v, k in unsupported],
                "evidence_carries": sorted(f"{v:g} {k}" for v, k in known),
            })
    return rows


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("markdown", type=Path, nargs="?", help="a generated artefact")
    parser.add_argument("--text", help="check one bullet directly")
    parser.add_argument("--atom", action="append", default=[],
                        help="evidence id to check --text against; repeatable")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 when a magnitude is unsupported; reports only by default")
    args = parser.parse_args(argv[1:])

    if not args.markdown and not args.text:
        parser.error("give an artefact, or --text with --atom")

    path = resolve()
    if path is None:
        print("no pack found", file=sys.stderr)
        return 1
    pack = json.loads(path.read_text())

    if args.text:
        cites = " ".join(f"<!-- Evidence: {a} -->" for a in args.atom)
        markdown = f"- {args.text}\n{cites}\n"
        label = "--text"
    else:
        markdown = args.markdown.read_text()
        label = str(args.markdown)

    rows = check(markdown, pack)

    if args.json:
        print(json.dumps({"artefact": label, "findings": rows}, indent=2))
    else:
        print(f"{'FLAG' if rows else 'ok'}  {label}  (against {path.relative_to(ROOT)})")
        for row in rows:
            print(f"      {row['bullet'][:100]}")
            for aid in row["unknown_ids"]:
                print(f"        cites unknown evidence id {aid}")
            for item in row["unsupported"]:
                print(f"        claims {item['value']:g} {item['kind']}, "
                      f"not carried by {', '.join(row['cites']) or 'any cited atom'}")
            if row["evidence_carries"]:
                print(f"        evidence carries: {', '.join(row['evidence_carries'])}")
    # Reporting mode by default on purpose. The real risk here is that a noisy
    # check teaches generation to delete the number rather than go back to the
    # atom, which makes documents vaguer. Measure the rate before it can block.
    return 1 if (rows and args.strict) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
