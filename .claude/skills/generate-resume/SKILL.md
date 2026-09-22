---
name: generate-resume
description: "Draft a resume from an existing approved career pack and ready resume plan. Normally called by make-resume, which also performs review and PDF/TXT/DOCX/Markdown delivery."
---

# Generate a resume

Read `docs/resume-authoring.md` for the versioned policy, planning, safe views,
writing decisions, voice preferences and revision checks. Follow `make-resume`
for durable context even when generation is requested directly. Direct generation
creates a draft, not an approval or a claim of successful export.

For employers with several positions, follow `docs/resume-employment.md` and the
safe view's derived employer groups. Default to one employer heading, compact
dated position rows and explicitly scoped achievements. Preserve the visual
hierarchy in every export; repeated employer headings and empty role sections
make progression difficult to understand.

Consume `resume_workflow.py view --plan <path>` for a current ready plan. Draft
experience first, preserving contribution, context, chronology, ownership and
constraints. Explain unfamiliar work only from approved facts. Retain distinctive
and relevant older evidence. Use the summary only if it adds understanding, and
write it last. Check for repeated projects/results and unsupported additions
introduced by transitions or compression. Follow saved safe wording preferences
without treating preferred examples as factual evidence.

Use the Markdown structure and inline evidence-comment placement in `make-resume`.
Keep public links accurate, employment titles literal, contact appropriate to the
application and internal warnings outside the artifact. New factual answers return
to Core review. Run `evaluate-output` before calling any artifact publishable;
resume delivery additionally requires verified PDF, TXT, DOCX and Markdown exports.

Before drafting, use the privacy comparison and intended-prominence checks in
`docs/resume-process.md`. An empty `strength_ids` list does not exempt an impression
from restrictions. Keep cross-role work in an explicitly company-wide section;
a particular title does not own the entire employer tenure. Generation is followed
by a pending per-claim process checklist, never automatic approval.

## Editorial quality

Use the opening, focus, contribution, language and metric-value questions in
`docs/resume-quality.md` while drafting. Inspect eligible alternatives before
concluding that a capability lacks evidence. The delivery workflow records these
judgments and consequential omissions in the version 2 process review, followed
by review of the exact exported PDF. A draft alone does not establish completion.
