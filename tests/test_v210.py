"""v2.1.0: migration of old records, decimal progress through the API,
type-aware lookups, batched refresh saves."""
import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import HTTPServer

import pytest

import api_server as api
from database.models import Novel, NovelRepository, apply_scrape_result
from scrapers.base import ScraperResult


# ── Migration ────────────────────────────────────────────────────────────────

def test_old_record_zero_means_not_started():
    old = {"_id": "a", "title": "Old", "progress": {"current_chapter": 0, "total_chapters": 0, "status": "ongoing"}}
    n = Novel.from_dict(old)
    assert n.current_chapter is None and n.latest_chapter is None


def test_old_record_numbers_become_strings():
    old = {"_id": "b", "title": "Old", "progress": {"current_chapter": 120, "total_chapters": 756,
                                                    "percent_complete": 15.9, "status": "ongoing"}}
    n = Novel.from_dict(old)
    assert n.current_chapter == "120" and n.latest_chapter == "756"
    assert n.content_type == "novel" and n.chapter_list == ""
    assert n.progress.mode == "simple" and n.progress.behind == 636


def test_new_record_real_chapter_zero_survives_round_trip():
    repo = NovelRepository()
    nid = repo.insert(Novel(title="Zero", current_chapter="0", latest_chapter="311",
                            chapter_list="0-311", content_type="manga"))
    doc = repo.table.get(lambda d: d["_id"] == nid)
    assert doc["progress"]["current_chapter"] == "0" and doc["schema"] == 2
    got = repo.get_by_id(nid)
    assert got.current_chapter == "0" and got.content_type == "manga"
    assert got.next_chapter == "1"


def test_legacy_mongo_style_construction_normalizes():
    n = Novel(title="From Mongo", current_chapter=0, latest_chapter=100)
    assert n.current_chapter is None and n.latest_chapter == "100"
    n = Novel(title="From Mongo", current_chapter=45)
    assert n.current_chapter == "45"


# ── Refresh application and batch save ───────────────────────────────────────

def _flame_result(**kw):
    r = ScraperResult(source_name="flamecomics", success=True, title="ORV", status="ongoing",
                      latest_chapter="621", content_type="manga",
                      chapter_list=[str(n) for n in range(1, 622)], locked_list=["620", "621"])
    for k, v in kw.items():
        setattr(r, k, v)
    return r


def test_apply_scrape_result_updates_site_data_only():
    n = Novel(title="ORV", current_chapter="300", status="dropped")
    assert apply_scrape_result(n, _flame_result())
    assert n.latest_chapter == "621" and n.chapter_list == "1-621" and n.locked_list == "620-621"
    assert n.content_type == "manga" and n.site_status == "ongoing"
    assert n.status == "dropped" and n.current_chapter == "300" and n.last_read is None
    assert not apply_scrape_result(n, _flame_result())       # nothing new the second time


def test_non_flame_scraper_does_not_change_type():
    n = Novel(title="X", content_type="manga")
    r = ScraperResult(source_name="novelfire", success=True, latest_chapter="10", status="ongoing")
    apply_scrape_result(n, r)
    assert n.content_type == "manga" and n.chapter_list == ""   # simple-mode sites keep no list


def test_update_many_single_write():
    repo = NovelRepository()
    ids = [repo.insert(Novel(title=f"Batch {i}")) for i in range(3)]
    novels = [repo.get_by_id(i) for i in ids]
    for n in novels:
        n.latest_chapter = "50"
    assert repo.update_many(novels) == 3
    assert all(repo.get_by_id(i).latest_chapter == "50" for i in ids)


# ── API ──────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def server():
    srv = HTTPServer(("127.0.0.1", 0), api.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def _progress(base, body):
    req = urllib.request.Request(base + "/progress", data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def test_api_decimal_progress_and_forward_only(server):
    repo = NovelRepository()
    nid = repo.insert(Novel(title="Decimal API", latest_chapter="3", chapter_list="0,1,2,2.5,3"))
    assert _progress(server, {"novel_id": nid, "chapter": "0"})["updated"]        # 0 from not started
    assert _progress(server, {"novel_id": nid, "chapter": "2"})["current"] == "2"
    r = _progress(server, {"novel_id": nid, "chapter": 2.5})
    assert r["updated"] and r["current"] == "2.5" and r["novel"]["next_chapter"] == "3"
    assert not _progress(server, {"novel_id": nid, "chapter": "2"})["updated"]    # never backwards
    assert repo.get_by_id(nid).current_chapter == "2.5"


def test_api_ambiguous_url_number_snaps_to_whole(server):
    repo = NovelRepository()
    nid = repo.insert(Novel(title="Ambiguous API", latest_chapter="10", chapter_list="1-10"))
    r = _progress(server, {"novel_id": nid, "chapter": "4.5", "ambiguous": True})
    assert r["current"] == "4"       # list has no 4.5 -> whole chapter
    nid2 = repo.insert(Novel(title="Ambiguous API 2", latest_chapter="10", chapter_list="1-4,4.5,5-10"))
    assert _progress(server, {"novel_id": nid2, "chapter": "4.5", "ambiguous": True})["current"] == "4.5"


def test_api_rejects_non_numeric_chapter(server):
    repo = NovelRepository()
    nid = repo.insert(Novel(title="Bad chapter"))
    req = urllib.request.Request(server + "/progress", data=json.dumps({"novel_id": nid, "chapter": "Prologue"}).encode(),
                                 method="POST", headers={"Content-Type": "application/json"})
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(req)
    assert e.value.code == 400


def test_find_title_fallback_respects_type(server):
    repo = NovelRepository()
    repo.insert(Novel(title="Twin Title Story", content_type="novel",
                      source_url="https://flamecomics.xyz/novel/901"))
    repo.insert(Novel(title="Twin Title Story", content_type="manga",
                      source_url="https://flamecomics.xyz/series/902"))

    def find(**q):
        with urllib.request.urlopen(f"{server}/find?{urllib.parse.urlencode(q)}") as r:
            return json.loads(r.read())

    # URL match: exact entry, regardless of the shared title
    r = find(url="https://flamecomics.xyz/series/902/abcdef0123456789", title="Twin Title Story", type="manga")
    assert r["match"] == "url" and r["novel"]["content_type"] == "manga"
    # URL unknown (e.g. entry saved without a URL match), title + type decides
    r = find(url="https://flamecomics.xyz/series/999/abcdef0123456789", title="Twin Title Story", type="novel")
    assert r["match"] == "title" and r["novel"]["content_type"] == "novel"
    # Without a type the shared title is ambiguous: no guess
    r = find(url="https://flamecomics.xyz/series/999/abcdef0123456789", title="Twin Title Story")
    assert r["found"] is False
