from pathlib import Path

import pytest

from crosspost import hugo

REPO = Path("/repo")
POST = REPO / "content/posts/new.md"
ROW = {"path": "content/posts/new.md", "permalink": "https://site/posts/new/"}


def fake_rows(published, all_):
    return lambda repo, which: published if which == "published" else all_


def test_live_post(monkeypatch):
    monkeypatch.setattr(hugo, "_rows", fake_rows([ROW], [ROW]))
    assert hugo.permalink(REPO, POST) == ("https://site/posts/new/", True)
    assert hugo.published_permalink(REPO, POST) == "https://site/posts/new/"


def test_not_live_post_gets_its_future_url_for_dry_runs_only(monkeypatch):
    monkeypatch.setattr(hugo, "_rows", fake_rows([], [ROW]))
    assert hugo.permalink(REPO, POST) == ("https://site/posts/new/", False)
    with pytest.raises(hugo.NotLive):
        hugo.published_permalink(REPO, POST)


def test_unknown_post(monkeypatch):
    monkeypatch.setattr(hugo, "_rows", fake_rows([], []))
    with pytest.raises(hugo.NotLive, match="doesn't know"):
        hugo.permalink(REPO, POST)
