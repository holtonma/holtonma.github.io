"""Render what Substack can't draw itself into PNGs: mermaid, big tables, SVGs."""

from __future__ import annotations

import html
import subprocess
from pathlib import Path

from markdown_it import MarkdownIt

from .convert import Table

HERE = Path(__file__).resolve().parent.parent
MMDC = HERE / "node_modules" / ".bin" / "mmdc"

MERMAID_WIDTH = 1200
TABLE_WIDTH = 1000
SCALE = 2

_TABLE_CSS = """
body { margin: 0; padding: 16px; background: #fff;
       font: 15px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
       color: #1f2328; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #d0d7de; padding: 8px 12px; text-align: left; vertical-align: top; }
th { background: #f6f8fa; font-weight: 600; }
tr:nth-child(even) td { background: #fbfcfd; }
code { font: 13px ui-monospace, SFMono-Regular, Menlo, monospace; background: #eff1f3;
       padding: 1px 4px; border-radius: 4px; }
"""


def render_mermaid(source: str, out: Path) -> Path:
    if not MMDC.exists():
        raise RuntimeError(f"mermaid-cli not installed; run `npm ci` in {HERE}")
    src = out.with_suffix(".mmd")
    src.write_text(source)
    subprocess.run(
        [str(MMDC), "-i", str(src), "-o", str(out), "-t", "neutral", "-b", "white",
         "--size", str(MERMAID_WIDTH), "-s", str(SCALE), "-q"],
        check=True,
    )
    return out


def _table_html(table: Table) -> str:
    md = MarkdownIt("commonmark")
    head = "".join(f"<th>{md.renderInline(h)}</th>" for h in table.headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{md.renderInline(c)}</td>" for c in row) + "</tr>"
        for row in table.rows
    )
    return (
        f"<!doctype html><meta charset='utf-8'><style>{_TABLE_CSS}</style>"
        f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
    )


class Screenshotter:
    """One headless Chromium for all table and SVG renders in a run."""

    def __enter__(self):
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch()
        return self

    def __exit__(self, *exc):
        self._browser.close()
        self._pw.stop()

    def _page(self, width: int):
        return self._browser.new_page(
            viewport={"width": width, "height": 600}, device_scale_factor=SCALE
        )

    def table(self, table: Table, out: Path) -> Path:
        page = self._page(TABLE_WIDTH)
        page.set_content(_table_html(table))
        page.locator("body").screenshot(path=str(out))
        page.close()
        return out

    def svg(self, svg_path: Path, out: Path, width: int = MERMAID_WIDTH) -> Path:
        page = self._page(width)
        page.set_content(
            "<!doctype html><style>body{margin:0;background:#fff}"
            "img{display:block;max-width:100%;height:auto}</style>"
            f"<img src='data:image/svg+xml;charset=utf-8,{html.escape(_quote(svg_path.read_text()))}'>"
        )
        page.wait_for_load_state("load")
        page.locator("img").screenshot(path=str(out))
        page.close()
        return out


def _quote(text: str) -> str:
    from urllib.parse import quote

    return quote(text)
