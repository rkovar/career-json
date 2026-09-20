# Development and validation

Use fictional fixtures for code changes. Personal career packs, source documents,
review decisions and generated outputs belong in ignored private directories.
Do not copy real material into tests or examples.

## Routine checks

The optional public website has a separate build and checks. See
[website development and publishing](website.md); its Node.js dependency is not
required for the career tools or their tests.

```sh
make test
make check
make hooks
```

`make test` runs deterministic regression tests, fictional lifecycle journeys and
clean component installations. It makes no model calls. `make check` first audits
the local workspace's packs, application records and source excerpts, then runs
those tests. On a clean checkout the local-data checks have nothing to inspect.

Core must also work without the Resume Application. `make test-releases` builds
isolated installations from the explicit component allowlists and exercises that
boundary. Add public runtime files and their tests to the owning component
manifest; adding a file to the repository alone does not ship it.

## What a commit checks

`make hooks` configures `.githooks/pre-commit`. The hook runs
`scripts/check_staged.py`, which:

1. Rejects tracked private paths, apart from exact, empty directory placeholders.
2. Copies the Git index to a temporary directory, preserving staged bytes and
   executable modes. Unstaged fixes cannot conceal broken staged code.
3. Clears workspace/Git overrides and runs `make check` in that directory.
4. Removes the temporary workspace after the check.

This tests the source being committed against fictional data. It does not certify
your existing resumes. Run `make records` and the relevant artifact checks in your
actual workspace when preparing a delivery.

Old private reviews can legitimately become stale after a policy, skill or source
change. Keep their original pins and approval history. Prepare new plans and
reviews for a new delivery; do not rewrite an old approval or relax publication
checks just to make a source commit pass.

## Browser and export tests

The launcher can be inspected without opening a model session:

```sh
python3 scripts/start.py --flow career --print-prompt
python3 scripts/start.py --flow update --print-prompt
python3 scripts/start.py --flow resume --print-prompt
python3 scripts/start.py --flow continue --print-prompt
```

The resume path needs the matching add-on; continuation needs saved work.
`make start` opens the interactive Claude CLI only from a terminal. Piped input
and an existing Claude Code conversation receive copyable prompts instead.
If the CLI is missing, the selected prompt remains available. Launcher tests use
a fake executable to check arguments, workspace and exit status without a model call.

Normal tests cover parsers, content equivalence, failure handling, link matching,
review navigation structure, input staleness, privacy and publication rules.
Normal tests also run temporary loopback HTTP checks for direct saving, corrected
previews, stale writes and origin/token rejection. They need permission to bind
a local socket. Creation tests cover partial packs, source registration, carried
approvals, repeated saves, intake scope and clean workspace installation.
Real PDF/browser checks are optional because they need installed external tools.

With Chrome/Chromium and Poppler or macOS Swift/PDFKit available:

```sh
CAREER_TEST_REAL_PDF=1 python3 tests/test_pdf_links.py
CAREER_TEST_REAL_PDF=1 python3 tests/test_employer_layout.py
```

For interactive review navigation, with Node.js providing built-in WebSocket:

```sh
node tests/test_review_navigation.mjs
```

Set `CAREER_BROWSER` if Chrome is installed elsewhere. The browser test covers both the 80-question offline page and actual connected
saves, corrections and reload recovery. These checks use temporary
fictional workspaces and an isolated browser profile. They do not open the user's
career files. Rendering and text/link extraction still do not establish good prose
or universal ATS compatibility; inspect the final document and record any judgment.

## Model and reader evaluations

See [quality benchmarks](quality-benchmarks.md) and
[resume quality](resume-quality.md). Model scenarios call the configured Claude
CLI and consume tokens; they are separate from the automatic test suite.

The fictional resume corpus can be prepared without calling a model:

```sh
python3 tests/run_resume_quality.py prepare --output /tmp/career-quality-review
```

Run each case through the actual authoring workflow, retain its outputs and record
reader observations before checking the suite. Leave unobserved quality measures
empty. Deterministic consistency, model judgments, actual reader observations and
hiring outcomes are different kinds of evidence.

## Source guidance and privacy

`docs/policies/resume-authoring.json` is the versioned, distributable authoring
policy. Local research inputs in `resume_information/` are ignored and do not ship.
Update the distilled policy deliberately; changing its bytes makes earlier pinned
plans stale.

`data/`, `reviews/`, `outputs/`, `backups/` and local archive directories must remain
outside source commits. Public release archives use explicit allowlists; private
workspace backups use a separate format and contain personal material.

Source-to-pack checks and bounded live runs are documented in
[quality benchmarks](quality-benchmarks.md#source-to-pack-preservation).
`make check` includes evaluator calibration using fictional sources and deliberate
factual errors. Live model runs remain opt-in; do not report deterministic tests
as proof of extraction quality. Review UI regressions also exercise multi-card
wording edits and require a fresh confirmation before accepting revised text.
