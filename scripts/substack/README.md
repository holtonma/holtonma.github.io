# Substack cross-post

Turns one live Hugo post into a **Substack draft**. It never publishes or sends: you review the draft in Substack's editor and publish it yourself.

Substack has no official write API. This uses [python-substack](https://github.com/ma2za/python-substack), which calls the same undocumented endpoints as Substack's web editor using your browser session cookies. Those endpoints can change without notice. If they break, use the [manual fallback](#if-the-api-breaks).

## Setup (once)

```sh
cd scripts/substack
uv venv .venv && uv pip install --python .venv -r requirements.txt
.venv/bin/python -m playwright install chromium   # browser for table/SVG renders
npm ci                                              # mermaid-cli (brings its own Chromium)
```

### Cookies

1. Log in at substack.com in Chrome, open DevTools → Network, reload, and click any `substack.com` request.
2. Copy the whole **Cookie** request header (it must include `substack.sid`).
3. `.venv/bin/python export.py --save-cookies` and paste. This writes `~/.config/substack-crosspost/cookies.json` with mode 600. The script won't run if that file's permissions are any looser.

Cookies expire. When requests start failing with 401/403, repeat these steps.

### Publication

Pass `--publication https://<you>.substack.com` each time, or set it once:

```sh
echo '{"publication_url": "https://<you>.substack.com"}' > ~/.config/substack-crosspost/config.json
```

## Use

```sh
# 1. Local only, no Substack access: convert, render, and preview
.venv/bin/python export.py ../../content/posts/<post>.md --dry-run
open out/<post>/preview.html

# 2. Create the draft (only if the dry run looks right)
.venv/bin/python export.py ../../content/posts/<post>.md
```

Then in Substack, review the draft against the Hugo post → **Publish** → choose **web only** or **send email** as a deliberate step.

### What gets converted

| Hugo | Substack draft |
| --- | --- |
| ```` ```mermaid ```` | PNG (mermaid-cli, neutral theme) |
| Table, ≤3 columns and ≤8 rows | bullet list, each value next to its header |
| Larger table | PNG, then the same header-labelled list |
| `![alt](/images/x)` + `*caption*` on the next line | captioned image (uploaded) |
| `.svg` image | rasterized to PNG (Substack only takes JPEG, PNG, GIF, WebP) |
| `[^n]` side notes | Substack footnotes |
| `$` in prose | escaped, so python-substack doesn't read it as LaTeX |
| — | "Originally published at <permalink>" footer |

**Refused (blocking):** Hugo shortcodes, raw or inline HTML, an image sharing a paragraph with text, image paths outside `/images/`, missing image files, and posts that `hugo list published` doesn't list (drafts, future-dated, expired). Fix the post or add a converter. There is no override.

**Tags:** `substack_tags:` from front matter if set, otherwise the Hugo `tags:` list. They're added right after the draft is created; if that fails, you get a warning and the draft is kept.

**Non-blocking warnings:** missing alt text, tables turned into lists, mermaid blocks with generic alt text (put a `%% description` as the block's first line).

### No duplicate drafts

The ledger at `~/.config/substack-crosspost/ledger.json` maps `(publication, permalink)` to one draft. Before creating anything, the script:

1. takes a per-post lock (a second run at the same time stops immediately)
2. checks the ledger's recorded draft, if any
3. searches every draft and published post on Substack for the exact permalink
4. stops if any lookup fails

It records `creating` **before** sending the single create request, and `created` after it succeeds. A timeout, an error, or a crash mid-request leaves `pending`/`creating`, and every later run refuses until the draft is found or you resolve it:

```sh
.venv/bin/python export.py ../../content/posts/<post>.md --resolve-pending
```

This searches again. If nothing turns up, it asks you to check the dashboard (Drafts, Scheduled, Published) and type the post's permalink to confirm. It only clears the record and never creates a draft.

### If the API breaks

Open `out/<post>/preview.html`, select everything, and paste it into a new Substack post. Every image in it is a local file, including the post's own images, the diagrams, and the tables, so each may need dragging into the editor by hand.

## Tests

```sh
.venv/bin/pytest
```

## Spike results (python-substack 0.10.0, 2026-11-27)

- Footnotes become native Substack footnotes: ✅
- Image captions (Markdown image title) become Substack captions: ✅. Local images upload to Substack's CDN.
- Code blocks become Substack code blocks: ✅
- Cover image is set through `put_draft(cover_image=…)`: ✅ (the script checks it took)
- `Api.get_drafts` (`/drafts`) returns **400 Invalid value**, so the duplicate search uses the dashboard's `/post_management/{drafts,scheduled,published}` endpoints (`crosspost/client.py`), which page with offset/limit and include scheduled posts: ✅
- A deleted draft returns 404, which the script treats as deleted: ✅
- Subtitles over some limit are rejected with **400 "Subtitle is too long"** (325 characters failed; 237 passed). The script shortens descriptions over 256 characters to whole sentences, or uses `substack_subtitle:` from front matter. A 400/422 rejection creates nothing, so it clears the record instead of leaving it `pending`.
- Second run on the same post: refuses and prints the existing draft's URL. With the ledger entry removed, it finds the draft by permalink and refuses: ✅
- `rel="canonical"` on a published post points to the **Substack URL itself** (checked on /p/the-foreman-carries-no-tools-sub). Substack offers no way to point it at Hugo. This matches the SEO decision: two indexed copies, and the footer is attribution only.
- Image sizes: python-substack 0.10.0 records every image as 1456×819, which squashes or stretches anything that isn't 16:9 on the **published** page (editor and preview look fine). The script now writes each image's real size before creating the draft.
- Tags: `add_tags_to_post` works on drafts and published posts and reuses existing tags. The draft response doesn't include them; check `/api/v1/posts/<slug>` → `postTags`.
