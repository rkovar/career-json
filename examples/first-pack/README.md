# A first career pack: Jules Elm

**Entirely fictional.** This is a small demonstration of the review workflow,
using two achievements from one short resume. Extraction and decisions are authored
fixtures; it is not a claim about model extraction accuracy or real user approval.
No installation or private source upload is needed to read this walkthrough.

## Start with one resume

Jules is a Head of Engineering at Fictional Fieldwork Ltd. The
[source resume](data/sources/resume.md) records a deployment rehearsal tool and
engineering coaching with peer design reviews. It contains no revenue figures,
independent corroborators or contact details beyond name and location.

## See what was captured

[Open or download the interactive review page](review.html). GitHub shows HTML as
source: download the file and open it locally in your browser. It needs no server.

The overview contains:

| Career record | What Jules sees |
| --- | --- |
| Timeline | Head of Engineering, January 2018 to present |
| Deployment rehearsals | Designed the format and co-built the runner; two teams adopted it |
| Engineering practice | Hired and coached engineers; the group adopted peer design reviews |
| Proposed strength | Builds technical capabilities that teams adopt; needs Jules’s interpretation |
| Open question | What part of coaching was most useful to the engineers? |

The source excerpts remain beside the proposed records. These examples are
self-asserted. Team ownership and an unmeasured outcome remain explicit.
See the [proposed JSON](data/candidates/proposal.json) if you want the stored fields.

## Review a useful amount, then stop

The [scripted sample decisions](decisions.json) accept the two achievements,
role, source and profile details. They keep everything private and defer the
strengths interpretation. No missing metric is invented and no status is promoted.

[See the review after those decisions](after-review.html): one role and two
achievements are saved, the strengths interpretation is pending, and the coaching
question remains available. This is already useful; Jules can stop here.

The [readable saved career pack](career.html) and [accepted JSON](data/packs/accepted.json)
show the result. The relative source and decision records in this example folder
are retained so the accepted JSON’s references can be inspected.

## Retrieve an achievement

Jules asks: **“Show me the deployment rehearsal example and its original source.”**

The [actual recall result](recall.json) contains the rehearsal achievement and
its recorded source excerpt. A conversational response can say:

> You designed the rehearsal format and co-built its runner with engineers.
> Two teams adopted rehearsals before deployment. This is recorded in your own
> resume; the example does not establish independent verification.

That is the first payoff: reusable history with ownership and provenance intact.
Later Jules can say **“Continue my career-pack review”** to discuss the proposed
strength or add a richer coaching example.

## Build your own

Follow [your first session](../../docs/first-session.md), using one actual resume.
Keep these fictional records out of your personal pack.

Developers can regenerate the demonstration with
`python3 tests/build_first_pack_demo.py --output-dir examples/first-pack`.
The builder uses an isolated temporary workspace and never reads a live career pack.
