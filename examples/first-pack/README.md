# Jules Elm: a career you can review

**[Open the browser walkthrough](index.html)** to explore Jules's career, try the
review controls, and compare the proposed and saved records.

Everything here is fictional: people, employers, source material, answers and
decisions. The example uses the real capture, review, acceptance and recall tools.
The imperfect extraction and scripted decisions are authored fixtures; this is
not an assessment of model extraction accuracy or real user approval.

On GitHub, HTML is shown as source. Download the repository ZIP and open
`examples/first-pack/index.html` locally. No installation or server is needed.
Keep the example folder together so its source and history links work.

## Meet Jules

Jules has sixteen years of software engineering experience and now leads
18 engineers through three engineering managers. Jules wants technical leadership
work that stays close to system design and helps other engineers develop; a
larger reporting organization is not the main goal.

| When | Employer and role | Work represented |
| --- | --- | --- |
| 2010–2014 | Fictional Civic Atlas — Software Engineer | Data-import validation and recovery runbooks |
| 2014–2017 | Fictional North Quay Systems — Senior Software Engineer | Queue visibility, shared ownership and incident exercises |
| January 2018–June 2022 | Fictional Fieldwork Ltd — Staff Engineer | Deployment rehearsals, service architecture and a shared conference talk |
| July 2022–present | Fictional Fieldwork Ltd — Head of Engineering | Platform priorities, developing managers and migration planning |

The two Fieldwork positions have separate dates and a recorded promotion
relationship. Earlier technical work remains useful alongside management
experience. Education and the co-presented talk have their own sourced records.

## Choose what to inspect

| Stage | Open | What it demonstrates |
| --- | --- | --- |
| Initial proposal | [Interactive review](review.html) | Twelve proposed achievements, four roles, three possible strengths and four sources |
| Partial acceptance | [Saved review](after-review.html), [first career record](first-career.html) | Nine achievements are saved while six items need further decisions |
| Corrections | [New wording to review](correction-review.html), [decisions applied](after-correction.html) | Shared ownership is corrected and duplicate accounts become one supported achievement |
| Corrected career | [Readable record](corrected-career.html) | Ten achievements, a confirmed strength and a stated career preference |
| Later update | [New work to review](update-review.html), [decisions applied](after-update.html) | A captured note becomes a reviewed planning achievement |
| Current career | [Readable career pack](career.html) | Eleven accepted achievements; uncertain claims remain in review |

Browser reviews show five items at a time. You can jump between batches, expand
source excerpts, correct wording or leave something for later. Your browser
experiments do not rewrite these files. Applying downloaded decisions requires
the career tool; the checked-in decisions are explicitly scripted examples.

## What should a critical reviewer notice?

- **Overstated ownership.** The initial coaching claim says Jules designed the
  format and coached every engineer. The manager review credits Mara and Theo
  with the format. The correction says Jules sponsored the pilot and coached
  three managers; it still asks which coaching was most useful.
- **Duplicate work.** “Queue-age dashboard” and “service health dashboard” describe
  one March 2016 project. The revised record keeps one achievement with both
  accounts and the five-service adoption detail.
- **An unsupported metric.** A 35% improvement has no retained baseline or
  measurement period. It remains unresolved and is absent from every accepted pack.
- **Accurate but private work.** The supplier review is accepted and explicitly
  kept private. Only the shared talk, its publication listing and the Staff
  Engineer role receive scripted external-use permission.
- **A strength that needs the person's judgment.** Jules confirms helping teams
  adopt practical engineering approaches in a recorded answer. The broader
  enterprise-transformation claim remains a correction request.
- **A note without an invented outcome.** The August 2026 migration was still
  being planned. The saved achievement records agreement and a rollback guide,
  while preserving operations' ownership of the rehearsal.

Acceptance does not establish independent verification. Even where a fictional
manager review or programme provides another account, the examples remain
self-asserted until a separate evidence review warrants a different status.

## See the ongoing habit

Jules captures: “Helped operations and product agree a phased customer-data
migration. I wrote the rollback decision guide; operations ran the rehearsal.”

The [capture snapshot](capture-before-review.json) shows the note waiting for
review and the unchanged accepted-pack hash. A [later account](data/sources/update-2026.md)
adds context. Only a new proposal and explicit scripted acceptance put that work
in the career pack. The note then points to its accepted achievement.

The earlier pack versions, original source material and decision files remain
available. The 35% claim and two unresolved strengths interpretations also remain
visible in the latest review.

## Return without repeating the interview

The [saved process example](process-habits.json) records an answered coaching
question and a deferred request for the old speed baseline. Both keep their exact
question, answer or deferral, and affected records. These are scripted examples.

The follow-up adds qualitative feedback from three managers. The
[reassessed strength candidate](data/candidates/coaching-reassessed.json) updates
its caveat while preserving shared ownership and the missing numerical outcome.
It remains proposed; the accepted career record is unchanged. Repeating intake
reports unchanged files without another factual approval. The [recovered handoff](outputs/career-handoff.md)
opens saved work after a simulated interrupted conversation.

## Reuse the record

The [browser walkthrough](index.html) shows readable results from actual searches:

| Need | Example request |
| --- | --- |
| Annual review | “What did I contribute to developing other engineers?” |
| Staff Engineer interview | “Show the service-separation decision and who delivered it.” |
| Latest progress update | “What can I accurately say about the customer-data migration?” |
| Leadership resume planning | “Emphasize manager coaching and platform adoption; show what still needs external permission.” |

The [search results](use-cases.json) and [deployment recall](recall.json) retain the
recorded wording and source excerpts. The resume prompt is a next-step example,
not a generated or evaluated resume.

## Build your own

Follow [your first session](../../docs/getting-started.md) with your own source
material. Keep Jules's fictional records out of your personal career pack.

Developers can regenerate the example:

```sh
python3 tests/build_first_pack_demo.py --output-dir examples/first-pack
```

The builder uses an isolated temporary workspace and never reads a live career
pack. The scenario is authored in `tests/jules_fixture.py`; the browser guide is
in `tests/jules_pages.py`. Regression checks verify partial acceptance, corrected
ownership, privacy, retained history, source hashes, pending questions and note
promotion. They do not establish the quality of an AI interview.
