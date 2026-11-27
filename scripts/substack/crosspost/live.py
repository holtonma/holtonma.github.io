"""The only code that talks to Substack. It creates drafts; it never publishes or sends.

Duplicate rules (no override exists):
  1. Hold an exclusive per-post lock for the whole run.
  2. Ledger says `created` -> fetch that draft; if it exists, stop with its URL.
  3. Always search Substack (drafts + published, full bodies) for the exact
     permalink before creating. A match is recorded and stops the run.
  4. Any lookup that errors or returns something unexpected stops the run.
  5. Write `creating` before the single create request; `created` after.
     Errors/timeouts -> `pending`. `creating`/`pending` block all later runs
     until a search finds the draft or Mark resolves it with --resolve-pending.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .ledger import CREATED, CREATING, PENDING, Ledger, key

PAGE = 25
MAX_ITEMS = 5000
# Validation refusals (e.g. 400 "Subtitle is too long"): definitive, nothing created.
# Timeouts, 5xx, 408/409/429 and missing ids stay ambiguous -> pending.
REJECTED = {400, 422}


class Stop(Exception):
    """End the run without creating anything. The message says why and what to do."""


class AmbiguousLookup(Stop):
    pass


@dataclass
class DraftSpec:
    title: str
    subtitle: str
    markdown: str
    cover_image: Path | None


def base_url(api) -> str:
    return api.publication_url.removesuffix("/").removesuffix("/api/v1")


def editor_url(api, draft_id) -> str:
    return f"{base_url(api)}/publish/post/{draft_id}"


def _status(exc) -> int | None:
    return getattr(exc, "status_code", None)


def _items(resp, what: str) -> list[dict]:
    if isinstance(resp, list):
        return resp
    if isinstance(resp, dict) and isinstance(resp.get("posts"), list):
        return resp["posts"]
    raise AmbiguousLookup(f"unexpected response listing {what}: {type(resp).__name__}")


def _contains(obj, permalink: str) -> bool:
    text = json.dumps(obj, ensure_ascii=False)
    return permalink in text or permalink.replace("/", "\\/") in text


def find_existing(api, permalink: str) -> dict | None:
    """Return {'id', 'url'} of any draft or post whose body holds the permalink."""
    seen: set = set()
    listings = [
        (f"{kind} posts", lambda off, kind=kind: api.post_management(kind, off, PAGE))
        for kind in ("drafts", "scheduled", "published")
    ]
    for what, fetch in listings:
        offset = 0
        while True:
            try:
                page = _items(fetch(offset), what)
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
                if _contains(full, permalink):
                    return {"id": draft_id, "url": editor_url(api, draft_id)}
            if len(page) < PAGE:
                break
            offset += PAGE
            if offset >= MAX_ITEMS:
                raise AmbiguousLookup(f"stopped listing {what} after {MAX_ITEMS} items")
    return None


def _draft_still_exists(api, draft_id) -> bool:
    try:
        api.get_draft(draft_id)
        return True
    except Exception as exc:
        if _status(exc) == 404:
            return False
        raise AmbiguousLookup(f"could not check recorded draft {draft_id}: {exc}") from exc


def _pending_message(entry: dict, permalink: str) -> str:
    return (
        f"An earlier run's create request for {permalink} has an unknown outcome "
        f"(ledger state '{entry['state']}', {entry['updated']}). The draft may exist.\n"
        "Check the Substack dashboard (Drafts, Scheduled, Published). If no draft is "
        "there, run again with --resolve-pending. Nothing was created."
    )


def image_size(path: str) -> tuple[int, int]:
    from PIL import Image

    with Image.open(path) as im:
        return im.size


def fix_image_sizes(doc: dict, sizes: dict[str, tuple[int, int]]) -> int:
    """Set each image node's width/height to the real file's.

    python-substack 0.10.0 stamps every image 1456x819 (16:9), and Substack lays
    the image out at that ratio, squashing anything taller or wider.
    Returns how many nodes were fixed; raises if an image's size is unknown.
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


def create_draft(
    api,
    ledger: Ledger,
    publication: str,
    permalink: str,
    spec: DraftSpec,
    log: Callable[[str], None] = print,
    body_builder: Callable = build_body,
) -> dict:
    """Create exactly one draft for this permalink, or raise Stop."""
    k = key(publication, permalink)
    with ledger.post_lock(k):
        entry = ledger.get(k)
        if entry and entry["state"] in (CREATING, PENDING):
            found = find_existing(api, permalink)
            if found:
                ledger.set(k, CREATED, draft_id=found["id"], url=found["url"])
                raise Stop(f"Draft already exists (recovered from '{entry['state']}'): {found['url']}")
            raise Stop(_pending_message(entry, permalink))
        if entry and entry["state"] == CREATED:
            if _draft_still_exists(api, entry["draft_id"]):
                raise Stop(f"Draft already exists: {entry['url']}")
            log(f"Recorded draft {entry['draft_id']} was deleted on Substack; searching before creating.")

        found = find_existing(api, permalink)
        if found:
            ledger.set(k, CREATED, draft_id=found["id"], url=found["url"])
            raise Stop(f"Draft already exists: {found['url']}")

        body = body_builder(api, spec)  # image uploads happen here, before any create

        ledger.set(k, CREATING)
        try:
            resp = api.post_draft(body)
        except Exception as exc:
            if _status(exc) in REJECTED:
                # Substack validated the request and refused it: nothing was made.
                ledger.clear(k)
                raise Stop(f"Substack rejected the draft; nothing was created: {exc}") from exc
            ledger.set(k, PENDING, error=str(exc)[:300])
            raise Stop(
                f"Create request failed or timed out ({exc}). The draft may exist; "
                "check Substack by hand. Nothing will be retried."
            ) from exc
        draft_id = resp.get("id") if isinstance(resp, dict) else None
        if draft_id is None:
            ledger.set(k, PENDING, error="create response had no draft id")
            raise Stop("Create returned no draft id. The draft may exist; check Substack by hand.")
        url = editor_url(api, draft_id)
        ledger.set(k, CREATED, draft_id=draft_id, url=url)
    return {"id": draft_id, "url": url}


def set_cover(api, draft_id, image: Path) -> bool:
    """Try to set the draft's cover image; True only if Substack shows it took."""
    try:
        uploaded = api.get_image(str(image))
        url = uploaded.get("url")
        api.put_draft(draft_id, cover_image=url)
        return api.get_draft(draft_id).get("cover_image") == url
    except Exception:
        return False


def resolve_pending(
    api,
    ledger: Ledger,
    publication: str,
    permalink: str,
    ask: Callable[[str], str] = input,
    log: Callable[[str], None] = print,
) -> None:
    """Clear a creating/pending record after Mark confirms the dashboard. Never creates."""
    k = key(publication, permalink)
    with ledger.post_lock(k):
        entry = ledger.get(k)
        if not entry or entry["state"] not in (CREATING, PENDING):
            raise Stop("Nothing to resolve: no creating/pending record for this post.")
        found = find_existing(api, permalink)
        if found:
            ledger.set(k, CREATED, draft_id=found["id"], url=found["url"])
            log(f"Found the draft; recorded it: {found['url']}")
            return
        log(
            "The API search found no draft, but that alone isn't enough.\n"
            f"Open {base_url(api)}/publish/posts and check Drafts, Scheduled and Published.\n"
            "If you found NO matching draft, type the post's permalink to clear the record:"
        )
        if ask("> ").strip() != permalink:
            raise Stop("Confirmation did not match the permalink; the record is unchanged.")
        ledger.clear(k)
        log("Record cleared. The next run repeats every duplicate check before creating.")
