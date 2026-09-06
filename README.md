# career.json

**Your career, in a file you own.**

A Claude-native workspace for remembering what you did, and for building a
different resume from it every time.

## The problem

A long career has two failure modes, and they pull against each other.

**You forget.** The stalled programme you unblocked in two weeks, the migration
that halved a bill, the incident you ran at 3am. None of it gets written down at
the time, and eighteen months later it is gone. By the time you need it, you are
reconstructing your own career from memory and a stale resume.

**You have too much.** Once there is enough to remember, no single resume can
carry it. Every role wants a different subset, and hand-curating that from a
ten-page document, for every application, is miserable enough that most people
send the same resume everywhere.

## The idea

Keep one durable, structured record of your career. Treat resumes as **disposable
outputs** of it, not as the thing you maintain.

The record is a **datapack**: evidence atoms in STAR form, employment history,
skills, each traceable to the source it came from. The pack is the product. A
resume is a query against it, shaped for one role.

Two properties make it trustworthy enough to build on:

- **Nothing is invented.** Every claim traces to a source. Every employer, title,
  and date traces to an employment record. If evidence for something does not
  exist, the document says less rather than more.
- **The record knows what it does not know.** Unresolved claims, inferred dates,
  gaps in the timeline, and evidence that would read badly for a given role are
  all recorded rather than smoothed over.

## Quick start

```sh
git clone <this repo> && cd career.json
make hooks                      # optional: validate on commit
```

Put your material in `data/sources/` — a resume, a LinkedIn export, an
end-of-year write-up. Then, in Claude Code:

```
Use build-career-pack on everything in data/sources/
```

It ingests, reviews the evidence, and ends with one batch of questions plus a
readiness statement. Then:

```
Use make-resume for Head of AI Security
```

You get a draft, an integrity evaluation, and a recruiter's verdict on whether it
would actually be shortlisted.

## The loop

```
    capture-work ──────────┐
    (seconds, any time)    │
                           ▼
    annual write-up ──▶ build-career-pack ──▶  datapack  ──▶ make-resume ──▶ draft
    (once a year)                              (the product)      │            │
                                                                  ▼            ▼
                                                          make-interview-brief  recruiter-screen
```

**Capture continuously.** `capture-work` records a one-line note in seconds and
never touches the pack, because a note that costs a pack version is a note nobody
writes.

**Import the annual write-up.** Your end-of-year self-review is the biggest
capture event of the year. It is handled as a review period: deduplicated against
what you already have, dated from the document, and defaulted to internal-only
because a self-review is written for an employer.

**Curate per role.** Selection ranks your evidence against the role's
requirements and hands generation a shortlist, so curation stays sharp as the pack
grows past what anyone would read.

## Skills

Invoke these by name in Claude Code. The first four are what you use day to day.

### `capture-work`

Records something before you forget it. No questions, no STAR, no metrics — a note
is a hook for memory, and every question asked here makes the next capture less
likely.

```
Remember that I cleared the controls backlog in two weeks without formal authority
```
```
capture that I shipped the MCP delegation pattern, tag it ai-security
```
```
What notes do I have waiting?
```

### `build-career-pack`

Setup, run whenever you have new material. Ingests and reviews in one pass, then
asks everything at once and tells you how ready the pack is.

```
Use build-career-pack on my 2026 end-of-year review
```
```
I've added my LinkedIn export, update the pack
```

### `make-resume`

Delivery. Reads the pack, writes the document, evaluates it, and screens it.
**Asks nothing** — ambiguity is resolved by inference or by narrowing the claim,
and every inference is reported afterwards.

```
Use make-resume for this job description
```
```
Make me a cover letter for the Head of Security Architecture role
```
```
Draft a LinkedIn About section
```

### `make-interview-brief`

Private preparation. Reads the **whole** pack, deliberately including the evidence
no artefact may cite, because the claims you had to leave out are the ones an
interviewer will find.

```
Prep me for the interview on Thursday
```

### `recruiter-screen`

Runs automatically at the end of `make-resume`, and on its own against anything —
including documents this workspace did not produce.

```
Review my existing CV as a recruiter
```
```
Would this get shortlisted?
```

Returns `advance`, `borderline`, or `reject`, the reason, and splits every
weakness into what a rewrite can fix versus what needs new evidence. A `reject`
is a successful run: it is cheaper here than in the market.

### Stage skills

`ingest-career-materials`, `review-evidence`, `generate-resume`, and
`evaluate-output` are called by the two orchestrators above. Use them directly
only to run one stage deliberately.

## Command line

Everything is standard library Python or shell. There are no dependencies.

| Command | Does |
| --- | --- |
| `make check` | Validate packs and records, run the test suite |
| `make fit` | Score your evidence against every role profile |
| `make coverage` | Timeline, gaps, undated atoms, stale skills |
| `make notes` | Capture notes awaiting promotion |
| `make dupes` | Near-duplicate atoms already in the pack |
| `make index` | Regenerate `outputs/INDEX.md` |
| `make verdicts` | Record screen verdicts and show the trend |
| `make hooks` | Install the pre-commit hook |

```sh
scripts/capture.py "what you did"                      # 30-second note
scripts/find.py --skill "threat modelling" --since 2020
scripts/select_evidence.py --role head-of-ai-security  # ranked shortlist
scripts/dedupe.py --text "<claim>"                     # already in the pack?
scripts/extract_text.sh --record data/sources/cv.pdf   # text and provenance
```

## Privacy

`data/`, `outputs/`, and `reviews/` are ignored by Git and never leave your
machine. `examples/` is committed and contains only fictional material. The
pre-commit hook refuses any commit that stages private material.

Contact details live in the pack's `private_profile` and appear in full only on a
document sent to a named recipient. A public artefact gets name and location.
Street address and photo references never appear in any artefact.

## Interoperability: resume.json

[JSON Resume](https://jsonresume.org/) is an established open standard
(`resume.json`) with a schema, a CLI, and a theme ecosystem. It is a
**presentation** format: it has no notion of evidence, provenance, confidence, or
material you must not publish.

So the two are layers, not competitors. `career.json` is the private superset;
`resume.json` is a lossy projection of it that anyone's renderer can consume.

```sh
scripts/export_resume_json.py --role head-of-ai-security -o outputs/resume.json
scripts/export_resume_json.py --audience public          # name and location only
```

The projection drops everything unpublishable, collapses promotions into their
parent role, converts dates to ISO 8601, and stamps `meta.canonical` so the file
says where it came from. What you get back is every JSON Resume theme for free.

## Documentation

- [Getting started](docs/getting-started.md) — a first session, end to end
- [Workflow](docs/claude-workflow.md) — how the pieces fit
- [Data model](docs/data-model.md) — the datapack schema and why it is shaped this way
- [Source intake](docs/source-intake.md) — what to feed it
- [Extraction](docs/extraction.md) — PDFs and provenance
- [LinkedIn](docs/linkedin.md) — why there is no connector, and what to do instead
- [Architecture](docs/architecture.md) — what is code, what is a skill, and why

## Design notes

**Skills hold judgement; scripts hold everything decidable.** Eligibility
filtering, rendering, and artefact checks are pure functions over the pack, so
they are code with tests rather than instructions repeated to a model. Ineligible
evidence never enters context at all: you cannot cite what you were never shown.

**Corroboration is optional.** `self_asserted` is the normal resting state for
career evidence and is not a defect. Employment is the exception, because
employers, titles, and dates are what a background check actually tests.

**Honest beats flattering.** The evaluation will tell you a document is not
publishable, the screen will tell you it would be rejected, and role fit will tell
you your evidence does not support a title. Those are the product working.
