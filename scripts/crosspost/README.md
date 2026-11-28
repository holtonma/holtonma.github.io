# Cross-post to Substack and Dev.to

Turns one live Hugo post into a **draft** on Substack, Dev.to, or both. It never publishes or sends: you review each draft in that site's editor and publish it yourself. In Claude Code you can just ask ("cross-post the sub-agents post to Dev.to"); the `crosspost` skill in `.claude/skills/` runs these steps with you.

Substack has no official write API. This uses [python-substack](https://github.com/ma2za/python-substack), which calls the same undocumented endpoints as Substack's web editor using your browser session cookies. Those endpoints can change without notice. If they break, use the [manual fallback](#if-the-api-breaks).

## Setup (once)

```sh
cd scripts/crosspost
uv venv .venv && uv pip install --python .venv -r requirements.txt
.venv/bin/python -m playwright install chromium   # browser for table/SVG renders
npm ci                                              # mermaid-cli (brings its own Chromium)
```

### Cookies

1. Log in at substack.com in Chrome, open DevTools → Network, reload, and click any `substack.com` request.
2. Copy the whole **Cookie** request header (it must include `substack.sid`).
3. Run `pbpaste | .venv/bin/python export.py --save-cookies`. The header is too long to paste at a terminal prompt (macOS caps a typed line at 1024 characters), so it reads your clipboard instead. This writes `~/.config/crosspost/substack/cookies.json` with mode 600. The script won't run if that file's permissions are any looser.

Cookies expire. When requests start failing with 401/403, repeat these steps.

### Publication

Pass `--publication https://<you>.substack.com` each time, or set it once:

```sh
echo '{"publication_url": "https://<you>.substack.com"}' > ~/.config/crosspost/substack/config.json
```

## Use

```sh
# 1. Local only, nothing sent: convert, render, and preview
.venv/bin/python export.py ../../content/posts/<post>.md --to both --dry-run
open out/<post>/preview-substack.html out/<post>/preview-devto.html

# 2. Create the draft(s) (only if the dry run looks right)
.venv/bin/python export.py ../../content/posts/<post>.md --to substack   # or devto, or both
```

Then in Substack, review the draft against the Hugo post → **Publish** → choose **web only** or **send email** as a deliberate step.

### What gets converted

| Hugo | Substack draft |
| --- | --- |
| ```` ```mermaid ```` | PNG (mermaid-cli, neutral theme); alt text from `accDescr:`, `accTitle:` or a `%%` first line |
| Table, ≤3 columns and ≤8 rows | bullet list, each value next to its header |
| Larger table | PNG, then the same header-labelled list |
| `![alt](/images/x)` + `*caption*` on the next line | captioned image (uploaded) |
| `.svg` image | rasterized to PNG (Substack only takes JPEG, PNG, GIF, WebP) |
| `<video poster="/images/…">` with one `<source src="/videos/…">` | the poster image, then a "▶ Watch the video on the blog" link (neither site takes video through its API; on Substack you can drag the MP4 into the draft by hand) |
| `[^n]` side notes | Substack footnotes |
| `$` in prose | escaped, so python-substack doesn't read it as LaTeX |
| — | "Originally published at <permalink>" footer |

**Refused (blocking):** Hugo shortcodes, raw or inline HTML (other than the `<video>` form above), an image sharing a paragraph with text, image paths outside `/images/`, missing image files, and posts that `hugo list published` doesn't list (drafts, future-dated, expired). Fix the post or add a converter. There is no override.

**Tags:** `substack_tags:` from front matter if set, otherwise the Hugo `tags:` list. They're added right after the draft is created; if that fails, you get a warning and the draft is kept.

**Non-blocking warnings:** missing alt text, tables turned into lists, mermaid blocks with generic alt text (put a `%% description` as the block's first line).

### No duplicate drafts

The ledger at `~/.config/crosspost/substack/ledger.json` maps `(publication, permalink)` to one draft. Before creating anything, the script:

1. takes a per-post lock (a second run at the same time stops immediately)
2. checks the ledger's recorded draft, if any
3. searches every draft and published post on Substack for the exact permalink
4. stops if any lookup fails

It records `creating` **before** sending the single create request, and `created` after it succeeds. A timeout, an error, or a crash mid-request leaves `pending`/`creating`, and every later run refuses until the draft is found or you resolve it:

```sh
.venv/bin/python export.py ../../content/posts/<post>.md --to <substack|devto> --resolve-pending
```

This searches again. If nothing turns up, it asks you to check the dashboard (Drafts, Scheduled, Published) and type the post's permalink to confirm. It only clears the record and never creates a draft.

### If the API breaks

Open `out/<post>/preview.html`, select everything, and paste it into a new Substack post. Every image in it is a local file, including the post's own images, the diagrams, and the tables, so each may need dragging into the editor by hand.

## Dev.to

Dev.to has an official API with drafts (`published: false`) and `canonical_url`, so search engines credit the blog. It has **no image upload API**, so:

- The post's own images are referenced at `https://holtonma.github.io/images/...`.
- Rendered PNGs (mermaid, SVGs) are copied to `static/images/crosspost/<post>/`. The dry run lists them. **Commit and deploy them before the live run**: it checks every image URL and refuses if any isn't live.

### New post: one deploy

A dry run works before the post is live (it uses the URL Hugo will give it and says "NOT LIVE YET"), so:

1. `export.py <post> --to both --dry-run`, while the post is still a draft or not yet deployed.
2. Commit the post **and** any `static/images/crosspost/<post>/` PNGs it lists, together. Deploy once.
3. Once the post is live: `export.py <post> --to both` creates the drafts.

A live run always requires the post to be published.

Differences from Substack: tables stay as Markdown tables, captions become `<figcaption>`, `$` isn't escaped, and any `{%`/`{{` left in the output stops the run (Dev.to would read it as Liquid). Tags: `devto_tags:` or the first four Hugo tags, lowercased with punctuation stripped. AI label: `ai_disclosure:` in front matter, default `some_ai`.

API key: dev.to → Settings → Extensions → "DEV Community API Keys" → generate. Save it with `.venv/bin/python export.py --save-devto-key` (stored at `~/.config/crosspost/devto/api_key`, mode 600).

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

## Dev.to spike results (Forem API v1, 2026-11-27)

- `POST /api/articles` with `published: false` creates a private draft; the response includes `body_html`, `url` (add `/edit`) and `ai_disclosure_level`: ✅
- Tables, footnotes and `<figcaption>` captions render natively: ✅. `$` is left alone: ✅
- Front matter in `body_markdown` sets `ai_disclosure_level` and isn't shown in the post: ✅
- **Once the body has front matter, `tags` and `cover_image` come from it, and the API's `tags`/`main_image` are ignored.** The script writes tags, cover image and canonical URL into the front matter.
- `canonical_url` and `description` from the API fields: ✅
- `/api/articles/me/all` lists drafts, so the duplicate search sees them: ✅
- The API **can't delete** an article. A test draft has to be deleted in the dashboard.
