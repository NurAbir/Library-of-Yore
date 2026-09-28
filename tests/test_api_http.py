"""End-to-end check of the local HTTP API on a random port."""
import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import HTTPServer

import pytest

import api_server as api
from database.models import Novel, NovelRepository


@pytest.fixture(scope="module")
def server():
    srv = HTTPServer(("127.0.0.1", 0), api.Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def _post(base, path, body, content_type="application/json", origin=None):
    req = urllib.request.Request(base + path, data=body.encode(), method="POST")
    req.add_header("Content-Type", content_type)
    if origin:
        req.add_header("Origin", origin)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, dict(r.headers), json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), json.loads(e.read())


def test_progress_requires_json_content_type(server):
    repo = NovelRepository()
    nid = repo.insert(Novel(title="CT test"))
    status, _, _ = _post(server, "/progress", json.dumps({"novel_id": nid, "chapter": 5}), "text/plain")
    assert status == 415
    assert repo.get_by_id(nid).current_chapter == 0

    status, _, body = _post(server, "/progress", json.dumps({"novel_id": nid, "chapter": 5}))
    assert status == 200 and body["updated"] is True
    assert repo.get_by_id(nid).current_chapter == 5


def test_foreign_origin_gets_no_cors_header(server):
    repo = NovelRepository()
    nid = repo.insert(Novel(title="CORS test"))
    _, headers, _ = _post(server, "/progress", json.dumps({"novel_id": nid, "chapter": 1}),
                          origin="http://localhost.attacker.example")
    assert "Access-Control-Allow-Origin" not in headers
    _, headers, _ = _post(server, "/progress", json.dumps({"novel_id": nid, "chapter": 2}),
                          origin="chrome-extension://abcdefghijklmnop")
    assert headers.get("Access-Control-Allow-Origin") == "chrome-extension://abcdefghijklmnop"


def test_find_reports_match_type(server):
    repo = NovelRepository()
    repo.insert(Novel(title="Match Type Novel", source_url="https://novelfire.net/book/match-type-novel"))
    q = urllib.parse.urlencode({"url": "https://novelfire.net/book/match-type-novel/chapter-3",
                                "title": "Match Type Novel"})
    with urllib.request.urlopen(f"{server}/find?{q}") as r:
        body = json.loads(r.read())
    assert body["found"] and body["match"] == "url"

    q = urllib.parse.urlencode({"url": "https://novelfire.net/book/renamed-slug/chapter-3",
                                "title": "Match Type Novel"})
    with urllib.request.urlopen(f"{server}/find?{q}") as r:
        body = json.loads(r.read())
    assert body["found"] and body["match"] == "title"


def test_bad_json_is_rejected_not_crashing(server):
    status, _, body = _post(server, "/progress", "{not json")
    assert status == 400 and "invalid JSON" in body["error"]
