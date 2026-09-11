# Resume Application — beta companion

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
See `docs/resume-workflow.md` and `docs/editorial-memory.md` for the full process.

Beta means factual validation and editorial safeguards are tested, while writing
quality still requires review across careers and roles. Integrity, representation,
shortlistability and PDF layout are separate judgments. A passing test suite is
not a hiring-outcome guarantee.

The pack is consumed as ground truth. New factual information returns through
core review and a new pack version; generated wording never updates facts by itself.
Scoped editorial decisions persist separately from disposable documents.
