#!/usr/bin/env python3
"""Validate the workspace's own output records.

The pack has been validated since day one; the evaluation and screen records the
system writes about its own work had no contract at all. That asymmetry is how a
decorative provenance block survived review.

Standard library only. Structural rather than a full JSON Schema implementation,
but it reads required fields and enums from the schema so the two stay in step.

    python3 scripts/validate_records.py              # every record in outputs/
    python3 scripts/validate_records.py <file.json>
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CAREER_WORKSPACE", Path(__file__).resolve().parent.parent))
SCHEMAS = ROOT / "schemas"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from current_pack import resolve  # noqa: E402
from select_evidence import links, atom_prose  # noqa: E402
KINDS = {
    "evaluation": (re.compile(r"-evaluation\.json$"), "evaluation-record.schema.json"),
    "screen": (re.compile(r"-screen\.json$"), "screen-record.schema.json"),
    "role": (re.compile(r"^(?!.*-(evaluation|screen)\.json$).*\.json$"), "role-profile.schema.json"),
}


def load(name):
    return json.loads((SCHEMAS / name).read_text())


def type_ok(value, spec):
    types = spec.get("type")
    if types is None:
        return True
    if isinstance(types, str):
        types = [types]
    checks = {"string": str, "boolean": bool, "object": dict, "array": list,
              "integer": int, "number": (int, float), "null": type(None)}
    return any(isinstance(value, checks[t]) for t in types if t in checks)


def walk(node, spec, schema, where, errors):
    if "$ref" in spec:
        ref = spec["$ref"]
        if ref.startswith("#/$defs/"):
            spec = schema["$defs"][ref.split("/")[-1]]
        else:
            file_part, _, frag = ref.partition("#")
            other = load(file_part)
            spec = other
            for part in frag.strip("/").split("/"):
                if part:
                    spec = spec[part]
            schema = other

    if not type_ok(node, spec):
        errors.append(f"{where}: expected {spec.get('type')}, got {type(node).__name__}")
        return

    if isinstance(node, dict):
        for field in spec.get("required", []):
            if field not in node:
                errors.append(f"{where}: missing required field {field!r}")
        props = spec.get("properties", {})
        if spec.get("additionalProperties") is False:
            for field in set(node) - set(props):
                errors.append(f"{where}: unknown field {field!r}")
        for field, value in node.items():
            if field in props:
                walk(value, props[field], schema, f"{where}.{field}" if where else field, errors)
    elif isinstance(node, list):
        item_spec = spec.get("items")
        if spec.get("minItems") and len(node) < spec["minItems"]:
            errors.append(f"{where}: needs at least {spec['minItems']} item(s)")
        if spec.get("maxItems") and len(node) > spec["maxItems"]:
            errors.append(f"{where}: at most {spec['maxItems']} item(s)")
        if item_spec:
            for i, item in enumerate(node):
                walk(item, item_spec, schema, f"{where}[{i}]", errors)
    else:
        if "enum" in spec and node not in spec["enum"]:
            errors.append(f"{where}: {node!r} not in {spec['enum']}")
        if "pattern" in spec and isinstance(node, str) and not re.search(spec["pattern"], node):
            errors.append(f"{where}: {node!r} does not match {spec['pattern']}")
        if spec.get("minLength") and isinstance(node, str) and len(node) < spec["minLength"]:
            errors.append(f"{where}: must not be empty")


def kind_of(path):
    if path.parent.name == "roles":
        return "role", "role-profile.schema.json"
    for kind, (pattern, schema_name) in KINDS.items():
        if kind == "role":
            continue
        if pattern.search(path.name):
            return kind, schema_name
    return None, None


def check(path):
    """Returns (kind, errors, warnings). Warnings are printed and never fail."""
    kind, schema_name = kind_of(path)
    if kind is None:
        return None, [f"{path.name}: not a recognised record type"], []
    try:
        record = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return kind, [f"invalid JSON: {exc}"], []
    schema = load(schema_name)
    errors, warnings = [], []
    walk(record, schema, schema, "", errors)

    # Cross-record consistency the schema cannot express.
    if kind == "evaluation":
        blockers = [f for f in record.get("findings", []) if f.get("severity") == "blocker"]
        if blockers and record.get("publishable"):
            errors.append("publishable is true while blocker findings are recorded")
        for artefact in record.get("artifacts", []):
            if not (ROOT / artefact).exists():
                errors.append(f"artifact {artefact} does not exist")
    if kind == "role":
        essential = [r for r in record.get("requirements", []) if r.get("weight") == "essential"]
        if not essential:
            errors.append("no essential requirement: a profile that weights nothing cannot rank evidence")
        # role_fit scores whatever evidenced_by names. A typo here silently turned
        # an evidenced essential into "not supported", and no validator read the
        # list. Checked against the current pack for profiles that live in this
        # workspace's data/roles; a walkthrough or example profile belongs to
        # another pack and is not held to this one.
        pack_path = resolve()
        in_workspace = (ROOT / "data" / "roles").resolve() in path.resolve().parents
        proposed = sum(1 for req in record.get("requirements", [])
                       for l in links(req) if l["linked_by"] != "subject")
        if proposed:
            warnings.append(f"{proposed} link(s) are proposed, not confirmed by the subject; role_fit "
                            "counts none of them. Confirm or reject each with scripts/link_evidence.py")
        if pack_path is not None and in_workspace:
            atoms = {a["id"]: a for a in json.loads(pack_path.read_text()).get("evidence_atoms", [])}
            for req in record.get("requirements", []):
                words = set(re.findall(r"[a-z]{4,}", (req.get("text", "") + " "
                                                      + " ".join(record.get("ats_keywords", []))).lower()))
                for link in links(req):
                    aid = link["id"]
                    if aid not in atoms:
                        errors.append(f"requirement {req.get('text', '')[:50]!r} cites {aid}, "
                                      f"which is not in {pack_path.name}")
                    elif link["linked_by"] == "subject":
                        # Weak, deliberately: a confirmed link whose atom shares
                        # no word with the requirement or the role's keywords is
                        # worth a second look, not a rejection.
                        prose = set(re.findall(r"[a-z]{4,}", atom_prose(atoms[aid]).lower()))
                        if words and not words & prose:
                            warnings.append(f"confirmed link {aid} shares no word with requirement "
                                            f"{req.get('text', '')[:40]!r}; check it evidences it")
    if kind == "screen":
        artefact = record.get("artifact")
        if artefact and not (ROOT / artefact).exists():
            errors.append(f"artifact {artefact} does not exist")
        if record.get("verdict") == "reject" and not record.get("reason"):
            errors.append("reject verdict with no reason")
        # A screen produced in the context that wrote the document is the model
        # grading its own work. Recorded so a verdict says where it came from;
        # a warning, not an error, so screens written before the field existed
        # still validate and are visibly the weaker kind.
        if record.get("context") != "fresh":
            warnings.append("screen context is not 'fresh': the verdict was produced in the context "
                            "that generated the document, or does not say. Re-screen in a fresh context.")
    return kind, errors, warnings


def main(argv):
    if argv[1:]:
        targets = [Path(a) for a in argv[1:]]
    else:
        # Discovery only takes files this validator recognises. It used to take
        # every JSON file in outputs/, so the documented `make resume-json` left
        # a resume.json there that then failed `make records` as an unknown
        # record type. An explicit path is still checked whatever it is called.
        found = sorted(ROOT.glob("outputs/*.json")) + sorted(ROOT.glob("data/roles/*.json"))
        targets = [p for p in found if kind_of(p)[0] is not None]
    if not targets:
        print("no records found")
        return 0
    failed = False
    for path in targets:
        kind, errors, warnings = check(path)
        print(f"{'FAIL' if errors else 'ok'}  {path.name}" + (f"  ({kind} record)" if kind else ""))
        for err in errors:
            print(f"      error: {err}")
        for warn in warnings:
            print(f"      warn:  {warn}")
        failed |= bool(errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
