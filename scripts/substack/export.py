#!/usr/bin/env python3
"""Cross-post one Hugo post to Substack as a draft (never published or sent).

    .venv/bin/python export.py ../../content/posts/<post>.md --dry-run
    .venv/bin/python export.py ../../content/posts/<post>.md
    .venv/bin/python export.py ../../content/posts/<post>.md --resolve-pending
    .venv/bin/python export.py --save-cookies

See README.md.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import stat
import sys
from pathlib import Path

import yaml
from markdown_it import MarkdownIt
from mdit_py_plugins.footnote import footnote_plugin

from crosspost import convert, hugo, live
from crosspost.ledger import CONFIG_DIR, Ledger, Locked

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / "out"
COOKIES = CONFIG_DIR / "cookies.json"
CONFIG = CONFIG_DIR / "config.json"


SUBTITLE_MAX = 256  # Substack rejects long subtitles; exact limit undocumented


def subtitle_for(meta: dict, warnings: list[str]) -> str:
    """`substack_subtitle` if set, else the description, cut to whole sentences that fit."""
    if meta.get("substack_subtitle"):
        return str(meta["substack_subtitle"]).strip()
    desc = str(meta.get("description") or "").strip()
    if len(desc) <= SUBTITLE_MAX:
        return desc
    import re

    out = ""
    for sentence in re.split(r"(?<=[.!?])\s+", desc):
        candidate = f"{out} {sentence}".strip()
        if len(candidate) > SUBTITLE_MAX:
            break
        out = candidate
    if not out:
        out = desc[: SUBTITLE_MAX - 1].rsplit(" ", 1)[0] + "…"
    warnings.append(
        f"description is {len(desc)} chars; subtitle shortened to {out!r} "
        "(set `substack_subtitle:` in front matter to choose it)"
    )
    return out


def fail(msg: str, code: int = 1):
    sys.stdout.flush()
    print(f"\n✗ {msg}", file=sys.stderr)
    sys.exit(code)


def split_front_matter(raw: str) -> tuple[dict, str, int]:
    lines = raw.split("\n")
    if lines[0].strip() != "---":
        fail("post has no YAML front matter")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        fail("front matter is not closed")
    meta = yaml.safe_load("\n".join(lines[1:end])) or {}
    return meta, "\n".join(lines[end + 1 :]), end + 1


def build(post: Path) -> dict:
    raw = post.read_text()
    meta, body, offset = split_front_matter(raw)
    try:
        permalink = hugo.published_permalink(REPO, post)
    except hugo.NotLive as exc:
        fail(str(exc))

    analysis = convert.analyze(body, offset)
    problems = analysis.problems + convert.check_images_exist(analysis, REPO)
    if problems:
        fail(
            "Unsupported content; no draft will be made until these are converted "
            "or changed in the post:\n  " + "\n  ".join(problems)
        )

    slug = post.stem
    out = OUT / slug
    out.mkdir(parents=True, exist_ok=True)

    from crosspost import render

    mermaid_pngs = [
        render.render_mermaid(m.source, out / f"mermaid-{n}.png")
        for n, m in enumerate(analysis.mermaids, start=1)
    ]
    table_pngs: dict[int, Path] = {}
    overrides: dict[str, Path] = {}
    big = [n for n, t in enumerate(analysis.tables) if not t.is_simple]
    svgs = sorted({f.src for f in analysis.figures if f.src.lower().endswith(".svg")})
    if big or svgs:
        with render.Screenshotter() as shot:
            for n in big:
                table_pngs[n] = shot.table(analysis.tables[n], out / f"table-{n + 1}.png")
            for src in svgs:
                overrides[src] = shot.svg(
                    convert.local_image_path(REPO, src), out / (Path(src).stem + ".png")
                )

    md = convert.rewrite(body, analysis, REPO, mermaid_pngs, table_pngs, overrides, permalink)
    (out / "substack.md").write_text(md)
    write_preview(out, meta.get("title", slug), meta.get("description", ""), md)

    warnings = list(analysis.warnings)
    for n, m in enumerate(analysis.mermaids, start=1):
        if m.alt(n) == f"Diagram {n}":
            warnings.append(
                f"mermaid {n} has generic alt text 'Diagram {n}'; add a `%% description` "
                "first line to the block, or edit the alt in Substack"
            )
    for n, t in enumerate(analysis.tables):
        kind = "image + list" if n in table_pngs else "list"
        warnings.append(f"table {n + 1} ({', '.join(t.headers)}) shown as {kind}")

    subtitle = subtitle_for(meta, warnings)
    cover = (meta.get("cover") or {}).get("image")
    return {
        "meta": meta,
        "permalink": permalink,
        "analysis": analysis,
        "markdown": md,
        "out": out,
        "warnings": warnings,
        "cover": convert.local_image_path(REPO, cover) if cover else None,
        "svgs": svgs,
        "subtitle": subtitle,
        "tags": [str(t) for t in (meta.get("substack_tags") or meta.get("tags") or [])],
    }


def write_preview(out: Path, title: str, subtitle: str, md: str) -> None:
    html = MarkdownIt("commonmark").use(footnote_plugin).render(md)
    (out / "preview.html").write_text(
        "<!doctype html><meta charset='utf-8'>"
        "<style>body{max-width:728px;margin:40px auto;padding:0 16px;"
        "font:18px/1.6 Georgia,serif;color:#222}img{max-width:100%}"
        "pre{background:#f6f6f6;padding:12px;overflow:auto;font-size:14px}"
        "figure,img{display:block;margin:24px auto}</style>"
        f"<h1>{title}</h1><h3 style='color:#666;font-weight:normal'>{subtitle}</h3>{html}"
    )


def report(b: dict) -> None:
    a = b["analysis"]
    captions = sum(1 for f in a.figures if f.caption)
    print(f"Post:       {b['meta'].get('title')}")
    print(f"Subtitle:   {b['subtitle']}")
    print(f"Permalink:  {b['permalink']}")
    print(f"Mermaid:    {len(a.mermaids)} → PNG")
    print(f"Tables:     {len(a.tables)}")
    print(f"Images:     {len(a.figures)} ({captions} with captions, {len(b['svgs'])} SVG → PNG)")
    print(f"Footnotes:  {a.footnote_refs}")
    print(f"Cover:      {b['cover'] or 'none'}")
    print(f"Tags:       {', '.join(b['tags']) or 'none'}")
    if b["warnings"]:
        print("Non-blocking warnings:")
        for w in b["warnings"]:
            print(f"  - {w}")
    print(f"Output:     {b['out']}/substack.md")
    print(f"Preview:    {b['out']}/preview.html")


# -------------------------------------------------------------------- auth


def save_cookies() -> None:
    print("Paste the Cookie header from a logged-in substack.com request (input hidden):")
    raw = getpass.getpass("> ")
    cookies = {}
    for pair in raw.split(";"):
        if "=" in pair:
            k, v = pair.strip().split("=", 1)
            cookies[k] = v
    if "substack.sid" not in cookies:
        fail("no substack.sid in what you pasted; copy the whole Cookie header")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    fd = os.open(COOKIES, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(cookies, f)
    os.chmod(COOKIES, 0o600)
    print(f"Saved {len(cookies)} cookies to {COOKIES} (mode 600).")


def connect(publication: str | None):
    if not COOKIES.exists():
        fail(f"no cookies at {COOKIES}; run with --save-cookies first")
    mode = stat.S_IMODE(COOKIES.stat().st_mode)
    if mode & 0o077:
        fail(f"{COOKIES} is mode {oct(mode)}; run `chmod 600 {COOKIES}`")
    if not publication and CONFIG.exists():
        publication = json.loads(CONFIG.read_text()).get("publication_url")
    if not publication:
        fail(f"no publication: pass --publication URL or set publication_url in {CONFIG}")
    from crosspost.client import Client

    api = Client(cookies_path=str(COOKIES), publication_url=publication, timeout=60)
    print(f"Publication: {live.base_url(api)}")
    return api, live.base_url(api)


# -------------------------------------------------------------------- main


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("post", nargs="?", type=Path)
    ap.add_argument("--dry-run", action="store_true", help="convert and preview locally; no Substack access")
    ap.add_argument("--publication", help="Substack publication URL, e.g. https://you.substack.com")
    ap.add_argument("--resolve-pending", action="store_true",
                    help="clear an unknown-outcome create after you've checked the dashboard")
    ap.add_argument("--save-cookies", action="store_true", help="store Substack session cookies (mode 600)")
    args = ap.parse_args()

    if args.save_cookies:
        return save_cookies()
    if not args.post:
        ap.error("a post path is required")
    post = args.post.resolve()

    try:
        if args.resolve_pending:
            permalink = hugo.published_permalink(REPO, post)
            api, pub = connect(args.publication)
            live.resolve_pending(api, Ledger(), pub, permalink)
            return

        b = build(post)
        report(b)
        if args.dry_run:
            print("\nDry run: nothing sent to Substack.")
            return

        api, pub = connect(args.publication)
        spec = live.DraftSpec(
            title=b["meta"]["title"],
            subtitle=b["subtitle"],
            markdown=b["markdown"],
            cover_image=b["cover"],
        )
        draft = live.create_draft(api, Ledger(), pub, b["permalink"], spec)
        print(f"\n✓ Draft created (not published, not sent): {draft['url']}")
        if spec.cover_image:
            if live.set_cover(api, draft["id"], spec.cover_image):
                print(f"✓ Cover image set from {spec.cover_image.name}")
            else:
                print(f"! Set the cover image by hand: {spec.cover_image}")
        if b["tags"]:
            try:
                api.add_tags_to_post(draft["id"], b["tags"])
                print(f"✓ Tags added: {', '.join(b['tags'])}")
            except Exception as exc:
                print(f"! Tags not added ({exc}); add them in the editor: {', '.join(b['tags'])}")
    except (live.Stop, Locked, hugo.NotLive) as exc:
        fail(str(exc))


if __name__ == "__main__":
    main()
