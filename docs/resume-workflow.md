# Resume workflow: operator reference (beta)

People use [Create a resume](resume-start.md). The assistant follows the
[resume setup contract](operators/resume-start.md) when direction or preferences
need clarification. Its saved brief feeds selection and planning below.

Install Career Evidence Core first. Both components use the same workspace and
versioned career schema; no import or conversion is needed when adding the app.
The factual record, supported interpretations and preferences belong to the core.

For a document, use `make-resume` (or `make-interview-brief` for private preparation).
See [Editorial memory](editorial-memory.md) for briefs, ranked selections, scoped
feedback and exact provenance. Generation uses the selected safe evidence view;
private interview preparation deliberately reads the full private pack.

The application owns `data/roles`, `data/briefs`, `data/selections`, `data/plans`, and
`reviews/decisions`. Its generated Markdown, exports and review sidecars belong
under `outputs`. Deleting outputs must not erase selection choices or feedback.
Application records reference stable core IDs and exact pack hashes. Schema 1.3
and 1.4 packs remain supported. Legacy `editorial.py status`, `migrate` and
`bind-strength` commands forward to `career_core.py`.

A wording change is an output edit. A changed inclusion preference is a scoped
editorial decision. A new achievement, ownership correction or measurement is
core evidence work: record the source answer, write a new pack version and
reassess affected interpretations. An application cannot upgrade an evidence
status or silently turn its own prose into a source.

Before delivering, run representation and integrity review, then a cold recruiter
screen. Review exact final bytes; regenerate manifests after edits. Every resume requires PDF, TXT and DOCX exports. Check final PDF
layout and verify recovered text across all three formats. Report shortcomings independently: a faithful
resume may still be weak, and a well-written one may target an unsupported role.

The add-on includes `Makefile.resume` for its deterministic checks. The developer
checkout has `make check-resume` and `make test-releases` as well. Model scenarios
are separate, consume tokens and require the locally configured Claude CLI.

See [Resume authoring](resume-authoring.md) for the full planning and review flow
and [Exports](resume-exports.md) for prerequisites and failure handling.

## JSON Resume projection

The private career pack can be projected into the separate JSON Resume
presentation format:

```sh
python3 scripts/export_resume_json.py --audience public -o outputs/resume.json
```

This lossy export omits ineligible material, retains separate position rows for
promotions, converts recorded dates and records its canonical source. It does
not replace evidence, sources or review history in the career pack. Third-party
themes need their own layout checks. Use Core's private JSON export for a lossless
copy of the accepted pack.
