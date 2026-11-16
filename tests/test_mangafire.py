"""MangaFire (mangafire.to): scraper, URL matching and extension registration.

What was checked against the live site: old links redirect to /title/{id}-{slug}
(e.g. /read/lag.zl363/en/chapter-1 -> /title/zl363-lagg, with the slug changing),
and every un-rendered page carries the generic title "MangaFire - Read Manga
Online Free". The series-page HTML below is SYNTHETIC: built from those URL
shapes, not captured from a real page, so these tests prove the parsing logic,
not that the live markup matches. When a real saved page is available
(tools/capture_mangafire.py), add it under tests/fixtures/ and test against it.
"""
import re
from pathlib import Path

import pytest

import api_server as api
from database.models import Novel, apply_scrape_result
from scrapers import get_scraper_for_url, MangaFireScraper
from scrapers import mangafire as mf
from scrapers.base import FetchError, ScraperResult

EXT = Path(__file__).resolve().parent.parent / "Library of Yore Browser Extension"
SID = "zl363"
CURRENT = "zl363-lagg"       # /title/{id}-{slug}
OLDER = "lag.zl363"          # /manga/{slug}.{id}, /read/{slug}.{id}/...
GENERIC_TITLE = "MangaFire - Read Manga Online Free"


def _page(links, title="L.A.G", extra=""):
    anchors = "".join(f'<a href="{h}">link</a>' for h in links)
    return (
        "<html><head>"
        '<meta property="og:image" content="https://static.mangafire.to/cover.jpg">'
        f"</head><body><h1>{title}</h1>{extra}{anchors}</body></html>"
    )


def _read(lang, num, seg=OLDER):
    """Older reader link: /read/{slug}.{id}/{lang}/chapter-{N}"""
    return f"/read/{seg}/{lang}/chapter-{num}"


def _title(lang, num, seg=CURRENT):
    """A chapter link under the current series path (shape guessed; see module notes)"""
    return f"/title/{seg}/{lang}/chapter-{num}"


def _parse(html, lang=None):
    return mf.parse_page(html, SID, lang, ScraperResult(source_name="mangafire"))


# URLs and factory

@pytest.mark.parametrize("url, id_, slug, lang, chapter, page_url", [
    ("https://mangafire.to/title/zl363-lagg", "zl363", "lagg", None, None,
     "https://mangafire.to/title/zl363-lagg"),
    ("https://mangafire.to/title/pjkw6-g22?x=1#top", "pjkw6", "g22", None, None,
     "https://mangafire.to/title/pjkw6-g22"),
    ("https://mangafire.to/manga/lag.zl363", "zl363", "lag", None, None,
     "https://mangafire.to/manga/lag.zl363"),
    ("https://www.mangafire.to/read/lag.zl363/en/chapter-7", "zl363", "lag", "en", "7",
     "https://mangafire.to/manga/lag.zl363"),
    ("https://mangafire.to/read/Fire-Fire-Firee.2wl/es-la/chapter-7.2", "2wl", "fire-fire-firee", "es-la", "7.2",
     "https://mangafire.to/manga/fire-fire-firee.2wl"),
    ("https://mangafire.to/read/to-yy.5krrq/en/chapter-7-2", "5krrq", "to-yy", "en", "7.2",
     "https://mangafire.to/manga/to-yy.5krrq"),
    ("https://mangafire.to/title/zl363-lagg/en/chapter-12", "zl363", "lagg", "en", "12",
     "https://mangafire.to/title/zl363-lagg"),
])
def test_parse_url(url, id_, slug, lang, chapter, page_url):
    assert mf.parse_url(url) == {"id": id_, "slug": slug, "lang": lang, "chapter": chapter, "page_url": page_url}


@pytest.mark.parametrize("url", [
    "https://mangafire.to/", "https://mangafire.to/updated", "https://mangafire.to/title/",
    "https://mangafire.to/filter?type=manga",
    "https://flamecomics.xyz/series/2", "https://mangafire.rip/title/the-world-after-the-end/chapter-258/",
    "not a url", "", None,
])
def test_parse_url_rejects_other_pages_and_look_alike_sites(url):
    assert mf.parse_url(url) is None and mf.canonical_url(url) is None and mf.series_id(url) is None


def test_the_id_is_the_same_across_formats_even_when_the_slug_changes():
    older = mf.series_id("https://mangafire.to/read/lag.zl363/en/chapter-1")
    current = mf.series_id("https://mangafire.to/title/zl363-lagg")   # slug "lag" became "lagg"
    assert older == current == "zl363"


def test_canonical_url_is_id_language_and_page():
    assert mf.canonical_url("https://mangafire.to/title/zl363-lagg/es-la/chapter-3") == \
        ("zl363", "es-la", "https://mangafire.to/title/zl363-lagg")


def test_factory_returns_mangafire_scraper():
    assert isinstance(get_scraper_for_url("https://mangafire.to/title/zl363-lagg"), MangaFireScraper)
    assert MangaFireScraper().can_handle("https://www.mangafire.to/read/x.abc1/en/chapter-1")
    assert get_scraper_for_url("https://flamecomics.xyz/series/2").SOURCE_NAME == "flamecomics"


# Parsing

def test_latest_is_the_highest_chapter_with_decimals_in_numeric_order():
    html = _page([_read("en", n) for n in ("1", "2", "9", "10", "100", "7.2", "100.5")])
    r = _parse(html)
    assert r.success and r.title == "L.A.G"
    assert r.latest_chapter == "100.5"          # numeric, not string, ordering
    assert r.content_type == "manga"
    assert r.cover_url == "https://static.mangafire.to/cover.jpg"


@pytest.mark.parametrize("make", [_read, _title])
def test_chapter_links_are_found_under_either_series_path(make):
    assert _parse(_page([make("en", n) for n in (1, 2, 30)])).latest_chapter == "30"


def test_a_series_page_may_mix_both_link_formats_and_absolute_urls():
    html = _page([_read("en", 1), _title("en", 2), f"https://mangafire.to{_title('en', 3)}",
                  f"https://www.mangafire.to{_read('en', 4)}"])
    r = _parse(html)
    assert r.latest_chapter == "4" and r.raw_data["chapter_links_found"] == 4


def test_dashed_decimal_is_read_as_a_decimal():
    r = _parse(_page([_read("en", "7"), _read("en", "7-2"), _read("en", "7-1")]))
    assert r.latest_chapter == "7.2"


def test_links_without_a_language_still_count():
    html = _page([f"/title/{CURRENT}/chapter-{n}" for n in (1, 2, 3)])
    r = _parse(html)
    assert r.latest_chapter == "3" and r.raw_data["languages_found"] == ["und"]


def test_english_is_preferred_and_a_requested_language_wins():
    html = _page([_read("en", n) for n in (1, 2, 3)] + [_read("es-la", n) for n in range(1, 40)])
    assert _parse(html).latest_chapter == "3"
    r = _parse(html, "es-la")
    assert r.latest_chapter == "39" and r.raw_data["language"] == "es-la"
    assert r.raw_data["languages_found"] == ["en", "es-la"]


def test_without_english_the_fullest_language_is_used():
    html = _page([_read("fr", n) for n in (1, 2)] + [_read("pt-br", n) for n in (1, 2, 3, 4)])
    r = _parse(html)
    assert r.raw_data["language"] == "pt-br" and r.latest_chapter == "4"


def test_a_lone_button_in_english_does_not_hide_another_languages_real_list():
    # English holds only the "read first chapter" button while Spanish holds the
    # real list: the lone button must not win merely because it is English.
    html = _page([_read("en", 1)] + [_read("es-la", n) for n in range(1, 40)])
    r = _parse(html)
    assert r.raw_data["language"] == "es-la" and r.latest_chapter == "39"
    r = _parse(html, "en")                        # asking for "en" is no better
    assert r.raw_data["language"] == "es-la" and r.latest_chapter == "39"


def test_other_series_links_on_the_page_are_ignored():
    # "Recommended" cards link to other series' chapters
    html = _page([_read("en", 1), _read("en", 2), _read("en", 900, seg="other.zzz9"),
                  _title("en", 800, seg="abc12-other")])
    assert _parse(html).latest_chapter == "2"


def test_a_single_chapter_link_means_latest_is_unknown():
    # Usually just the "Read first chapter" button on a page whose list
    # didn't render: guessing "1" would mark every title as caught up.
    r = _parse(_page([_read("en", 1)]))
    assert r.success and r.latest_chapter is None
    r = _parse(_page([]))
    assert r.success and r.latest_chapter is None


def test_volume_and_series_links_are_not_chapters():
    html = _page([_read("en", 1), _read("en", 2), f"/read/{OLDER}/en/volume-12", f"/title/{CURRENT}"])
    assert _parse(html).latest_chapter == "2"


def test_no_chapter_list_or_status_is_stored():
    html = _page([_read("en", n) for n in range(1, 30)],
                 extra="<ul><li>Completed</li><li>Releasing</li></ul>")   # e.g. a filter menu
    r = _parse(html)
    assert r.chapter_list == [] and r.locked_list == []
    assert r.status == ""


def test_title_falls_back_to_og_then_document_title():
    og = ('<html><head><meta property="og:title" content="Read L.A.G Manga Online - MangaFire">'
          "</head><body></body></html>")
    assert _parse(og).title == "L.A.G"
    doc = "<html><head><title>L.A.G Manga | MangaFire</title></head><body></body></html>"
    assert _parse(doc).title == "L.A.G"
    empty = _parse("<html><body></body></html>")
    assert not empty.success and "title" in empty.error_message


def test_the_generic_site_title_is_never_taken_as_the_series_title():
    # Every un-rendered MangaFire page, whatever the route, has this title and og:title
    shell = (f'<html><head><title>{GENERIC_TITLE}</title><meta property="og:title" content="{GENERIC_TITLE}">'
             "</head><body></body></html>")
    r = _parse(shell)
    assert r.title == "" and not r.success
    assert mf._clean_title(GENERIC_TITLE) == ""
    # ... but a rendered heading still wins over it
    assert _parse(shell.replace("<body>", "<body><h1>L.A.G</h1>")).title == "L.A.G"


def test_authors_and_genres_are_deduplicated_and_capped():
    extra = ('<a href="/author/a1">Oda</a><a href="/author/a1">Oda</a>'
             + "".join(f'<a href="/genre/g{i}">G{i}</a>' for i in range(8)))
    r = _parse(_page([_read("en", 1), _read("en", 2)], extra=extra))
    assert r.author == "Oda"
    assert r.genres == ["G0", "G1", "G2", "G3", "G4"]


def test_ready_check_needs_two_chapters_of_this_series_in_one_language():
    ready = mf.chapters_rendered(SID)
    assert not ready("") and not ready(None)
    assert not ready(_page([]))
    assert not ready(_page([_read("en", 1)]))                                    # the "read first" button
    assert not ready(_page([_read("en", 1), _read("en", 1)]))                    # same chapter twice
    assert not ready(_page([_read("en", 1), _read("es-la", 2)]))                 # two languages, one each
    assert not ready(_page([_read("en", 1), _read("en", 2, seg="other.zz9")]))   # another series
    assert ready(_page([_read("en", 1), _read("en", 2)]))
    assert ready(_page([_title("en", 1), _title("en", "1.5")]))                  # current path shape
    assert ready(_page([_read("en", 1), _title("en", 2)]))                       # formats mixed


def test_link_order_is_reported_for_diagnostics():
    def order(nums):
        return _parse(_page([_read("en", n) for n in nums])).raw_data["link_order"]
    assert order([10, 9, 8]) == "desc"
    assert order([1, 2, 3]) == "asc"
    assert order([3, 1, 2]) == "mixed"
    assert order([1]) == "n/a"


# scrape()

@pytest.mark.parametrize("given, fetched", [
    ("https://mangafire.to/read/lag.zl363/en/chapter-3", "https://mangafire.to/manga/lag.zl363"),
    ("https://mangafire.to/manga/lag.zl363", "https://mangafire.to/manga/lag.zl363"),
    ("https://mangafire.to/title/zl363-lagg", "https://mangafire.to/title/zl363-lagg"),
    ("https://www.mangafire.to/title/zl363-lagg/en/chapter-3", "https://mangafire.to/title/zl363-lagg"),
])
def test_scrape_fetches_the_series_page_and_waits_for_rendered_chapter_links(monkeypatch, given, fetched):
    seen = {}

    def fake_fetch(url, must_contain=None, ready=None, **kw):
        seen["url"], seen["ready"] = url, ready
        return _page([_read("en", n) for n in range(1, 6)])

    monkeypatch.setattr(mf, "fetch_html", fake_fetch)
    r = MangaFireScraper().scrape(given)
    assert seen["url"] == fetched
    assert r.success and r.latest_chapter == "5" and r.source_name == "mangafire"
    assert r.raw_data["url"] == fetched and r.raw_data["series_id"] == SID
    # The ready check it passed rejects the page shell and accepts a rendered list
    assert not seen["ready"](_page([_read("en", 1)]))
    assert seen["ready"](_page([_read("en", 1), _read("en", 2)]))


def test_scrape_reports_fetch_errors_and_bad_urls(monkeypatch):
    def boom(*a, **k):
        raise FetchError("blocked")
    monkeypatch.setattr(mf, "fetch_html", boom)
    r = MangaFireScraper().scrape("https://mangafire.to/title/zl363-lagg")
    assert not r.success and "blocked" in r.error_message
    r = MangaFireScraper().scrape("https://mangafire.to/updated")
    assert not r.success and "MangaFire series" in r.error_message


def test_shell_only_plain_response_triggers_the_browser_and_yields_the_latest(monkeypatch):
    """Plain HTTP gets the page shell (just the "read first chapter" link); the chapter
    list only exists once a real browser has rendered it. End to end through fetch_html."""
    import requests
    from scrapers import base

    class Resp:
        status_code = 200
        text = _page([_read("en", 1)])

    browser_calls = []

    def fake_browser(url, must_contain=None, json_url=None, ready=None):
        browser_calls.append((url, ready))
        return _page([_title("en", n) for n in range(1, 41)])

    monkeypatch.setattr(requests, "get", lambda *a, **k: Resp())
    monkeypatch.setattr(base, "_browser_fetch", fake_browser)
    r = MangaFireScraper().scrape(f"https://mangafire.to/title/{CURRENT}")
    assert len(browser_calls) == 1 and browser_calls[0][0] == f"https://mangafire.to/title/{CURRENT}"
    assert r.success and r.latest_chapter == "40"


def test_fully_rendered_plain_response_needs_no_browser(monkeypatch):
    import requests
    from scrapers import base

    class Resp:
        status_code = 200
        text = _page([_read("en", n) for n in range(1, 8)])

    monkeypatch.setattr(requests, "get", lambda *a, **k: Resp())
    monkeypatch.setattr(base, "_browser_fetch", lambda *a, **k: pytest.fail("browser must not start"))
    assert MangaFireScraper().scrape(f"https://mangafire.to/title/{CURRENT}").latest_chapter == "7"


# Library behaviour

def test_refresh_sets_latest_and_type_but_never_touches_your_status_or_progress():
    n = Novel(title="L.A.G", source_url=f"https://mangafire.to/title/{CURRENT}",
              status="completed", content_type="novel")
    n.current_chapter = "5"
    r = _parse(_page([_read("en", i) for i in range(1, 30)]))
    assert apply_scrape_result(n, r) is True
    assert n.content_type == "manga"
    assert n.latest_chapter == "29"
    assert n.status == "completed"              # empty site status leaves it alone
    assert n.current_chapter == "5"


def test_unknown_latest_does_not_erase_a_known_one():
    n = Novel(title="L.A.G", source_url=f"https://mangafire.to/title/{CURRENT}")
    n.latest_chapter = "40"
    apply_scrape_result(n, _parse(_page([_read("en", 1)])))
    assert n.latest_chapter == "40"


def _lib():
    return [
        Novel(_id="lag", title="L.A.G", source_url=f"https://mangafire.to/title/{CURRENT}"),
        Novel(_id="ff", title="Fire Fire Fire", source_url="https://mangafire.to/manga/fire-fire-firee.2wl"),
        Novel(_id="g", title="G", source_url="https://mangafire.to/title/pjkw6-g22"),
        Novel(_id="flame", title="Flame", source_url="https://flamecomics.xyz/series/2"),
    ]


@pytest.mark.parametrize("url, expected", [
    # saved as /title/zl363-lagg; the browser is on an older-format URL whose slug is "lag", not "lagg"
    ("https://mangafire.to/read/lag.zl363/en/chapter-7", "lag"),
    ("https://www.mangafire.to/read/lag.zl363/es-la/chapter-7", "lag"),        # other language, same series
    (f"https://mangafire.to/title/{CURRENT}/en/chapter-7", "lag"),             # current-style path
    ("https://mangafire.to/title/zl363-some-new-slug/chapter-7", "lag"),       # slug changed again, id is the same
    # saved as an older /manga/slug.id link, browser on the current format
    ("https://mangafire.to/title/2wl-fire-fire-fire/en/chapter-1", "ff"),
    ("https://mangafire.to/read/fire-fire-firee.2wl/en/chapter-1", "ff"),
    ("https://mangafire.to/read/g22.pjkw6/en/chapter-3", "g"),
    ("https://mangafire.to/read/lag.zzzzz/en/chapter-7", None),                # same slug, different id
    ("https://mangafire.to/read/another.1abc/en/chapter-7", None),
])
def test_extension_urls_match_saved_series_by_id(url, expected):
    n = api._find_by_url(_lib(), url)
    assert (n._id if n else None) == expected


def test_other_sites_are_still_matched_by_path():
    n = api._find_by_url(_lib(), "https://flamecomics.xyz/series/2/abcdef0123456789")
    assert n is not None and n._id == "flame"
    assert api._series_key("https://flamecomics.xyz/series/2") is None
    assert api._series_key("https://mangafire.to/title/zl363-lagg") == "zl363"


# Extension registration

def test_every_detector_site_is_registered_in_manifest_background_and_popup():
    sites = re.findall(r'^  "([a-z0-9.\-]+)": \(\) =>', (EXT / "content.js").read_text("utf-8"), re.M)
    assert "mangafire.to" in sites and len(sites) >= 6
    manifest = (EXT / "manifest.json").read_text("utf-8")
    background = (EXT / "background.js").read_text("utf-8")
    popup = (EXT / "popup.html").read_text("utf-8")
    for site in sites:
        assert f'"*://{site}/*"' in manifest and f'"*://www.{site}/*"' in manifest, site
        assert f'"{site}"' in background, site
        assert f">{site}<" in popup, site


def test_build_scripts_bundle_the_scraper():
    root = Path(__file__).resolve().parent.parent
    for name in ("build.py", "build.bat", "build_release.bat"):
        assert "scrapers.mangafire" in (root / name).read_text("utf-8"), name


# Real-page text shapes
# The labels below ("Author: ...", "Genres: ...", "Chapter 341: Jul 01, 2026", "the latest
# chapter 341 is available") are the visible text of a crawled MangaFire series page
# (I Am The Fated Villain, id m2wxz). The tags around them are guesses.

FATED = "m2wxz"


def _fated_page(chapter_items="", head_extra="", body_extra="", title="I Am The Fated Villain"):
    return (
        f"<html><head><title>{title} Manga - Read Manga Online Free</title>{head_extra}</head><body>"
        f"<h1>{title}</h1>"
        '<img class="poster-img" alt="I Am The Fated Villain" src="data:image/gif;base64,R0lGOD" '
        'data-src="/cdn/covers/m2wxz.jpg">'
        '<div class="info"><p><span>Author:</span><a href="/p/1">Liu Mang</a>, <a href="/p/2">Mu Tou Ren</a>, '
        '<a href="/p/3">Tian Ming Fan Pai</a></p><p>Published: Nov 07, 2021 to ?</p>'
        "<p><span>Genres:</span> Action, Comedy, Drama, Isekai, Fantasy, Martial Arts, Magic</p></div>"
        '<div class="description">Gu Changge was reincarnated as a villain of a famous novel and decided to '
        "make the best of it. Read more</div>"
        f"<ul>{chapter_items}</ul>{body_extra}</body></html>"
    )


def _fated(html, lang=None):
    return mf.parse_page(html, FATED, lang, ScraperResult(source_name="mangafire"),
                         "https://mangafire.to/title/m2wxz-wo-tian-ming-da-fanpaii")


def test_author_genres_cover_and_synopsis_come_from_visible_text_and_alt():
    r = _fated(_fated_page())
    assert r.title == "I Am The Fated Villain"
    assert r.author == "Liu Mang, Mu Tou Ren, Tian Ming Fan Pai"
    assert r.genres == ["Action", "Comedy", "Drama", "Isekai", "Fantasy"]
    # the poster is found by its alt text; the data: placeholder in src is skipped
    assert r.cover_url == "https://mangafire.to/cdn/covers/m2wxz.jpg"
    assert r.synopsis.startswith("Gu Changge was reincarnated") and "Read more" not in r.synopsis


def test_og_image_wins_and_links_win_over_labels():
    page = _fated_page(head_extra='<meta property="og:image" content="https://cdn.x/og.jpg">',
                       body_extra='<a href="/author/9">Real Author</a><a href="/genre/9">Real Genre</a>')
    r = _fated(page)
    assert r.cover_url == "https://cdn.x/og.jpg"
    assert r.author == "Real Author" and r.genres == ["Real Genre"]


def test_the_generic_site_description_is_not_a_synopsis():
    page = ('<html><body><h1>X</h1><div class="description">Free read manga online in high quality. '
            "Update hourly, No ads, No registration required. Just enjoy your manga</div></body></html>")
    assert _fated(page).synopsis == ""


def test_latest_from_links_whose_url_mentions_the_id_and_whose_text_is_a_chapter_label():
    # The chapter number is only in the link text; the URL carries the id but no chapter-N shape
    items = "".join(f'<li><a href="/title/m2wxz-x/read?c={n}"><span>Chapter {n}: </span><span>Jul 01, 2026</span></a></li>'
                    for n in (341, 340, 339))
    r = _fated(_fated_page(items))
    assert r.latest_chapter == "341"
    assert r.raw_data["latest_from"] == "link-text" and r.raw_data["language"] == "und"


def test_link_text_chapters_of_other_series_are_ignored():
    items = ('<li><a href="/read/m2wxz/en/5">Chapter 5: a</a></li><li><a href="/read/m2wxz/en/6">Chapter 6: b</a></li>'
             '<li><a href="/read/other.zz9/en/999">Chapter 999: sidebar</a></li>')
    assert _fated(_fated_page(items)).latest_chapter == "6"


def test_latest_from_the_pages_visible_chapter_lines_when_links_carry_nothing():
    items = "".join(f"<li><span>Chapter {n}:</span> <span>Jul 01, 2026</span></li>" for n in (341, 340, 339, "338.5"))
    sidebar = '<a href="/read/other.zz9/en/chapter-900">Chap 900</a><div>Chap 120</div><div>Chapter 7</div>'
    r = _fated(_fated_page(items, body_extra=sidebar))
    assert r.latest_chapter == "341" and r.raw_data["latest_from"] == "page-text"


def test_latest_falls_back_to_the_sites_own_sentence():
    page = _fated_page(body_extra="<p>I Am The Fated Villain manga, read all chapters here, the latest chapter 341 "
                                  "is available.</p>")
    r = _fated(page)
    assert r.latest_chapter == "341" and r.raw_data["latest_from"] == "page-sentence"


def test_a_real_list_beats_the_sentence_and_one_line_is_not_a_list():
    items = "".join(f"<li>Chapter {n}: x</li>" for n in (12, 11, 10))
    assert _fated(_fated_page(items, body_extra="<p>the latest chapter 341 is available</p>")).latest_chapter == "12"
    assert _fated(_fated_page("<li>Chapter 1: first</li>")).latest_chapter is None


def test_language_tab_counts_are_never_read_as_the_latest_chapter():
    tabs = "<div><span>English (20 Chapters)</span><span>Spanish (LATAM) (15 Chapters)</span></div>"
    assert _fated(_fated_page(body_extra=tabs)).latest_chapter is None


def test_ready_check_accepts_text_based_lists_too():
    ready = mf.chapters_rendered(FATED)
    shell = "<html><head><title>MangaFire - Read Manga Online Free</title></head><body><div id=app></div></body></html>"
    assert not ready(shell)
    assert ready(_fated_page("".join(f"<li>Chapter {n}: x</li>" for n in (2, 1))))
    assert ready(_fated_page("".join(f'<li><a href="/read/m2wxz/en/{n}">Chapter {n}</a></li>' for n in (2, 1))))
    assert not ready(_fated_page("<li>Chapter 1: x</li>"))


def test_bare_id_series_segments_parse_but_plain_words_do_not():
    assert mf.parse_url("https://mangafire.to/read/m2wxz/en/chapter-3")["id"] == "m2wxz"
    assert mf.parse_url("https://mangafire.to/title/m2wxz")["page_url"] == "https://mangafire.to/title/m2wxz"
    assert mf.parse_url("https://mangafire.to/title/updated") is None
    assert mf.parse_url("https://mangafire.to/title/filter/chapter-1") is None


@pytest.mark.parametrize("browser_url", [
    "https://mangafire.to/read/wo-tian-ming-da-fanpaii.m2wxz/en/chapter-108",   # a real reader URL
    "https://mangafire.to/read/m2wxz/en/chapter-108",
    "https://mangafire.to/title/m2wxz-wo-tian-ming-da-fanpaii/en/chapter-108",
    "https://mangafire.to/manga/wo-tian-ming-da-fanpaii.m2wxz",
])
def test_the_real_series_matches_whatever_url_the_browser_shows(browser_url):
    library = [Novel(_id="fv", title="I Am the Fated Villain",
                     source_url="https://mangafire.to/title/m2wxz-wo-tian-ming-da-fanpaii")]
    assert api._find_by_url(library, browser_url)._id == "fv"


# Debug copy of the fetched page

def test_the_fetched_page_is_saved_for_inspection(monkeypatch, tmp_path):
    monkeypatch.setattr(mf, "LOGS_DIR", tmp_path / "logs")
    html = _fated_page("".join(f"<li>Chapter {n}: x</li>" for n in (3, 2, 1)))
    monkeypatch.setattr(mf, "fetch_html", lambda *a, **k: html)
    r = MangaFireScraper().scrape("https://mangafire.to/title/m2wxz-wo-tian-ming-da-fanpaii")
    saved = Path(r.raw_data["saved_page"])
    assert saved.name == "mangafire_last_page.html" and saved.read_text("utf-8") == html
    assert r.success and r.latest_chapter == "3"


def test_an_unwritable_logs_folder_never_breaks_a_scrape(monkeypatch, tmp_path):
    blocker = tmp_path / "not-a-folder"
    blocker.write_text("x")
    monkeypatch.setattr(mf, "LOGS_DIR", blocker / "logs")          # cannot be created under a file
    monkeypatch.setattr(mf, "fetch_html", lambda *a, **k: _fated_page("<li>Chapter 2: x</li><li>Chapter 1: y</li>"))
    r = MangaFireScraper().scrape("https://mangafire.to/title/m2wxz-wo-tian-ming-da-fanpaii")
    assert r.success and r.latest_chapter == "2" and r.raw_data["saved_page"] is None


# More chapter URL forms

@pytest.mark.parametrize("path, chapter", [
    ("/read/m2wxz/en/chapter-108", "108"),
    ("/read/m2wxz/en/ch-108", "108"),
    ("/read/m2wxz/en/chapter108", "108"),
    ("/read/m2wxz/en/chapter_108", "108"),
    ("/title/m2wxz-x/en/chapter-7-2", "7.2"),
])
def test_chapter_number_forms(path, chapter):
    assert mf.parse_url(f"https://mangafire.to{path}")["chapter"] == chapter


@pytest.mark.parametrize("path", [
    "/title/zkw8p-reverend-insanity-2025/chapter/8205410",   # the current reader URL: 8205410 is an internal id
    "/title/m2wxz-x/2",            # page 2 of the chapter list, not chapter 2
    "/title/m2wxz-x/page/3",
    "/title/m2wxz-x/en/108",       # a bare number is never a chapter (it could be an internal id)
    "/title/m2wxz-x/es-la/12.5",
    "/title/m2wxz-x/en/volume-2",
    "/title/m2wxz-x",
])
def test_a_bare_number_is_never_a_chapter_number(path):
    assert mf.parse_url(f"https://mangafire.to{path}")["chapter"] is None


def test_the_current_reader_url_identifies_the_series_but_not_the_chapter():
    # Reported from a real browser: the last segment is MangaFire's internal chapter id
    info = mf.parse_url("https://mangafire.to/title/zkw8p-reverend-insanity-2025/chapter/8205410")
    assert info == {"id": "zkw8p", "slug": "reverend-insanity-2025", "lang": None, "chapter": None,
                    "page_url": "https://mangafire.to/title/zkw8p-reverend-insanity-2025"}
    assert mf.canonical_url("https://mangafire.to/title/zkw8p-reverend-insanity-2025/chapter/8205410") == \
        ("zkw8p", None, "https://mangafire.to/title/zkw8p-reverend-insanity-2025")


def test_series_page_chapter_links_that_carry_internal_ids_are_read_by_their_text():
    ri = "zkw8p"
    items = "".join(f'<li><a href="/title/zkw8p-reverend-insanity-2025/chapter/{8205000 + n}">'
                    f"<span>Chapter {n}</span><span>Jul 01, 2026</span></a></li>" for n in (2334, 2333, 2332))
    page = f"<html><body><h1>Reverend Insanity</h1><ul>{items}</ul></body></html>"
    r = mf.parse_page(page, ri, None, ScraperResult(source_name="mangafire"),
                      "https://mangafire.to/title/zkw8p-reverend-insanity-2025")
    # tier 1 must not mistake 8207334 (an id) for a chapter; tier 2 reads "Chapter N" from the link text
    assert r.latest_chapter == "2334" and r.raw_data["latest_from"] == "link-text"
    assert list(mf._chapter_links(["/title/zkw8p-x/chapter/8205410"], ri)) == []
    assert mf.chapters_rendered(ri)(page)


def test_a_saved_series_matches_the_current_reader_url():
    library = [Novel(_id="ri", title="Reverend Insanity",
                     source_url="https://mangafire.to/title/zkw8p-reverend-insanity-2025")]
    n = api._find_by_url(library, "https://mangafire.to/title/zkw8p-reverend-insanity-2025/chapter/8205410")
    assert n is not None and n._id == "ri"


# Authors and genres from different structures

def _author_of(body, head=""):
    return _fated(f"<html><head>{head}</head><body><h1>X</h1>{body}</body></html>").author


def test_author_from_a_label_element_and_its_sibling_with_or_without_a_colon():
    assert _author_of("<div><span>Author</span><span><a href='/p/1'>Liu Mang</a>, Mu Tou Ren</span></div>") \
        == "Liu Mang, Mu Tou Ren"
    assert _author_of("<div><div>Author:</div><div>Liu Mang</div></div>") == "Liu Mang"
    assert _author_of("<dl><dt>Authors</dt><dd>Liu Mang; Mu Tou Ren</dd></dl>") == "Liu Mang, Mu Tou Ren"


def test_author_from_itemprop_json_ld_and_meta():
    assert _author_of('<span itemprop="author">Liu Mang</span>') == "Liu Mang"
    ld = '{"@type": "Book", "author": [{"@type": "Person", "name": "Liu Mang"}, {"name": "Mu Tou Ren"}]}'
    assert _author_of("", f'<script type="application/ld+json">{ld}</script>') == "Liu Mang, Mu Tou Ren"
    assert _author_of("", '<meta name="author" content="Liu Mang">') == "Liu Mang"
    assert _author_of("", '<meta name="author" content="MangaFire">') == ""          # the site, not an author


def test_author_links_in_a_menu_or_sidebar_are_not_this_series():
    menu = '<nav><a href="/author/1">Menu Person</a></nav><div class="sidebar"><a href="/author/2">Other</a></div>'
    assert _author_of(menu) == ""
    assert _author_of(menu + '<div><a href="/author/3">Liu Mang</a></div>') == "Liu Mang"


def test_a_site_wide_genre_list_is_not_taken_as_this_series_genres():
    nav = "<nav>" + "".join(f'<a href="/genre/g{i}">G{i}</a>' for i in range(30)) + "</nav>"
    assert _fated(f"<html><body><h1>X</h1>{nav}</body></html>").genres == []
    wide = "<div>" + "".join(f'<a href="/genre/g{i}">G{i}</a>' for i in range(30)) + "</div>"
    assert _fated(f"<html><body><h1>X</h1>{wide}</body></html>").genres == []        # too many to be one series
    few = '<div><a href="/genre/a">Action</a><a href="/genre/f">Fantasy</a></div>'
    assert _fated(f"<html><body><h1>X</h1>{few}</body></html>").genres == ["Action", "Fantasy"]


def test_genres_from_a_label_and_sibling():
    html = "<html><body><h1>X</h1><div><span>Genres</span><div>Action, Comedy, Drama</div></div></body></html>"
    assert _fated(html).genres == ["Action", "Comedy", "Drama"]
