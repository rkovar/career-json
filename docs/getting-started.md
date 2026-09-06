# Getting Started

A first session, end to end. Assumes you have cloned the repo and have Claude Code
open in it.

## 1. Add source material

Copy whatever you already have into `data/sources/`. That directory is Git
ignored, so nothing leaves your machine.

Good first sources, in rough order of value:

1. Your most recent resume or CV.
2. Your LinkedIn data export. Not the PDF: use Settings, Data privacy, Get a copy
   of your data. See [linkedin.md](linkedin.md) for why the export beats both the
   PDF and any API.
3. End-of-year self-reviews. These are the richest source most people own, because
   you wrote them while you still remembered.
4. A list of public work: talks, articles, repositories.

## 2. Build the pack

```
Use build-career-pack on everything in data/sources/
```

It runs ingestion and evidence review without stopping, then gives you one batch
of questions and a readiness statement. On a first run the batch includes your
contact details, because a pack without them cannot produce a document anyone can
reply to.

Answer what you can. **Unanswered questions are not a blocker**: they mark the
claim `unresolved` and it is simply left out of documents until you come back to
it.

Check what you got:

```sh
make check          # the pack validates
make coverage       # where the record is thin
```

## 3. Describe a role

Selection and screening work much better against a structured role profile than
against a title. Put a job description in `data/sources/` and ask Claude to build
one, or write it by hand into `data/roles/<role-id>.json` following
[the schema](../schemas/role-profile.schema.json).

The field that matters most is `central_requirement`: the one thing the role is
actually hiring for. If your evidence cannot support it, that is a rejection and
better to know now.

```sh
make fit            # which roles your evidence actually supports
```

## 4. Make something

```
Use make-resume for <role>
```

You get three files in `outputs/`: the draft in Markdown, the same in HTML, and an
evaluation record. Plus a recruiter screen with a verdict.

Expect the first verdict to be unflattering. That is the point — it is cheaper
here than in the market, and the screen tells you which weaknesses a rewrite can
fix and which need new evidence.

## 5. Keep capturing

This is the habit that makes the rest worth having.

```
Remember that I <thing you just did>
```

Takes seconds, asks nothing, and never touches the pack. Then once a year, when
you write your self-review, import it with `build-career-pack` and promote the
notes at the same time — you are already in a remembering frame of mind, which is
the cheapest moment all year to do it.

## What good looks like after a year

- Your capture log has a few dozen notes, most promoted into atoms.
- `make coverage` shows no multi-year gaps.
- `make fit` scores at least one target role as well supported.
- Generating a tailored resume for a new role takes one message.
