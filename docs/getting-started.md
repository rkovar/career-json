# Your first session

Prefer a plain-language introduction with a downloadable starter?
[Start here if you're not technical](nontechnical-start.md).

Start with a role and a few achievements you can read, correct and find again.
You can add the rest of your career over time.

Want to see the result first? [Explore Jules's fictional career](../examples/first-pack/README.md),
including multiple roles, review corrections and a later update. You can start
with much less material.

## 1. Open the tool

This section is the **terminal route**: you need the Claude Code CLI installed
and signed in, Git, Python 3.9+, `make`, and macOS or Linux. Follow
[Anthropic's CLI quickstart](https://code.claude.com/docs/en/quickstart) for installation
and authentication. A working `claude --version` checks that the CLI is on PATH.

For the downloadable **Desktop route**, follow the
[Mac starter guide](nontechnical-start.md) instead. It uses Code → Local with a
selected folder and does not require Git, `make` or a separate CLI installation.

Source files and review pages live in your workspace. Material
you ask Claude to read is processed by your configured model service.

For a new checkout, run this in your terminal:

```sh
git clone https://github.com/rkovar/career-json.git
cd career-json
make start
```

If you already cloned or unzipped the project, skip cloning and run from its directory
`make start`. It opens a menu and launches Claude Code for your choice. The full
checkout includes both **Build my career pack** and **Create a resume**.
A Core-only archive offers career-pack tools until you install the resume add-on.
**Continue saved work** appears for active setups or career reviews. Completed
work stays in history. Once you save a pack, **View my saved career record** refreshes and links to the readable current record and its complete Markdown snapshot.

Choose **Build my career pack** for the first exercise below. If you need a
resume now, choose **Create a resume**: your target is saved while the assistant
helps you build a pack.

**Already in Claude Code?** Ask “Walk me through the career-pack wizard” or
“Walk me through the resume wizard.” These are alternatives to opening the launcher.

For PDF sources, macOS can use an installed, working Swift/PDFKit toolchain or
Poppler; Linux needs Poppler. See
[PDF source setup](extraction.md#what-it-uses) if extraction tools are missing.
You can also start with text, a Word document, or your own account.

If you also develop the tool, use a [separate personal workspace](workspace-maintenance.md#create-a-separate-personal-workspace). A normal Core archive can already be your personal workspace.

## 2. Bring what you have

The wizard asks whether you want to use documents, gather material, or describe
your work. One old resume is enough. Several sources are welcome if you already
have them ready; you do not need to collect your whole archive.

Put documents in `data/sources/` and tell the assistant which to use. Say “Use everything in Sources” to inspect the whole directory. It inventories duplicate, unchanged and unreadable files before proposing new facts. It can help
identify resumes, project notes, talks and other useful material. Job descriptions
and writing advice guide the work but do not become facts about your career.

Answer in ordinary language. “Later”, “none”, “not applicable” and “skip” are
valid answers. Setup choices are saved in a readable summary. The assistant then
prepares a proposed career record for you to review.

## 3. Review a useful amount

Read the timeline, achievements and original source excerpts. Check who did what,
the dates, and whether anything important is missing or understated.

You can give decisions in conversation:

> The rehearsal example is accurate. Keep it private. The mentoring example
> needs a correction: the engineers developed the approach together.

Or use the connected browser review, which shows five items at a time. Confirm a
role once, then review its achievements with source excerpts available when needed.
Enter your name under **How review and saving work**. **Save reviewed changes**
writes accepted facts to your local pack; **Save and next five** also takes you to
the next batch. The status tells you what was saved and what still needs review.

To fix wording, expand **Correct the recorded wording**, edit the details, and
choose **Show revised wording**. This previews edits across all cards. Saving while
you have edited wording also opens a preview first; choose **Looks accurate** on
the revised items and save again. Earlier approvals carry forward only when they
still apply. New or changed information stays private by default.

The assistant opens a temporary connection to your local workspace for browser
saving. If you use a standalone HTML file instead, download the decisions and tell
the assistant where you saved them. A download alone does not update the pack.
After saving, use **Read saved career pack** to see your current record.

You can stop after a role and a few useful achievements. Unanswered factual
questions remain visible, and claims needing clarification stay out of resumes.
There is no need to finish every question or a strengths interview now. “Not
measured”, “later” and “keep this private” are useful answers. The assistant saves
the question and your exact response, so you do not have to repeat them later.

## 4. Get something back

Ask:

> Show me one recorded achievement and its original source.

Then try a topic from your own work:

> Find an example of how I helped another team solve a problem.

The answer should show the recorded contribution and its source, including any
uncertainty. You now have a record you can reuse and improve.

Viewing your saved record generates `outputs/career-record.html` and
`outputs/career.md`. The Markdown copy includes the complete saved pack, including
private contact details and restrictions; it is not a clean resume. The JSON pack
remains authoritative, and edits to the generated views do not sync back.
See [your files and exports](files-and-exports.md) for the file map and commands.

## 5. Come back when something changes

Say “pause” when you want to stop. Later, use `make start` and choose
**Update my career pack** for new material, **Continue saved work** for a pending review, or copy the continuation prompt from your setup summary.
The assistant resumes the named work with your earlier answers available.
**Continue saved work** shows the latest correction under the original review name.

Between reviews, save a quick note:

> Remember that I helped the operations team rehearse the migration.

Notes are saved for later review, so you can capture a detail without organizing
your whole career at that moment. See [Keep your career pack current](keep-current.md)
for bringing those notes into your reviewed record.

First-run time and token use depend on the material and model; there is no
reliable general estimate yet. Start with a small amount you can review.

For resume creation, exports and technical help, use the [documentation index](README.md).
