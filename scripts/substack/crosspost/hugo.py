"""Ask Hugo itself which posts are live and what their permalinks are."""

from __future__ import annotations

import csv
import io
import subprocess
from pathlib import Path


class NotLive(Exception):
    pass


def published_permalink(repo: Path, post: Path) -> str:
    """Return the post's permalink if Hugo considers it published, else raise NotLive.

    `hugo list published` leaves out drafts, future-dated and expired content.
    """
    result = subprocess.run(
        ["hugo", "list", "published"], cwd=repo, capture_output=True, text=True, check=True
    )
    rel = post.resolve().relative_to(repo.resolve()).as_posix()
    rows = list(csv.DictReader(io.StringIO(result.stdout)))
    if rows and "permalink" not in rows[0]:
        raise RuntimeError(f"`hugo list published` has no permalink column: {list(rows[0])}")
    for row in rows:
        if row.get("path") == rel:
            permalink = (row.get("permalink") or "").strip()
            if not permalink:
                raise NotLive(f"{rel}: Hugo lists it but gives no permalink")
            return permalink
    raise NotLive(f"{rel}: not live on Hugo (draft, future-dated, expired, or not found)")
