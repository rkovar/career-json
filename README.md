<picture>
  <source media="(prefers-color-scheme: dark)" srcset="graphics/career-json-reversed.svg">
  <img src="graphics/career-json-primary.svg" alt="career.json logo" width="180">
</picture>

# career.json

**Your career, structured. The right facet, selected.**

career.json is an open-source career evidence system for experienced
professionals, especially those pursuing senior, specialist, technical or
leadership roles.

Keep the roles, achievements and context that a single resume leaves out. Build
a reusable **career pack**, keep achievements connected to their original sources,
and select relevant evidence for resumes, interviews and performance reviews.

Start with an old resume or describe your work. Claude Code proposes a record;
you review the wording and decide what can be used externally. Add quick notes
and new documents as your career develops.

Accepted changes are saved in versioned JSON with a private reading page. The
pack holds employment history, achievements, qualifications, publications and
source references, with optional strengths and preferences. You can build it
before choosing a target job.

[Start here](#start-here) · [See an example](#see-an-example) · [All guides](docs/README.md)

## Start here

You need **Claude Code installed and configured**, Git, Python 3.9+, `make`, and
macOS or Linux. The Python tools use the standard library.

Run this in your terminal:

```sh
git clone https://github.com/rkovar/career-json.git
cd career-json
make start
```

Choose **Build my career pack**. One old resume is enough.

`make start` launches Claude Code for your menu choice. Answer in the conversation;
the assistant runs the tools. If the launcher prints a prompt instead, paste it
into Claude Code in this directory.

| Menu choice | Use it to… |
| --- | --- |
| **Build my career pack** | Turn existing material or your own account into a reviewed record. |
| **Update my career pack** | Capture a note or review new material once a pack exists. |
| **View my saved career record** | Read the current saved pack once one exists. |
| **Continue saved work** | Resume an unfinished setup or career review when saved work is available. |
| **Create a resume** | Choose a job or direction and prepare a resume from your career pack. |

Already in Claude Code? Say **“Walk me through the career-pack wizard”** or
**“Walk me through the resume wizard.”** These enter the same workflows.

PDF input needs Poppler, or Swift/PDFKit when using macOS. Text, Markdown and DOCX
need neither. See [source setup](docs/extraction.md#what-it-uses). Model-assisted work
consumes tokens; cost and time depend on your material and configured service.

## Build your first pack

1. **Bring what you have.** Put resumes, LinkedIn PDFs, reviews, project notes or
   publication material in `data/sources/`. Name the files to use, or say
   **“Use everything in Sources”** for the whole folder.
2. **Read the proposal.** Check your contribution, dates, shared ownership and
   anything missing. Supporting excerpts and caveats are available when needed.
3. **Confirm or correct.** Give decisions in conversation or use the browser
   review, which shows five items at a time. Corrected wording is shown again
   before acceptance. You can defer uncertain items.
4. **Save something useful.** Save a role and a few achievements, then ask:
   **“Show me one recorded achievement and its original source.”** Accepted
   changes become a new pack version; pending proposals stay separate.

In the connected review, **Save and next five** saves and advances. Standalone
HTML reviews require downloading decisions and asking the assistant to apply them;
downloading alone does not update the pack. [Review details](docs/pack-review.md)

Intake identifies unchanged files, duplicates and extraction problems. The review
tracks remaining source work across batches. A source linked to a career record
does not prove that every important detail in it was captured.

Your own account is valid evidence. Strengths interviews, contact details and
independent corroboration can wait. Accepting wording, assessing its evidence and
allowing external use are separate decisions. New or changed content stays private
unless you allow external use.

## Keep it current

Capture useful details while they are fresh. Choose **Update my career pack**,
or ask in Claude Code:

| When | What to say |
| --- | --- |
| A useful detail is fresh | “Remember that I helped the operations team rehearse the migration.” |
| You have new material | “I've added my annual review to Sources. Help me update my career pack.” |
| You're ready to review notes | “Review my recent notes with me and update my career pack.” |
| You need an example | “Find an achievement that shows how I mentored other engineers.” |

Quick capture saves your supplied note without an interview. Notes enter the
accepted pack after review. Updates compare new material with your existing
record; earlier pack versions and review history remain available.

```text
New work -> Quick note or document -> Your review -> Updated career pack
                                                          |
                                                   Recall or reuse
```

Say **“pause”** and return through **Continue saved work**. Saved answers and
deferrals are reused; changed evidence can need a fresh review. **View my saved
career record** refreshes the reading page. [Keeping your pack current](docs/keep-current.md)

## See an example

[Jules Elm's fictional walkthrough](examples/first-pack/README.md) follows sixteen
years across four roles, through ownership corrections, partial acceptance and a
later update. Its sources and decisions are scripted examples.

Open [examples/first-pack/index.html](examples/first-pack/index.html) locally after
cloning or downloading the repository. It needs no Claude session or server.
GitHub displays HTML as source; use your local browser to try the review controls.

## Create a resume when you need one

Choose **Create a resume**. Bring a job description, describe a role, or explore
directions. If you need a career pack first, the wizard saves your target while
you build one.

Review ranked achievements and inclusion reasons, or request automatic drafting
and review. The workflow uses eligible career evidence and prepares **PDF, TXT
and DOCX** from shared content. Each application can draw a different selection from
the same career record. New facts return through career-pack review.

PDF export also needs Chrome/Chromium and a supported PDF extractor. Failed checks
or missing formats leave the bundle incomplete; final layout needs inspection.
See [resume creation](docs/resume-start.md) and
[export setup and checks](docs/resume-exports.md).

## Your files and privacy

Career sources, packs and review history are local files. Material you ask Claude
to read is processed by your configured model service.

The default `.gitignore` excludes personal work in the designated data folders,
`reviews/`, `outputs/` and `backups/` from ordinary commits. Files elsewhere do
not inherit that protection. Reading pages include withheld information too.

Local saves are separate from GitHub backup. If you also develop this tool,
[create a separate personal workspace](docs/workspace-maintenance.md#create-a-separate-personal-workspace).
The installer creates neither a GitHub repository nor automatic syncing.
[Backup and restore](docs/workspace-maintenance.md#portable-private-backup-and-restore)
preserves sources, pending reviews and saved packs; archives are not encrypted.

## Project status and help

**Career Evidence Core `0.1.0-alpha.6` is early access; Resume Application
`0.1.0-beta.7` is beta.** This checkout includes both. Core also works as a separate installation; see
[component versions and releases](docs/releases.md).

Automated checks help catch structural, source and export problems. Human review
remains necessary: the checks establish neither complete extraction nor likely
hiring outcomes.

- [Your first session](docs/getting-started.md)
- [All guides and technical references](docs/README.md)
- [Development and validation](docs/development.md)
- [MIT license](LICENSE)
