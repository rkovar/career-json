# Career Evidence Core

**Keep your career information current, one conversation at a time.**

Start with a resume or describe your work. The assistant organizes your roles,
achievements and sources into a career pack you can read, review and reuse.
Add notes or documents as your work changes.

## Start here

Unzip the Core archive into a new directory. You need Claude Code installed and
configured, Python 3.9+, `make`, and macOS or Linux.

From that directory, run:

```sh
make start
```

Choose **Build my career pack** and answer in the Claude Code conversation that
opens. One old resume is enough. You can review a few useful achievements, save
them, and leave the rest for later.

Follow [Your first session](docs/getting-started.md) for source setup, review and
saving. [Preview Jules's fictional example](examples/first-pack/README.md) if you
want to see the result first.

## Keep it current

Tell the assistant “Remember that I…” to save a quick note. When convenient,
ask it to review your recent notes and update the pack. Proposed changes enter
your reviewed record after you check them.

Once a pack exists, **Update my career pack** handles new notes and documents.
Review roles once, then achievements in batches of five. The connected review
saves directly to the local pack; corrections are previewed before confirmation.
Sources are registered separately from factual approval. Private content and
optional strengths questions never prevent a useful first save.

Developing the tool too? [Create a separate personal workspace](docs/workspace-maintenance.md#create-a-separate-personal-workspace).

Choose **View my saved career record** to read what you have saved. Use
**Continue saved work** to return to active setups and reviews. Answers,
corrections and deferrals remain available when you return.
See [Keep your career pack current](docs/keep-current.md) for examples.

Resume generation is optional. Installing the matching add-on makes **Create a
resume** available in the same launcher. [Release instructions](docs/releases.md)
cover that installation.

## Privacy and status

Core is early access. Your files stay in your workspace, but material you ask
Claude to read is processed by your configured model service. Private records
are excluded from normal source commits and public release archives.
Keep readable reviews, exports and backups private.

[All Core guides and technical references](docs/README.md). MIT licensed; see LICENSE.
