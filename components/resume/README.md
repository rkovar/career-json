# Resume Application

**Turn your reviewed career record into a resume for the next opportunity.**

This optional beta add-on uses the Career Evidence Core pack. If you cloned the
full repository, both workflows are already included. For an archive installation,
follow [release instructions](../../docs/releases.md) to add the matching version
to your Core workspace.

## Start here

With your career folder open in Claude Code, including Desktop's Code → Local,
ask “Walk me through the resume wizard.” For the terminal launcher, run from the
shared project directory:

```sh
make start
```

Choose **Create a resume**. The launcher opens Claude Code with the resume wizard.
Bring a job description, name a type of role, or ask for help choosing a direction.

You can review ranked achievements and their selection reasons before writing.
The assistant keeps your preferences, prepares PDF, TXT, DOCX and Markdown, and reports
remaining work. The clean `files/resume.md` is selected resume content; the full
private `outputs/career.md` is a separate record. Send the format the employer
requests, rather than the entire export directory. If your career pack needs
building first, the target is saved while you do that.

Follow [Create a resume](../../docs/resume-start.md) for the complete user guide,
including PDF prerequisites. Use **Continue saved work** in the launcher to return
to a named setup.

## Your record remains reusable

New facts and corrections go through career-pack review. Resume wording does not
automatically change your history. Later applications can reuse the same reviewed
record and applicable preferences.

The workflow is beta. Read the final documents and review findings; automated
checks do not predict hiring outcomes. Working drafts, reviews and setup records
contain private information.

For planning, validation, export commands and component contracts, see the
[resume technical reference](../../docs/resume-reference.md).
