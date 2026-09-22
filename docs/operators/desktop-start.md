# Desktop first achievement: assistant instructions

Trigger: **Help me start my career notebook.** The person has downloaded the
starter and opened its folder in Claude Desktop's Code tab. Do the technical
work yourself. Ask one short question at a time. They do not need a human helper,
Git, make, the Claude CLI, or a target job for this route.

Keep user-facing messages short and concrete. Do not show schema field names,
evidence-status codes, source IDs, validation counts or tool transcripts. Say
“your own account” and “kept private” instead. Put technical details in the saved
review. Explain a failure only when it changes what the person needs to do.
At the first review, show the role, a short achievement paragraph, any material
uncertainty, and one question. Aim for under 180 words.

## Check the folder and Python

Read the workspace's CLAUDE.md. Confirm this folder contains
`scripts/desktop_setup.py`. If missing, guide the person to extract the starter
and select the inner **My Career** folder containing **START-HERE.html**. Do not
clone another project, create a nested workspace, or touch their other folders.

Locate a working Python 3.9+ interpreter. On macOS, also inspect the standard
python.org installation at `/Library/Frameworks/Python.framework/Versions/Current/bin/python3`
if `python3` is missing or points to Apple's developer-tools stub. Do not launch
that stub merely to install Xcode. If Python is missing, send the person to
https://www.python.org/downloads/macos/ : choose the latest stable Python 3
macOS installer, open the downloaded .pkg, and follow its installer. Ask them
to quit and reopen Claude, select the same folder, and say the trigger again.
No Homebrew or terminal instructions are needed for this recovery. On Linux,
use the installed Python or the distribution's normal software installer.

Native Windows cannot run the current file-locking tools. Say so before intake;
do not claim readiness or silently replace the locking code. A configured
Linux/WSL environment is the technical alternative, not an automatic installation.

Run the working Python interpreter with `scripts/desktop_setup.py --prepare`.
This also restores the text extractor's executable permission if unzipping lost it.
If blocked, explain the returned problem and its recovery in plain language.
Never delete or overwrite an existing career folder to repair installation.
If an application approval appears, explain the actual command and its purpose;
do not ask the person to disable safeguards. A tool permission is not factual
acceptance of their career claims.

After a passing check, run `scripts/career_core.py health --summary --json` using
the same interpreter. Resolve any existing review or pack before proposing new
work. A repeated trigger resumes saved work rather than restarting onboarding.
Do not ask for the same material or decisions again.

## Get one useful account

Follow `docs/operators/first-pack.md` and the `build-career-pack` workflow with
these first-session defaults: one role and one achievement, conversation review,
private by default. Honor a larger scope if the person explicitly requests it.
Skip contact details, strengths, target jobs, PDF export and software for those
optional steps.

If no material was supplied, ask: **Would you like to use a CV, or tell me about
one thing you helped accomplish?** If they choose a document, show the path to
`data/sources` and explain how to copy it there in Finder. If extraction fails,
offer to paste a paragraph or describe the work instead; never present failed
extraction as complete. A typed account can reach the first saved achievement
without PDF tools, a browser server, or an executable shell script.

For a conversation account, ask only missing essentials for that example. Keep
unknown dates and outcomes explicitly uncertain; never supply plausible facts.
Save their exact supplied words as a pinned private `person` source. Their
account is evidence, not approval of wording you have not yet shown.

## Review, save, retrieve

Use the existing candidate validation and review commands. Show the exact role
and achievement wording in everyday language, naming who did what and what
changed. Ask for factual acceptance or correction. Keep external use private;
the person need not decide publication permissions before this first save.
Show any correction again before accepting it. Apply only the person's actual
decisions through the review system. Never write accepted packs directly.

After acceptance, run the saved reading view and a fresh health summary. Read
the accepted pack from disk, locate the accepted achievement and its pinned
source, and verify the excerpt. Show the person the saved wording, the original
source, and a link to `outputs/career-record.html`. If no achievement was saved,
state what is pending and continue resolving the actual blocker. A proposal,
chat response, or downloaded decision file is not a saved achievement.

Save a short `outputs/CONTINUE.txt` handoff naming the workspace, saved reading
page, and any pending review's continuation prompt. It must reflect actual
state. Give this returning prompt: **Show my saved career record and help me
continue where I left off.** Explain that they should choose this same folder
next time, rather than downloading another starter.

Success means the person reviewed a fact, a version was saved, and a separate
read retrieved that fact with its source. Offer a backup after that milestone.
Do not claim a complete career, a finished CV, or a verified Desktop UI merely
because the Python checks pass.
