---
name: review-strengths
description: "Use during onboarding, when the person wants to clarify their strengths or direction, or when changed evidence makes a saved interpretation stale. Conducts a resumable interview; does not generate a resume."
---

# Review career strengths

Read `docs/core-workflow.md` for record contracts and commands. Start with
`scripts/career_core.py status` and the current pack, including existing answers.
During onboarding, use `status --pack <candidate-path>` and the staged proposal
when it contains the pending evidence or no accepted pack exists yet. Keep all
interview changes in a new candidate until its wording is explicitly accepted.

After evidence intake, propose a small set of interpretations from achievements.
Each strength needs supporting atom IDs, their fingerprints, a timeframe,
limitations, and `basis: single_achievement` or `recurring_pattern`. Proposals
are interpretations, never new evidence. Keep `external_safe: false` until their
wording has been reviewed against the disclosure constraints of every support.
Do not force a recurring narrative onto someone with one significant achievement.

Ask one question and wait. Explain the examples behind the interpretation, invite
correction, and allow a genuine null answer. Explore missing contribution,
contradictory examples, overlooked work, and what the person wants next without
coaching toward a job-fit score. Historical strengths and future direction are
separate. Do not require an interview to use an otherwise usable pack.

Keep each turn to one answerable issue. First validate the interpretation; save
ownership follow-ups about individual examples for subsequent turns. Appending
two ownership questions to the first question is still a batch, even when it is
presented as one paragraph.

Record each answer immediately with `scripts/answer.py --subject <strength-or-preference-id>`.
Create its person source in the pack and cite the recorded excerpt. Route new
achievements and ownership corrections through `review-evidence`; preferences
belong in `positioning_preferences`; publication restrictions belong on the
underlying evidence. A confirmed interpretation never promotes evidence status.

Persist proposed questions in `review_question` and `question_status`. Answers
close questions; declined questions stay closed. Preserve rejected interpretations
so a future session does not re-propose them. Resume from `career_core.py status`,
revisiting only materially changed support or an explicitly changed direction.

Write a new candidate pack, not an in-place update. Use `docs/pack-review.md`
to present and accept the exact interpretation and preference wording. The
readable page shows support, limitations and future intent separately. Use `bind-strength` only after
actually reassessing the named interpretation: it refreshes fingerprints, not
truth or approval. Never bulk-refresh hashes to dismiss stale findings. Validate
the candidate before review and the accepted version’s supersedes chain after
explicit user decisions. Report remaining questions
and readiness without turning completion of this interview into a prerequisite.
