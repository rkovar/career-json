# Start here if you're not technical

You can use career.json by talking about your work in ordinary language. Download
your career folder, open it in Claude, and let Claude handle the tools. Your job
is to read what it proposes and tell it what is accurate.

Your first goal is small: **save one achievement, then find it again.** Bring one
old CV or resume. If you have neither, you can describe something you did.

## Think of it as a career notebook

Imagine writing down the useful details of your working life in a notebook:
what happened, what you did, who helped, and what changed.

When you apply for a job, you choose the pages that matter for that job. When
you prepare for an interview, you find a story that answers the question.

career.json helps you keep that notebook. It calls the saved collection your
**career pack**. Claude helps organize it and find things in it. You check the
facts. A CV is one document you can make from the collection.

The “JSON” in the name is the format the computer uses to store the information.
You can read your record on a normal reading page without learning that format.

Want to see one first? [Explore Jules's fictional career](../examples/first-pack/index.html).
The example uses invented information and needs no installation.

## What you need

Use a **Mac**, **Claude Desktop**, and a paid Claude plan that includes **Code**.
The app includes Code; [Anthropic's instructions](https://code.claude.com/docs/en/desktop-quickstart)
explain access. Have your computer connected to the internet.

The career tools also need Python 3.9 or newer, a small program that runs their
instructions. Claude will check whether it is installed and guide you if it is
missing. You do not need to learn Python, install Git, or type terminal commands
for this starter route. Claude usage counts toward your plan's limits.

**Windows:** the current career tools do not support native Windows. This guide
is a Mac route. Linux with Python and Claude Code can use the same download;
WSL needs its own technical configuration and is not the guided starter route.

## 1. Download, open, and send one message

This website contains instructions and examples. Your personal record lives in
a folder on your computer, where Claude can save it.

1. [Get the career starter from the Get Started page](https://career-json.com/start/#download).
   It is a ZIP file: a folder packed into one download.
2. Double-click the ZIP if your Mac has not already opened it. Move the extracted
   **My Career** folder into Documents, or somewhere else you can find again.
   Keep the whole folder together. If you already have a career folder, reopen
   that one instead of replacing it with a new download.
3. Inside it, double-click **START-HERE.html**. It opens a short set of instructions
   in your browser. You can return to those instructions any time.
4. Open Claude Desktop. Select **Code**, choose **Local**, then **Select folder**.
   Choose **My Career**, the folder containing START-HERE.html.
5. Send this message:

> Help me start my career notebook.

Although the tab is called Code, your conversation is about your career. Claude
checks the folder and required software, then helps you start. When the app asks
for permission, Claude can explain what it needs to do and why.

You can use a CV or simply describe something you did. For a CV, Claude will
show you where to put a copy. If you would rather talk, say:

> Ask me about one thing I helped accomplish. Ask one question at a time.

You can say “I don't remember,” “skip that,” or “let's do that later.” You do not
need to prepare your whole career history before starting.

## 2. Make one example accurate

Suppose you say:

> Our team kept answering the same customer questions. I wrote a guide and
> showed two new colleagues how to use it.

Claude might propose:

> Led a customer-service transformation that improved team productivity.

That sounds impressive, but it adds things you never said. Did you lead the
whole change? Was productivity measured? A useful record keeps the details you
can stand behind.

You could reply:

> That's too strong. I wrote the guide and trained two colleagues. My manager
> led the wider project. We didn't measure the time saved. Please show me the
> corrected wording.

Read the revision. Check three things: **what you did, who else contributed,
and what actually happened.** If a detail is missing, add it. Your own account
can be recorded as the source; you do not need a certificate for every useful
piece of work.

Now consider two separate choices:

- **Is it accurate?** This decides whether it belongs in your accepted record.
- **May it be used externally?** This decides whether it may appear in a CV or
  another document you share.

An accurate detail might still be private. For example, you could say:

> This wording is accurate. Save it in my record, but keep it private for now.

New or changed information stays private unless you allow external use. You can
review that choice later.

## 3. Check that it was saved

A sentence in a conversation is only a sentence in a conversation. Ask Claude
to show you the saved result:

> Show me my saved career record. Find the achievement we just reviewed and
> show me its original source.

Check that the corrected wording appears. The source might be your CV, a project
note, or the answer you just gave.

Claude can give you a reading page and a Markdown file called `career.md` in
`outputs`. Markdown is a text format you can read in an editor. This copy contains
your full saved record, including private details. Keep it for yourself; a CV uses
a separate, clean export. Editing the copy does not update your saved record.
[Your files and exports](files-and-exports.md) explains the difference.

If Claude opens a browser review, you can review there. You can also ask to give
your decisions in the conversation. If a page asks you to **download decisions**,
tell Claude where you saved that file and ask it to apply them. Downloading the
file alone does not update your record.

Try explaining what happened in your own words: “I supplied an example, checked
the wording, chose whether it could be shared, and found the saved version.”
That is the whole first exercise. You can stop there.

## 4. Come back when you have something useful

Before stopping, say:

> Pause here. Save our progress and tell me how to continue next time.

Next time, open the same folder in Code and use the continuation instructions.
The folder holds the saved record. You do not have to trust Claude to remember
every previous conversation.

Here are a few requests to try as you build it:

| When you want to… | Say… |
| --- | --- |
| Capture something fresh | “Remember that I helped train two new colleagues this week.” |
| Review those notes | “Review my recent notes with me and update my career pack.” |
| Prepare for an interview | “Find an example of how I helped someone learn something.” |
| Make a CV | “Walk me through the resume wizard. Here is the job description.” |

A quick note waits for review before joining your accepted record. A CV uses
information you have allowed for external use. The starter includes the resume tools. It prepares PDF, Word, text and clean Markdown versions of a resume. Only PDF
needs additional export software; ask Claude to follow the
[export setup guide](resume-exports.md) when you reach that step. You do not need
PDF software for your first saved achievement or the full career Markdown copy.

## If something gets in the way

**Claude says Python is missing.** Open [Python's Mac downloads](https://www.python.org/downloads/macos/).
Choose the latest stable Python 3 macOS installer. Open the downloaded file ending
in `.pkg` and follow the installer's steps. Quit and reopen Claude, select the
same My Career folder, and send “Help me start my career notebook” again. If a
work computer prevents installation, its administrator controls that permission;
there is no career.json setting that can override it.

**You cannot find Code.** Update Claude Desktop and check your plan using
[Anthropic's setup guide](https://code.claude.com/docs/en/desktop-quickstart).
Opening a normal chat does not open your career folder.

**Claude cannot find the career tools.** Check the selected folder. It should
contain START-HERE.html and a folder called scripts. Select that folder itself,
not the ZIP or the folder containing it.

**Your CV is an unreadable PDF.** Paste a paragraph from it or describe the work
in your own words. Claude can record that as your account. You can add the PDF
later; it need not hold up the first exercise.

**An error or approval makes no sense.** Ask:

> Explain what this means in everyday language. What will change, and what is
> the next step I can take?

Allowing Claude to run a tool is separate from confirming a career fact. If an
installation check reports a damaged download, extract a fresh copy into a new
folder. Keep the old folder if you have started recording your career there.

**You reached your Claude usage limit.** Return when your account permits more
work. Open the same folder and ask to continue. Your saved files stay there.

Cowork and ordinary chat are not verified routes for this starter. Use the Code
tab and local folder described above.

## Where your information goes

Your career documents and saved record live in your local folder. Material you
ask Claude to read is processed by the model service you use. “Saved on my
computer” does not mean “never sent to Claude.”

Keeping a detail private controls its use in generated documents. It does not
hide that detail from Claude when Claude reads it. Your private reading page
can contain those details too.

After your first save, ask Claude: “Help me back up my career folder.” Saving a
file locally does not automatically back it up to GitHub or another service.

## What this route checks

The starter checks its application files and whether it can prepare your folder.
The first exercise ends by reading your accepted achievement back from disk with
its source. Those checks establish a saved record, not that every detail of your
career has been captured.

The Desktop buttons follow Anthropic's documentation. Automated checks of the
starter and career tools do not establish that every Desktop version or computer
will behave identically.
