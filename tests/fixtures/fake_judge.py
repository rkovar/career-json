#!/usr/bin/env python3
"""Stands in for `claude -p` in the suite. Reads the prompt (last argument) and
returns a verdict by a fixed rule, so entailment.py's plumbing is tested without
a model: a bullet containing 'halved' against evidence saying 'a third' is
overstated; a bullet mentioning 'revenue' with no revenue in the evidence is
unsupported; anything else is supported."""
import json, sys
text = sys.argv[-1]
evidence, _, bullet = text.partition("BULLET")
b, e = bullet.lower(), evidence.lower()
if "halved" in b and "third" in e:
    out = {"verdict": "overstated", "reason": "evidence says roughly a third", "overreach": "halved"}
elif "revenue" in b and "revenue" not in e:
    out = {"verdict": "unsupported", "reason": "no revenue claim in evidence", "overreach": "revenue"}
else:
    out = {"verdict": "supported", "reason": "entailed", "overreach": None}
print(json.dumps({"structured_output": out}))
