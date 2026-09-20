# Maintain and move your career record

You can ask the assistant to check your career workspace, explain an achievement's
history, combine duplicate achievements, split a large achievement, attach a new
source, or back up your work. These are core features; no resume add-on is needed.

## Create a separate personal workspace

Keep tool development and your career history in separate directories. From the
application checkout (or an installed Core release), run:

```sh
python3 scripts/career_core.py workspace create --directory ~/Career/my-career
cd ~/Career/my-career
make start
```

This installs only public Core files and creates empty private data directories.
It never copies the developer checkout's sources, packs or reviews. Add
`--with-resume` if you also want the matching installed Resume component.
The destination must be new and outside the tool directory; existing workspaces
are never overwritten. This is a new workspace installer, not an upgrade command.

The workspace includes the runtime it needs, so it does not depend on editing the
development checkout or patching source paths. Component versions and file hashes
are recorded under `components/workspace/installation.json`.

Save career material inside this workspace. Local saves are not GitHub backups.
Configure a separate **private** repository if you want centralized Git backup;
the installer does not create a remote or publish files. The inherited `.gitignore`
protects personal folders by default, so Git needs a deliberate private-data
tracking policy before it can back them up. The backup command below already
includes pending reviews and sources without changing that policy.

## Review connected information

On an achievement card, expand **Role and sources for this achievement** to inspect
the exact supporting records. **Show achievement and role together**
shows their existing decision controls together. No career claim is automatically accepted; verifiable source metadata is registered separately. Existing supporting records whose content and dependencies are unchanged can be reused; a legacy role does not need reapproval merely because an achievement is clarified.
**Preview what will be saved** explains your wording and external-use choices and
identifies supporting items that may still need review. The browser preview is a
planning aid; the CLI checks the exact resulting pack and sources before saving.

The assistant can preview downloaded decisions without recording or accepting them:

```sh
python3 scripts/career_core.py review preview --session reviews/pack-reviews/onboarding/session.json --input data/private/decisions.json
```

An unchanged external-use choice preserves the **latest saved permission**. It
never restores permission from an older review baseline. A known source-excerpt
mismatch blocks acceptance. Unavailable sources are reported separately; absence
of independent corroboration does not make a self-asserted claim invalid.

## Resolve an evidence question

Wording acceptance does not increase confidence. After recording the person's
answer as a source and proposing the clarified claim, the person can explicitly
select **Evidence reassessment** and explain why the attached sources justify the
proposed status. The decision must accept the wording and name the proposed status.
Resolving to `self_asserted` needs a verifiable person-answer excerpt and no remaining
open questions. Stronger corroboration needs independently supporting source
material with verifiable excerpts. Missing sources never silently grant a promotion.

Operator decision records can include this optional field on an accepted item:

```json
{"reassessment": {"status": "self_asserted", "reason": "My recorded answer clarifies my ownership", "source_refs": [{"source_id": "SRC_ANSWER", "excerpt": "The exact recorded answer"}]}}
```

This is a shape example, not an approval. Use the actual person's explanation and
excerpts already attached to the proposal. Status reassessment and permission for
external use remain separate decisions. Strength reassessment always produces a
candidate; use the normal review checkpoint before making it current.

## Workspace health

```sh
python3 scripts/career_core.py health
python3 scripts/career_core.py health --json
python3 scripts/career_core.py health --output outputs/health.txt
```

Health separates integrity problems from useful follow-ups. It checks the current
pack, source references, review-session pins, stored input hashes, questions,
strength support and timeline coverage. A nonzero exit indicates integrity problems.
There is no completeness score. Periods without recorded work may be intentional,
and a useful first pack can contain only a few achievements.

## Read an achievement's history

```sh
python3 scripts/career_core.py history E_PROJECT
python3 scripts/career_core.py history E_PROJECT --output outputs/project-history.html
```

The private page shows previous and current wording, sources and answers, acceptance
attribution, privacy changes, maintenance relationships, dependent strengths and
saved application inputs. Historical versions and citations remain intact. An old
selection is still pinned to its original inputs; regeneration must use a current
selection. Existing records without human-review receipts remain labelled as such.

## Merge, split or refresh

The assistant prepares a JSON file with `atoms` containing the exact proposed
replacement records and optional `source_records` for new supporting material.
The supplied wording must come from existing sources or the person's actual answer.
The tool does not automatically combine prose or reassign a strength's meaning.

```sh
python3 scripts/career_core.py maintain merge --from E_ACCOUNT_A E_ACCOUNT_B --input data/private/replacements.json --reason 'Two accounts of the same project' --output data/candidates/merged.json
python3 scripts/career_core.py maintain split --from E_LARGE_PROJECT --input data/private/parts.json --reason 'Distinct contributions within one project' --output data/candidates/split.json
python3 scripts/career_core.py maintain refresh --from E_PROJECT --input data/private/refreshed.json --reason 'Attach my clarified account and source' --output data/candidates/refreshed.json
```

Merge creates one new ID from multiple originals; split creates multiple new IDs
from one original. Original records remain in the pack as declined, private history
once the change is accepted. Refresh preserves the original ID. Replacement content
starts private. New source versions use new source IDs. Sources and historical
versions are never overwritten.

Maintenance records live in `metadata.evidence_maintenance`. Review the originals,
replacements and maintenance explanation together; partial acceptance cannot publish
only half of a replacement. The preview explains other source dependencies.
Dependent strengths remain attached to their historical support and require explicit
reassessment. `history` follows the replacement relationships; no old citation is
silently redirected to different wording.

## Portable private backup and restore

Resume plan and startup-session references are audited alongside selections and
career inputs, including selected source hashes and earlier session revisions.
Missing files and changed immutable references block backup and restore. A changed
authoring policy is reported as a warning for historical plans, so a policy upgrade
does not prevent preserving history. A missing policy still blocks the archive;
the warning does not make an old plan current or usable for generation.

```sh
python3 scripts/career_core.py backup --output backups/career.zip
python3 scripts/career_core.py restore --input backups/career.zip --destination ../career-restored
```

The archive includes `data/`, `reviews/`, `outputs/`, the installed runtime and
public documentation, and `CAREER-OVERVIEW.html`. It preserves pending decisions,
pack history, source files, paused wizard sessions and application inputs. It excludes Git metadata,
other backups and caches. Archives contain private material and are not encrypted;
store them with the same care as your original documents. Files are restricted to
the local user on creation/restoration.

Every archived file has a SHA-256 inventory entry. Restore verifies those hashes,
local source and decision references and the current pack before publishing a new
workspace. It refuses existing destinations, symlinks, unsafe archive paths,
duplicate entries and oversized archives (100,000 files or 2 GiB uncompressed).
It never executes code from the archive during verification. Checksums detect
corruption; they do not authenticate an archive from another person.

Broken or absolute local references must be repaired before backup so the archive
can be moved. Remote sources without saved copies are listed as unavailable, not
claimed to be embedded. Backup/restore preserves existing content and does not
approve proposals, repair factual claims or certify resume quality. On a new machine,
open the restored directory with your assistant and continue the saved review.

## Recorded questions and read-only progress

Backups include immutable `reviews/questions/` revisions and their pinned context.
Legacy packs and answer logs stay unchanged. See [questions and updates](questions-and-updates.md)
for previewable, idempotent answer import and semantic strength reassessment.
Use `career_core.py health --summary --json` for navigation; full `health` also
checks sources and backup references. `start.py --history` includes completed work.
