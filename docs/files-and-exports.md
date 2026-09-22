# Your files and exports

Your **career pack** is the saved JSON record of your career. Reading pages,
Markdown snapshots and resumes are generated from it. They serve different
purposes and do not all contain the same information.

## Know which file you are using

Paths below are relative to your career workspace. A pack's filename and a
resume's export directory depend on the saved version.

| File | What it contains | Intended use |
| --- | --- | --- |
| `data/packs/*.json` | Saved versions of your career record, including evidence IDs, sources and use restrictions | Authoritative record; make changes through career review |
| `outputs/career-record.html` | A reading view of the saved record, including restricted work; omits the profile contact block | Browse your career privately |
| `outputs/career.md` | The complete selected saved pack, including contact details, private notes, recorded states and supporting evidence | Read or reuse your full record in a Markdown editor; private by default |
| `outputs/<application>-draft.md` | A selected resume draft with internal evidence citations | Authoring and review; use the clean export for sharing |
| `outputs/<export>/files/resume.md` | Clean resume wording, headings, emphasis, bullets and links, without internal citations | Edit or reuse the selected resume; share only when appropriate to the recipient |
| `outputs/<export>/files/resume.pdf`, `resume.txt`, `resume.docx` | The same selected resume content in submission formats | Send the format the employer requests |
| `outputs/<export>/review/` | Export report, internal document data and HTML preview | Private diagnostics and review |

Resume rows apply when the Resume Application is installed. The combined checkout
and downloadable starter include it; a Core-only archive does not.

**`career.md` and `resume.md` are different documents.** The first contains your
full saved record, including information you have not permitted for external use.
The second contains the selected resume content. Do not send your full career
snapshot in place of a resume.

## Generate your full Markdown record

Ask Claude to “Show my saved career record and give me the Markdown copy.” Viewing
the saved career record refreshes both `career-record.html` and `career.md`.
The HTML page's contact omission does not apply to the complete Markdown file.

From the workspace directory, you can also run:

```sh
python3 scripts/career_core.py view
python3 scripts/career_core.py export-markdown
```

The first command refreshes both views and prints their paths. Open the HTML path
in a browser or the Markdown path in your editor. The second refreshes only
`outputs/career.md`. `make career-markdown` is an equivalent shortcut for the second.
These commands require a saved pack and make no model calls.

To export a particular version without replacing the default snapshot:

```sh
python3 scripts/career_core.py export-markdown --pack data/packs/example.json --output outputs/example.md
```

Replace the example pack path with a real saved version. The destination must be
under `outputs/` and end in `.md`. A valid export replaces an existing file at
that destination; invalid input leaves the previous file intact.

The snapshot includes its source path, schema version and source hash. It covers
the selected saved pack, including unresolved or restricted entries that are
already in that pack. It does not include separate pending capture notes, review
proposals, earlier pack versions or the source-document files themselves.

## Edit the record, then regenerate

JSON remains authoritative. Editing `career.md` or its HTML view does not update
the pack. Ask Claude to correct the recorded information, review the proposed
change, save it, then regenerate the views. Keep a separate copy of Markdown
before making personal edits you want to retain.

Editing a clean resume export also does not update the pack or the cited draft.
It invalidates that export's recorded hash. For a verified delivery, apply the
wording change through the resume workflow and export into a new directory.

## Exports and backups

A full JSON copy is available separately:

```sh
python3 scripts/career_core.py export --output data/private/career-export.json
```

This command requires a new output filename. Neither a JSON copy nor `career.md`
is a complete workspace backup: source files, pending work and history live
elsewhere in the workspace. Use [backup and restore](workspace-maintenance.md#portable-private-backup-and-restore)
to preserve them together.

Generated files stay local unless you share or sync them. Material an assistant
reads is processed by its configured model service. A record's private status
controls inclusion in generated documents; it is not encryption and does not
prevent the assistant from reading the record.
