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
        if stype == "url":
            if not rec.get("retrieved"):
                errors.append(f"{where}: url sources need a retrieved date to be auditable")
        else:
            if not SHA256.match(rec.get("sha256") or ""):
                errors.append(f"{where}: file sources need a sha256")
            if not isinstance(rec.get("character_count"), int):
                errors.append(f"{where}: file sources need an integer character_count")
        if "independent" not in rec:
            warnings.append(f"{where}: no independent flag; assumed not independent")

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

        # Status must be earned by the sources, not asserted.
        if status == "externally_verified":
            independent = {r["source_id"] for r in pack.get("source_records", []) if r.get("independent")}
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

        if not isinstance(atom.get("star"), dict):
            errors.append(f"{where}: missing star object; flat situation/task/action/result is no longer part of the contract")
        if status == "unresolved" and not atom.get("open_questions"):
            warnings.append(f"{where}: unresolved with no open_questions recorded")
        if strict and not atom.get("corroborators"):
            warnings.append(f"{where}: no corroborator identified; rests on the subject's word alone")
        if outcome is None and status != "unresolved":
            warnings.append(f"{where}: no outcome_type set")

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
