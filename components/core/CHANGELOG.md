# Career Evidence Core release notes

## 0.1.0-alpha.6 — local release candidate

- Preserve scoped questions and exact answers in immutable private history, with deferral and explicit reopening.
- Require documented strength reassessment after support changes; keep ordinary human review.
- Share current-work and question counts, hide completed work, report repair states, and regenerate saved reading views atomically.
- Recover interrupted reviews; keep source annotations separate from approval and preserve date uncertainty.
- Expand fictional source evaluations and PDF/DOCX intake coverage. No accepted pack migration is required.
- Checkpoint large imports, show staging warnings, and reconcile answer-driven corrections across dependent records before handoff.
- Import escaped JSON answers only with their exact question; conflicting saved decisions require explicit resolution.
- Warn when inferred achievement dates extend beyond the linked role without guessing replacement dates.
- Keep keyword-based intake hints separate from inspected classifications so relevant career sources are not silently excluded.
- Stage small record additions and corrections with `review revise --changes`, preserving omitted content and returning changed strengths to proposed review.

## 0.1.0-alpha.5 — local release candidate

- Add `make start` with named continuation of saved setups and reviews; make the two starting paths prominent in onboarding docs.

- Add a resumable conversational wizard, private HTML setup summaries and a tested handoff into the existing workflow.
- Keep five-item review navigation in view and preserve saved progress.
- Add a private career reading page using only recorded pack content, safe links
  and current strength-support states; remove person-specific source extraction.
- Serialize decision recording with pack publication so concurrent operations
  cannot lose decisions.
- Audit startup source and session pins during backup and restore.
- Reject cyclic employment parent relationships before acceptance.

## 0.1.0-alpha.4

Preserve current privacy decisions; require candidate-only strength reassessment and
sourced status transitions. Verify excerpts across all career records before
acceptance. Add connected review and save previews, workspace health, readable
achievement history, reviewed merge/split/refresh, and verified private backup and
restore. Add diverse lifecycle benchmarks and Linux/macOS CI.

## 0.1.0-alpha.3 — local release candidate, 2026-09-11

- Strength refreshes link accepted history, never temporary first-import candidates.

- One-document onboarding, a complete fictional walkthrough, career-first review pages, apply/resume commands and useful stopping-point summaries.

## 0.1.0-alpha.2 — local release candidate, 2026-09-09

- Stage proposed career changes separately from the accepted pack.
- Offline review page presents sources, changes, achievements, strengths and
  direction in batches of five, with portable decisions and omission feedback.
- Explicit acceptance records exact content and preserves corrections and
  deferrals. Wording review, evidence confidence and external permission remain
  separate. Partial acceptance can resume without replaying previous decisions.
- First-time onboarding can inspect candidate question queues before acceptance.

## 0.1.0-alpha.1 — local release candidate, 2026-09-09

- First separately packaged early-access core, with five conversational skills.
- Core validation, strengths, migration, recall and private export run without
  resume selection, rendering or review modules.
- Reads career schema 1.3 and 1.4; current writing schema remains 1.4.
- Preserves evidence IDs, status, disclosure constraints, source references,
  history, strengths and preferences. No existing career data is migrated by installation.
- Six core contract tests cover five fictional personas. A core-only model check
  verifies the first strengths-interview question and pending confirmation.
- Broader real-user onboarding testing remains required before leaving early access.

See `docs/releases.md` for compatibility, installation and release gates.
