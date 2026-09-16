# Your first session

Start with a role and a few achievements you can read, correct and find again.
You can add the rest of your career over time.

## 1. Open the tool

You need Claude Code installed and configured, Git, Python 3.9+, `make`, and
macOS or Linux. Source files and review pages live in your workspace. Material
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
**Continue saved work** appears when there are saved setups or career reviews.

Choose **Build my career pack** for the first exercise below. If you need a
resume now, choose **Create a resume**: your target is saved while the assistant
helps you build a pack.

**Already in Claude Code?** Ask “Walk me through the career-pack wizard” or
“Walk me through the resume wizard.” These are alternatives to opening the launcher.

For PDF sources, macOS can use Swift/PDFKit; Linux needs Poppler. See
[PDF source setup](extraction.md#what-it-uses) if extraction tools are missing.
You can also start with text, a Word document, or your own account.

## 2. Bring what you have

The wizard asks whether you want to use documents, gather material, or describe
your work. One old resume is enough. Several sources are welcome if you already
have them ready; you do not need to collect your whole archive.

Put documents in `data/sources/` and tell the assistant which to use. It can help
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

Or use the browser review, which shows five items at a time. **Save and next five**
keeps your place in the browser. To apply those choices to your pack, use
**Download review decisions**, then tell the assistant where that file is:

> Apply my saved review decisions and show me what remains. The file is at
> [the location of my downloaded file].

The assistant saves accepted items and preserves corrections and unfinished work.
It may show related role or source information that needs your review too.
Confirming accurate wording and allowing external use are separate choices;
new information stays private unless you allow it externally.

You can stop after a role and a few useful achievements. Unanswered factual
questions remain visible, and claims needing clarification stay out of resumes.
There is no need to finish every question or a strengths interview now.

## 4. Get something back

Ask:

> Show me one recorded achievement and its original source.

Then try a topic from your own work:

> Find an example of how I helped another team solve a problem.

The answer should show the recorded contribution and its source, including any
uncertainty. You now have a record you can reuse and improve.

## 5. Come back when something changes

Say “pause” when you want to stop. Later, use `make start` and choose
**Continue saved work**, or copy the continuation prompt from your setup summary.
The assistant resumes the named work with your earlier answers available.

Between reviews, save a quick note:

> Remember that I helped the operations team rehearse the migration.

Notes are saved for later review, so you can capture a detail without organizing
your whole career at that moment. See [Keep your career pack current](keep-current.md)
for bringing those notes into your reviewed record.

First-run time and token use depend on the material and model; there is no
reliable general estimate yet. Start with a small amount you can review.

For resume creation, exports and technical help, use the [documentation index](README.md).
