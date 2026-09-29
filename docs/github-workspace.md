# Save your career to GitHub

A GitHub career workspace is a private, self-contained repository containing your
career records, sources, captured notes, pending reviews and generated documents.
Its README links to `CAREER.md`, a complete Markdown copy of the accepted pack.
Saving to GitHub does not approve pending claims or grant external-use permission.

Choose **Save my career to GitHub** in `make start`, or ask your assistant to
“Save my career workspace to a private GitHub repository.” The assistant should
use these commands and show the destination and inventory before the first sync.
An existing request to upload to a named private repository supplies that authorization.

## Prepare a workspace

You need Python 3.9+, Git, and GitHub CLI (`gh`). Authenticate with `gh auth login`
before connecting or syncing. Local preparation works without GitHub access.

From your existing workspace, replace the example destination and repository:

```sh
python3 scripts/career_core.py github prepare --directory ../my-career --repo OWNER/my-career
cd ../my-career
python3 scripts/career_core.py github preview
```

Preparation creates a new directory and a fresh Git history. It copies the
portable workspace, checks source/history references, creates personal Git rules,
and generates `README.md`, `CAREER.md` and the browser view. It uploads nothing.
The destination must be outside the source workspace and must not already exist.
A workspace without an accepted pack can still preserve notes and pending reviews.

**Continue career work in the new directory.** Keep the original as a recovery
copy; changes made there later are not synchronized into the new workspace.

The preview lists files eligible for upload. Included folders are `data/`,
`reviews/`, `outputs/`, and the installed runtime, schemas, skills and documentation.
Backups, caches, common credential filenames and local Claude settings are excluded.
Other personal files must be imported into `data/sources/` first. This is a file
tracking policy, not a general secret scanner; review the inventory.

## Connect and save

Create a private repository:

```sh
python3 scripts/career_core.py github connect --create
make sync
```

If you already created an **empty private repository** with the configured name,
use `github connect` without `--create`. Connection verifies the destination but
uploads nothing. A populated compatible career repository should be cloned using
the instructions below; connecting does not overwrite or merge existing history.

Sync checks the private destination, fetches remote history, validates career
records and source references, refreshes the generated views, and commits and
pushes changes. This includes pending notes and reviews. Every staged source and
reference is checked in isolation. Large files (100 MiB or more), symlinks,
submodules and excluded tracked files block the commit with an explanation.

`CAREER.md` is generated from the same accepted record as `outputs/career.md`.
It includes restricted information and contact details. Edit facts through career
review; changes to the generated Markdown do not update the JSON record.
GitHub renders Markdown; open `outputs/career-record.html` locally for its browser view.

## Daily use and another machine

| Command | Result |
| --- | --- |
| `make start` | Continue the career or resume workflow; show last fetched Git status |
| `make status` | Fetch and report local changes, pending commits or remote changes |
| `make sync` | Validate, refresh, commit and push the private workspace |
| `make pull` | Fetch and fast-forward a clean workspace |
| `make check` | Check career records and source/history integrity |
| `make overview` | Refresh the complete Markdown record and browser view |
| `make hooks` | Reinstall local Git protections after an ordinary Git clone |

Offline status is available with `python3 scripts/career_core.py github status`.
It explicitly reports that remote information comes from the last fetch.
If a push fails, the local commit remains available for a later `make sync`.
Nothing automatically uploads after a career save.

From a current installation of the tool on another machine:

```sh
python3 scripts/career_core.py github clone --repo OWNER/my-career --directory ../my-career
cd ../my-career
make start
```

Clone requires a compatible workspace produced by this feature and a new local
directory. It verifies the private destination and references, and installs hooks.
Only clone a workspace whose installed code you trust. An ordinary `gh repo clone`
also works; run `make hooks` and `make check` afterwards.

If GitHub contains changes missing locally, sync stops before making a commit.
Pull when your working tree is clean. If both machines have independent commits,
preserve both and reconcile the career records through review. The tool never
automatically resolves conflicting career facts or force-pushes.

## Recovery and tool versions

Use the existing [portable backup and restore](workspace-maintenance.md#portable-private-backup-and-restore)
commands for an offline ZIP. They preserve the GitHub configuration, readable
record and Git rules, but not Git history. After restoring to a new directory,
initialize Git on `main`; a populated remote should be cloned separately before
deliberately reconciling uncommitted restored files.

Installed component versions and the initial runtime hashes are recorded in
`components/workspace/github.json`. The generated `README.md`, `Makefile`, and
`.gitignore` have their own workspace hashes; original release inventories remain
intact. Desktop checks use those generated hashes for the three workspace files
and the original release hashes for application code, so a prepared or cloned
workspace can still pass setup without exempting scripts from integrity checks.
Tool upgrades are a
separate operation: back up first, test the replacement runtime in a copy, retain
career files and review history, and preserve `README.md`, `Makefile`, Git rules
and `components/workspace/github.json`. This release does not provide automatic
tool upgrades or migration of custom private-repository helpers.

Keep this repository private. Public portfolio publishing is a separate,
selected output; GitHub workspace sync never changes repository visibility.
