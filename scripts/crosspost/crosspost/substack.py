"""Substack target: drafts through python-substack. Never publishes or sends."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .guard import AmbiguousLookup, status_of

PAGE = 25
MAX_ITEMS = 5000


@dataclass
class DraftSpec:
    title: str
    subtitle: str
    markdown: str
    cover_image: Path | None


def base_url(api) -> str:
    return api.publication_url.removesuffix("/").removesuffix("/api/v1")


def _items(resp, what: str) -> list[dict]:
    if isinstance(resp, list):
        return resp
    if isinstance(resp, dict) and isinstance(resp.get("posts"), list):
        return resp["posts"]
    raise AmbiguousLookup(f"unexpected response listing {what}: {type(resp).__name__}")


def contains(obj, permalink: str) -> bool:
    text = json.dumps(obj, ensure_ascii=False)
    return permalink in text or permalink.replace("/", "\\/") in text


def image_size(path: str) -> tuple[int, int]:
    from PIL import Image

    with Image.open(path) as im:
        return im.size


def fix_image_sizes(doc: dict, sizes: dict[str, tuple[int, int]]) -> int:
    """Set each image node's width/height to the real file's.

    python-substack 0.10.0 stamps every image 1456x819 (16:9), and Substack's
    published page lays the image out at that ratio, squashing anything taller
    or wider. Returns how many nodes were fixed; raises if a size is unknown.
    """
    fixed = 0

    def walk(node):
        nonlocal fixed
        if isinstance(node, dict):
            if node.get("type") == "image2":
                attrs = node["attrs"]
                if attrs["src"] not in sizes:
                    raise ValueError(f"no known size for image {attrs['src']}")
                attrs["width"], attrs["height"] = sizes[attrs["src"]]
                fixed += 1
            for child in node.get("content") or []:
                walk(child)

    walk(doc)
    return fixed


def build_body(api, spec: DraftSpec) -> dict:
    """Upload images and build the draft JSON. Nothing is created yet."""
    from substack.post import Post

    sizes: dict[str, tuple[int, int]] = {}
    upload = api.get_image

    def recording_upload(path):
        result = upload(path)
        sizes[result["url"]] = image_size(path)
        return result

    post = Post(
        title=spec.title,
        subtitle=spec.subtitle or "",
        user_id=api.get_user_id(),
        audience="everyone",
        write_comment_permissions="everyone",
    )
    api.get_image = recording_upload
    try:
        post.from_markdown(spec.markdown, api=api)
    finally:
        api.get_image = upload
    fix_image_sizes(post.draft_body, sizes)
    return post.get_draft()


class SubstackTarget:
    name = "Substack"

    def __init__(self, api, body_builder: Callable = build_body):
        self.api = api
        self._body_builder = body_builder
        self.account = base_url(api)
        self.dashboard = f"the Substack dashboard ({self.account}/publish/posts: Drafts, Scheduled, Published)"

    def url(self, draft_id) -> str:
        return f"{self.account}/publish/post/{draft_id}"

    def find_existing(self, permalink: str) -> dict | None:
        """Any draft, scheduled or published post whose body holds the permalink."""
        api = self.api
        seen: set = set()
        for kind in ("drafts", "scheduled", "published"):
            what = f"{kind} posts"
            offset = 0
            while True:
                try:
                    page = _items(api.post_management(kind, offset, PAGE), what)
                except AmbiguousLookup:
                    raise
                except Exception as exc:
                    raise AmbiguousLookup(f"could not list {what}: {exc}") from exc
                for item in page:
                    draft_id = item.get("id")
                    if draft_id is None:
                        raise AmbiguousLookup(f"a listed item in {what} has no id")
                    if draft_id in seen:
                        continue
                    seen.add(draft_id)
                    try:
                        full = api.get_draft(draft_id)
                    except Exception as exc:
                        raise AmbiguousLookup(f"could not fetch {what} item {draft_id}: {exc}") from exc
                    if contains(full, permalink):
                        return {"id": draft_id, "url": self.url(draft_id)}
                if len(page) < PAGE:
                    break
                offset += PAGE
                if offset >= MAX_ITEMS:
                    raise AmbiguousLookup(f"stopped listing {what} after {MAX_ITEMS} items")
        return None

    def exists(self, draft_id) -> bool:
        try:
            self.api.get_draft(draft_id)
            return True
        except Exception as exc:
            if status_of(exc) == 404:
                return False
            raise AmbiguousLookup(f"could not check recorded draft {draft_id}: {exc}") from exc

    def build(self, spec: DraftSpec) -> dict:
        return self._body_builder(self.api, spec)

    def create(self, payload: dict):
        return self.api.post_draft(payload)

    @staticmethod
    def draft_id(resp):
        return resp.get("id") if isinstance(resp, dict) else None

    # ------------------------------------------------- after the draft exists

    def set_cover(self, draft_id, image: Path) -> bool:
        """Try to set the draft's cover image; True only if Substack shows it took."""
        try:
            uploaded = self.api.get_image(str(image))
            url = uploaded.get("url")
            self.api.put_draft(draft_id, cover_image=url)
            return self.api.get_draft(draft_id).get("cover_image") == url
        except Exception:
            return False

    def add_tags(self, draft_id, tags: list[str]) -> None:
        self.api.add_tags_to_post(draft_id, tags)
