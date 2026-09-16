# Resume Application — beta companion

## Start here

Run `make start` from your combined workspace and choose **Create a resume**.
The launcher opens Claude Code with the [resume wizard](../../docs/resume-start.md).
Already in the conversation? Say **“Walk me through the resume wizard.”**

The wizard records your target, qualities, examples and constraints, then hands
the brief to selection and planning. If you need a career pack first, your target
is saved while you build one. Choose **Continue saved work** to return to a named
setup; its summary includes a prompt for continuing.

Turn a Career Evidence Core pack into a targeted resume, biography, cover letter
or private interview brief. Selection, tailoring, representation review, integrity
review, rendering and the cold recruiter screen belong to this component.

This add-on requires the exact core version declared in `component.json`. It
shares that workspace and reads career schema 1.3 or 1.4. It does not include or
replace the core's factual records. Install the core archive first, then unpack
this add-on at the same root. Its file paths are disjoint from the core archive;
it supplies no `data/`, `reviews/` or `outputs/` content. Test a fresh installation
before upgrading an existing workspace; do not blindly overwrite local code.

```sh
make -f Makefile.resume check
```

Open the workspace in Claude Code and ask: `Use make-resume for this job description`.
See `docs/resume-authoring.md` for planning, optional selection review, voice
preferences and revision checks. `docs/resume-exports.md` describes required PDF,
TXT and DOCX delivery. `docs/editorial-memory.md` explains durable decisions.

Beta means factual validation and editorial safeguards are tested, while writing
quality still requires review across careers and roles. Integrity, representation,
shortlistability and PDF layout are separate judgments. A passing test suite is
not a hiring-outcome guarantee.

The pack is consumed as ground truth. New factual information returns through
core review and a new pack version; generated wording never updates facts by itself.
Scoped editorial decisions persist separately from disposable documents.

Resume export uses a shared document to preserve content across PDF, UTF-8 TXT
and editable DOCX. TXT/DOCX need standard-library Python; PDF additionally needs
Chrome/Chromium plus Poppler or macOS Swift/PDFKit for verification. Missing tools
are reported as incomplete delivery, never successful verification. No model
calls are made by deterministic checks or export scripts.

The [process review](../../docs/resume-process.md) preserves per-claim checks,
reader prominence, privacy comparisons, compression attempts and revision history.
Use `resume_process.py handoff` to generate continuation notes from validated
records. Existing reviews are retained and are not automatically upgraded.
