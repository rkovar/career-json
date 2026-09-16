# Start here

Run `make start` from the project directory:

```text
What would you like to do?

1. Build my career pack
2. Create a resume
3. Continue saved work
```

The launcher opens Claude Code with the chosen wizard prompt. Answer in that
conversation. Resume creation appears only with the compatible add-on installed;
Continue saved work appears when saved setups or career reviews exist. Menu
numbers follow the available choices.

**Unsure? Start with your career pack. One old resume is enough.**

Already in Claude Code? Say **“Walk me through the career-pack wizard”** or
**“Walk me through the resume wizard.”** You can say “later”, “skip”, “go back”
or “pause”. Each summary shows what is saved, what happens next and one prompt
you can copy to continue the named setup. No JSON editing or file hunting is needed.

For a resumed setup, use its latest summary or choose its name under
**Continue saved work**. Finished setups retain a prompt for continuing into
career-pack preparation or resume creation. Existing answers are reused.

See [Build my career pack](guided-starts.md) or [Create a resume](resume-start.md).
The walkthrough below covers importing a source directly when you already know
what to use.

## 1. Add source material

Copy whatever you already have into `data/sources/`. That directory is Git
ignored and excluded from release archives. Material you ask Claude to read is
processed by your configured model service; Git ignore rules do not prevent that.

Start with **one resume**. Follow [your first session](first-session.md) for the
short conversational path, or [preview the fictional result](../examples/first-pack/README.md).
Add LinkedIn exports, annual reviews and public work after you have a useful first record.

## 2. Build the pack

```
Build my first career pack from data/sources/my-resume.pdf. Keep it private.
Show me the overview before asking questions.
```

It runs ingestion without stopping, queues the questions the evidence raises,
and gives you a readiness statement. The questions are then asked one at a time
by `review-evidence`, which records each answer as you give it. Contact details
beyond the recorded name and location can wait until you want a document to send.

Answer what you can. **Unanswered questions are not a blocker**: they mark the
claim `unresolved` and it is simply left out of documents until you come back to
it.

Open the private career review page produced by the tool. It shows your timeline,
achievements, source excerpts, strengths and future direction in small batches.
Accept accurate wording, request corrections, or leave items for later; choose
external-use permission separately. Download your decisions and give the file
back to the tool to save the accepted items. It preserves the rest as pending.
See [review your career record](pack-review.md) for the complete flow.

Check the accepted record (the tool validates proposals separately):

```sh
make check          # the pack validates
make coverage       # where the record is thin
```

## 3. Keep or export your career pack

You can finish onboarding here without generating a document. Review strengths
with `review-strengths`, then resume or export the accepted record:

```sh
python3 scripts/career_core.py status
python3 scripts/career_core.py export --output data/private/career-export.json
```

The export is a lossless private JSON copy. While the first pack is still a
proposal, use `status --pack <candidate-path>` instead. Back up `data/` and
`reviews/` together so source files and review decisions stay with the record.
See [core workflow](core-workflow.md) for details.

## 4. Optionally add the Resume Application (beta)

The combined checkout includes it. Core archive users can install the matching
add-on using [release instructions](releases.md). The following steps need it.

### Describe a role

Selection and screening work much better against a structured role profile than
against a title. Put a job description in `data/sources/` and ask Claude to build
one, or write it by hand into `data/roles/<role-id>.json` following
[the schema](../schemas/role-profile.schema.json).

The `central_requirement` captures the role's primary requirement. If the recorded
evidence does not support it, the screen identifies the gap. That is a reason to
review the evidence or targeting, not a prediction of an employer's decision.

```sh
make fit            # which roles your evidence actually supports
```

### Make something

```
Use make-resume for <role>
```

If the target is unclear, the [resume wizard](resume-start.md) establishes the role
and qualities to highlight, then saves a brief. You receive PDF, TXT and DOCX,
alongside Markdown/HTML working drafts and private review records.

The screen distinguishes weaknesses that editing can address from missing evidence.
Its verdict is a model opinion; assess the passages and reasoning yourself.
A passing integrity check does not establish strong writing or a hiring outcome.

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
