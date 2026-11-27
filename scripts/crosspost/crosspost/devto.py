"""Dev.to target: drafts through the official Forem API v1. Never publishes.

Dev.to has no image upload API, so every image must already be live at a
public URL. build() checks each one before anything is created.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import requests

from .guard import AmbiguousLookup, Stop

API = "https://dev.to/api"
ACCEPT = "application/vnd.forem.api-v1+json"
PER_PAGE = 100
MAX_PAGES = 50
MAX_TAGS = 4

_IMAGE = re.compile(r"!\[[^\]]*\]\(<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\)")
_LIQUID = re.compile(r"\{%|\{\{")


@dataclass
class ArticleSpec:
    title: str
    description: str
    markdown: str
    canonical_url: str
    main_image: str | None
    tags: list[str] = field(default_factory=list)
    ai_disclosure: str | None = "some_ai"


def normalize_tags(tags: list[str]) -> tuple[list[str], list[str]]:
    """Dev.to tags are lowercase alphanumeric, at most four. Returns (kept, dropped)."""
    out: list[str] = []
    dropped: list[str] = []
    for t in tags:
        norm = re.sub(r"[^a-z0-9]", "", str(t).lower())
        if not norm or norm in out:
            continue
        (out if len(out) < MAX_TAGS else dropped).append(norm)
    return out, dropped


def body_with_front_matter(spec: ArticleSpec) -> str:
    """Front matter Dev.to reads from the body.

    Spike (2026-11-27): once body_markdown has front matter, Dev.to takes tags
    and the cover image from it and ignores the API's `tags`/`main_image`.
    Canonical URL is set both ways, so it holds whichever wins.
    """
    lines = []
    if spec.ai_disclosure:
        lines.append(f"ai_disclosure_level: {spec.ai_disclosure}")
    if spec.tags:
        lines.append(f"tags: {', '.join(spec.tags)}")
    if spec.main_image:
        lines.append(f"cover_image: {spec.main_image}")
    lines.append(f"canonical_url: {spec.canonical_url}")
    return "---\n" + "\n".join(lines) + "\n---\n\n" + spec.markdown


class DevtoTarget:
    name = "Dev.to"
    dashboard = "your Dev.to dashboard (https://dev.to/dashboard: Posts, including drafts)"

    def __init__(self, api_key: str, session: requests.Session | None = None, timeout: int = 60):
        self.s = session or requests.Session()
        self.s.headers.update({"api-key": api_key, "Accept": ACCEPT})
        self.timeout = timeout
        self._urls: dict = {}
        me = self._get("/users/me")
        self.username = me["username"]
        self.account = f"https://dev.to/{self.username}"

    # ------------------------------------------------------------ plumbing

    def _get(self, path: str, **params):
        r = self.s.get(API + path, params=params or None, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def _articles(self):
        """Every article of mine, drafts included."""
        for page in range(1, MAX_PAGES + 1):
            try:
                items = self._get("/articles/me/all", page=page, per_page=PER_PAGE)
            except Exception as exc:
                raise AmbiguousLookup(f"could not list your Dev.to articles: {exc}") from exc
            if not isinstance(items, list):
                raise AmbiguousLookup(f"unexpected response listing articles: {type(items).__name__}")
            for item in items:
                if item.get("id") is None:
                    raise AmbiguousLookup("a listed Dev.to article has no id")
                yield item
            if len(items) < PER_PAGE:
                return
        raise AmbiguousLookup(f"stopped listing articles after {MAX_PAGES} pages")

    def url(self, draft_id) -> str:
        base = self._urls.get(draft_id)
        return f"{base}/edit" if base else f"https://dev.to/dashboard (article {draft_id})"

    # ------------------------------------------------------------ the guard's interface

    def find_existing(self, permalink: str) -> dict | None:
        for item in self._articles():
            if item.get("canonical_url") == permalink or permalink in (item.get("body_markdown") or ""):
                self._urls[item["id"]] = item.get("url")
                return {"id": item["id"], "url": self.url(item["id"])}
        return None

    def exists(self, draft_id) -> bool:
        return any(item["id"] == draft_id for item in self._articles())

    def build(self, spec: ArticleSpec) -> dict:
        problems = []
        for m in _LIQUID.finditer(spec.markdown):
            line = spec.markdown.count("\n", 0, m.start()) + 1
            problems.append(f"line {line}: `{m.group(0)}` would be read as a Liquid tag by Dev.to")
        urls = _IMAGE.findall(spec.markdown) + ([spec.main_image] if spec.main_image else [])
        for url in dict.fromkeys(urls):
            if not url.startswith("https://"):
                problems.append(f"image is not a public https URL: {url}")
                continue
            try:
                r = requests.head(url, allow_redirects=True, timeout=30)
                ok = r.status_code == 200
            except Exception:
                ok = False
            if not ok:
                problems.append(f"image not live yet (commit and deploy the blog first): {url}")
        if problems:
            raise Stop("Not sending to Dev.to:\n  " + "\n  ".join(problems))
        article = {
            "title": spec.title,
            "body_markdown": body_with_front_matter(spec),
            "published": False,
            "canonical_url": spec.canonical_url,
            "description": spec.description,
            "tags": ", ".join(spec.tags),
        }
        if spec.main_image:
            article["main_image"] = spec.main_image
        return {"article": article}

    def create(self, payload: dict):
        assert payload["article"]["published"] is False
        r = self.s.post(f"{API}/articles", json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def draft_id(self, resp):
        if not isinstance(resp, dict) or resp.get("id") is None:
            return None
        self._urls[resp["id"]] = resp.get("url")
        return resp["id"]
