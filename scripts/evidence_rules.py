"""Shared evidence eligibility and reference primitives; no generation dependency."""
import re
from current_pack import metric_text

def links(req):
    """A requirement's links as records. A bare id is an unconfirmed link: the
    profile was edited by whoever wrote it, and a model editing the list it is
    scored on is the loop role_fit must not close. Only a link the subject
    confirmed ("linked_by": "subject") counts towards a verdict."""
    out = []
    for item in req.get("evidenced_by") or []:
        if isinstance(item, str):
            out.append({"id": item, "linked_by": "proposed", "on": None})
        else:
            out.append({"id": item.get("id"), "linked_by": item.get("linked_by", "proposed"),
                        "on": item.get("on"), "note": item.get("note")})
    return out


def linked_ids(req, confirmed_only=False):
    return [l["id"] for l in links(req) if not confirmed_only or l["linked_by"] == "subject"]


def eligible(atom):
    if not atom.get("external_safe"):
        return False, "external_safe is false"
    if atom.get("evidence_status") in ("unresolved", "declined"):
        return False, f"evidence_status is {atom['evidence_status']}"
    return True, None


def canonical(pack):
    out = {}
    for canon, aliases in (pack.get("skill_vocabulary") or {}).items():
        out[canon.lower()] = canon
        for alias in aliases:
            out[alias.lower()] = canon
    return out


def contains_term(text, term):
    """Whole-word containment. Substring matching let a short keyword ("AI",
    "LLM") score an atom for a word that merely contained those letters."""
    return re.search(r"(?<![a-z0-9])" + re.escape(term.lower()) + r"(?![a-z0-9])", text.lower()) is not None


def atom_prose(atom):
    """The text an atom asserts, for keyword matching. json.dumps(atom) matched
    field names and ids as well as prose."""
    star = atom.get("star") or {}
    return " ".join([atom.get("title", "")] + [star.get(k) or "" for k in star]
                    + [metric_text(m) for m in atom.get("metrics", [])] + list(atom.get("skills", [])))
