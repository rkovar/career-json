# career.json

**Your career, in a file you own.**

Build a private, readable record of your roles, achievements, sources and strengths.
Review the facts once, improve them over time, and reuse them for different roles
and document formats. The career pack is the ground truth; generated resumes are
disposable outputs.

[See a complete fictional first pack](examples/first-pack/README.md) before installing.

You can start with one resume, several sources, or a conversation about your work.
You do not need a target job or a complete career history. The tool runs through
Claude Code and local scripts. Career Evidence Core works independently; resume
generation is an optional application.

## Start your career pack

You need Claude Code with access to a configured model, Python 3.9+, `make`, and
macOS or Linux. Python scripts use the standard library. PDF intake uses macOS
PDFKit or Poppler (`poppler-utils` on Debian/Ubuntu). Model-assisted sessions
consume tokens; duration and cost depend on the material and model.

```sh
git clone https://github.com/rkovar/career-json.git
cd career-json
make check
```

Open the directory in Claude Code and say:

> Help me start a career pack.

The [guided start](docs/guided-starts.md) asks what material you have: old resumes,
LinkedIn exports, performance reviews, speaking engagements, publications, project
notes or your own account. It distinguishes career evidence from job descriptions
and writing advice. It saves your answers and provides a private HTML summary;
you can pause, go back and resume.

If you already know what you want, put the material in `data/sources/` and ask:

> Build my first career pack from everything in data/sources/. Keep it private.
> Show me the overview before asking questions.

The assistant inventories the supplied material, extracts candidate facts and
stages a proposal. It does not automatically accept that proposal.

1. **Read your proposed career record.** See roles, achievements, source excerpts,
   strengths and gaps before making decisions.
2. **Review five items at a time.** Keep accurate wording, request corrections,
   defer uncertain items and choose external-use permission separately. Navigation
   keeps the current batch in view instead of sending you back through the page.
3. **Download and apply your decisions.** Give the saved file back to the assistant.
   Accepted items enter a new pack version; pending work remains available.
4. **Retrieve something useful.** Ask “Show me one achievement and its original
   source.” Stop here or continue the evidence and strengths interviews.

A statement repeated in your resume and LinkedIn profile remains your own account.
Accepting wording does not independently verify it or permit external use.
New and changed content stays private until separately allowed.

To return, say **“Continue my career-pack review.”** See
[your first session](docs/first-session.md) and [the review workflow](docs/pack-review.md).

## Read and maintain your record

`make pack-html` creates a searchable private overview. `make career-page` creates
a simpler reading page at `outputs/career-record.html`. Both include withheld
material and are private working documents. The reading page uses recorded pack
content; it does not extract extra claims from raw sources or approve them.

```text
 Sources or your account
           |
           v
     Proposed pack <----- Corrections / missing work
           |                         ^
           v                         |
  Overview + your review ------------+
           |
     Accepted items
           |
           v
     Your career pack
       |           |
       v           v
  Recall/export  Optional documents
```

Use `capture-work` for a quick note before you forget a contribution. Use
`review-evidence` for focused follow-up questions and `review-strengths` for a
resumable interview about what the evidence demonstrates and what you want next.
Strength interpretations keep their supporting evidence; changed support makes
them stale and prompts reassessment.

Ask to check workspace health, explain an achievement's history, combine duplicate
accounts, split a large achievement or attach a clarified source. Maintenance
creates reviewable proposals and preserves historical IDs.

```sh
python3 scripts/career_core.py health
python3 scripts/career_core.py history E_PROJECT --output outputs/history.html
python3 scripts/career_core.py export --output data/private/career-export.json
python3 scripts/career_core.py backup --output backups/career.zip
python3 scripts/career_core.py restore --input backups/career.zip --destination ../career-restored
```

The JSON export preserves the full private pack. A backup also preserves sources,
pending reviews, wizard sessions, application inputs, outputs and the installed
runtime. Restore checks the archive and references, and requires a new directory.
Backups contain private data and are not encrypted.
See [workspace maintenance](docs/workspace-maintenance.md).

## Make a resume from the pack

In this combined checkout the Resume Application is already present. Core-only
archive users install the matching add-on first.

> Help me make a resume.

The [resume wizard](docs/resume-start.md) establishes whether you have a job
description, want a general resume or are exploring roles. It records the qualities
and examples you want to emphasize, anything to downplay, employer instructions,
and your preference for automatic or interactive review. Known answers are reused.
It can pause with a durable brief if your career pack still needs work.

You can also make a direct request:

> Use make-resume for this job description. Show me the ranked evidence before writing.

The workflow:

- Saves a brief and a plan connecting intended reader impressions to eligible evidence.
- Presents selection reasons, alternatives and gaps when review is requested.
- Writes with accurate ownership, employer/title/date relationships and source support.
- Reviews omitted evidence, representation of your strengths, language, factual
  integrity, privacy and the reader's first impression.
- Keeps feedback and revision history so concerns survive shortening and retargeting.
- Exports **PDF, TXT and DOCX** from shared content and checks the exact files.
  HTML is a private preview.

PDF export needs Chrome/Chromium and a PDF extractor. Verification checks recovered
content and order, page count, clickable link targets and file hashes. A recorded
visual review of the final PDF is also required for planned-resume publication.
TXT and DOCX need only Python; DOCX pagination can differ in Word.
[Export details](docs/resume-exports.md) explain the tools and limits.

The delivery includes review records and a private handoff explaining remaining
work. A partial export or unfinished review is reported as incomplete.
Submit only the files in the export bundle's `files/` directory.

**Successful validation does not establish a good resume or a hiring outcome.**
The recruiter screen returns `advance`, `borderline` or `reject` as a reasoned
model opinion, distinguishing editing problems from missing evidence. It is not
calibrated against employer decisions. Text extraction and keyword checks do not
certify compatibility with every ATS. Human judgment remains necessary for
emphasis, voice, credibility and role fit.

See [resume authoring](docs/resume-authoring.md),
[process review](docs/resume-process.md) and [editorial quality](docs/resume-quality.md).
The application also supports cover letters, biographies and private interview briefs.

## Components and releases

| Component | Status | Owns |
| --- | --- | --- |
| Career Evidence Core | Early access: `0.1.0-alpha.5` | Intake, factual review, supported strengths, recall, maintenance and private export |
| Resume Application | Beta: `0.1.0-beta.6` | Targeting, briefs, selection, plans, writing, document review and exports |

The add-on requires the exact Core version declared in its component manifest.
Both read career schemas 1.3 and 1.4. Separately built archives have disjoint file
lists and contain no personal workspace data. These are local release candidates;
broader usability and writing-quality evidence is still needed.
See [release and installation instructions](docs/releases.md).

## Useful commands

| Command | Purpose |
| --- | --- |
| `make check` | Validate local packs, reviews and excerpts, then run deterministic tests |
| `make test` | Run tests in fictional workspaces without auditing your historical outputs |
| `make check-core` / `make check-resume` | Check component contracts independently |
| `make test-releases` | Exercise clean Core and Core-plus-Resume installations |
| `make release-core` / `make release-resume` | Build local component archives in `dist/` |
| `make pack-html` / `make career-page` | Generate private views of the recorded career |
| `make coverage` / `make questions` | Inspect gaps and useful follow-up questions |
| `make notes` / `make dupes` | Review capture notes and possible duplicate achievements |
| `make records` | Check saved application records, dependencies and staleness |
| `make index` | Rebuild the generated-output index |
| `make hooks` | Install a hook that tests staged source and blocks private paths |

`make help` lists additional commands. Use `python3 scripts/career_core.py --help`
for Core operations and `python3 scripts/resume_workflow.py --help` for application
planning. Conversational skills handle these commands when you ask for a workflow.

The pre-commit hook checks the **exact staged source** in an isolated workspace.
`make check` also audits the current workspace's private records; it may flag
historical reviews after policy changes. Preserve those records and regenerate
reviews for a new delivery instead of editing old approvals to make checks pass.
See [development and validation](docs/development.md).

## Privacy and evidence boundaries

`data/`, `reviews/`, `outputs/`, `backups/`, local archives and
`resume_information/` research inputs are ignored by Git. Release builders use
explicit public allowlists. Committed examples are fictional. The pre-commit
hook rejects tracked private paths apart from the repository's empty placeholders.

These are filesystem and publication protections, not a network privacy guarantee:
material read in a Claude session is processed by the configured model service.
Do not give the tool material you cannot share with that service.

Contact details belong in `private_profile`. A resume for a named recipient can
carry an appropriate contact block; public documents use name and location.
Private reviews and lossless exports may include personal details, source excerpts
and withheld evidence. Keep them private. Reading views are not submission files.

Missing evidence narrows what can be claimed. New factual information discovered
while writing returns through Core review; polished resume wording never becomes
ground truth automatically.

## Interoperability

`scripts/export_resume_json.py` projects eligible content into
[JSON Resume](https://jsonresume.org/), a separate presentation format:

```sh
python3 scripts/export_resume_json.py --audience public -o outputs/resume.json
```

The export omits ineligible material, retains separate position rows for promotions,
converts recorded dates and records its canonical source. It is a lossy projection:
it does not replace the career pack's evidence, provenance or review history.
Third-party themes may need their own layout checks.

## Documentation

- [First session](docs/first-session.md) and [setup](docs/getting-started.md)
- [Career wizard](docs/guided-starts.md) and [resume wizard](docs/resume-start.md)
- [Core workflow](docs/core-workflow.md), [source intake](docs/source-intake.md)
  and [human review](docs/pack-review.md)
- [Workspace maintenance and backup](docs/workspace-maintenance.md)
- [Strengths and editorial memory](docs/editorial-memory.md)
- [Resume workflow](docs/resume-workflow.md), [authoring](docs/resume-authoring.md),
  [employment grouping](docs/resume-employment.md) and [exports](docs/resume-exports.md)
- [Process review](docs/resume-process.md), [editorial quality](docs/resume-quality.md)
  and [quality benchmarks](docs/quality-benchmarks.md)
- [Data model](docs/data-model.md), [architecture](docs/architecture.md)
  and [development](docs/development.md)
- [Releases](docs/releases.md), [PDF extraction](docs/extraction.md)
  and [LinkedIn intake](docs/linkedin.md)

MIT licensed. See [LICENSE](LICENSE).
