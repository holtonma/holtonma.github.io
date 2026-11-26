---
name: add-sidenote
description: Add a side note (a Markdown footnote that renders in the right margin) to a blog post. Use when the user asks to add a side note, sidenote, margin note, or footnote to a post, giving the note text and where in the post it belongs.
argument-hint: "[post path] <where it goes> :: <note text>"
---

# Add a side note to a post

This site turns ordinary Markdown footnotes into side notes (see `layouts/partials/extend_footer.html` and `assets/css/extended/sidenotes.css`). On wide screens the note sits in the right margin beside the line that cites it; on narrow screens the reader taps the number to open it in place. So adding a side note means adding a footnote correctly.

Arguments: `$ARGUMENTS`

## 1. Work out the three inputs

- **Post**: a path under `content/`. If none is given, use the post being worked on in this conversation. If that is unclear, ask.
- **Anchor**: the words in the post the note attaches to. The user may quote them exactly or describe them ("after the sentence about the merge button").
- **Note text**: what the note says, in the user's words. Keep their wording. Markdown is fine: links, `code`, *emphasis*.

If the input uses `::`, the part before it is the anchor and the part after it is the note text. If either is missing, ask for it. Don't invent note text.

## 2. Find the anchor

Read the post and find the anchor. It must be in body prose: a paragraph, list item or blockquote. Not in front matter, a heading, a code block, a table or an image caption. If it is in one of those, say so and suggest the nearest sentence that works.

If the anchor matches more than one place, show the user the matches and ask which one. If it matches nothing, show the closest sentences and ask.

## 3. Pick the label

Find every footnote label in the post (`[^...]`). The new label is the highest numeric label plus one, or `1` if there are none.

Hugo numbers footnotes by where they are first cited, not by label. So if a note goes earlier in the post than existing ones, readers see the numbers shift. That is expected. Don't renumber the existing labels.

## 4. Insert the reference

Put `[^N]` right after the anchor:

- At the end of a sentence or clause, after the punctuation, with no space: `...the merge button.[^3]`
- On a phrase in mid-sentence, directly after the phrase, with no space: `the harness[^3] validates it`

## 5. Insert the definition

Put `[^N]: note text` on its own line, with a blank line before and after, directly after the block that holds the reference: after that paragraph, after the whole list, or after the whole blockquote. Keeping it near its reference makes the source easy to edit.

A note must be one paragraph. If the text has line breaks, join them into one line.

## 6. Check and report

- Run `hugo --quiet -D -d "$TMPDIR/hugo-sidenote-check"` (or the scratchpad) and make sure the build succeeds.
- Show the user the edited sentence with its marker and the definition line, and give the label number.
- Tell them where to look: the side note appears in the right margin on windows at least 1420px wide. On narrower windows they tap the number to open it.
