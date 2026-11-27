"""Dev.to target and style, against a fake Forem API."""

from pathlib import Path

import pytest
import requests

from crosspost import convert, devto, guard
from crosspost.ledger import CREATED, PENDING, Ledger, key

LINK = "https://holtonma.github.io/posts/x/"
REPO = Path(__file__).resolve().parents[3]


class Resp:
    def __init__(self, status, data):
        self.status_code, self._data = status, data

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}", response=self)


class FakeForem(requests.Session):
    def __init__(self):
        super().__init__()
        self.articles: list[dict] = []
        self.posts: list[dict] = []
        self.create_status = 201
        self.list_fails = False

    def get(self, url, params=None, timeout=None):
        if url.endswith("/users/me"):
            return Resp(200, {"username": "mark"})
        if url.endswith("/articles/me/all"):
            if self.list_fails:
                return Resp(500, {})
            page, per = params["page"], params["per_page"]
            return Resp(200, self.articles[(page - 1) * per : page * per])
        raise AssertionError(url)

    def post(self, url, json=None, timeout=None):
        self.posts.append(json)
        if self.create_status == "timeout":
            self.articles.append({"id": 7, "canonical_url": json["article"]["canonical_url"], "url": "https://dev.to/mark/x"})
            raise requests.Timeout("read timed out")
        if self.create_status != 201:
            return Resp(self.create_status, {"error": "nope"})
        art = {"id": 7, "canonical_url": json["article"]["canonical_url"], "url": "https://dev.to/mark/x-tmp"}
        self.articles.append(art)
        return Resp(201, art)


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(devto.requests, "head", lambda url, **kw: Resp(200, None))
    s = FakeForem()
    return devto.DevtoTarget("k", session=s), s, Ledger(tmp_path)


def spec(md="Hello.\n\n![a](https://holtonma.github.io/images/a.png)\n"):
    return devto.ArticleSpec("T", "D", md, LINK, "https://holtonma.github.io/images/c.jpg", ["ai"])


def test_creates_a_draft_never_published(env):
    t, s, ledger = env
    d = guard.create_once(t, ledger, LINK, spec(), log=lambda m: None)
    assert d["url"] == "https://dev.to/mark/x-tmp/edit"
    art = s.posts[0]["article"]
    assert art["published"] is False and art["canonical_url"] == LINK
    assert art["body_markdown"].startswith(
        "---\nai_disclosure_level: some_ai\ntags: ai\n"
        "cover_image: https://holtonma.github.io/images/c.jpg\n"
        f"canonical_url: {LINK}\n---\n"
    )


def test_second_run_and_lost_ledger_both_refuse(env):
    t, s, ledger = env
    guard.create_once(t, ledger, LINK, spec(), log=lambda m: None)
    with pytest.raises(guard.Stop, match="already exists"):
        guard.create_once(t, ledger, LINK, spec(), log=lambda m: None)
    ledger.clear(key(t.account, LINK))
    with pytest.raises(guard.Stop, match="already exists"):
        guard.create_once(t, ledger, LINK, spec(), log=lambda m: None)
    assert len(s.posts) == 1


def test_422_clears_and_timeout_is_pending(env):
    t, s, ledger = env
    s.create_status = 422
    with pytest.raises(guard.Stop, match="nothing was created"):
        guard.create_once(t, ledger, LINK, spec(), log=lambda m: None)
    assert ledger.get(key(t.account, LINK)) is None
    s.create_status = "timeout"
    with pytest.raises(guard.Stop, match="may exist"):
        guard.create_once(t, ledger, LINK, spec(), log=lambda m: None)
    assert ledger.get(key(t.account, LINK))["state"] == PENDING
    s.create_status = 201
    with pytest.raises(guard.Stop, match="recovered"):
        guard.create_once(t, ledger, LINK, spec(), log=lambda m: None)
    assert ledger.get(key(t.account, LINK))["state"] == CREATED
    assert len(s.posts) == 2  # the 422 and the timeout; never a third


def test_listing_failure_stops_before_create(env):
    t, s, ledger = env
    s.list_fails = True
    with pytest.raises(guard.AmbiguousLookup):
        guard.create_once(t, ledger, LINK, spec(), log=lambda m: None)
    assert s.posts == []


def test_image_not_live_stops(env, monkeypatch):
    t, s, ledger = env
    monkeypatch.setattr(devto.requests, "head", lambda url, **kw: Resp(404, None))
    with pytest.raises(guard.Stop, match="not live yet"):
        guard.create_once(t, ledger, LINK, spec(), log=lambda m: None)
    assert s.posts == [] and ledger.get(key(t.account, LINK)) is None


def test_local_path_and_liquid_stop(env):
    t, s, ledger = env
    with pytest.raises(guard.Stop) as e:
        guard.create_once(t, ledger, LINK, spec("![a](</tmp/a.png>)\n\n`{{ x }}`\n"), log=lambda m: None)
    assert "not a public https URL" in str(e.value) and "Liquid" in str(e.value)
    assert s.posts == []


def test_tags_are_normalized_and_capped():
    kept, dropped = devto.normalize_tags(["AI", "Agents", "Sub-Agents", "Claude Code", "Architecture", "ai"])
    assert kept == ["ai", "agents", "subagents", "claudecode"] and dropped == ["architecture"]


def test_devto_style_keeps_tables_and_dollars_and_uses_figcaption():
    body = "| A | B |\n|---|---|\n| $1 | 2 |\n\n![Alt](/images/x.png)\n*Cap & more*\n\nCost $5.\n"
    a = convert.analyze(body)
    style = convert.Style(locate=lambda r: f"https://site{r}", tables="markdown", captions="figcaption", escape_dollars=False)
    md = convert.rewrite(body, a, REPO, [], {}, {}, LINK, style)
    assert "| $1 | 2 |" in md and "Cost $5." in md
    assert "![Alt](https://site/images/x.png)\n<figcaption>Cap &amp; more</figcaption>" in md
