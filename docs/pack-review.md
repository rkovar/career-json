# Review your career record

The core finishes an import with a reviewable proposal. Proposed information lives
in `data/candidates/`; it is not the current career pack. The person can compare
it with their previous version, correct it, defer it or accept exact items. The
accepted pack remains available while review is unfinished. Existing packs remain
usable and are labelled **not yet reviewed** rather than automatically approved.

## The conversational path

For your first pack, follow [your first session](first-session.md). Bring one
source and let the assistant handle the commands below. Review the overview,
then the exact items you want to accept or correct. Newly accepted content can
stay private; publication choices can wait.

After downloading decisions, say **“Apply my saved review decisions and show me
what remains”** and give the file location. To return later, say **“Continue my
career-pack review.”** The assistant finds the session, preserves your choices,
refreshes the readable page and gives you a useful stopping point plus a recall
example. Ambiguous sessions are clarified rather than guessed.

## Operator reference

The remaining instructions are for the assistant or someone operating the CLI.
They are not extra steps the person must perform during conversational onboarding.

### Create a review

Author a complete proposed pack, preserving existing facts, IDs, source references
and metadata. Keep omissions explicit; deleting a record is a proposed removal
that also needs acceptance. Sources, employment, education, achievements,
strengths, preferences and other factual fields all appear in the review.

```sh
python3 scripts/career_core.py review start --candidate data/candidates/proposal.json --id onboarding-v1
python3 scripts/career_core.py review render --session reviews/pack-reviews/onboarding-v1/session.json --output outputs/career-review.html
```

You can also review the current legacy pack by passing its path as the candidate.
Existing schema inconsistencies are shown in that legacy review; they must be
corrected in a new proposal before a new accepted version can be saved. The tool
never invents missing detail to make an older record pass validation.
The tool snapshots both versions and their hashes in a private review directory;
starting a review never edits or replaces the current pack. Open the generated
HTML in a browser. It works offline, without a server or installed dependencies.
It contains private material and personal details, so keep it on your device.
`make pack-html` remains a read-only overview, now including strengths, preferences,
source excerpts and wording-review status; it deliberately omits contact details.

### What the person reviews

The page starts with a career overview and recent contributions, then shows five
review items at a time. Supporting records remain available in All career sections.
Filter by career section or change type, search, inspect previous values, and
expand original source excerpts. Full stored fields and IDs remain available in
details. Text comes directly from the pack; no extra model summary is generated.

**Looks accurate** accepts the wording. **Correct this** requires an explanation.
**Not sure** and **Review later** leave the change pending. No choice is preselected.
Acceptance never increases evidence confidence. Existing confidence is preserved
or lowered; new claims remain self-asserted unless unresolved or declined. A
separate evidence review is still needed to establish stronger corroboration.

External-use permission is separate from the wording choice. New or changed
content stays private by default. **Keep private** can restrict an existing record
while its correction is pending. **Allow this exact content externally** requires
acceptance of that content. Keep-private does not confirm its wording. User review
of a strength also does not change its interpretation status automatically.

The final section asks what is missing, understated, personally important or
unrepresentative. These answers are saved as follow-up notes, never invented
achievements. During conversation, ask one follow-up question at a time. The page
is a self-paced review document, not a demand to answer every prompt.

### Save, resume and apply

Enter your name and download **Save review decisions**. The page attempts to keep
progress in browser storage, but the downloaded file is the portable record. It
can be loaded into the same proposal page on another browser. A changed proposal
cannot reuse the file. Closing the page never accepts anything into the pack.

Move the downloaded decisions JSON into a private workspace folder, then ask the
career tool to record it. The operator must use actual user-supplied decisions;
it must never fill in approvals, publication permissions or answers on the user's
behalf. Conversational decisions may be recorded using the same JSON contract only
after the person explicitly gives them, preserving their explanation in `note`.

```sh
python3 scripts/career_core.py review record --session reviews/pack-reviews/onboarding-v1/session.json --input data/private/onboarding-v1-decisions.json
python3 scripts/career_core.py review status --session reviews/pack-reviews/onboarding-v1/session.json
python3 scripts/career_core.py review accept --session reviews/pack-reviews/onboarding-v1/session.json --output data/packs/career-reviewed-v1.json
```

Here `accept` saves a **local accepted pack version**. `publish` remains a legacy
alias with the same local-only behavior. It uses only explicit accepted items and privacy restrictions. It
retains previous versions and records exact content fingerprints and decision-file
pins. Corrected, uncertain and deferred proposals remain in the private session.
Pending removals preserve the previous record. An initial pack needs enough
accepted items to satisfy its structural and source-reference requirements.

Partial acceptance must remain coherent: approve new/changed supporting sources,
roles and evidence together with claims that depend on them. The tool rejects a
partial result that would silently attach a claim to different support. A factual
correction can make an existing strength stale; reassess that interpretation later
rather than blocking the correction or refreshing fingerprints automatically.

After a partial save, record another user decision batch and save a new accepted
version through the same session. Previously applied choices are not repeated.
If an unrelated pack version becomes current, start a new comparison. Changed
proposals, source support or reviewed content cannot reuse an earlier acceptance.

To correct data, work from the latest accepted version and the pending notes,
record the person's answer with `answer.py`, author a revised candidate and start
a new review. Do not silently apply free-text corrections as facts. Generate a
fresh page after recording decisions to show the durable session state. The JSON
ledger, not browser storage or generated HTML, is the saved review history.

### Apply a downloaded file and resume

```sh
python3 scripts/career_core.py review apply --input data/private/my-decisions.json --output data/packs/career-reviewed-v1.json
python3 scripts/career_core.py review resume
python3 scripts/career_core.py review resume --session reviews/pack-reviews/onboarding-v1/session.json
```

Copy only the file the person supplied into the private workspace if it is outside
it. `apply` resolves the session from that file, records choices, attempts local
acceptance and returns saved counts, pending items, a stopping point and a recall
prompt. A blocked save returns a nonzero exit and `save_blocked`; the decisions
remain saved. Notes-only or repeated batches succeed without creating another
pack. Use a fresh output filename when new content is accepted. Refresh the HTML
with `review render` after applying decisions.

`resume` without a session lists saved reviews and their summaries. It never
chooses approvals or mutates a pack. Use the current conversation to select the
session; ask only when there are multiple plausible unfinished reviews.

### Short conversational handover

Rendering automatically prints a short handover after the page path. To retrieve
it later, use `career_core.py review handover --session <session-path>
--page <rendered-page-path>`. It produces the review link, directly recorded roles
and contributions, saved/pending counts and a stopping point. Use this for the
first-session response instead of adding technical status tables. A recall prompt
appears when an accepted record exists.
