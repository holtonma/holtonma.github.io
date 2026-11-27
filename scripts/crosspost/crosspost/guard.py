"""Create exactly one draft per (account, permalink) on any target. No override exists.

  1. Hold an exclusive per-post lock for the whole run.
  2. Ledger says `created` -> if that draft still exists, stop with its URL.
  3. Always search the target for the exact permalink before creating.
     A match is recorded and stops the run.
  4. Any lookup that errors or returns something unexpected stops the run.
  5. Write `creating` before the single create request; `created` after.
     A validation refusal (400/422) made nothing, so the record is cleared.
     Errors/timeouts/missing ids -> `pending`. `creating`/`pending` block all
     later runs until a search finds the draft or Mark resolves it with
     --resolve-pending after checking the dashboard himself.

A target provides:
  name, account, dashboard          labels and where Mark checks by hand
  find_existing(permalink)          {'id','url'} or None; raises AmbiguousLookup
  exists(draft_id)                  bool; raises AmbiguousLookup if unsure
  build(spec)                       payload; may upload files, never creates
  create(payload)                   the single create call
  draft_id(response), url(draft_id)
"""

from __future__ import annotations

from typing import Callable

from .ledger import CREATED, CREATING, PENDING, Ledger, key

# Validation refusals: definitive, nothing created.
# Timeouts, 5xx, 408/409/429 and missing ids stay ambiguous -> pending.
REJECTED = {400, 422}


class Stop(Exception):
    """End the run without creating anything. The message says why and what to do."""


class AmbiguousLookup(Stop):
    pass


class AlreadyExists(Stop):
    """Not a failure: this post already has its one draft (or post) on the target."""

    def __init__(self, url: str, note: str = ""):
        self.url = url
        super().__init__(f"Draft already exists{note}: {url}")


def status_of(exc) -> int | None:
    status = getattr(exc, "status_code", None)
    if status is None:
        response = getattr(exc, "response", None)
        status = getattr(response, "status_code", None)
    return status


def _pending_message(target, entry: dict, permalink: str) -> str:
    return (
        f"An earlier run's create request for {permalink} on {target.name} has an unknown "
        f"outcome (ledger state '{entry['state']}', {entry['updated']}). The draft may exist.\n"
        f"Check {target.dashboard}. If no draft is there, run again with --resolve-pending. "
        "Nothing was created."
    )


def create_once(target, ledger: Ledger, permalink: str, spec, log: Callable[[str], None] = print) -> dict:
    """Create exactly one draft for this permalink on this target, or raise Stop."""
    k = key(target.account, permalink)
    with ledger.post_lock(k):
        entry = ledger.get(k)
        if entry and entry["state"] in (CREATING, PENDING):
            found = target.find_existing(permalink)
            if found:
                ledger.set(k, CREATED, draft_id=found["id"], url=found["url"])
                raise AlreadyExists(found["url"], f" (recovered from '{entry['state']}')")
            raise Stop(_pending_message(target, entry, permalink))
        if entry and entry["state"] == CREATED:
            if target.exists(entry["draft_id"]):
                raise AlreadyExists(entry["url"])
            log(f"Recorded draft {entry['draft_id']} is gone from {target.name}; searching before creating.")

        found = target.find_existing(permalink)
        if found:
            ledger.set(k, CREATED, draft_id=found["id"], url=found["url"])
            raise AlreadyExists(found["url"])

        payload = target.build(spec)  # uploads/checks happen here, before any create

        ledger.set(k, CREATING)
        try:
            resp = target.create(payload)
        except Exception as exc:
            if status_of(exc) in REJECTED:
                ledger.clear(k)
                raise Stop(f"{target.name} rejected the draft; nothing was created: {exc}") from exc
            ledger.set(k, PENDING, error=str(exc)[:300])
            raise Stop(
                f"Create request failed or timed out ({exc}). The draft may exist; "
                f"check {target.dashboard}. Nothing will be retried."
            ) from exc
        draft_id = target.draft_id(resp)
        if draft_id is None:
            ledger.set(k, PENDING, error="create response had no draft id")
            raise Stop(f"Create returned no draft id. The draft may exist; check {target.dashboard}.")
        url = target.url(draft_id)
        ledger.set(k, CREATED, draft_id=draft_id, url=url)
    return {"id": draft_id, "url": url}


def resolve_pending(
    target,
    ledger: Ledger,
    permalink: str,
    ask: Callable[[str], str] = input,
    log: Callable[[str], None] = print,
) -> None:
    """Clear a creating/pending record after Mark confirms the dashboard. Never creates."""
    k = key(target.account, permalink)
    with ledger.post_lock(k):
        entry = ledger.get(k)
        if not entry or entry["state"] not in (CREATING, PENDING):
            raise Stop("Nothing to resolve: no creating/pending record for this post.")
        found = target.find_existing(permalink)
        if found:
            ledger.set(k, CREATED, draft_id=found["id"], url=found["url"])
            log(f"Found the draft; recorded it: {found['url']}")
            return
        log(
            "The API search found no draft, but that alone isn't enough.\n"
            f"Check {target.dashboard}.\n"
            "If you found NO matching draft, type the post's permalink to clear the record:"
        )
        if ask("> ").strip() != permalink:
            raise Stop("Confirmation did not match the permalink; the record is unchanged.")
        ledger.clear(k)
        log("Record cleared. The next run repeats every duplicate check before creating.")
