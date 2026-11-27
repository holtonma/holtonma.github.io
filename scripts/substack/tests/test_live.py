"""The no-duplicate rules, against a fake Substack."""

import json

import pytest

from crosspost import live
from crosspost.ledger import CREATED, CREATING, PENDING, Ledger, Locked, key

PUB = "https://example.substack.com"
LINK = "https://holtonma.github.io/posts/x/"
SPEC = live.DraftSpec(title="T", subtitle="S", markdown=f"body\n\n[{LINK}]({LINK})", cover_image=None)


class NotFound(Exception):
    status_code = 404


class FakeApi:
    publication_url = PUB + "/api/v1"

    def __init__(self):
        self.drafts: dict[int, dict] = {}
        self.published: list[int] = []
        self.creates = 0
        self.create_behavior = "ok"
        self.list_fails = False
        self._next = 100

    def post_management(self, kind, offset, limit):
        if self.list_fails:
            raise RuntimeError("boom")
        if kind == "drafts":
            ids = [i for i in self.drafts if i not in self.published]
        elif kind == "published":
            ids = self.published
        else:
            ids = []
        return {"posts": [{"id": i} for i in ids[offset : offset + limit]]}

    def get_draft(self, draft_id):
        if draft_id not in self.drafts:
            raise NotFound()
        return self.drafts[draft_id]

    def post_draft(self, body):
        self.creates += 1
        if self.create_behavior == "timeout":
            self._store(body)  # Substack got it; we never hear back
            raise TimeoutError("read timed out")
        if self.create_behavior == "crash":
            self._store(body)
            raise KeyboardInterrupt
        if self.create_behavior == "rejected":
            exc = Exception("APIError(code=400): Subtitle is too long")
            exc.status_code = 400
            raise exc
        if self.create_behavior == "no_id":
            return {}
        return {"id": self._store(body)}

    def _store(self, body):
        self._next += 1
        self.drafts[self._next] = {"id": self._next, "draft_body": json.dumps(body)}
        return self._next


def fake_body(api, spec):
    return {"draft_title": spec.title, "md": spec.markdown}


@pytest.fixture
def env(tmp_path):
    return FakeApi(), Ledger(tmp_path)


def create(api, ledger):
    return live.create_draft(api, ledger, PUB, LINK, SPEC, log=lambda m: None, body_builder=fake_body)


def test_second_run_returns_existing_url(env):
    api, ledger = env
    first = create(api, ledger)
    with pytest.raises(live.Stop, match=first["url"]):
        create(api, ledger)
    assert api.creates == 1


def test_lost_ledger_entry_found_by_permalink(env):
    api, ledger = env
    first = create(api, ledger)
    ledger.clear(key(PUB, LINK))
    with pytest.raises(live.Stop, match=first["url"]):
        create(api, ledger)
    assert api.creates == 1
    assert ledger.get(key(PUB, LINK))["state"] == CREATED


def test_published_post_counts_as_existing(env):
    api, ledger = env
    first = create(api, ledger)
    api.published.append(first["id"])
    ledger.clear(key(PUB, LINK))
    with pytest.raises(live.Stop, match="already exists"):
        create(api, ledger)


def test_deleted_draft_searches_then_creates(env):
    api, ledger = env
    first = create(api, ledger)
    del api.drafts[first["id"]]
    second = create(api, ledger)
    assert second["id"] != first["id"] and api.creates == 2


def test_failed_listing_stops_without_creating(env):
    api, ledger = env
    api.list_fails = True
    with pytest.raises(live.AmbiguousLookup):
        create(api, ledger)
    assert api.creates == 0


def test_timeout_leaves_pending_and_never_retries(env):
    api, ledger = env
    api.create_behavior = "timeout"
    with pytest.raises(live.Stop, match="may exist"):
        create(api, ledger)
    assert api.creates == 1
    assert ledger.get(key(PUB, LINK))["state"] == PENDING


def test_pending_is_recovered_when_search_finds_the_draft(env):
    api, ledger = env
    api.create_behavior = "timeout"
    with pytest.raises(live.Stop):
        create(api, ledger)
    api.create_behavior = "ok"
    with pytest.raises(live.Stop, match="recovered from 'pending'"):
        create(api, ledger)
    assert api.creates == 1
    assert ledger.get(key(PUB, LINK))["state"] == CREATED


def test_pending_with_nothing_found_still_refuses(env):
    api, ledger = env
    api.create_behavior = "no_id"
    with pytest.raises(live.Stop):
        create(api, ledger)
    api.create_behavior = "ok"
    with pytest.raises(live.Stop, match="--resolve-pending"):
        create(api, ledger)
    assert api.creates == 1


def test_crash_after_intent_is_treated_as_pending(env):
    api, ledger = env
    api.create_behavior = "crash"
    with pytest.raises(KeyboardInterrupt):
        create(api, ledger)
    assert ledger.get(key(PUB, LINK))["state"] == CREATING
    # The draft did land; the next run finds it rather than creating another.
    api.create_behavior = "ok"
    with pytest.raises(live.Stop, match="recovered from 'creating'"):
        create(api, ledger)
    assert api.creates == 1


def test_crash_with_no_draft_needs_dashboard_confirmation(env):
    api, ledger = env
    ledger.set(key(PUB, LINK), CREATING)
    with pytest.raises(live.Stop, match="--resolve-pending"):
        create(api, ledger)
    with pytest.raises(live.Stop, match="did not match"):
        live.resolve_pending(api, ledger, PUB, LINK, ask=lambda _: "yes", log=lambda m: None)
    assert ledger.get(key(PUB, LINK))["state"] == CREATING
    live.resolve_pending(api, ledger, PUB, LINK, ask=lambda _: LINK, log=lambda m: None)
    assert ledger.get(key(PUB, LINK)) is None
    assert api.creates == 0  # resolving never creates


def test_concurrent_run_hits_the_lock(env):
    api, ledger = env
    with ledger.post_lock(key(PUB, LINK)):
        with pytest.raises(Locked):
            create(api, ledger)
    assert api.creates == 0


def test_validation_rejection_clears_record_and_allows_fixed_retry(env):
    api, ledger = env
    api.create_behavior = "rejected"
    with pytest.raises(live.Stop, match="nothing was created"):
        create(api, ledger)
    assert ledger.get(key(PUB, LINK)) is None
    api.create_behavior = "ok"
    create(api, ledger)
    assert api.creates == 2 and len(api.drafts) == 1


def test_image_sizes_replace_the_16_9_default():
    doc = {"type": "doc", "content": [
        {"type": "captionedImage", "content": [
            {"type": "image2", "attrs": {"src": "https://cdn/x.png", "width": 1456, "height": 819}}]},
        {"type": "footnote", "content": [{"type": "captionedImage", "content": [
            {"type": "image2", "attrs": {"src": "https://cdn/y.png", "width": 1456, "height": 819}}]}]},
    ]}
    n = live.fix_image_sizes(doc, {"https://cdn/x.png": (2400, 350), "https://cdn/y.png": (100, 900)})
    assert n == 2
    assert doc["content"][0]["content"][0]["attrs"] | {} == {"src": "https://cdn/x.png", "width": 2400, "height": 350}
    with pytest.raises(ValueError):
        live.fix_image_sizes(doc, {})
