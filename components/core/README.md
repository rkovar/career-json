# Career Evidence Core — early access

Own a durable, traceable record of your career. Capture work, import sources,
review evidence, describe supported strengths, record future direction and export
the full private pack. Resume generation is an optional, separately versioned
application.

Requires Python 3.9+, `make`, and macOS or Linux. Conversational onboarding uses
Claude Code and its configured model. PDF intake uses poppler or macOS PDFKit.
No Python dependencies are installed.

[Preview a complete fictional first pack](examples/first-pack/README.md) before installing.

Unzip the core archive into a new directory and open that directory in Claude Code.

```sh
make check
mkdir -p data/sources
```

Add one resume, then ask: **Build my first career pack from data/sources/my-resume.pdf.
Keep it private and show me the overview before asking questions.**
Follow `docs/first-session.md`; the assistant handles review commands and saved sessions.
Open the private review page produced by onboarding; inspect the proposed data,
record your choices and save accepted items as described in `docs/pack-review.md`.
Continue with `review-evidence` and, if useful, `review-strengths`. A skipped
interview or unresolved claim does not prevent a useful pack.

```sh
make coverage
make strengths
python3 scripts/career_core.py export --output data/private/career-export.json
```

See `docs/core-workflow.md`, `docs/data-model.md`, and `docs/releases.md`. Schema versions 1.3 and 1.4 are supported;
component versions are independent of the schema version.

Early access means onboarding is still being tested across different careers.
Passing validation does not establish completeness or excellent resume writing.
The export is private; it includes withheld evidence and contacts. Local private
folders are excluded from release archives. Material read during a Claude session
is processed under your configured Claude service; Git ignore rules are not a
network privacy guarantee.

To add resume generation, use the matching Resume Application add-on as described
in its release instructions. MIT licensed; see LICENSE.
