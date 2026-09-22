# Keep your career pack current

A useful career pack grows alongside your work. Save details while you remember
them, then review and organize them when convenient.

Open Claude Code in your career workspace for the requests below. Once a pack exists, `make start` offers **Update my career pack** first. To return to an unfinished
setup or review, run `make start` and choose **Continue saved work**.

## Capture a detail now

> Remember that I helped the operations team rehearse the migration.

A quick capture saves a note. You do not need a polished achievement, a metric,
or an interview before saving it. Include whatever will help you remember later:
what happened, your contribution, who else was involved and when it happened.

Capture notes wait for review before becoming part of the accepted career pack.

[See Jules capture and review a migration-planning note](../examples/first-pack/README.md#see-the-ongoing-habit).
The example preserves the earlier pack, adds context, and saves only the reviewed
contribution; it leaves the unfinished migration's outcome open.

## Review notes when convenient

> Review my recent notes with me and update my career pack.

The assistant helps connect notes to existing work and proposes additions or
corrections. Check that it preserves your contribution and other people's
ownership. Explain missing context in your own words.

Use **Save reviewed changes** in the connected review to save useful items and leave the rest for later. The saved reading page updates at `outputs/career-record.html`. Exact corrections are shown again before acceptance, and unchanged approvals remain valid. A changed statement needs a
fresh review; an old approval does not cover new wording.

[Inspect Jules's proposed update](../examples/first-pack/update-review.html) and
[the saved result](../examples/first-pack/after-update.html) in your browser.

## Bring in a new document

> I've added my annual review to Sources. Help me update my career pack.

Put the file in `data/sources/`. New resumes, promotion write-ups, conference
listings, publications and project notes can all add detail. Tell the assistant
which material to use; you can ask it to inspect everything in Sources.

The intake report identifies unchanged files, exact duplicates and extraction problems. The assistant compares new material with your existing record, preserves record IDs, and proposes only meaningful additions and changes. An unchanged re-import needs no new approval. Earlier versions and sources remain available. Source
documents may contain private employer information; only bring material you can
share with your configured model service.

## Correct, clarify or connect work

| What you need | What to say |
| --- | --- |
| Correct ownership | “This makes the project sound like mine alone. I designed the approach; the team delivered it.” |
| Combine repeated accounts | “These two achievements describe the same project. Help me combine them.” |
| Add support | “This publication gives more detail about that work. Help me attach it.” |
| Revisit a strength | “Does my newer work change how we describe this strength?” |

The assistant shows proposed changes for review. Corrections preserve history;
they do not silently replace earlier sources or turn a suggested strength into
an independently verified fact. When a correction changes a strength’s supporting
evidence, the assistant revisits its wording and limitations using the answers
already recorded. You review any proposed change.

## Use what you have

> Find an achievement that shows how I mentored other engineers.

> Show me my current career record in a readable page.

> Help me prepare examples for my performance review.

A good result explains the recorded contribution and its source. You can use
the record without generating a resume or completing every outstanding question.

## Pause or recover interrupted work

> Continue my saved career review, using the answers I already gave.

Answered questions stay answered. Deferred work can wait; deliberately withheld
details are not treated as gaps to investigate. Completed reviews move to history.
If a session ends before the assistant hands over a page, ask “Recover my saved
career review.” A saved proposal can be reopened without being approved.

Choose **View my saved career record** in `make start` to regenerate its readable
page. If rendering failed after a save, your accepted facts remain saved.

## Keep a copy

> Back up my career workspace, including sources and pending reviews.

The assistant can create a private backup and explain how to restore it into a
new directory. It includes the sources and review history needed to continue
your work. Backups are not encrypted; keep them somewhere appropriate for your
personal and employer information.

You can also ask for a lossless JSON export of the accepted career pack.
See [workspace maintenance](workspace-maintenance.md) for backup, restore,
history and advanced maintenance details.

## Export the complete record as Markdown

Viewing or refreshing your saved career record also writes `outputs/career.md`.
This is a complete private snapshot of the selected saved JSON pack, including
contact details, restricted work, notes, evidence and recorded review/use states.
It retains source references without embedding the source files. Pending capture
notes and separate review proposals remain outside the saved-pack snapshot.

JSON stays authoritative: editing Markdown does not update your pack. Regeneration
replaces the generated snapshot. Keep a separate copy if you want to edit it.

```sh
make career-markdown
python3 scripts/career_core.py export-markdown --pack data/packs/example.json --output outputs/example.md
```

The export needs only Python, includes its source hash, and does not contact a
model or external service. Treat it as your personal record; it includes material
that has not been permitted for external use. A resume bundle’s `files/resume.md`
is a separate, clean document containing only the selected resume content.

For a complete file map and the difference between `career.md`, the cited draft
and clean `resume.md`, see [your files and exports](files-and-exports.md).
