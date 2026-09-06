# Examples

This directory is committed. Nothing here may contain real personal or employer
material.

[career.example.json](career.example.json) is an entirely
fictional pack showing the shape of every field and one atom in each
`evidence_status`. Alex Rivera does not exist. Use it as a format reference, never
as evidence.

[career.complex.example.json](career.complex.example.json) is the same idea at the
shape of a real pack: a three-deep promotion chain under one employer, withheld and
unresolved evidence, undated atoms, an `employer_of_record` that differs, metrics
carrying their measurement basis, and an `externally_verified` atom that earns it
from an independent source. It exists because a five-atom fixture with none of
those shapes let three defects through a passing suite. Morgan Vale does not exist
either.

[walkthrough/](walkthrough/) is one complete run over that pack: the role
profile, the draft it produced, the evaluation record, and the recruiter screen.

[fun/](fun/) holds three parody packs (Jean-Luc Picard, Steve Jobs, Bill
Clinton) that exercise the fields recording what works against you. Public record
only, fake contact details, and never for citation.

Your own material lives in the ignored working directories:

- `data/sources/`: raw source material.
- `data/packs/`: versioned career datapacks.
- `data/private/`: profiles and other private working files.
- `reviews/`, `outputs/`: review records and generated artefacts.

The canonical data contract is [../schemas/career.schema.json](../schemas/career.schema.json).
Anything added here must be fictional and must pass `python3 scripts/validate_pack.py`.
