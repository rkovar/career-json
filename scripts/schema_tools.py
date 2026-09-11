"""Dependency-free schema primitives shared by career records and applications."""
import json
import re
from current_pack import ROOT

def load(name):
    return json.loads((ROOT / "schemas" / name).read_text())

def type_ok(value, spec):
    types = spec.get("type")
    if types is None:
        return True
    if isinstance(types, str):
        types = [types]
    checks = {"string": str, "boolean": bool, "object": dict, "array": list,
              "integer": int, "number": (int, float), "null": type(None)}
    return any(isinstance(value, checks[t]) and not (t in ("integer", "number") and isinstance(value, bool))
               for t in types if t in checks)


def walk(node, spec, schema, where, errors, loader=None):
    loader = loader or load
    if "anyOf" in spec:
        alternatives = []
        for candidate in spec["anyOf"]:
            candidate_errors = []
            walk(node, candidate, schema, where, candidate_errors, loader)
            alternatives.append(candidate_errors)
        if all(alternatives):
            errors.append(f"{where}: does not match any allowed shape")
        return
    if "$ref" in spec:
        ref = spec["$ref"]
        if ref.startswith("#/$defs/"):
            spec = schema["$defs"][ref.split("/")[-1]]
        else:
            file_part, _, frag = ref.partition("#")
            other = loader(file_part)
            spec = other
            for part in frag.strip("/").split("/"):
                if part:
                    spec = spec[part]
            schema = other

    if not type_ok(node, spec):
        errors.append(f"{where}: expected {spec.get('type')}, got {type(node).__name__}")
        return
    if "const" in spec and node != spec["const"]:
        errors.append(f"{where}: expected {spec['const']!r}")

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
                walk(value, props[field], schema, f"{where}.{field}" if where else field, errors, loader)
            elif isinstance(spec.get("additionalProperties"), dict):
                walk(value, spec["additionalProperties"], schema, f"{where}.{field}", errors, loader)
    elif isinstance(node, list):
        if spec.get("uniqueItems") and len({json.dumps(v, sort_keys=True) for v in node}) != len(node):
            errors.append(f"{where}: duplicate items")
        item_spec = spec.get("items")
        if spec.get("minItems") and len(node) < spec["minItems"]:
            errors.append(f"{where}: needs at least {spec['minItems']} item(s)")
        if spec.get("maxItems") and len(node) > spec["maxItems"]:
            errors.append(f"{where}: at most {spec['maxItems']} item(s)")
        if item_spec:
            for i, item in enumerate(node):
                walk(item, item_spec, schema, f"{where}[{i}]", errors, loader)
    else:
        if "enum" in spec and node not in spec["enum"]:
            errors.append(f"{where}: {node!r} not in {spec['enum']}")
        if "pattern" in spec and isinstance(node, str) and not re.search(spec["pattern"], node):
            errors.append(f"{where}: {node!r} does not match {spec['pattern']}")
        if spec.get("minLength") and isinstance(node, str) and len(node) < spec["minLength"]:
            errors.append(f"{where}: must not be empty")
