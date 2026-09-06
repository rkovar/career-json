#!/usr/bin/env python3
"""Check a generated artefact against the pack it came from.

These checks were previously improvised as throwaway Python on every run, which
made them inconsistent and easy to skip. They are pure functions over two files,
so they belong in code.

    python3 scripts/validate_artifact.py outputs/draft.md
    python3 scripts/validate_artifact.py outputs/draft.md --html outputs/draft.html
"""
import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from current_pack import resolve, sha256, this_year, ROOT  # noqa: E402
import quantities  # noqa: E402

EVIDENCE_ID = re.compile(r"E_[A-Z0-9_]+")
# Internal vocabulary that must never reach a reader.
UNITS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
         "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
         "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
         "nineteen": 19}
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50}
# A career-span claim, not any mention of years. "Progressed ... over nine years"
# at one employer is a tenure claim and was being failed against the whole career
# span. Requiring a career marker under-flags rather than over-flags, which is the
# right direction: a missed span claim is silence, a false one trains people to
# ignore the check.
SPAN_CLAIM = re.compile(
    r"\b((?:\d{1,2})|(?:(?:%s)(?:[\s-](?:%s))?)|(?:%s))\s+years?\b"
    r"(?=[\s,]+(?:of\s+)?(?:experience|across))"
    % ("|".join(TENS), "|".join(UNITS), "|".join(UNITS)), re.I)


def words_to_number(text):
    """Career-span claims are written as digits or as words, and both must be checked."""
    text = text.strip().lower().replace("-", " ")
    if text.isdigit():
        return int(text)
    parts = text.split()
    total = 0
    for part in parts:
        if part in TENS:
            total += TENS[part]
        elif part in UNITS:
            total += UNITS[part]
        else:
            return 0
    return total


LEAKS = ["not publishable", "draft status", "publication warning", "withheld pending",
         "pending confirmation", "self_asserted", "user_asserted", "evidence_status",
         "external_safe", "unresolved", "TODO", "FIXME"]


# The HTML void elements, which never close. The list was partial, so any page
# carrying a form control read as permanently unclosed; artefacts have none, so
# it stayed latent until the pack browser was validated with the same parser.
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.errors = [], []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(tag)
        else:
            self.stack.pop()


def visible_text(markdown):
    """What a reader sees: evidence comments and the status rule stripped."""
    return re.sub(r"<!--.*?-->", "", markdown, flags=re.S)


def check(md_path, html_path, pack, private=False, strict=False):
    """private: an interview brief. It is prepared from the whole pack on purpose,
    including atoms no artefact may cite, so eligibility and contact rules invert.
    """
    errors, warnings = [], []
    md = md_path.read_text()
    atoms = {a["id"]: a for a in pack["evidence_atoms"]}
    profile = pack.get("private_profile") or {}

    cited = set(EVIDENCE_ID.findall(md))
    for aid in sorted(cited - set(atoms)):
        errors.append(f"cites unknown evidence id {aid}")
    for aid in sorted(cited & set(atoms)):
        atom = atoms[aid]
        if private:
            continue
        if not atom.get("external_safe"):
            errors.append(f"cites {aid}, which is external_safe: false")
        if atom.get("evidence_status") in ("unresolved", "declined"):
            errors.append(f"cites {aid}, which is {atom['evidence_status']}")
    if not cited:
        errors.append("no evidence IDs: claims cannot be traced to the pack")

    seen = visible_text(md)
    # A private brief has no reader to leak to, and make-interview-brief requires
    # this vocabulary: it must name which atoms are external_safe: false or
    # unresolved so the candidate knows what not to discuss. The eligibility rules
    # were already inverted for --private and the leak scan was not, so a real
    # brief failed on the words that make it useful. The existing fixture missed
    # it by never using them.
    if not private:
        for leak in LEAKS:
            if leak.lower() in seen.lower():
                errors.append(f"internal vocabulary visible to a reader: {leak!r}")

    for field in ("email", "phone"):
        if profile.get(field) and profile[field] in seen:
            has_contact = True
            break
    else:
        has_contact = False
    if not has_contact and not private:
        warnings.append("no email or phone in the visible text; sendable only if this is a public artefact")
    if private and has_contact:
        warnings.append("a private brief does not need contact details")
    for field in ("address", "photo_reference"):
        value = profile.get(field)
        if value and value in seen:
            errors.append(f"{field} must never appear in any artefact")

    if html_path and html_path.exists():
        html = html_path.read_text()
        if set(EVIDENCE_ID.findall(html)) != cited:
            errors.append("markdown and html cite different evidence sets; regenerate with scripts/render.py")
        parser = Tags()
        parser.feed(html)
        if parser.stack or parser.errors:
            errors.append(f"html malformed: unclosed {parser.stack}, mismatched {parser.errors}")
        html_seen = re.sub(r'<span class="evidence">.*?</span>', "", html, flags=re.S)
        if not private:
            for leak in LEAKS:
                if leak.lower() in html_seen.lower():
                    errors.append(f"internal vocabulary visible in html: {leak!r}")

    # Employment: dates, titles, and employers are what a background check tests,
    # and they carry no evidence ID, so nothing else here can see them.
    if not private:
        records = pack.get("employment", [])
        employers = {r["employer"] for r in records}
        titles = {r["title"] for r in records}
        years = set()
        for rec in records:
            for value in (rec.get("start"), rec.get("end")):
                if value and value != "present":
                    years.add(value[:4])
        # Role headings are written as "### Employer | Title | Dates".
        for heading in re.findall(r"^###\s+(.+)$", md, re.M):
            parts = [p.strip() for p in heading.split("|")]
            if len(parts) < 3:
                continue
            employer, title, dates = parts[0], parts[1], parts[2]
            if employer not in employers:
                errors.append(f"employer {employer!r} appears in a role heading but in no employment record")
            if title not in titles:
                warnings.append(f"title {title!r} does not match any employment record verbatim")
            for year in re.findall(r"(19|20)\d{2}", dates):
                pass
            for year in re.findall(r"(?:19|20)\d{2}", dates):
                if year not in years:
                    errors.append(f"year {year} in {employer!r} dates matches no employment record")
        if records:
            spans = []
            for rec in records:
                start = int(rec["start"][:4])
                end_raw = rec.get("end")
                end = this_year() if end_raw == "present" else (int(end_raw[:4]) if end_raw else start)
                spans.append((start, end))
            earliest = min(s for s, _ in spans)
            latest = max(e for _, e in spans)
            for claimed in SPAN_CLAIM.findall(seen):
                value = words_to_number(claimed)
                if value and abs(value - (latest - earliest)) > 1:
                    errors.append(
                        f"claims {value} years of experience; employment records span "
                        f"{earliest} to {latest}, which is {latest - earliest}")

    if strict:
        statuses = [atoms[a]["evidence_status"] for a in cited if a in atoms]
        if statuses and all(s == "self_asserted" for s in statuses):
            warnings.append("every cited atom is self_asserted; nothing here is corroborated")
        corroborated = sum(1 for a in cited if a in atoms and atoms[a].get("corroborators"))
        if cited and corroborated == 0:
            warnings.append("no cited atom has a corroborator identified")
    # A magnitude in a bullet that its cited evidence does not carry. A warning,
    # never an error: the risk is that a flag pressures the next draft into
    # deleting the number rather than going back to the atom, and a vaguer
    # document is a worse outcome than an unchecked one. Run against real drafts
    # this found a "50+ personnel" metric written up as a 55-person organisation,
    # and two documents disagreeing about the size of the same team.
    for row in quantities.check(md, pack):
        # Unknown ids are already an error above; do not report them twice.
        carried = ", ".join(row["evidence_carries"]) or "no magnitude"
        for item in row["unsupported"]:
            warnings.append(
                f"claims {item['value']:g} {item['kind']}, which "
                f"{', '.join(row['cites']) or 'the cited evidence'} does not carry "
                f"({carried}): {row['bullet'][:60]}")

    # Only a finding about *this document* when the pack held a business outcome
    # and the document did not use it. A pack with none makes every artefact fail
    # this check forever, which is a pack-level property reported at the wrong
    # altitude: validate_pack.py says it once instead.
    outcomes = [atoms[a].get("outcome_type") for a in cited if a in atoms]
    pack_has_outcome = any(a.get("outcome_type") == "business_outcome"
                           for a in pack.get("evidence_atoms", []))
    if outcomes and pack_has_outcome and not any(o == "business_outcome" for o in outcomes):
        warnings.append("no cited atom is a business_outcome, though the pack holds one; "
                        "the document describes work, not consequence")
    return errors, warnings


def producing_pack(md_path):
    """The pack this artefact was generated from, if its evaluation record pinned one.

    Validating a six-month-old artefact against today's pack produces failures that
    are about drift, not about the document. manifest.py records the pin precisely
    so this can be answered; not reading it made the pin decorative.
    """
    for candidate in (md_path.with_name(md_path.stem.replace("-draft", "") + "-evaluation.json"),
                      md_path.with_suffix(".evaluation.json")):
        if not candidate.exists():
            continue
        try:
            run = (json.loads(candidate.read_text()).get("run") or {})
        except json.JSONDecodeError:
            continue
        pinned, digest = run.get("pack"), run.get("pack_sha256")
        if not pinned:
            continue
        path = ROOT / pinned
        if not path.exists():
            return None, f"evaluation pins {pinned}, which no longer exists"
        if digest and sha256(path) != digest:
            return None, f"{pinned} has changed since this artefact was generated; the evaluation is stale"
        return path, None
    return None, None


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("markdown", type=Path)
    parser.add_argument("--html", type=Path, default=None)
    parser.add_argument("--strict", action="store_true",
                        help="also warn about missing corroboration, which is otherwise optional")
    parser.add_argument("--private", action="store_true",
                        help="an interview brief: expects ineligible evidence, has no contact block")
    parser.add_argument("--current", action="store_true",
                        help="check against the current pack even if the artefact pins an older one")
    args = parser.parse_args(argv[1:])

    md_path = args.markdown
    html_path = args.html or md_path.with_suffix(".html")

    note = None
    pack_path = None
    if not args.current:
        pack_path, note = producing_pack(md_path)
    if pack_path is None:
        pack_path = resolve()
    if pack_path is None:
        print("no pack found", file=sys.stderr)
        return 1
    pack = json.loads(pack_path.read_text())

    errors, warnings = check(md_path, html_path, pack, private=args.private, strict=args.strict)
    if note:
        warnings.insert(0, note)
    print(f"{'FAIL' if errors else 'ok'}  {md_path}  (against {pack_path.relative_to(ROOT)})")
    for err in errors:
        print(f"      error: {err}")
    for warn in warnings:
        print(f"      warn:  {warn}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
