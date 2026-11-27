---
name: crosspost
description: Cross-post a published blog post to Substack, Dev.to, or both, as a draft. Use when the user asks to cross-post, syndicate, share, or "put" a post on Substack or Dev.to, or asks whether a post is ready for either. Never publishes; the user publishes from each site's editor.
argument-hint: "[post] [to substack|devto|both]"
---

# Cross-post a blog post as a draft

The tool is `scripts/crosspost/export.py` (see `scripts/crosspost/README.md`). It converts a live Hugo post and creates **one draft** per target. It never publishes, never sends email, and refuses to create a second draft for the same post. Your job: work out what the user wants, show them the dry run, get a yes, then run it live and report.

Arguments: `$ARGUMENTS`

Run every command from `scripts/crosspost/` with `.venv/bin/python`. If `.venv` or `node_modules` is missing, follow the README's Setup section first.

## 1. Work out the post and the target

- **Post**: a file in `content/posts/`. The user may name it loosely ("the sub-agents post"). Match it against titles and filenames. If more than one matches, or none does, ask.
- **Target**: `substack`, `devto` or `both`. "Dev", "dev.to" and "DEV" mean `devto`. If they didn't say, ask. Don't default to both.

## 2. Dry run, always first

```sh
.venv/bin/python export.py ../../content/posts/<post>.md --to <target> --dry-run
```

If it stops with **unsupported content** (shortcodes, raw HTML, an image sharing a paragraph with text) or **not live on Hugo**, tell the user exactly what it says and stop. Don't edit the post to get around a block unless they ask for that specific edit.

Otherwise summarize the report in a few lines:
- what converts and how: diagrams, tables, captions, footnotes
- Substack: the subtitle if it was shortened, and the tags
- Dev.to: the four tags (and any dropped), the AI label, and the canonical URL
- non-blocking warnings, briefly

Point them at the preview file(s) printed in the report.

**Dev.to only:** if the report lists **images to commit and deploy**, those PNGs must be live on the blog before the live run (Dev.to can't take uploads). Say so. With the user's go-ahead, commit them. Pushing to `main` deploys the site, so get explicit permission before any push. Wait until the deploy finishes. The live run checks every image URL and refuses if any isn't live yet.

## 3. Ask before the live run

Ask plainly: "Create the <target> draft(s) now?" Only a clear yes counts. Offer front-matter tweaks if the report suggests them (`devto_tags:`, `substack_tags:`, `substack_subtitle:`), but make them only if the user agrees.

## 4. Live run

```sh
.venv/bin/python export.py ../../content/posts/<post>.md --to <target>
```

Report each target's line from the summary: the draft URL, or why it stopped.

- **"= already there: <url>"** means the post already has its draft or post on that site, and nothing was created. That's the correct outcome, not an error. Give them the URL.
- **"rejected ... nothing was created"**: Substack or Dev.to refused a field. Explain which one and suggest the front-matter fix.
- **Unknown outcome / pending**: don't retry. Tell them to check the dashboard it names, then run `--to <target> --resolve-pending` **in their own terminal** (it asks them to type the permalink). Never type that confirmation for them.
- **Missing credentials**: they run `--save-cookies` (Substack) or `--save-devto-key` (Dev.to) in their own terminal. The prompt hides input. Ask them never to paste secrets into the chat.

## 5. After

Remind them the draft is waiting in the site's editor: review it, then publish there. For Substack, choose **web only** or **send email** deliberately. Dev.to drafts carry the canonical link back to the blog, so search engines credit the original.

## Never

- Publish, send, schedule, or set `published: true`.
- Retry a create after an unknown outcome, or work around the duplicate checks.
- Read, print or paste the user's cookies or API key.
