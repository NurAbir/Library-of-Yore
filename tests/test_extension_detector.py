"""The MangaFire detector in the browser extension's content.js, run under Node.

The current reader URL is /title/{id}-{slug}/chapter/{internal chapter id}, e.g.
/title/zkw8p-reverend-insanity-2025/chapter/8205410. The last segment is an internal
id, so the chapter number must come from the page. The page contents below are
SCRIPTED (what a tab title / heading could say), since the real reader DOM hasn't been seen.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

HARNESS = Path(__file__).resolve().parent / "js" / "detector_harness.js"
RI = "/title/zkw8p-reverend-insanity-2025/chapter/8205410"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")


def run(*steps):
    proc = subprocess.run(["node", str(HARNESS)], input=json.dumps(list(steps)), capture_output=True,
                          text=True, check=True, timeout=30)
    return json.loads(proc.stdout)


def one(**step):
    step.setdefault("path", RI)
    return run(step)[0]


def test_the_chapter_number_comes_from_the_tab_title_not_the_internal_id():
    r = one(title="Reverend Insanity Manga, Chapter 1234")
    assert r["info"]["chapter"] == "1234" and r["info"]["chapter"] != "8205410"
    assert r["info"]["sourceUrl"] == "https://mangafire.to/title/zkw8p-reverend-insanity-2025"
    assert r["info"]["contentType"] == "manga" and r["info"]["ambiguous"] is False


@pytest.mark.parametrize("kind, step, chapter", [
    ("title, dash form", {"title": "Reverend Insanity - Chapter 12.5 - MangaFire"}, "12.5"),
    ("title, short form", {"title": "Reverend Insanity Ch. 7"}, "7"),
    ("og:title", {"title": "MangaFire - Read Manga Online Free", "og": "Reverend Insanity Chapter 88"}, "88"),
    ("a heading", {"title": "MangaFire", "headings": ["Reverend Insanity", "Chapter 301: A title"]}, "301"),
    ("the selected chapter", {"title": "MangaFire", "current": ["Chap 45"]}, "45"),
])
def test_chapter_number_sources(kind, step, chapter):
    assert one(**step)["info"]["chapter"] == chapter


def test_the_title_is_preferred_over_headings_and_selection():
    r = one(title="Reverend Insanity Chapter 10", headings=["Chapter 11"], current=["Chapter 12"])
    assert r["info"]["chapter"] == "10"


@pytest.mark.parametrize("title, novel", [
    ("I Am the Fated Villain - Chapter 370", "I Am the Fated Villain"),
    ("Reverend Insanity Manga, Chapter 1234", "Reverend Insanity"),
    ("Reverend Insanity - Chapter 12.5 - MangaFire", "Reverend Insanity"),
    ("Reverend Insanity Ch. 7", "Reverend Insanity"),
])
def test_the_series_title_is_read_from_the_tab_title(title, novel):
    # The live tab title is "Title - Chapter N"; the old pattern only knew
    # "Title Manga, Chapter N" and fell back to the URL slug.
    assert one(title=title)["info"]["novelTitle"] == novel


def test_words_that_merely_contain_ch_are_not_chapters():
    r = one(title="MangaFire - Search 12", headings=["Touch 5"])
    assert r["info"] is None and "no chapter number" in r["debug"]


def test_no_chapter_number_on_the_page_explains_itself_for_the_popup():
    r = one(title="MangaFire - Read Manga Online Free", headings=["Reverend Insanity"])
    assert r["info"] is None
    assert "id 8205410" in r["debug"] and "MangaFire - Read Manga Online Free" in r["debug"]
    assert "Reverend Insanity" in r["debug"]


def test_a_stale_title_after_navigation_is_not_reported_as_the_new_chapter():
    first = {"path": RI, "title": "Reverend Insanity Chapter 10"}
    # URL changed to the next chapter but the page still says chapter 10
    stale = {"path": "/title/zkw8p-reverend-insanity-2025/chapter/8205411", "title": "Reverend Insanity Chapter 10",
             "advance": 500}
    updated = {**stale, "title": "Reverend Insanity Chapter 11", "advance": 500}
    r = run(first, stale, updated)
    assert r[0]["info"]["chapter"] == "10"
    assert r[1]["info"] is None                        # skipped, not mis-reported
    assert r[2]["info"]["chapter"] == "11"


def test_a_stale_value_is_skipped_only_while_a_fresher_one_may_still_arrive():
    first = {"path": RI, "title": "Reverend Insanity Chapter 10"}
    same = {"path": "/title/zkw8p-reverend-insanity-2025/chapter/8205411", "title": "Reverend Insanity Chapter 10"}
    r = run(first, {**same, "advance": 500}, {**same, "advance": 5000})
    assert r[1]["info"] is None
    assert r[2]["info"]["chapter"] == "10"             # after the grace period the page's answer is taken


def test_a_fresh_candidate_elsewhere_wins_over_a_stale_title():
    first = {"path": RI, "title": "Reverend Insanity Chapter 10"}
    nxt = {"path": "/title/zkw8p-reverend-insanity-2025/chapter/8205411", "title": "Reverend Insanity Chapter 10",
           "headings": ["Chapter 11"], "advance": 300}
    assert run(first, nxt)[1]["info"]["chapter"] == "11"


@pytest.mark.parametrize("path, chapter", [
    ("/read/lag.zl363/en/chapter-7", "7"),                  # older reader URLs still carry the number
    ("/read/wo-tian-ming-da-fanpaii.m2wxz/en/chapter-108", "108"),
    ("/title/zl363-lagg/en/chapter-7.2", "7.2"),
])
def test_older_reader_urls_need_nothing_from_the_page(path, chapter):
    assert one(path=path, title="MangaFire")["info"]["chapter"] == chapter


@pytest.mark.parametrize("path", [
    "/title/zkw8p-reverend-insanity-2025",                  # the series page
    "/title/zkw8p-reverend-insanity-2025/2",
    "/title/zkw8p-reverend-insanity-2025/chapter",
    "/title/zkw8p-reverend-insanity-2025/chapter/abc",
    "/title/updated/chapter/8205410",                       # not a series id (no digit)
    "/updated",
])
def test_pages_that_are_not_chapters_are_ignored(path):
    assert one(path=path, title="Reverend Insanity Chapter 5")["info"] is None
