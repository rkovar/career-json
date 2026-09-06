#!/usr/bin/env python3
"""Structural validator for career datapacks.

Standard library only, by design: this workspace has no Python dependencies and
should not acquire any. It checks the constraints that matter in practice rather
than implementing JSON Schema. Enum values are read from the schema so the two
cannot drift.

    python3 scripts/validate_pack.py data/packs/<pack>.json
    python3 scripts/validate_pack.py            # validates every pack and example
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CAREER_WORKSPACE", Path(__file__).resolve().parent.parent))
SCHEMA = ROOT / "schemas" / "career.schema.json"
SHA256 = re.compile(r"^[a-f0-9]{64}$")


def enums(schema):
    atom = schema["$defs"]["evidenceAtom"]["properties"]
    src = schema["$defs"]["sourceRecord"]["properties"]
    return {
        "status": set(atom["evidence_status"]["enum"]),
        "outcome": {v for v in atom["outcome_type"]["enum"] if v is not None},
        "source_type": set(src["source_type"]["enum"]),
        "version": schema["properties"]["schema_version"]["const"],
    }


def check(path, schema, strict=False):
    errors, warnings = [], []
    try:
        pack = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return [f"invalid JSON: {exc}"], []

    e = enums(schema)
    if pack.get("schema_version") != e["version"]:
        errors.append(f"schema_version is {pack.get('schema_version')!r}, expected {e['version']!r}")

    # The supersedes chain is how "which pack is current" gets exactly one answer.
    # A link to a file that does not exist, or to itself, was never checked, so a
    # typo here silently changed which pack every script resolved.
    supersedes = (pack.get("metadata") or {}).get("supersedes")
    if supersedes:
        target = (ROOT / supersedes)
        if target.resolve() == path.resolve():
            errors.append("metadata.supersedes points at this pack itself")
        elif not target.exists():
            errors.append(f"metadata.supersedes points at {supersedes}, which does not exist")

    source_ids = set()
    for i, rec in enumerate(pack.get("source_records", [])):
        where = f"source_records[{i}]"
        for field in ("source_id", "source_type", "path"):
            if not rec.get(field):
                errors.append(f"{where}: missing {field}")
        sid = rec.get("source_id")
        if sid in source_ids:
            errors.append(f"{where}: duplicate source_id {sid!r}")
        source_ids.add(sid)
        stype = rec.get("source_type")
        if stype and stype not in e["source_type"]:
            errors.append(f"{where}: source_type {stype!r} not in {sorted(e['source_type'])}")
        # A person source is a conversation. Like a URL it has no hash, so the date
        # is the only thing making it auditable. "person" sat in the enum from the
        # start and was unusable, because anything that was not a url was required
        # to carry a sha256.
        if stype in ("url", "person"):
            if not rec.get("retrieved"):
                errors.append(f"{where}: {stype} sources need a retrieved date to be auditable")
        else:
            if not SHA256.match(rec.get("sha256") or ""):
                errors.append(f"{where}: file sources need a sha256")
            if not isinstance(rec.get("character_count"), int):
                errors.append(f"{where}: file sources need an integer character_count")
        if "independent" not in rec:
            warnings.append(f"{where}: no independent flag; assumed not independent")
        elif not isinstance(rec.get("independent"), bool):
            # external_safe is type-checked in three places and this never was, so
            # the string "false" was truthy and could authorise externally_verified.
            # A typo must not upgrade the strength of the record.
            errors.append(f"{where}: independent must be boolean, got {rec.get('independent')!r}")

    # Employment: the facts a background check actually verifies.
    employment_ids = set()
    emp_schema = schema["$defs"]["employmentRecord"]
    for i, rec in enumerate(pack.get("employment", [])):
        eid = rec.get("employment_id") or f"<index {i}>"
        where = f"employment[{eid}]"
        for field in emp_schema["required"]:
            if rec.get(field) in (None, "") and field != "external_safe":
                errors.append(f"{where}: missing {field}")
        if rec.get("employment_id") in employment_ids:
            errors.append(f"{where}: duplicate employment_id")
        employment_ids.add(rec.get("employment_id"))
        for field in set(rec) - set(emp_schema["properties"]):
            errors.append(f"{where}: unknown field {field!r}")
        if rec.get("evidence_status") not in e["status"]:
            errors.append(f"{where}: evidence_status {rec.get('evidence_status')!r} not in {sorted(e['status'])}")
        if not isinstance(rec.get("external_safe"), bool):
            errors.append(f"{where}: external_safe must be present and boolean")
        start, end = rec.get("start"), rec.get("end")
        if start and not re.match(r"^\d{4}(-\d{2})?$", start):
            errors.append(f"{where}: start {start!r} must be YYYY or YYYY-MM")
        if end is None:
            warnings.append(f"{where}: end is unknown; if this role is current, set it to 'present'")
        elif end != "present":
            if not re.match(r"^\d{4}(-\d{2})?$", end):
                errors.append(f"{where}: end {end!r} must be YYYY, YYYY-MM, or 'present'")
            elif start and end < start:
                errors.append(f"{where}: ends {end} before it starts {start}")
        if not rec.get("source_refs"):
            warnings.append(f"{where}: no source_refs; the dates trace to nothing")
        for ref in rec.get("source_refs", []):
            if ref.get("source_id") not in source_ids:
                errors.append(f"{where}: source_ref points at unknown source_id {ref.get('source_id')!r}")
    for i, rec in enumerate(pack.get("employment", [])):
        parent = rec.get("parent_employment_id")
        if parent and parent not in employment_ids:
            errors.append(f"employment[{rec.get('employment_id')}]: unknown parent_employment_id {parent!r}")
    if not pack.get("employment"):
        errors.append("no employment records; every date and title in a generated artefact would be unsourced")

    # Education: like employment, a fact a background check tests rather than a
    # claim an atom argues. Held to the same standard.
    edu_schema = schema["$defs"]["educationRecord"]
    education_ids = set()
    for i, rec in enumerate(pack.get("education", [])):
        rid = rec.get("education_id") or f"<index {i}>"
        where = f"education[{rid}]"
        for field in edu_schema["required"]:
            if rec.get(field) in (None, "") and field != "external_safe":
                errors.append(f"{where}: missing {field}")
        if rec.get("education_id") in education_ids:
            errors.append(f"{where}: duplicate education_id")
        education_ids.add(rec.get("education_id"))
        for field in set(rec) - set(edu_schema["properties"]):
            errors.append(f"{where}: unknown field {field!r}")
        if rec.get("evidence_status") not in e["status"]:
            errors.append(f"{where}: evidence_status {rec.get('evidence_status')!r} not in {sorted(e['status'])}")
        if not isinstance(rec.get("external_safe"), bool):
            errors.append(f"{where}: external_safe must be present and boolean")
        for field in ("start", "end"):
            value = rec.get(field)
            if value in (None, "present"):
                continue
            if not re.match(r"^\d{4}(-\d{2})?$", str(value)):
                errors.append(f"{where}: {field} {value!r} must be YYYY or YYYY-MM")
        if not rec.get("source_refs"):
            warnings.append(f"{where}: no source_refs; the qualification traces to nothing")
        for ref in rec.get("source_refs", []):
            if ref.get("source_id") not in source_ids:
                errors.append(f"{where}: source_ref points at unknown source_id {ref.get('source_id')!r}")

    atoms = pack.get("evidence_atoms")
    if not atoms:
        errors.append("evidence_atoms is empty or missing")
    seen = set()
    for i, atom in enumerate(atoms or []):
        aid = atom.get("id") or f"<index {i}>"
        where = f"evidence_atoms[{aid}]"
        if not atom.get("id"):
            errors.append(f"{where}: missing id")
        if not atom.get("title"):
            errors.append(f"{where}: missing title")
        if atom.get("id") in seen:
            errors.append(f"{where}: duplicate id")
        seen.add(atom.get("id"))

        status = atom.get("evidence_status")
        if status is None:
            errors.append(f"{where}: missing evidence_status, which fails open past the publication guard")
        elif status not in e["status"]:
            errors.append(f"{where}: evidence_status {status!r} not in {sorted(e['status'])}")
        if not isinstance(atom.get("external_safe"), bool):
            errors.append(f"{where}: external_safe must be present and boolean")

        outcome = atom.get("outcome_type")
        if outcome is not None and outcome not in e["outcome"]:
            errors.append(f"{where}: outcome_type {outcome!r} not in {sorted(e['outcome'])}")

        known = set(schema["$defs"]["evidenceAtom"]["properties"])
        for field in set(atom) - known:
            errors.append(f"{where}: unknown field {field!r}; a typo here is silently ignored by every consumer")

        eid = atom.get("employment_id")
        if eid and eid not in employment_ids:
            errors.append(f"{where}: unknown employment_id {eid!r}")

        for ref in atom.get("source_refs", []):
            rid = ref.get("source_id")
            if rid not in source_ids:
                errors.append(f"{where}: source_ref points at unknown source_id {rid!r}")
        # An atom citing nothing was silent, and that is where evidence created by a
        # persuasive question hides. A conversation is a legitimate source; it just
        # has to be recorded as one, with source_type "person".
        if not atom.get("source_refs"):
            warnings.append(f"{where}: no source_refs; this claim traces to nothing, so the pack "
                            "cannot tell recall from persuasion. Record a person source for the "
                            "conversation that produced it.")
        # A citation says where to look; an excerpt says what was found. Without
        # one, verify_excerpts.py cannot check the source-to-atom hop at all.
        elif not any(r.get("excerpt") for r in atom.get("source_refs", [])):
            warnings.append(f"{where}: no excerpt on any source_ref, so the claim cannot be checked "
                            "against its source (verify_excerpts.py)")

        # Status must be earned by the sources, not asserted.
        if status == "externally_verified":
            independent = {r["source_id"] for r in pack.get("source_records", [])
                           if r.get("independent") is True}
            if not {r.get("source_id") for r in atom.get("source_refs", [])} & independent:
                errors.append(f"{where}: externally_verified requires a source_ref to an independent source record")
        occurred = atom.get("occurred")
        if occurred is not None:
            if not isinstance(occurred, dict) or not occurred.get("start"):
                errors.append(f"{where}: occurred must be an object with a start")
            else:
                for field in ("start", "end"):
                    value = occurred.get(field)
                    if value in (None, "ongoing"):
                        continue
                    if not re.match(r"^\d{4}(-\d{2})?$", str(value)):
                        errors.append(f"{where}: occurred.{field} {value!r} must be YYYY or YYYY-MM")
        elif atom.get("evidence_status") != "declined":
            warnings.append(f"{where}: no occurred date, so it cannot be placed in time")

        capture = atom.get("capture")
        if capture is not None:
            method = capture.get("method")
            allowed = schema["$defs"]["evidenceAtom"]["properties"]["capture"]["properties"]["method"]["enum"]
            if method and method not in allowed:
                errors.append(f"{where}: capture.method {method!r} not in {allowed}")

        # A metric may be a plain string or an object carrying its measurement
        # basis. An unknown key here would be silently ignored by every consumer,
        # which is how a recorded basis quietly stops existing.
        for j, metric in enumerate(atom.get("metrics") or []):
            if isinstance(metric, str):
                continue
            if not isinstance(metric, dict):
                errors.append(f"{where}: metrics[{j}] must be a string or an object")
            elif not metric.get("value"):
                errors.append(f"{where}: metrics[{j}] object form needs a value")
            else:
                for field in set(metric) - {"value", "basis", "measured"}:
                    errors.append(f"{where}: metrics[{j}] unknown field {field!r}")

        if not isinstance(atom.get("star"), dict):
            errors.append(f"{where}: missing star object; flat situation/task/action/result is no longer part of the contract")
        if status == "unresolved" and not atom.get("open_questions"):
            warnings.append(f"{where}: unresolved with no open_questions recorded")
        if strict and not atom.get("corroborators"):
            warnings.append(f"{where}: no corroborator identified; rests on the subject's word alone")
        if outcome is None and status != "unresolved":
            warnings.append(f"{where}: no outcome_type set")

    # Said once, at the altitude where it is true. Generation ranks business
    # outcomes first and evaluate-output checks for them, so a pack with none
    # leaves both inert and makes every artefact warn forever.
    if atoms and not any(a.get("outcome_type") == "business_outcome" for a in atoms):
        warnings.append(
            f"no atom is typed business_outcome ({len(atoms)} atoms); selection ranking and "
            "artefact evaluation both key on it, so every document from this pack will "
            "describe work rather than consequence")

    profile = pack.get("private_profile")
    if profile is None:
        errors.append("private_profile is missing; make-resume cannot produce a contact block, so any resume from this pack is unsendable")
    elif not profile.get("name"):
        errors.append("private_profile.name is missing")
    elif not (profile.get("email") or profile.get("phone")):
        warnings.append("private_profile has no email or phone; a named-recipient resume cannot be actioned")

    return errors, warnings


def main(argv):
    schema = json.loads(SCHEMA.read_text())
    # Corroboration is an optional signal, not a requirement. --strict opts back in.
    strict = "--strict" in argv
    explicit = [Path(a) for a in argv[1:] if not a.startswith("-")]
    targets = explicit or sorted(ROOT.glob("data/packs/*.json")) + sorted(ROOT.glob("examples/*.json"))
    if not targets:
        print("no packs found")
        return 0

    # A pack that a newer pack supersedes is retained history, not a live contract.
    superseded = set()
    if not explicit:
        for path in targets:
            try:
                meta = json.loads(path.read_text()).get("metadata") or {}
            except json.JSONDecodeError:
                continue
            if meta.get("supersedes"):
                superseded.add((ROOT / meta["supersedes"]).resolve())

    failed = False
    for path in targets:
        if path.resolve() in superseded:
            print(f"skip  {path.name} (superseded)")
            continue
        errors, warnings = check(path, schema, strict=strict)
        status = "FAIL" if errors else "ok"
        try:
            shown = path.resolve().relative_to(ROOT)
        except ValueError:
            shown = path
        print(f"{status}  {shown}")
        for err in errors:
            print(f"      error: {err}")
        for warn in warnings:
            print(f"      warn:  {warn}")
        failed |= bool(errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
