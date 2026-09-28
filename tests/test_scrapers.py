"""Shared chapter parser and the Flame Comics scraper."""
import json

import pytest

from scrapers.base import BaseScraper, ScraperResult, parse_chapter_label, latest_from_labels
from scrapers import flamecomics, get_scraper_for_url
from utils import chapters as C


P = BaseScraper()


@pytest.mark.parametrize("text,expected", [
    ("Latest Chapter: 45.5", "45.5"),            # decimals kept (was 45)
    ("Latest: Chapter 900  Chapter 1", "900"),
    ("Latest release: Ch. 2,111", "2111"),
    ("756 Chapters Latest Chapter 755", "755"),  # explicit latest beats a count
    ("1,234 Chapters", "1234"),
    ("Views 12,345 Reads 2024 chess", None),     # was 2024 ("ch" in "chess")
    ("Rank 3 characters", None),
    ("Page 7 of 12, 99 reviews", None),          # no "largest number" guess (was 99)
    ("", None),
])
def test_extract_chapter_number(text, expected):
    assert P._extract_chapter_number(text) == expected


@pytest.mark.parametrize("label,expected", [
    ("Chapter 12", "12"),
    ("Chapter 45.5", "45.5"),
    ("Ch. 2.2", "2.2"),
    ("chapter 12-5", "12"),
    ("Chapter 12. The Beginning", "12"),
    ("Chapter 18 - Star-Counting Night (4)", "18"),
    ("Chapter 220 - Side Story", "220"),
    ("Extra Chapter 3", None),
    ("Prologue", None),
    ("Epilogue 2", None),
    ("Night (4)", None),
])
def test_parse_chapter_label(label, expected):
    assert parse_chapter_label(label) == expected


def test_latest_from_labels_ignores_page_order():
    assert latest_from_labels(["Chapter 0", "Chapter 1", "Chapter 755"]) == "755"   # was 0/1
    assert latest_from_labels(["Chapter 755", "Chapter 754", "Prologue"]) == "755"
    assert latest_from_labels(["Chapter 9", "Chapter 10", "Chapter 9.5"]) == "10"
    assert latest_from_labels(["Prologue"]) is None


# ── Flame Comics ──────────────────────────────────────────────────────────────

def _page(kind, info, chapters_json, og_image=True):
    key = "novels" if kind == "novel" else "series"
    data = {"props": {"pageProps": {key: info, "chapters": chapters_json, "gallery": []}},
            "page": f"/{kind}/[id]", "buildId": "test"}
    og = ('<meta property="og:image" content="https://cdn.flamecomics.xyz/uploads/images/'
          f'{key}/{info.get("novel_id") or info.get("series_id")}/thumbnail.webp"/>') if og_image else ""
    return (f"<html><head><title>{info['title']} - Flame Comics</title>{og}</head><body>"
            f"<div>JavaScript is required</div>"
            f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(data)}</script>'
            "</body></html>")


def _novel_chapter(n, price="0.00", title=""):
    return {"chapter_id": 1, "novel_id": 8, "chapter": n, "title": title, "notice": 0,
            "price": price, "public_release": None, "release_date": 1786201269,
            "token": "f48067c3fe28e0a0", "edit_time": 1, "mtl": 0}


ORV_NOVEL = {"novel_id": 8, "title": "Omniscient Reader's Viewpoint",
             "description": '<p class="x">‘This is a development that I know of.’</p>',
             "type": "Web Novel", "tags": ["Action", "Fantasy", "Apocalypse", "Drama", "Modern", "Hunters"],
             "author": ["Sing-Shong"], "status": "Ongoing", "cover": "thumbnail.webp", "series_id": 2,
             "unlock_policy": "ROLLING_LATEST", "locked_chapter_count": 10}


def test_flame_novel_page_orv_shape():
    # newest first, 1..621 with 221-224 missing; 130-135 and 527-621 locked
    nums = [n for n in range(621, 0, -1) if n not in (221, 222, 223, 224)]
    chs = [_novel_chapter(f"{n}.00", "50.00" if (n >= 527 or 130 <= n <= 135) else "0.00") for n in nums]
    r = flamecomics.parse_page(_page("novel", ORV_NOVEL, chs), "novel", "8", ScraperResult())
    assert r.success and r.title == "Omniscient Reader's Viewpoint"
    assert r.author == "Sing-Shong" and r.content_type == "novel"
    assert r.synopsis.startswith("‘This is a development")
    assert r.status == "Ongoing" and r.genres == ["Action", "Fantasy", "Apocalypse", "Drama", "Modern"]
    assert r.cover_url.endswith("/novels/8/thumbnail.webp")
    assert r.latest_chapter == "621"
    assert len(r.chapter_list) == 617 and C.encode_ranges(r.chapter_list) == "1-220,225-621"
    assert C.encode_ranges(r.locked_list) == "130-135,527-621"
    assert r.raw_data["linked_series_id"] == 2


def test_flame_series_with_chapter_zero_and_decimals():
    info = {"series_id": 5, "title": "Some Manhwa", "type": "Manhwa", "status": "Hiatus",
            "author": ["A"], "tags": ["Action"], "description": "", "cover": "thumbnail.png", "novel_id": None}
    chs = [{"chapter": n, "title": "", "token": "abc"} for n in ["18.00", "16.50", "16.00", "5.50", "5.00", "0.00"]]
    r = flamecomics.parse_page(_page("series", info, chs), "series", "5", ScraperResult())
    assert r.content_type == "manga"
    assert r.chapter_list == ["0", "5", "5.5", "16", "16.5", "18"]
    assert r.latest_chapter == "18" and r.locked_list == []


def test_flame_novel_starting_at_0_01():
    info = dict(ORV_NOVEL, novel_id=13, title="Novel 13")
    chs = [_novel_chapter(f"{n}.00") for n in range(755, 0, -1)] + [_novel_chapter("0.01")]
    r = flamecomics.parse_page(_page("novel", info, chs), "novel", "13", ScraperResult())
    assert C.encode_ranges(r.chapter_list) == "0.01,1-755" and len(r.chapter_list) == 756


def test_flame_duplicate_numbers_drop_the_list():
    chs = [_novel_chapter("2.10"), _novel_chapter("2.1"), _novel_chapter("1.00")]
    r = flamecomics.parse_page(_page("novel", ORV_NOVEL, chs), "novel", "8", ScraperResult())
    assert r.chapter_list == [] and r.latest_chapter == "2.1"   # simple mode for this title


def test_flame_page_without_data():
    r = flamecomics.parse_page("<html>Just a moment...</html>", "novel", "8", ScraperResult())
    assert not r.success and "__NEXT_DATA__" in r.error_message


def test_flame_canonical_url():
    assert flamecomics.canonical_url("https://flamecomics.xyz/novel/8/f48067c3fe28e0a0") == \
        ("novel", "8", "https://flamecomics.xyz/novel/8")
    assert flamecomics.canonical_url("https://www.flamecomics.xyz/series/2") == \
        ("series", "2", "https://flamecomics.xyz/series/2")
    assert flamecomics.canonical_url("https://flamecomics.xyz/series/21?x=1")[1] == "21"
    assert flamecomics.canonical_url("https://flamecomics.xyz/browse") is None


def test_flame_scrape_end_to_end_with_mocked_request(monkeypatch):
    chs = [_novel_chapter(f"{n}.00") for n in range(3, 0, -1)]
    html = _page("novel", ORV_NOVEL, chs)

    class Resp:
        text = html
        def raise_for_status(self):
            pass

    monkeypatch.setattr(flamecomics.requests, "get", lambda *a, **k: Resp())
    scraper = get_scraper_for_url("https://flamecomics.xyz/novel/8/f48067c3fe28e0a0")
    assert isinstance(scraper, flamecomics.FlameComicsScraper)
    r = scraper.scrape("https://flamecomics.xyz/novel/8/f48067c3fe28e0a0")
    assert r.success and r.status == "ongoing" and r.latest_chapter == "3"
    assert r.raw_data["url"] == "https://flamecomics.xyz/novel/8"


def test_flame_real_series_page_structure():
    """Fixture rebuilt from the live page https://flamecomics.xyz/series/5
    (September 2026): same keys, same chapter numbers and order, same meta
    tag; only the synopsis is shortened."""
    from pathlib import Path
    html = (Path(__file__).parent / "fixtures" / "flame_series_5.html").read_text(encoding="utf-8")
    r = flamecomics.parse_page(html, "series", "5", ScraperResult(source_name="flamecomics"))
    assert r.success and r.title == "Unnamed Memory" and r.content_type == "manga"
    assert r.author == "FURUMIYA Kuji" and r.genres == ["Fantasy", "Shounen", "Romance"]
    assert r.status == "Dropped"
    assert r.cover_url == "https://cdn.flamecomics.xyz/uploads/images/series/5/thumbnail.jpg"
    assert C.encode_ranges(r.chapter_list) == "1-5,5.5,6-16,16.5,17-18"
    assert r.latest_chapter == "18" and r.locked_list == []
    assert r.synopsis.startswith("“As long as you")
    p = C.compute_progress("5", r.latest_chapter, C.encode_ranges(r.chapter_list))
    assert p.next_chapter == "5.5" and p.behind == 15 and p.total == 20
