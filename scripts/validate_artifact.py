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
import render  # noqa: E402
from quantities import CITATION  # noqa: E402

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


# Phrases recruiters told us they discount on sight. Warnings: the fix is a
# rewrite, and a document is not unsafe for carrying one.
CLICHES = ["results-driven", "results driven", "proven track record", "passionate about",
           "dynamic team player", "team player", "self-starter", "go-getter", "synergy",
           "leverage", "leveraged", "thought leader", "cross-functional leader", "detail-oriented",
           "hard-working", "hardworking", "responsible for", "seasoned", "guru", "ninja", "rockstar"]
# Bullet economics. A recruiter's first pass is seconds; these are the limits the
# screens kept asking for, as warnings until their rate is measured.
MAX_BULLETS = {"current": 5, "recent": 3, "old": 1}
OLD_AFTER_YEARS = 12
MAX_BULLET_WORDS = 40
MAX_SUMMARY_WORDS = 75

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


def economics(md, records):
    """Bullets per role block against the role's age, bullet length, summary length."""
    out = []
    by_key = {(r["employer"], r["title"]): r for r in records}
    blocks = re.split(r"^(?=###\s)", md, flags=re.M)
    for block in blocks:
        head = block.splitlines()[0] if block.strip() else ""
        if not head.startswith("### "):
            continue
        parts = [p.strip() for p in head[4:].split("|")]
        if len(parts) < 3:
            continue
        rec = by_key.get((parts[0], parts[1]))
        bullets = re.findall(r"^\s*[-*]\s+(.+)$", block, re.M)
        if rec:
            end = rec.get("end")
            if end == "present":
                kind = "current"
            else:
                ended = int((end or rec["start"])[:4])
                kind = "old" if this_year() - ended > OLD_AFTER_YEARS else "recent"
            limit = MAX_BULLETS[kind]
            if len(bullets) > limit:
                out.append(f"{parts[0]!r} ({kind} role) has {len(bullets)} bullets; a recruiter's first pass "
                           f"gives it {limit}. Cut to the ones that prove the role's requirements")
        for b in bullets:
            words = len(re.sub(r"<!--.*?-->", "", b).split())
            if words > MAX_BULLET_WORDS:
                out.append(f"bullet of {words} words (limit {MAX_BULLET_WORDS}): {b[:60]!r}")
    # The summary: the first paragraph after the contact block.
    paras = [p for p in re.split(r"\n\s*\n", md.split("\n## ")[0]) if p.strip() and not p.startswith("#")]
    if len(paras) >= 2:
        words = len(re.sub(r"<!--.*?-->", "", paras[1]).split())
        if words > MAX_SUMMARY_WORDS:
            out.append(f"summary is {words} words (limit {MAX_SUMMARY_WORDS}); four lines is what gets read")
    return out


def top_third(md, profile, pack):
    """The target title in the headline, and an essential requirement's confirmed
    evidence cited before the second role heading. What ATS and human both look
    for first, and what the AI Security draft buried under an architect title."""
    from select_evidence import linked_ids
    out = []
    before_roles = md.split("\n### ")[0]
    headline = "\n".join(before_roles.splitlines()[:8]).lower()
    title = (profile.get("title") or "").lower()
    if title and title not in headline and not all(w in headline for w in title.split()):
        out.append(f"the target title {profile.get('title')!r} does not appear in the headline or summary; "
                   "a recruiter matching titles will not find it")
    top = md.split("\n### ", 2)
    top_text = top[0] + ("\n### " + top[1] if len(top) > 1 else "")
    cited_top = set(EVIDENCE_ID.findall(top_text))
    essentials = [req for req in profile.get("requirements", []) if req.get("weight") == "essential"]
    proven = [req for req in essentials if set(linked_ids(req, confirmed_only=True)) & cited_top]
    if essentials and not proven:
        out.append("no confirmed evidence for an essential requirement is cited in the summary or first role "
                   "block; the proof of the central requirement sits below the fold")
    return out


def check(md_path, html_path, pack, private=False, strict=False, audience="named_recipient", role=None):
    """private: an interview brief. It is prepared from the whole pack on purpose,
    including atoms no artefact may cite, so eligibility and contact rules invert.

    audience: a public artefact carries name and location only, so an email or
    phone in it is an error rather than the absence being a warning.
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
        # evaluate-output calls an evidence id in visible prose a blocker, and
        # nothing checked it: the id set was read from the whole file, comments
        # included, so "(see E_X for detail)" in a bullet passed as a citation.
        for aid in sorted(set(EVIDENCE_ID.findall(seen))):
            errors.append(f"evidence id {aid} is visible to a reader; ids belong in citation comments only")

    def present(field):
        value = profile.get(field)
        if not value:
            return False
        if field == "phone":
            # Compared on digits: "+1 469 298 8782" and "+1.469.298.8782" are one
            # number, and an exact match reported a reformatted one as missing.
            digits = re.sub(r"\D", "", value)
            return len(digits) >= 7 and digits in re.sub(r"\D", "", seen)
        return value in seen

    has_contact = any(present(field) for field in ("email", "phone"))
    if audience == "public" and not private:
        for field in ("email", "phone", "personal_website"):
            if present(field):
                errors.append(f"{field} appears in a public artefact; a public document carries "
                              "name and location only")
    elif not has_contact and not private:
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
        # Same evidence ids is not the same document. "Reduced spend" and
        # "Increased spend" citing one atom passed this check; the renderer is
        # deterministic, so the html must be exactly what it would produce.
        elif html != render.render(md):
            errors.append("html does not match the renderer's output for this markdown; "
                          "regenerate with scripts/render.py")
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
        all_records = pack.get("employment", [])
        # Withheld employment is as ineligible as a withheld atom, and it used to
        # feed the employer, title and year sets like any other record.
        records = [r for r in all_records if r.get("external_safe")
                   and r.get("evidence_status") not in ("unresolved", "declined")]
        withheld_employers = {r["employer"] for r in all_records} - {r["employer"] for r in records}

        def chain_of(rec):
            """A record plus the promotion chain it belongs to. Generation collapses
            a progression into its parent's heading, so the parent's title may
            legitimately carry the whole chain's years."""
            head = rec.get("parent_employment_id") or rec["employment_id"]
            return [r for r in records
                    if r["employment_id"] == head or r.get("parent_employment_id") == head]

        def year_span(recs):
            starts = [int(r["start"][:4]) for r in recs]
            ends = [this_year() if r.get("end") == "present" else int((r.get("end") or r["start"])[:4])
                    for r in recs]
            return min(starts), max(ends)

        # A role heading with no bullets under it. Only a finding when the pack
        # HELD eligible evidence for that role and the document did not use it:
        # a heading with nothing under it is a normal convention for early career,
        # and reporting it when the pack has nothing to say would be blaming the
        # document for a gap in the record. open_questions.py owns that case.
        by_employment = {}
        for atom in pack.get("evidence_atoms", []):
            eid = atom.get("employment_id")
            if eid and atom.get("external_safe") and \
                    atom.get("evidence_status") not in ("unresolved", "declined"):
                by_employment.setdefault(eid, []).append(atom["id"])
        blocks = re.split(r"^###\s+", md, flags=re.M)[1:]
        for block in blocks:
            head = block.splitlines()[0]
            parts = [p.strip() for p in head.split("|")]
            if len(parts) < 3 or re.search(r"^\s*[-*]\s", block, re.M):
                continue
            for rec in records:
                if rec["employer"] != parts[0] or rec["title"] != parts[1]:
                    continue
                unused = [i for i in by_employment.get(rec["employment_id"], [])
                          if i not in cited]
                if unused:
                    warnings.append(
                        f"role heading {parts[0]!r} has no claims under it, but the pack holds "
                        f"eligible evidence for it: {', '.join(sorted(unused))}")

        # Role headings are written as "### Employer | Title | Dates". The three
        # parts are validated as one combination against one record, not as three
        # independent sets: with separate sets, one employer joined to another
        # employer's title and dates passed with no warning at all.
        global_span = year_span(records) if records else None
        for heading in re.findall(r"^###\s+(.+)$", md, re.M):
            parts = [p.strip() for p in heading.split("|")]
            if len(parts) < 3:
                continue
            employer, title, dates = parts[0], parts[1], parts[2]
            same_employer = [r for r in records if r["employer"] == employer]
            if not same_employer:
                if employer in withheld_employers:
                    errors.append(f"employer {employer!r} is withheld (external_safe false, "
                                  f"unresolved or declined) and may not appear in a role heading")
                else:
                    errors.append(f"employer {employer!r} appears in a role heading but in no employment record")
                # Still say whether the dates are possible at all, against the
                # whole record: an unknown employer with impossible years is two
                # facts, and the second is worth having.
                if global_span:
                    for year in re.findall(r"(?:19|20)\d{2}", dates):
                        if not global_span[0] <= int(year) <= global_span[1]:
                            errors.append(f"year {year} in {employer!r} dates matches no employment record")
                continue
            matched = [r for r in same_employer if r["title"] == title]
            if not matched:
                errors.append(f"title {title!r} does not match any employment record verbatim "
                              f"for {employer!r}; it belongs to no record of that employer")
                continue
            low, high = year_span([r for rec in matched for r in chain_of(rec)])
            for year in re.findall(r"(?:19|20)\d{2}", dates):
                if not low <= int(year) <= high:
                    errors.append(f"year {year} in {employer!r} dates matches no employment record "
                                  f"for that role ({low} to {high})")

        # Every bullet must cite. The document-wide check that some evidence id
        # exists let an invented bullet ride on a neighbour's citation.
        current = []
        def flush():
            if current and not CITATION.search(" ".join(current)):
                errors.append(f"bullet cites no evidence: {current[0][:70]!r}")
            current.clear()
        for line in md.splitlines():
            stripped = line.strip()
            if re.match(r"^[-*]\s", stripped):
                flush()
                current.append(stripped[2:])
            elif current and (not stripped or stripped.startswith("#")):
                flush()
            elif current:
                current.append(stripped)
        flush()

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

    if not private:
        for phrase in CLICHES:
            if re.search(r"(?<![a-z])" + re.escape(phrase) + r"(?![a-z])", seen.lower()):
                warnings.append(f"cliche a recruiter discounts on sight: {phrase!r}")
        warnings.extend(economics(md, [r for r in pack.get("employment", []) if r.get("external_safe")]))
        if role:
            warnings.extend(top_third(md, role, pack))

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


def evaluation_record(md_path):
    """The evaluation record beside an artefact, if there is one."""
    for candidate in (md_path.with_name(md_path.stem.replace("-draft", "") + "-evaluation.json"),
                      md_path.with_suffix(".evaluation.json")):
        if not candidate.exists():
            continue
        try:
            return json.loads(candidate.read_text())
        except json.JSONDecodeError:
            continue
    return None


def producing_pack(md_path):
    """The pack this artefact was generated from, if its evaluation record pinned one.

    Validating a six-month-old artefact against today's pack produces failures that
    are about drift, not about the document. manifest.py records the pin precisely
    so this can be answered; not reading it made the pin decorative.
    """
    run = (evaluation_record(md_path) or {}).get("run") or {}
    pinned, digest = run.get("pack"), run.get("pack_sha256")
    if not pinned:
        return None, None
    path = ROOT / pinned
    if not path.exists():
        return None, f"evaluation pins {pinned}, which no longer exists"
    if digest and sha256(path) != digest:
        return None, f"{pinned} has changed since this artefact was generated; the evaluation is stale"
    return path, None


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
    parser.add_argument("--audience", choices=("named_recipient", "public"), default=None,
                        help="defaults to the evaluation record's audience, else named_recipient")
    parser.add_argument("--role", help="role_id in data/roles/; defaults to the profile whose title matches "
                                       "the evaluation record's target_role, if any")
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

    record = evaluation_record(md_path) or {}
    audience = args.audience or record.get("audience") or "named_recipient"
    profile = None
    roles = ROOT / "data" / "roles"
    if args.role and (roles / f"{args.role}.json").exists():
        profile = json.loads((roles / f"{args.role}.json").read_text())
    elif record.get("target_role") and roles.is_dir():
        for path in roles.glob("*.json"):
            candidate = json.loads(path.read_text())
            if candidate.get("title", "").lower() == record["target_role"].lower():
                profile = candidate
    errors, warnings = check(md_path, html_path, pack, private=args.private, strict=args.strict,
                             audience=audience, role=profile)
    if note:
        warnings.insert(0, note)
    pinned_artifact = (record.get("run") or {}).get("artifact_sha256")
    if pinned_artifact and pinned_artifact != sha256(md_path):
        warnings.insert(0, "the artefact has changed since it was evaluated; the evaluation "
                           "does not cover this text")
    print(f"{'FAIL' if errors else 'ok'}  {md_path}  (against {pack_path.relative_to(ROOT)})")
    for err in errors:
        print(f"      error: {err}")
    for warn in warnings:
        print(f"      warn:  {warn}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
