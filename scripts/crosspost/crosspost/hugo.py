"""Ask Hugo itself which posts are live and what their permalinks are."""

from __future__ import annotations

import csv
import io
import subprocess
from pathlib import Path


class NotLive(Exception):
    pass


def _rows(repo: Path, which: str) -> list[dict]:
    result = subprocess.run(
        ["hugo", "list", which], cwd=repo, capture_output=True, text=True, check=True
    )
    rows = list(csv.DictReader(io.StringIO(result.stdout)))
    if rows and "permalink" not in rows[0]:
        raise RuntimeError(f"`hugo list {which}` has no permalink column: {list(rows[0])}")
    return rows


def _find(rows: list[dict], rel: str) -> dict | None:
    return next((row for row in rows if row.get("path") == rel), None)


def published_permalink(repo: Path, post: Path) -> str:
    """Return the post's permalink if Hugo considers it published, else raise NotLive.

    `hugo list published` leaves out drafts, future-dated and expired content.
    """
    rel = post.resolve().relative_to(repo.resolve()).as_posix()
    row = _find(_rows(repo, "published"), rel)
    if row is None:
        raise NotLive(f"{rel}: not live on Hugo (draft, future-dated, expired, or not found)")
    permalink = (row.get("permalink") or "").strip()
    if not permalink:
        raise NotLive(f"{rel}: Hugo lists it but gives no permalink")
    return permalink


def permalink(repo: Path, post: Path) -> tuple[str, bool]:
    """(permalink, live). For a post that isn't live yet, the URL it will have.

    Used by dry runs, so a new post's rendered images can be generated and
    committed in the same deploy as the post itself.
    """
    try:
        return published_permalink(repo, post), True
    except NotLive:
        pass
    rel = post.resolve().relative_to(repo.resolve()).as_posix()
    row = _find(_rows(repo, "all"), rel)
    url = (row or {}).get("permalink", "").strip()
    if not url:
        raise NotLive(f"{rel}: Hugo doesn't know this post (check the path and front matter)")
    return url, False
