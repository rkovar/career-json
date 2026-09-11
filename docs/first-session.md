# Your first career pack

Start with one existing resume. A target job, a complete archive and independently
verified achievements are not prerequisites. Your goal is a small record you can
inspect, correct and retrieve something from.

Before installing, [see the fictional first-pack walkthrough](../examples/first-pack/README.md).
It includes the source, browser review, saved career record and a recall example.

## 1. Bring one document

Follow the README installation steps, then put one resume in `data/sources/`.
Only ask the tool to read material you are comfortable sending to your configured
Claude service. Local files and the offline review page remain under your control;
model processing is separate from permission to publish a career claim.

In Claude Code, say:

> Build my first career pack from data/sources/my-resume.pdf. Keep it private.
> Show me the overview before asking questions.

Use your actual filename. The assistant extracts that document, stages a proposal
and gives you a link to its readable review. It handles JSON and review commands.
You can add LinkedIn exports, performance reviews and other sources later.

## 2. Read your career before reviewing fields

Start with the timeline and recorded contributions. Check whether the tool captured
your work and shared ownership accurately. Proposed strengths are interpretations;
you can explore them later. The overview is not a claim that your career is complete.

Pick a few useful achievements. Inspect their source excerpts and related role
records. Sources and profile details appear under **All career sections**; those
supporting records also need acceptance before the first pack can be saved.

You can answer in conversation, using the displayed wording, or use the browser:

> The rehearsal example is accurate. Keep it private. I want to revisit the
> mentoring example because it understates the engineers’ contribution.

The assistant records only your actual decisions. It shows related records that
need your review rather than approving them for you. You do not need to decide
external-use permissions now; newly accepted content stays private by default.

## 3. Save or correct, then stop

In the browser, choose **Save review decisions** and return to the conversation:

> Apply my saved review decisions and show me what remains. The file is at
> [the location of my downloaded decisions file].

The assistant copies that supplied file into the private workspace if needed,
checks which proposal it belongs to, saves accepted items and refreshes the page.
A download alone does not change the current pack. If a supporting record is
missing, your decisions stay saved while the assistant shows what needs review.

For a correction, explain it in your words. The assistant records the answer and
shows revised wording in a new proposal. Your note is never treated as approval
of wording you have not seen. Previously accepted, unchanged facts remain saved.

A useful stopping point is a saved role and a few supported achievements you can
retrieve. You do not need to finish every question or the strengths interview.
The assistant states what is saved, what remains pending and what can wait.
It must not claim that counts establish completeness or career quality.

## 4. Get something back

Ask:

> Show me one recorded achievement and its original source.

Or use an actual topic from your record:

> Find the project where I helped teams change how they worked.

The answer should identify the recorded contribution, its source and anything
still uncertain. If the record contains nothing relevant, the tool should say so.

## 5. Return when useful

> Continue my career-pack review.

The assistant finds saved sessions and resumes the one you were working on. It
asks which review you mean only when several are plausible. It does not re-ingest
your files or re-ask unchanged accepted facts just because the conversation ended.

Back up `data/` and `reviews/` together. Keep downloaded decisions until they have
been imported. The [operator reference](pack-review.md#operator-reference) contains
commands for manual operation; you do not need them for the conversational path.

First-run duration and token use have not been benchmarked across source types.
This is deliberately a bounded first exercise, not a promise about minutes or cost.
