# Career setup: assistant reference

This is the operator contract for the career wizard. The person uses
[Build my career pack](../guided-starts.md) and answers in conversation.

## Assistant operation

Use the wizard for an uncertain first start, help gathering sources, or an explicit
wizard request. Inspect supplied material, the current pack, prior answers and
saved reviews first. A specific import request already defines scope: reuse those
choices and proceed without a questionnaire. Quick capture, maintenance and
continuing an evidence review keep their existing routes.

Present at most five concise prompts at a time, generally fewer. Follow the
conditional question list and omit answers already supplied in the conversation,
pack, preferences or relevant prior session. Do not force empty batches or an
additional confirmation when the user has instructed you to proceed.

The shared session engine belongs to Core. The Resume Application adds its own
questions and typed brief handoff. Private records live in
`reviews/startup/<career|resume>/<session-id>/` and are excluded from releases.
They contain workflow context, not accepted facts or editorial approvals.

The assistant runs the commands; the person should not need to edit JSON:

```sh
python3 scripts/career_core.py start list
python3 scripts/career_core.py start create --id first-start
python3 scripts/career_core.py start show --session reviews/startup/career/first-start/000001.json
```

`create --answers data/private/start-answers.json` preloads actual supplied
answers. `answer --input <file> --session <latest-json>` applies a patch:

```json
{
  "route": {"state": "answered", "origin": "user", "value": "existing"},
  "sources": {
    "state": "answered", "origin": "user",
    "value": [
      {"path": "data/sources/my-resume.pdf", "purpose": "career_evidence"},
      {"path": "data/sources/job-description.pdf", "purpose": "job_context"}
    ]
  },
  "missing_work": {"state": "later", "origin": "user", "value": null}
}
```

For a direct source request, run `career_core.py intake <authorized-path>` without creating an unnecessary wizard session. Use `data/sources` only when the whole directory was authorized. Read its inventory and extracted text; unchanged material needs no new candidate. Before extracting facts, inspect and classify files within the requested scope:
`career_evidence`, `job_context`, `writing_reference`, or `defer`. A filename alone
does not establish purpose. “Everything in Sources” authorizes inspection of that
directory, not treating advice or employer requirements as career history.
`resume_information/` remains writing guidance. New files never silently enter
the selected scope.

Every answer has `state`, `origin`, and `value`. States are `answered`, `none`,
`not_applicable`, `later`, and `skipped`; non-answers have null value. Origins are
`user` (actually supplied), `saved` (reused), and `inferred` (assistant assumption,
never person acceptance). A question update replaces its whole value; preserve
other categories when editing one. Prior revisions retain previous wording.

| Question | Answer value |
| --- | --- |
| `route` | `existing`, `gather`, or `conversation` |
| `sources` | List of `{path, purpose, note?}` inside `data/sources/` |
| `materials` | Category map, each with `{state, detail?}` |
| `career_story` | Exact user account as text |
| `missing_work` | Exact user account as text |
| `restrictions` | Handling instructions as text |

Material categories: `resumes`, `linkedin`, `reviews`, `public_work`, `projects`,
`feedback`, `qualifications`. None/not-applicable/later can apply to one category
without closing the others. Do not invent checklist responses.

## Continue and hand off

`pause`, `resume`, `refresh`, `back --question <id>` and `handoff` take
`--session <latest-json>`. Omit the session only with one unfinished start; ask
which one if multiple are plausible. `refresh` reopens a handed-off start and
inventories new material while retaining answers. `back` reopens one question.
Saved none/later/skip answers stay closed until the person returns to them; they
are not permanent claims that work does not exist.

Writes use immutable revisions and a workspace lock. Stale edits fail instead of
overwriting newer answers. Selected files are pinned by hash. Refreshing the
inventory does not approve changed bytes: inspect and save source choices again.

Run `career_core.py start handoff --session <latest-json>` and link its summary:

- `gather_sources`: show the saved checklist and a clear stopping point.
- `ingest_candidates`: use only `career_sources` and `user_accounts` as career
  evidence; keep `context_sources` and `deferred_sources` separate.

Save exact user accounts with their origin in a new private source note before
normal extraction. An inferred account is never user testimony. Preserve handling
restrictions. Continue ingestion into `data/candidates/` and the existing readable
review; setup has accepted no wording and granted no external-use permission.

Reuse saved category answers in later evidence/strength interviews. Do not re-ask
a settled absence merely because no publication record was generated. New career
claims still go through source and human review. A handoff completes setup, not
the career pack.

At a pause or handoff, show the report's `saved`, `next` and `continue_prompt`
alongside the summary link. When the person names a saved setup, resolve that
name through `start list` and read its latest revision. For active/paused setup,
continue with the existing answers. For handed-off setup, use its recorded handoff
to continue downstream work; do not call `resume` on a completed setup or create a
duplicate brief. Refresh only when the inputs or choices need to change.
