"""v2.2.0: Novelfire / NovelPhoenix / FreeWebNovel / Wuxiaworld scrapers,
shared fetch with browser fallback, NovelUpdates removal.

Fixtures are rebuilt from the live pages (captured in a browser on
2026-09-30): same markup, meta tags and embedded data, with long text cut."""
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

import scrapers
from scrapers import base, get_scraper_for_url
from scrapers import novelfire as nf_mod, freewebnovel as fwn_mod, wuxiaworld as wx_mod
from scrapers.base import ScraperResult
from scrapers.freewebnovel import FreeWebNovelScraper
from scrapers.novelfire import NovelfireScraper
from scrapers.novelphoenix import NovelPhoenixScraper
from scrapers.wuxiaworld import WuxiaworldScraper
from utils import chapters as C

FIX = Path(__file__).parent / "fixtures"


def fixture(name):
    return (FIX / name).read_text(encoding="utf-8")


# ── NovelUpdates is gone ─────────────────────────────────────────────────────

def test_novelupdates_removed():
    assert get_scraper_for_url("https://www.novelupdates.com/series/lord-of-the-mysteries/") is None
    assert not hasattr(scrapers, "NovelUpdatesScraper")
    root = Path(__file__).parent.parent
    assert not (root / "scrapers" / "novelupdates.py").exists()
    for f in ["build.py", "build.bat", "build_release.bat",
              "Library of Yore Browser Extension/manifest.json",
              "Library of Yore Browser Extension/background.js"]:
        assert "novelupdates" not in (root / f).read_text(encoding="utf-8").lower(), f


# ── Novelfire / NovelPhoenix ─────────────────────────────────────────────────

def test_novelfire_count_gives_latest_and_full_list(monkeypatch):
    html = fixture("novelfire_the_authors_pov.html")
    seen = {}

    def fake_fetch(url, must_contain=None, **kw):
        seen["url"], seen["marker"] = url, must_contain
        return html

    monkeypatch.setattr(nf_mod, "fetch_html", fake_fetch)
    r = NovelfireScraper().scrape("https://novelfire.net/book/the-authors-pov/chapter-17")
    assert seen["url"] == "https://novelfire.net/book/the-authors-pov"      # chapter link -> novel page
    assert r.success and r.title == "The Author's POV" and r.author == "Entrail_JI"
    assert r.status == "completed"
    # Last chapter's title is "Epilogue" (no number); the URL numbering is 1..862
    assert r.latest_chapter == "862" and C.encode_ranges(r.chapter_list) == "1-862"
    assert r.cover_url == "https://novelfire.net/server-1/the-authors-pov.jpg"
    assert r.genres == ["Action", "Adventure", "Comedy", "Fantasy", "Romance"]
    assert r.synopsis.startswith("Waking up to find himself") and "Show More" not in r.synopsis


def test_novelfire_without_stats_falls_back_to_latest_label():
    html = fixture("novelfire_the_authors_pov.html").replace("header-stats", "gone").replace(
        "Chapter Epilogue — The Author’s POV", "Chapter 861 Epilogue")
    r = NovelfireScraper()._parse_soup(BeautifulSoup(html, "html.parser"), "u", ScraperResult())
    assert r.latest_chapter == "861" and r.chapter_list == []


def test_novelphoenix_uses_same_template_with_novel_path(monkeypatch):
    html = fixture("novelfire_the_authors_pov.html")
    seen = {}
    monkeypatch.setattr(nf_mod, "fetch_html", lambda url, **kw: seen.setdefault("url", url) and html)
    r = NovelPhoenixScraper().scrape("https://novelphoenix.com/novel/the-authors-pov/chapter-3")
    assert seen["url"] == "https://novelphoenix.com/novel/the-authors-pov"
    assert r.source_name == "novelphoenix" and r.latest_chapter == "862"
    assert get_scraper_for_url("https://novelphoenix.com/novel/x").__class__ is NovelPhoenixScraper


# ── FreeWebNovel ─────────────────────────────────────────────────────────────

def test_freewebnovel_meta_and_chapter_total(monkeypatch):
    html = fixture("freewebnovel_lotm.html")
    calls = {}
    monkeypatch.setattr(fwn_mod, "fetch_html", lambda url, **kw: html)

    def fake_json(url, params, page_url):
        calls.update(url=url, params=params)
        return {"code": 200, "html": "", "page": 1, "pageSize": 200, "totalPage": 8, "totalChapters": 1432}

    monkeypatch.setattr(fwn_mod, "fetch_json", fake_json)
    r = FreeWebNovelScraper().scrape("https://freewebnovel.com/novel/lord-of-the-mysteries/chapter-5")
    assert calls["url"] == "https://freewebnovel.com/novel/lord-of-the-mysteries"
    assert calls["params"] == {"ajax": "chapters", "page": 1, "pageSize": 200}
    assert r.success and r.title == "Lord of the Mysteries"
    assert r.author == "Cuttlefish That Loves Diving, 爱潜水的乌贼"
    assert r.status == "completed" and r.genres[:3] == ["Xuanhuan", "Mystery", "Fantasy"]
    assert r.synopsis.startswith("In the waves of steam")              # not og:description
    assert r.latest_chapter == "1432" and C.encode_ranges(r.chapter_list) == "1-1432"


def test_freewebnovel_without_chapter_api_keeps_meta_latest(monkeypatch):
    monkeypatch.setattr(fwn_mod, "fetch_html", lambda url, **kw: fixture("freewebnovel_lotm.html"))

    def boom(*a, **k):
        raise base.FetchError("blocked")

    monkeypatch.setattr(fwn_mod, "fetch_json", boom)
    r = FreeWebNovelScraper().scrape("https://freewebnovel.com/novel/lord-of-the-mysteries")
    assert r.success and r.latest_chapter == "1432" and r.chapter_list == []   # "Chapter 1432-END ..."


@pytest.mark.parametrize("url,expected", [
    ("https://freewebnovel.com/novel/lord-of-the-mysteries", "https://freewebnovel.com/novel/lord-of-the-mysteries"),
    ("https://freewebnovel.com/novel/lord-of-the-mysteries/chapter-12", "https://freewebnovel.com/novel/lord-of-the-mysteries"),
    ("https://freewebnovel.com/lord-of-the-mysteries.html", "https://freewebnovel.com/novel/lord-of-the-mysteries"),
    ("https://freewebnovel.com/lord-of-the-mysteries/chapter-12.html", "https://freewebnovel.com/novel/lord-of-the-mysteries"),
])
def test_freewebnovel_canonical_url(url, expected):
    assert FreeWebNovelScraper.canonical_url(url) == expected


# ── Wuxiaworld ───────────────────────────────────────────────────────────────

def _wx(monkeypatch, slug):
    monkeypatch.setattr(wx_mod, "fetch_html", lambda url, **kw: fixture(f"wuxiaworld_{slug}.html"))
    return WuxiaworldScraper().scrape(f"https://www.wuxiaworld.com/novel/{slug}/some-chapter-3")


def test_wuxiaworld_consistent_books_give_full_list(monkeypatch):
    r = _wx(monkeypatch, "the-second-coming-of-gluttony")
    assert r.success and r.title == "The Second Coming of Gluttony" and r.author == "Ro Yu Jin (로유진)"
    assert r.status == "completed"                      # from tags, not item.status
    assert r.latest_chapter == "550" and C.encode_ranges(r.chapter_list) == "1-550"
    assert r.locked_list == [] and r.synopsis == "Seol Jihu was a loser."
    assert r.raw_data["url"] == "https://www.wuxiaworld.com/novel/the-second-coming-of-gluttony"


def test_wuxiaworld_uneven_books_use_simple_mode_with_advance_chapters(monkeypatch):
    # Real Against the Gods data: two books hold one more chapter than their
    # number range (651-800 has 151), so the exact numbers aren't knowable;
    # the newest book has 10 paid "advance" chapters after chapter 2190.
    r = _wx(monkeypatch, "against-the-gods")
    assert r.status == "ongoing"
    assert r.chapter_list == []
    assert r.latest_chapter == "2200"
    assert C.encode_ranges(r.locked_list) == "2191-2200"
    p = C.compute_progress("2190", r.latest_chapter, "", C.encode_ranges(r.locked_list))
    assert p.behind == 10 and p.locked_behind == 10


def test_wuxiaworld_book_chapter_numbering(monkeypatch):
    r = _wx(monkeypatch, "coiling-dragon")
    assert r.latest_chapter == "21.044" and r.chapter_list == []
    assert C.is_newer("21.044", "21.043") and not C.is_newer("20.099", "21.001")


def test_wuxiaworld_state_parser_ignores_following_scripts():
    state = wx_mod.extract_state(fixture("wuxiaworld_against-the-gods.html"))
    assert wx_mod.novel_item(state)["slug"] == "against-the-gods"


# ── Shared fetch with browser fallback ───────────────────────────────────────

class _Resp:
    def __init__(self, text, status=200):
        self.text, self.status_code = text, status

    def json(self):
        import json
        return json.loads(self.text)


def test_fetch_html_uses_plain_request_when_it_works(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resp("<html>ok __NEXT_DATA__</html>"))
    monkeypatch.setattr(base, "_browser_fetch", lambda *a, **k: pytest.fail("browser not needed"))
    assert "ok" in base.fetch_html("https://x.test/p", must_contain="__NEXT_DATA__")


@pytest.mark.parametrize("resp", [
    _Resp("<title>Just a moment...</title>", 200),        # Cloudflare challenge page
    _Resp("forbidden", 403),                                # blocked
    _Resp("<html>unexpected page</html>", 200),             # marker missing
])
def test_fetch_html_falls_back_to_browser(monkeypatch, resp):
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: resp)
    monkeypatch.setattr(base, "_browser_fetch", lambda url, must_contain=None, json_url=None: "<html>real header-stats</html>")
    assert "real" in base.fetch_html("https://x.test/p", must_contain="header-stats")


def test_fetch_json_falls_back_to_browser(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resp("<title>Just a moment...</title>", 503))
    seen = {}

    def fake_browser(url, must_contain=None, json_url=None):
        seen.update(url=url, json_url=json_url)
        return '{"totalChapters": 7}'

    monkeypatch.setattr(base, "_browser_fetch", fake_browser)
    data = base.fetch_json("https://x.test/novel/a", {"ajax": "chapters", "page": 1}, "https://x.test/novel/a")
    assert data == {"totalChapters": 7}
    assert seen["url"] == "https://x.test/novel/a" and seen["json_url"].endswith("?ajax=chapters&page=1")
