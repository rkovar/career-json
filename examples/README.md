# Examples

This directory is committed. Nothing here may contain real personal or employer
material.

[career.example.json](career.example.json) is an entirely
fictional pack showing the shape of every field and one atom in each
`evidence_status`. Alex Rivera does not exist. Use it as a format reference, never
as evidence.

[walkthrough/](walkthrough/) is one complete run over that pack: the role
profile, the draft it produced, the evaluation record, and the recruiter screen.

Your own material lives in the ignored working directories:

- `data/sources/`: raw source material.
- `data/packs/`: versioned career datapacks.
- `data/private/`: profiles and other private working files.
- `reviews/`, `outputs/`: review records and generated artefacts.

The canonical data contract is [../schemas/career.schema.json](../schemas/career.schema.json).
Anything added here must be fictional and must pass `python3 scripts/validate_pack.py`.
