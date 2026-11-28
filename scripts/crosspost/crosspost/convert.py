"""Turn a Hugo post's Markdown into Markdown that python-substack converts faithfully.

What Substack can't take as-is gets rewritten here:
  - ```mermaid blocks  -> a rendered PNG (the blog draws them in the browser)
  - tables             -> a header-labelled bullet list, plus a PNG for big tables
  - /images/... paths  -> absolute paths into static/, which python-substack uploads
  - bare `$` in prose  -> `\\$`, so python-substack's math plugin leaves prices alone
  - <video> blocks     -> the poster image plus a link to the video on the blog

Anything else it would drop or mangle (shortcodes, raw HTML, images that share a
paragraph with text, image paths outside /images/) is a blocking error.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdit_py_plugins.footnote import footnote_plugin

SIMPLE_TABLE_MAX_COLS = 3
SIMPLE_TABLE_MAX_ROWS = 8
SIMPLE_TABLE_MAX_CELL = 60


class UnsupportedContent(Exception):
    """The post contains syntax the Substack draft would silently lose."""

    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("\n".join(problems))


@dataclass
class Table:
    headers: list[str]
    rows: list[list[str]]
    start: int  # 0-based first line in the body
    end: int  # 0-based line after the table

    @property
    def is_simple(self) -> bool:
        cells = self.headers + [c for r in self.rows for c in r]
        return (
            len(self.headers) <= SIMPLE_TABLE_MAX_COLS
            and len(self.rows) <= SIMPLE_TABLE_MAX_ROWS
            and all(len(c) <= SIMPLE_TABLE_MAX_CELL for c in cells)
        )


@dataclass
class Mermaid:
    source: str
    start: int
    end: int

    def alt(self, n: int) -> str:
        # Mermaid's own accessibility lines, which the blog's diagram already uses.
        for key in ("accDescr", "accTitle"):
            m = re.search(rf"^\s*{key}\s*:\s*(.+)$", self.source, re.M)
            if m:
                return m.group(1).strip()
        for line in self.source.splitlines():
            line = line.strip()
            if line.startswith("%%") and not line.startswith("%%{"):
                return f"Diagram: {line.lstrip('%').strip()}"
        return f"Diagram {n}"


@dataclass
class Figure:
    """A paragraph holding one image, optionally followed by an *italic caption* line."""

    src: str
    alt: str
    caption: str | None
    start: int
    end: int


@dataclass
class Video:
    """A raw <video> block: neither target hosts video, so it becomes its poster plus a link."""

    poster: str  # /images/... (the picture readers see)
    src: str  # /videos/... (where the link goes)
    alt: str
    start: int
    end: int


@dataclass
class Analysis:
    tables: list[Table] = field(default_factory=list)
    mermaids: list[Mermaid] = field(default_factory=list)
    figures: list[Figure] = field(default_factory=list)
    videos: list[Video] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    footnote_refs: int = 0
    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def make_parser() -> MarkdownIt:
    # CommonMark leaves tables off; Hugo (Goldmark) has them on.
    return MarkdownIt("commonmark").use(footnote_plugin).enable("table")


def _inline_text(tok: Token) -> str:
    return tok.content.strip()


def _extract_table(tokens: list[Token], i: int) -> tuple[Table, int]:
    open_tok = tokens[i]
    headers: list[str] = []
    rows: list[list[str]] = []
    current: list[str] | None = None
    in_head = False
    j = i + 1
    while tokens[j].type != "table_close":
        t = tokens[j]
        if t.type == "thead_open":
            in_head = True
        elif t.type == "thead_close":
            in_head = False
        elif t.type == "tr_open":
            current = []
        elif t.type == "tr_close":
            if in_head:
                headers = current or []
            else:
                rows.append(current or [])
            current = None
        elif t.type == "inline" and current is not None:
            current.append(_inline_text(t))
        j += 1
    start, end = open_tok.map
    return Table(headers, rows, start, end), j


_SHORTCODE = re.compile(r"\{\{[<%]")


def analyze(body: str, line_offset: int = 0) -> Analysis:
    """Find everything that needs converting or blocks conversion.

    line_offset turns body line numbers into file line numbers for messages.
    """
    a = Analysis()
    tokens = make_parser().parse(body)

    def where(tok: Token) -> str:
        return f"line {tok.map[0] + 1 + line_offset}" if tok.map else "unknown line"

    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t.type == "table_open":
            table, i = _extract_table(tokens, i)
            a.tables.append(table)
        elif t.type == "fence" and t.info.strip().split(" ")[0] == "mermaid":
            a.mermaids.append(Mermaid(t.content, t.map[0], t.map[1]))
        elif t.type == "html_block" and t.content.lstrip().lower().startswith("<video"):
            _check_video(t, a, where(t))
        elif t.type == "html_block":
            a.problems.append(f"{where(t)}: raw HTML block ({t.content.strip()[:60]!r})")
        elif t.type == "inline":
            _check_inline(t, tokens, i, a, where(t))
        i += 1
    return a


def _attr(html: str, name: str) -> str | None:
    m = re.search(rf'\b{name}\s*=\s*"([^"]*)"', html)
    return m.group(1) if m else None


def _check_video(tok: Token, a: Analysis, where: str) -> None:
    """Accept <video poster="/images/..."> with one <source src="/videos/...">; block anything else."""
    html = tok.content
    opening = html.split(">", 1)[0]
    poster = _attr(opening, "poster")
    sources = re.findall(r'<source\b[^>]*\bsrc\s*=\s*"([^"]*)"', html)
    alt = _attr(opening, "aria-label") or ""
    if not poster or not poster.startswith("/images/"):
        a.problems.append(f'{where}: <video> needs poster="/images/..." to stand in for it')
        return
    if len(sources) != 1 or not sources[0].startswith("/videos/"):
        a.problems.append(f'{where}: <video> needs exactly one <source src="/videos/...">')
        return
    if not alt.strip():
        a.warnings.append(f"{where}: <video> has no aria-label, so its poster has no alt text")
    a.images.append(poster)
    a.videos.append(Video(poster, sources[0], alt, tok.map[0], tok.map[1]))


def _caption_of(children: list[Token]) -> tuple[str | None, bool]:
    """For [image, softbreak, em_open, ..., em_close], return (caption, ok).

    ok is False when the paragraph holds anything other than a lone image or the
    blog's image-plus-italic-caption pattern.
    """
    kids = [c for c in children if not (c.type == "text" and not c.content.strip())]
    if len(kids) == 1 and kids[0].type == "image":
        return None, True
    if (
        len(kids) >= 4
        and kids[0].type == "image"
        and kids[1].type == "softbreak"
        and kids[2].type == "em_open"
        and kids[-1].type == "em_close"
    ):
        inner = kids[3:-1]
        if all(k.type in ("text", "code_inline") for k in inner):
            return "".join(k.content for k in inner).strip(), True
    return None, False


def _check_inline(tok: Token, tokens: list[Token], idx: int, a: Analysis, where: str):
    children = tok.children or []
    in_paragraph = idx > 0 and tokens[idx - 1].type == "paragraph_open"
    images = [c for c in children if c.type == "image"]
    for c in children:
        if c.type == "text" and _SHORTCODE.search(c.content):
            a.problems.append(f"{where}: Hugo shortcode ({c.content.strip()[:60]!r})")
        elif c.type == "html_inline":
            a.problems.append(f"{where}: inline HTML ({c.content!r})")
        elif c.type == "footnote_ref":
            a.footnote_refs += 1
    for img in images:
        src = img.attrs.get("src", "")
        a.images.append(src)
        if not src.startswith("/images/"):
            a.problems.append(f"{where}: image path outside /images/ ({src})")
        if not img.content.strip():
            a.warnings.append(f"{where}: image has no alt text ({src})")
    if not images:
        return
    caption, ok = _caption_of(children)
    if in_paragraph and ok:
        img = images[0]
        a.figures.append(Figure(img.attrs.get("src", ""), img.content, caption, tok.map[0], tok.map[1]))
    else:
        a.problems.append(
            f"{where}: image shares its paragraph with other content; "
            f"Substack would show only its alt text ({images[0].attrs.get('src', '')})"
        )


# ---------------------------------------------------------------- rewriting


def table_to_list(table: Table) -> str:
    headers = [h or f"Column {n}" for n, h in enumerate(table.headers, start=1)]
    lines = []
    for row in table.rows:
        parts = []
        for n, header in enumerate(headers):
            value = row[n] if n < len(row) else ""
            parts.append(f"**{header}:** {value or '—'}")
        lines.append("- " + " · ".join(parts))
    return "\n".join(lines)


_CODE_SPAN = re.compile(r"(`+)(?:.+?)\1", re.S)


def escape_dollars(text: str) -> str:
    """Escape `$` outside code spans so it can't open a math span."""
    out = []
    pos = 0
    for m in _CODE_SPAN.finditer(text):
        out.append(re.sub(r"(?<!\\)\$", r"\\$", text[pos : m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(re.sub(r"(?<!\\)\$", r"\\$", text[pos:]))
    return "".join(out)


def _fence_ranges(body: str) -> list[tuple[int, int]]:
    return [
        tuple(t.map)
        for t in make_parser().parse(body)
        if t.type in ("fence", "code_block") and t.map
    ]


def _md_image(alt: str, path: Path | str, caption: str | None = None) -> str:
    alt = alt.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")
    target = str(path)
    if any(c in target for c in " ()<>"):
        target = f"<{target}>"  # CommonMark form; only when the path needs it
    if caption:
        caption = caption.replace("\\", "\\\\").replace('"', '\\"')
        return f'![{alt}]({target} "{caption}")'
    return f"![{alt}]({target})"


def local_image_path(repo: Path, src: str) -> Path:
    return (repo / "static" / src.lstrip("/")).resolve()


@dataclass
class Style:
    """How one target wants the shared conversion written out.

    locate turns an image (a /images/ src from the post, or a rendered file
    under out/) into the reference the target can use: a local path for
    targets that upload, a public URL for targets that can't.
    """

    locate: Callable[[str | Path], str]
    tables: str = "list"  # "list": list (+ PNG when big); "markdown": keep the table
    captions: str = "title"  # "title": ![alt](src "caption"); "figcaption": HTML line
    escape_dollars: bool = True


def substack_style(repo: Path) -> Style:
    def locate(ref):
        if isinstance(ref, Path):
            return str(ref.resolve())
        return str(local_image_path(repo, ref))

    return Style(locate=locate, tables="list", captions="title", escape_dollars=True)


def figure_markdown(style: Style, alt: str, ref, caption: str | None) -> str:
    target = style.locate(ref)
    if caption and style.captions == "figcaption":
        safe = caption.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return _md_image(alt, target) + f"\n<figcaption>{safe}</figcaption>"
    return _md_image(alt, target, caption)


def rewrite(
    body: str,
    analysis: Analysis,
    repo: Path,
    mermaid_pngs: list[Path],
    table_pngs: dict[int, Path],
    image_overrides: dict[str, Path],
    permalink: str,
    style: Style | None = None,
) -> str:
    """Produce the target-ready Markdown.

    mermaid_pngs is parallel to analysis.mermaids. table_pngs maps a table's
    index in analysis.tables to its PNG (big tables only). image_overrides maps
    an original /images/ src to a substitute file (e.g. an SVG rasterized to PNG).
    """
    style = style or substack_style(repo)
    lines = body.split("\n")
    code_ranges = _fence_ranges(body)

    replacements: list[tuple[int, int, str]] = []
    for n, (m, png) in enumerate(zip(analysis.mermaids, mermaid_pngs, strict=True), start=1):
        replacements.append((m.start, m.end, _md_image(m.alt(n), style.locate(png))))
    if style.tables == "list":
        for n, table in enumerate(analysis.tables):
            block = table_to_list(table)
            if n in table_pngs:
                alt = "Table: " + ", ".join(h for h in table.headers if h)
                block = _md_image(alt, style.locate(table_pngs[n])) + "\n\n" + block
            replacements.append((table.start, table.end, block))
    for fig in analysis.figures:
        ref = image_overrides.get(fig.src) or fig.src
        replacements.append((fig.start, fig.end, figure_markdown(style, fig.alt, ref, fig.caption)))
    site = "{0.scheme}://{0.netloc}".format(urlsplit(permalink))
    for v in analysis.videos:
        block = _md_image(v.alt, style.locate(v.poster)) + f"\n\n[▶ Watch the video on the blog]({site}{v.src})"
        replacements.append((v.start, v.end, block))

    replaced: set[int] = set()
    for start, end, _ in replacements:
        replaced.update(range(start, end))
    if style.escape_dollars:
        for ln in range(len(lines)):
            if ln in replaced or any(s <= ln < e for s, e in code_ranges):
                continue
            lines[ln] = escape_dollars(lines[ln])

    for start, end, text in sorted(replacements, key=lambda r: r[0], reverse=True):
        lines[start:end] = text.split("\n")

    out = "\n".join(lines).rstrip() + "\n"
    out += f"\n---\n\n*Originally published at [{permalink}]({permalink}).*\n"
    return out


def check_images_exist(analysis: Analysis, repo: Path) -> list[str]:
    missing = []
    for src in analysis.images:
        if src.startswith("/images/"):
            p = local_image_path(repo, src)
            if not p.is_file():
                missing.append(f"image file not found: {p}")
    return missing
