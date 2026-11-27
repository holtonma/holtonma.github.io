#!/usr/bin/env python3
"""Cross-post one Hugo post as a draft to Substack, Dev.to, or both. Never publishes.

    .venv/bin/python export.py ../../content/posts/<post>.md --to devto --dry-run
    .venv/bin/python export.py ../../content/posts/<post>.md --to substack
    .venv/bin/python export.py ../../content/posts/<post>.md --to both
    .venv/bin/python export.py ../../content/posts/<post>.md --to devto --resolve-pending
    .venv/bin/python export.py --save-cookies        # Substack session
    .venv/bin/python export.py --save-devto-key      # Dev.to API key

See README.md.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

import yaml
from markdown_it import MarkdownIt
from mdit_py_plugins.footnote import footnote_plugin

from crosspost import convert, guard, hugo
from crosspost.ledger import CONFIG_DIR, Ledger, Locked

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / "out"
SUBSTACK_DIR = CONFIG_DIR / "substack"
DEVTO_DIR = CONFIG_DIR / "devto"
COOKIES = SUBSTACK_DIR / "cookies.json"
SUBSTACK_CONFIG = SUBSTACK_DIR / "config.json"
DEVTO_KEY = DEVTO_DIR / "api_key"
TARGETS = ("substack", "devto")

SUBTITLE_MAX = 256  # Substack rejects long subtitles; exact limit undocumented


def fail(msg: str, code: int = 1):
    sys.stdout.flush()
    print(f"\n✗ {msg}", file=sys.stderr)
    sys.exit(code)


def shorten(text: str, limit: int) -> str:
    """Whole leading sentences that fit, else a word-boundary cut."""
    text = text.strip()
    if len(text) <= limit:
        return text
    out = ""
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        candidate = f"{out} {sentence}".strip()
        if len(candidate) > limit:
            break
        out = candidate
    return out or text[: limit - 1].rsplit(" ", 1)[0] + "…"


def split_front_matter(raw: str) -> tuple[dict, str, int]:
    lines = raw.split("\n")
    if lines[0].strip() != "---":
        fail("post has no YAML front matter")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        fail("front matter is not closed")
    meta = yaml.safe_load("\n".join(lines[1:end])) or {}
    return meta, "\n".join(lines[end + 1 :]), end + 1


# ------------------------------------------------------------------ shared build


def build(post: Path, targets: list[str]) -> dict:
    """Everything both targets share: checks, analysis, rendered PNGs."""
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
    # Only the list-style target (Substack) needs big tables as pictures.
    big = [n for n, t in enumerate(analysis.tables) if not t.is_simple] if "substack" in targets else []
    svgs = sorted({f.src for f in analysis.figures if f.src.lower().endswith(".svg")})
    if big or svgs:
        with render.Screenshotter() as shot:
            for n in big:
                table_pngs[n] = shot.table(analysis.tables[n], out / f"table-{n + 1}.png")
            for src in svgs:
                overrides[src] = shot.svg(
                    convert.local_image_path(REPO, src), out / (Path(src).stem + ".png")
                )

    warnings = list(analysis.warnings)
    for n, m in enumerate(analysis.mermaids, start=1):
        if m.alt(n) == f"Diagram {n}":
            warnings.append(
                f"mermaid {n} has generic alt text 'Diagram {n}'; add a `%% description` "
                "first line to the block"
            )

    cover = (meta.get("cover") or {}).get("image")
    return {
        "post": post,
        "slug": slug,
        "meta": meta,
        "body": body,
        "permalink": permalink,
        "site": "{0.scheme}://{0.netloc}".format(urlsplit(permalink)),
        "analysis": analysis,
        "mermaid_pngs": mermaid_pngs,
        "table_pngs": table_pngs,
        "overrides": overrides,
        "out": out,
        "warnings": warnings,
        "cover": cover,
        "svgs": svgs,
    }


def write_preview(path: Path, title: str, subtitle: str, md: str) -> None:
    html = MarkdownIt("commonmark").use(footnote_plugin).enable("table").render(md)
    path.write_text(
        "<!doctype html><meta charset='utf-8'>"
        "<style>body{max-width:728px;margin:40px auto;padding:0 16px;"
        "font:18px/1.6 Georgia,serif;color:#222}img{max-width:100%}"
        "pre{background:#f6f6f6;padding:12px;overflow:auto;font-size:14px}"
        "table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:4px 8px}"
        "figcaption{text-align:center;color:#666;font-size:15px}"
        "figure,img{display:block;margin:24px auto}</style>"
        f"<h1>{title}</h1><h3 style='color:#666;font-weight:normal'>{subtitle}</h3>{html}"
    )


def report(b: dict) -> None:
    a = b["analysis"]
    captions = sum(1 for f in a.figures if f.caption)
    print(f"Post:       {b['meta'].get('title')}")
    print(f"Permalink:  {b['permalink']}")
    print(f"Mermaid:    {len(a.mermaids)} → PNG")
    print(f"Tables:     {len(a.tables)}")
    print(f"Images:     {len(a.figures)} ({captions} with captions, {len(b['svgs'])} SVG → PNG)")
    print(f"Footnotes:  {a.footnote_refs}")
    print(f"Cover:      {b['cover'] or 'none'}")
    if b["warnings"]:
        print("Non-blocking warnings:")
        for w in b["warnings"]:
            print(f"  - {w}")


# ------------------------------------------------------------------ Substack


def substack_prepare(b: dict) -> dict:
    a, meta = b["analysis"], b["meta"]
    md = convert.rewrite(
        b["body"], a, REPO, b["mermaid_pngs"], b["table_pngs"], b["overrides"], b["permalink"],
        convert.substack_style(REPO),
    )
    warnings = []
    for n, t in enumerate(a.tables):
        kind = "image + list" if n in b["table_pngs"] else "list"
        warnings.append(f"table {n + 1} ({', '.join(t.headers)}) shown as {kind}")
    if meta.get("substack_subtitle"):
        subtitle = str(meta["substack_subtitle"]).strip()
    else:
        desc = str(meta.get("description") or "")
        subtitle = shorten(desc, SUBTITLE_MAX)
        if subtitle != desc.strip():
            warnings.append(f"subtitle shortened to {len(subtitle)} chars (set `substack_subtitle:` to choose it)")
    (b["out"] / "substack.md").write_text(md)
    write_preview(b["out"] / "preview-substack.html", meta.get("title", b["slug"]), subtitle, md)
    tags = [str(t) for t in (meta.get("substack_tags") or meta.get("tags") or [])]
    print("\n[Substack]")
    print(f"  Subtitle: {subtitle}")
    print(f"  Tags:     {', '.join(tags) or 'none'}")
    for w in warnings:
        print(f"  - {w}")
    print(f"  Preview:  {b['out']}/preview-substack.html")
    return {"markdown": md, "subtitle": subtitle, "tags": tags}


def substack_connect(publication: str | None):
    if not COOKIES.exists():
        raise guard.Stop(f"no Substack cookies at {COOKIES}; run with --save-cookies first")
    mode = stat.S_IMODE(COOKIES.stat().st_mode)
    if mode & 0o077:
        raise guard.Stop(f"{COOKIES} is mode {oct(mode)}; run `chmod 600 {COOKIES}`")
    if not publication and SUBSTACK_CONFIG.exists():
        publication = json.loads(SUBSTACK_CONFIG.read_text()).get("publication_url")
    if not publication:
        raise guard.Stop(f"no publication: pass --publication URL or set publication_url in {SUBSTACK_CONFIG}")
    from crosspost.client import Client
    from crosspost.substack import SubstackTarget

    try:
        target = SubstackTarget(Client(cookies_path=str(COOKIES), publication_url=publication, timeout=60))
    except Exception as exc:
        raise guard.Stop(
            f"Substack sign-in failed ({exc}). Your saved cookies have probably expired; "
            "run --save-cookies in your terminal with a fresh Cookie header."
        ) from exc
    print(f"  Publication: {target.account}")
    return target


def substack_live(b: dict, prep: dict, publication: str | None) -> str:
    from crosspost.substack import DraftSpec

    target = substack_connect(publication)
    cover = convert.local_image_path(REPO, b["cover"]) if b["cover"] else None
    spec = DraftSpec(b["meta"]["title"], prep["subtitle"], prep["markdown"], cover)
    draft = guard.create_once(target, Ledger(SUBSTACK_DIR), b["permalink"], spec)
    print(f"  ✓ Draft created (not published, not sent): {draft['url']}")
    if cover:
        if target.set_cover(draft["id"], cover):
            print(f"  ✓ Cover image set from {cover.name}")
        else:
            print(f"  ! Set the cover image by hand: {cover}")
    if prep["tags"]:
        try:
            target.add_tags(draft["id"], prep["tags"])
            print(f"  ✓ Tags added: {', '.join(prep['tags'])}")
        except Exception as exc:
            print(f"  ! Tags not added ({exc}); add them in the editor: {', '.join(prep['tags'])}")
    return draft["url"]


# ------------------------------------------------------------------ Dev.to


def devto_style(b: dict) -> tuple[convert.Style, list[Path]]:
    """Public URLs for everything; rendered PNGs are published via static/."""
    publish_dir = REPO / "static" / "images" / "crosspost" / b["slug"]
    published: list[Path] = []

    def locate(ref):
        if isinstance(ref, Path):
            publish_dir.mkdir(parents=True, exist_ok=True)
            dest = publish_dir / ref.name
            if not dest.exists() or not same_pixels(dest, ref):
                shutil.copyfile(ref, dest)
            published.append(dest)
            return f"{b['site']}/images/crosspost/{b['slug']}/{ref.name}"
        return f"{b['site']}{ref}"

    return convert.Style(locate=locate, tables="markdown", captions="figcaption", escape_dollars=False), published


def same_pixels(a: Path, b: Path) -> bool:
    """Re-rendering a diagram gives different PNG bytes but the same image."""
    if a.read_bytes() == b.read_bytes():
        return True
    from PIL import Image, ImageChops

    with Image.open(a) as ia, Image.open(b) as ib:
        if ia.size != ib.size:
            return False
        return ImageChops.difference(ia.convert("RGBA"), ib.convert("RGBA")).getbbox() is None


def unpublished_files(paths: list[Path]) -> list[str]:
    """Files git doesn't have committed as they are now."""
    if not paths:
        return []
    rel = [str(p.relative_to(REPO)) for p in paths]
    res = subprocess.run(["git", "status", "--porcelain", "--", *rel], cwd=REPO, capture_output=True, text=True)
    return [line[3:] for line in res.stdout.splitlines()]


def devto_prepare(b: dict) -> dict:
    from crosspost.devto import normalize_tags

    meta = b["meta"]
    style, published = devto_style(b)
    md = convert.rewrite(
        b["body"], b["analysis"], REPO, b["mermaid_pngs"], {}, b["overrides"], b["permalink"], style
    )
    tags, dropped = normalize_tags(meta.get("devto_tags") or meta.get("tags") or [])
    description = shorten(str(meta.get("description") or ""), SUBTITLE_MAX)
    main_image = f"{b['site']}{b['cover']}" if b["cover"] else None
    (b["out"] / "devto.md").write_text(md)
    write_preview(b["out"] / "preview-devto.html", meta.get("title", b["slug"]), description, md)
    pending = unpublished_files(sorted(set(published)))
    print("\n[Dev.to]")
    print(f"  Canonical:   {b['permalink']}")
    print(f"  Tags:        {', '.join(tags) or 'none'}" + (f" (dropped: {', '.join(dropped)}; set `devto_tags:`)" if dropped else ""))
    print(f"  AI label:    {meta.get('ai_disclosure') or 'some_ai'}")
    print(f"  Preview:     {b['out']}/preview-devto.html")
    if pending:
        print("  Images to commit and deploy before the live run:")
        for p in pending:
            print(f"    {p}")
    return {"markdown": md, "tags": tags, "description": description, "main_image": main_image}


def devto_connect():
    if not DEVTO_KEY.exists():
        raise guard.Stop(f"no Dev.to API key at {DEVTO_KEY}; run with --save-devto-key first")
    mode = stat.S_IMODE(DEVTO_KEY.stat().st_mode)
    if mode & 0o077:
        raise guard.Stop(f"{DEVTO_KEY} is mode {oct(mode)}; run `chmod 600 {DEVTO_KEY}`")
    from crosspost.devto import DevtoTarget

    try:
        target = DevtoTarget(DEVTO_KEY.read_text().strip())
    except Exception as exc:
        raise guard.Stop(
            f"Dev.to sign-in failed ({exc}). Check the key, or make a new one and run --save-devto-key."
        ) from exc
    print(f"  Account: {target.account}")
    return target


def devto_live(b: dict, prep: dict) -> str:
    from crosspost.devto import ArticleSpec

    target = devto_connect()
    spec = ArticleSpec(
        title=b["meta"]["title"],
        description=prep["description"],
        markdown=prep["markdown"],
        canonical_url=b["permalink"],
        main_image=prep["main_image"],
        tags=prep["tags"],
        ai_disclosure=b["meta"].get("ai_disclosure") or "some_ai",
    )
    draft = guard.create_once(target, Ledger(DEVTO_DIR), b["permalink"], spec)
    print(f"  ✓ Draft created (not published): {draft['url']}")
    return draft["url"]


# ------------------------------------------------------------------ secrets


def _save_secret(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(content)
    os.chmod(path, 0o600)


def _read_secret(prompt: str) -> str:
    """From a pipe (e.g. `pbpaste | ... --save-cookies`), else a hidden prompt.

    macOS terminals cap one typed line at 1024 characters, and a Substack
    Cookie header is longer, so the pipe is the way that works for cookies.
    """
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    print(prompt)
    return getpass.getpass("> ").strip()


def save_cookies() -> None:
    raw = _read_secret(
        "Paste the Cookie header (input hidden). If it won't paste, it's too long for the\n"
        "terminal: copy it, then run  pbpaste | .venv/bin/python export.py --save-cookies"
    )
    cookies = dict(p.strip().split("=", 1) for p in raw.split(";") if "=" in p)
    if "substack.sid" not in cookies:
        fail("no substack.sid in what you pasted; copy the whole Cookie header")
    _save_secret(COOKIES, json.dumps(cookies))
    print(f"Saved {len(cookies)} cookies to {COOKIES} (mode 600).")


def save_devto_key() -> None:
    key = _read_secret("Paste your Dev.to API key (dev.to/settings/extensions; input hidden):")
    if not key or " " in key:
        fail("that doesn't look like an API key")
    _save_secret(DEVTO_KEY, key)
    print(f"Saved the key to {DEVTO_KEY} (mode 600).")


# ------------------------------------------------------------------ main


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("post", nargs="?", type=Path)
    ap.add_argument("--to", choices=[*TARGETS, "both"], help="where to create the draft")
    ap.add_argument("--dry-run", action="store_true", help="convert and preview locally; nothing is sent")
    ap.add_argument("--publication", help="Substack publication URL, e.g. https://you.substack.com")
    ap.add_argument("--resolve-pending", action="store_true",
                    help="clear an unknown-outcome create after you've checked the dashboard")
    ap.add_argument("--save-cookies", action="store_true", help="store Substack session cookies (mode 600)")
    ap.add_argument("--save-devto-key", action="store_true", help="store your Dev.to API key (mode 600)")
    args = ap.parse_args()

    if args.save_cookies:
        return save_cookies()
    if args.save_devto_key:
        return save_devto_key()
    if not args.post or not args.to:
        ap.error("a post path and --to substack|devto|both are required")
    post = args.post.resolve()
    targets = list(TARGETS) if args.to == "both" else [args.to]

    if args.resolve_pending:
        if len(targets) != 1:
            ap.error("--resolve-pending works on one target at a time")
        try:
            permalink = hugo.published_permalink(REPO, post)
            if targets[0] == "substack":
                target, home = substack_connect(args.publication), SUBSTACK_DIR
            else:
                target, home = devto_connect(), DEVTO_DIR
            guard.resolve_pending(target, Ledger(home), permalink)
        except (guard.Stop, Locked, hugo.NotLive) as exc:
            fail(str(exc))
        return

    b = build(post, targets)
    report(b)
    preps = {
        t: (substack_prepare(b) if t == "substack" else devto_prepare(b)) for t in targets
    }
    if args.dry_run:
        print("\nDry run: nothing sent.")
        return

    results: dict[str, str] = {}
    for t in targets:
        print(f"\n[{'Substack' if t == 'substack' else 'Dev.to'} live]")
        try:
            if t == "substack":
                results[t] = "✓ " + substack_live(b, preps[t], args.publication)
            else:
                results[t] = "✓ " + devto_live(b, preps[t])
        except guard.AlreadyExists as exc:
            results[t] = f"= already there: {exc.url}"
            print(f"  = Already there (nothing created): {exc.url}")
        except (guard.Stop, Locked) as exc:
            results[t] = f"✗ {exc}"
            print(f"  ✗ {exc}", file=sys.stderr)
    sys.stdout.flush()
    print("\nSummary:")
    for t, r in results.items():
        print(f"  {t:9} {r.splitlines()[0]}")
    if any(r.startswith("✗") for r in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
