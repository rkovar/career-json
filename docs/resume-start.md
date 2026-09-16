# Create a resume

Run `make start` and choose **Create a resume**, or say **“Walk me through the resume wizard.”** Start from a job description, a general role,
or help choosing a direction. Name the qualities and achievements to highlight,
or ask for suggestions grounded in your pack. The proposed selection explains
why each example matters and what it leaves out.

Setup also records market, employer instructions, length preferences and whether
you want to review the selection before writing. PDF, TXT and DOCX remain
required; there is no additional format question.

Without an accepted pack, your target and preferences stay saved while Claude
helps build and review the pack. Desired qualities are preferences, not facts.

## Pause and continue

Every new summary explains what was saved, the next step, and an exact prompt for
continuing that named setup. Copy the prompt into the conversation, or run
`make start` and choose **Continue saved work**. The HTML is a private snapshot;
use the newest summary after an edit.

## Assistant workflow

Follow [Guided starts](guided-starts.md) for conversation, answer states and
saved sessions. Complete explicit resume requests can bypass the interview.
Reuse applicable saved choices; never guess the newest application or force an
extra checkpoint on an automatic request.

```sh
python3 scripts/editorial.py start list
python3 scripts/editorial.py start create --id application-start
python3 scripts/editorial.py start create --id returning --brief data/briefs/prior.json
```

Reuse a named brief only when applicable. Wizard-created briefs recover their
exact original target, pinned source and deferred answers from the handoff.
Legacy briefs supply their recorded settings. When changing targets, review which
employer constraints still apply. The wizard reopens constraints when a target
or JD changes and employer rules were recorded, preserving the old answer in
context. Confirm/update applicable settings or explicitly clear them before
handoff. Reuse unchanged market/preferences instead of asking for them again.

Use `create --answers <file>` or `answer --input <file> --session <latest-json>`
with the shared answer envelope:

| Question | Value when answered |
| --- | --- |
| `target` | `{mode: "job_description", path: "data/sources/job.pdf"}`; `{mode: "role", description: "...", role_id?: "...", role_family?: "..."}`; or `{mode: "explore"}` |
| `focus` | `{text?: "...", strength_ids?: [...], suggest?: true}` |
| `achievements` | `{include_ids?: [...], deemphasize_ids?: [...], notes?: "..."}` |
| `constraints` | Partial application settings plus `length`, `audience`, `setting_sources` |
| `review_mode` | `"interactive"` or `"automatic"` |

These are operator data shapes; the person answers in ordinary language.
Resolve named examples to existing IDs. Route new facts through Core.

Constraints support `market` (UK, US, unspecified), `document_type`,
`submission_channel`, `contact_mode`, `paper_size`, `page_limit`,
`employer_instructions`, `length` and `audience`. Use `setting_sources` for
employer provenance, e.g. `"page_limit": {"origin": "employer", "reason":
"Two pages required by the supplied job description."}`. Defaults remain inferred.

For `explore`, suggest a few directions from actual evidence and explain support
and gaps, then save the chosen direction. If there is no pack or chosen target,
keep setup open while starting Core. Do not invent a target to finish the wizard.
For requested strength suggestions, inspect supported strengths and eligible
atoms, distinguish proposed interpretations, and use Core for factual review.

For a JD, build `data/roles/<role-id>.json` and set `source` to that exact
job-description path. Handoff checks the profile and source. Changed JD bytes
require reinspection and a new target answer.

```sh
python3 scripts/editorial.py start handoff \
  --session reviews/startup/resume/application-start/000002.json \
  --id application-brief-v1 --application application-one --role target-role
```

Omit `--role` for a general target or when saving before the first pack.
`--output-id` can retain the logical output across brief revisions. Handoff saves
an existing-schema brief in `data/briefs/` and pins it in the session; use new IDs
for new versions. It never overwrites a brief.

- `build_pack_then_resume`: retain the brief and start Core. After acceptance,
  refresh the same resume session, supply the JD profile if needed, and save a
  new brief. Existing answers remain available.
- `prepare_selection`: run `editorial.py prepare` on the exact saved brief, then
  continue [resume planning](resume-workflow.md).

Read private brief instructions during selection. Inclusion and de-emphasis
preferences persist there; explain material tradeoffs rather than dropping them.
Use the existing scoped decision workflow for a requested durable omission or
broader preference. De-emphasis is not factual deletion. Private instructions
must not be copied into prose; communicate the desired impression through eligible
evidence and the reviewed plan.

Interactive mode waits for actual selection feedback. Automatic mode proceeds
through assistant review. Setup completion supplies no factual, selection or
publication approval. Existing evaluation, process and export checks still apply.

At a pause or handoff, show the report's `saved`, `next` and `continue_prompt`
alongside the summary link. When the person names a saved setup, resolve that
name through `start list` and read its latest revision. For active/paused setup,
continue with the existing answers. For handed-off setup, use its recorded handoff
to continue downstream work; do not call `resume` on a completed setup or create a
duplicate brief. Refresh only when the inputs or choices need to change.
