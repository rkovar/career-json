# Create a resume

In Claude Code, with your career folder open, say **“Walk me through the resume
wizard.”** This works with the CLI or the Desktop Code tab's Local environment.
For the terminal launcher, run `make start` and choose **Create a resume**.
The [first-session guide](getting-started.md) covers shared installation.

## Bring a target, or explore one

You can supply a job description, name a type of role, or ask for help exploring
directions supported by your experience. Tell the assistant what you want the
reader to remember and which achievements feel important.

If you do not have a career pack yet, your target and preferences are saved while
the assistant helps you build and review one. You do not need to start the resume
setup again afterwards.

## Choose how much to review

You can ask:

> Show me the ranked achievements and explain why you would include them.

The assistant presents relevant examples, alternatives and gaps. You can change
the selection, explain what deserves more emphasis, or ask for automatic drafting
and review. New factual information goes through career-pack review; a preference
about emphasis does not create a new career fact.

Share any employer instructions, page limit or contact-detail requirements.
If you do not know an answer yet, say “later” or ask for guidance.

## Read the result

The assistant prepares **PDF, TXT, DOCX and Markdown** and provides review findings alongside
the documents. Read the final wording and check whether it represents your
contribution well. Missing evidence or incomplete exports are reported.

PDF export needs Chrome/Chromium and a PDF extractor. See
[export setup and verification](resume-exports.md) for prerequisites.
Send the file format the employer requests from the export bundle's `files/`
directory. The workflow creates four formats so you can choose; you do not need
to submit all four. Its `resume.md` is clean resume content. Your full
`outputs/career.md`, the cited draft and the `review/` directory are private
working material. [File-by-file guide](files-and-exports.md)

If PDF prerequisites or checks fail, the export is incomplete even if Markdown,
TXT and DOCX succeeded. The assistant should identify the failed format and keep
the successful files. Fix the cause and export into a new directory. Do not edit
an export and assume its previous verification still applies.

## Pause, return or retarget

Say “pause” to save a stopping point. Your summary explains what is saved and
includes a prompt for continuing the same setup. You can also choose
**Continue saved work** in `make start`.

For another application, describe the new target. Your reviewed career record
remains available; the assistant checks which previous preferences still apply.

The resume workflow is beta. Its checks and reader assessments help identify
problems but cannot predict hiring decisions. For technical details, see the
[resume reference index](resume-reference.md).
