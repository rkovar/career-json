# career.json

**Keep your career up to date, one conversation at a time.**

Projects finish and useful details fade. career.json helps you keep a record
while the work is fresh, ready for your next review, interview or job opportunity.

Start with a resume or describe your work. The assistant organizes it into a
**career pack**: a file containing your roles, achievements, sources and strengths.
Review it in a browser, add information over time, and export it when useful.

## See what you keep

In our fictional example, Jules's old resume says:

> I designed a deployment rehearsal format and co-built its runner with engineers.
> Two teams adopted rehearsals before deployment.

The career pack keeps the contribution, shared ownership and original source
together. Months later, Jules can ask:

> Find the deployment rehearsal example and show me its source.

That reviewed example can support a review, interview or resume. [Follow Jules's complete walkthrough](examples/first-pack/README.md)
to see the proposed record, corrections and saved result.

## Start here

You need **Claude Code**, Git, Python 3.9+, `make`, and macOS or Linux. Claude Code
must already be installed and configured. The repository includes both career-pack
and resume workflows.

Run these commands in your terminal:

```sh
git clone https://github.com/rkovar/career-json.git
cd career-json
make start
```

`make start` opens a menu, then launches Claude Code for your chosen path.
Answer in the conversation; the assistant handles the underlying scripts and files.

| Choose | What happens |
| --- | --- |
| **Build my career pack** | Bring existing material or describe your work, then review the proposed record. |
| **Create a resume** | Choose a job or direction and the strengths you want to highlight. |

**Unsure? Start with your career pack. One old resume is enough.** Use several documents if you have them ready.

If Claude Code is already open in this directory, simply say **“Walk me through
the career-pack wizard”** or **“Walk me through the resume wizard.”** These enter
the same workflows as the menu.

PDF sources need a text extractor; PDF resume export also needs Chrome/Chromium.
See the [first-session guide](docs/getting-started.md) for source setup and
[export setup](docs/resume-exports.md) for PDF resumes.
Model-assisted conversations consume tokens; time and cost depend on your material
and configured service.

## Build my career pack

The wizard helps you choose useful sources: old resumes, LinkedIn exports,
performance reviews, publications, talks, project notes or your own account.
You can leave material for later and start with what you have.

1. **Read the proposed record.** The assistant gives you a browser view of your
   history, achievements and their sources.
2. **Review a useful amount.** Confirm accurate wording, explain corrections, or
   defer uncertain items. Browser reviews show five items at a time.
3. **Save and try it.** Accept a role and a few achievements, then ask to retrieve
   one. You can stop there and return whenever useful.

You can give decisions in conversation. If you use the browser controls, download
the decisions and give that file back to the assistant to apply. You decide both
whether wording is accurate and whether it may be used in external documents.

## Keep it up to date

Use ordinary requests as your work changes:

| When | What to say |
| --- | --- |
| Something worth remembering happens | “Remember that I helped the operations team rehearse the migration.” |
| You have new material | “I've added my annual review. Help me update my career pack.” |
| You're ready to organize your notes | “Review my recent notes with me and update my career pack.” |
| You need an example | “Find an achievement that shows how I mentored other engineers.” |

Quick notes are saved for later review. They become part of the reviewed pack
after you check the proposed wording. Earlier versions and sources remain available.

```text
New work -> Quick note or document -> Your review -> Updated career pack
                                                          |
                                                   Recall or reuse
```

You do not have to finish every question in one session. Say **“pause”**, then
use `make start` and choose **Continue saved work** when you return. Saved setups
and career reviews appear by name. New setup summaries also include a prompt
you can copy to continue.

## Create a resume

Choose **Create a resume** from the same launcher. Bring a job description, name
a type of role, or ask for help exploring directions. If you need a career pack
first, the wizard saves your target while you build one.

You can review ranked achievements and the reasons for including them before
writing. The assistant uses your reviewed facts, retains feedback through revisions,
and prepares **PDF, TXT and DOCX**. Missing evidence or unfinished checks are reported.

The next application starts from the same reusable career record.

## Privacy and project status

Your workspace files stay on your computer, but material you ask Claude to read
is processed by your configured model service. Personal data and generated
documents are excluded from normal Git commits and public release archives.
Keep private review pages and backups private too.

Career Evidence Core `0.1.0-alpha.5` is early access; Resume Application
`0.1.0-beta.6` is beta. Human review is part of using the tool. Automated checks
help catch problems, but do not establish excellent writing or predict hiring outcomes.

## Find help

- [Your first session](docs/getting-started.md)
- [Keep your career pack current](docs/keep-current.md)
- [Create a resume](docs/resume-start.md)
- [All guides and technical references](docs/README.md)

MIT licensed. See [LICENSE](LICENSE).
