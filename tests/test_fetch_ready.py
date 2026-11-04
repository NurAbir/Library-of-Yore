"""fetch_html / _browser_fetch `ready` check: pages whose content JavaScript fills in."""
import sys
import types

import pytest

from scrapers import base
from scrapers.base import FetchError

SHELL = "<html><body>page shell</body></html>"
RENDERED = "<html><body>page shell + chapter list</body></html>"


def _ready(html):
    return "chapter list" in html


class _Resp:
    def __init__(self, text, status=200):
        self.text, self.status_code = text, status


def _plain(monkeypatch, text, status=200):
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resp(text, status))


# ── plain request stage ─────────────────────────────────────────────────────

def test_plain_response_that_is_ready_is_used_without_a_browser(monkeypatch):
    _plain(monkeypatch, RENDERED)
    monkeypatch.setattr(base, "_browser_fetch", lambda *a, **k: pytest.fail("browser must not start"))
    assert base.fetch_html("https://x.test/", ready=_ready) == RENDERED


def test_plain_response_that_is_not_ready_goes_to_the_browser(monkeypatch):
    _plain(monkeypatch, SHELL)
    seen = {}

    def fake_browser(url, must_contain=None, json_url=None, ready=None):
        seen.update(url=url, ready=ready)
        return RENDERED

    monkeypatch.setattr(base, "_browser_fetch", fake_browser)
    assert base.fetch_html("https://x.test/", ready=_ready) == RENDERED
    assert seen == {"url": "https://x.test/", "ready": _ready}


def test_not_ready_without_browser_fallback_is_an_error(monkeypatch):
    _plain(monkeypatch, SHELL)
    with pytest.raises(FetchError, match="JavaScript"):
        base.fetch_html("https://x.test/", ready=_ready, use_browser_fallback=False)


def test_without_ready_nothing_changes(monkeypatch):
    _plain(monkeypatch, SHELL)
    monkeypatch.setattr(base, "_browser_fetch", lambda *a, **k: pytest.fail("browser must not start"))
    assert base.fetch_html("https://x.test/") == SHELL
    _plain(monkeypatch, SHELL, status=503)
    monkeypatch.setattr(base, "_browser_fetch", lambda *a, **k: "from browser")
    assert base.fetch_html("https://x.test/") == "from browser"


# ── browser stage (fake Playwright) ─────────────────────────────────────────

class _Page:
    def __init__(self, contents):
        self.contents, self.calls = list(contents), 0

    def goto(self, *a, **k):
        pass

    def content(self):
        i = min(self.calls, len(self.contents) - 1)     # keeps returning the last one
        self.calls += 1
        return self.contents[i]

    def wait_for_timeout(self, ms):
        pass


class _Browser:
    def __init__(self, page):
        self.page = page

    def new_context(self, **k):
        return types.SimpleNamespace(new_page=lambda: self.page)

    def close(self):
        pass


@pytest.fixture
def fake_browser(monkeypatch):
    def install(contents):
        page = _Page(contents)

        class _PW:
            def __enter__(self):
                return object()

            def __exit__(self, *a):
                return False

        mod = types.ModuleType("playwright.sync_api")
        mod.sync_playwright = lambda: _PW()
        monkeypatch.setitem(sys.modules, "playwright", types.ModuleType("playwright"))
        monkeypatch.setitem(sys.modules, "playwright.sync_api", mod)
        monkeypatch.setattr(base, "_launch_browser", lambda p: _Browser(page))
        return page
    return install


def test_browser_waits_until_the_page_is_ready(fake_browser):
    page = fake_browser([SHELL, SHELL, RENDERED])
    assert base._browser_fetch("https://x.test/", ready=_ready) == RENDERED
    assert page.calls == 3


def test_browser_uses_a_loaded_page_that_never_becomes_ready(fake_browser):
    # e.g. a series with a single chapter: the list never reaches the "ready" bar
    page = fake_browser([SHELL])
    assert base._browser_fetch("https://x.test/", ready=_ready) == SHELL
    assert page.calls == 16          # 15 polls, then one last read


def test_browser_still_fails_on_a_bot_check_even_with_ready(fake_browser):
    fake_browser(["<html><title>Just a moment...</title></html>"])
    with pytest.raises(FetchError, match="bot check"):
        base._browser_fetch("https://x.test/", ready=_ready)


def test_browser_without_ready_keeps_the_old_strictness(fake_browser):
    fake_browser([SHELL])
    with pytest.raises(FetchError, match="bot check"):
        base._browser_fetch("https://x.test/", must_contain="chapter list")
    fake_browser([SHELL, RENDERED])
    assert base._browser_fetch("https://x.test/", must_contain="chapter list") == RENDERED
