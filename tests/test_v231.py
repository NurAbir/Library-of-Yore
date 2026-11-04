"""v2.3.1 regression tests: quitting/startup, duplicate inserts, locked
chapters without a chapter list, chapter-URL matching, empty status filters,
port collisions, hostname matching, status defaults, cover file formats and
atomic config writes."""
import io
import sys

import pytest
from PIL import Image

import api_server as api
import config
import startup
from database.models import Novel, NovelRepository, apply_scrape_result, apply_site_status
from scrapers import get_scraper_for_url
from scrapers.base import ScraperResult
from scrapers.novelfire import NovelfireScraper


# ── Duplicate inserts / repeated legacy import ───────────────────────────────

def test_insert_with_same_id_replaces_instead_of_duplicating():
    repo = NovelRepository()
    novel = Novel(title="Dup Test")
    novel._id = repo.insert(novel)

    repo.insert(novel)  # e.g. the legacy importer running a second time

    docs = [d for d in repo.table.all() if d["_id"] == novel._id]
    assert len(docs) == 1


def test_insert_collapses_duplicate_rows_left_by_older_versions():
    repo = NovelRepository()
    novel = Novel(title="Messy Dup")
    novel._id = repo.insert(novel)

    # Simulate the pre-2.3.1 bug: a second raw row with the same _id.
    repo.table.insert(dict(repo.table.get(lambda d: d["_id"] == novel._id)))
    assert len(repo.table.search(lambda d: d["_id"] == novel._id)) == 2

    novel.title = "Messy Dup (fixed)"
    repo.insert(novel)
    assert len(repo.table.search(lambda d: d["_id"] == novel._id)) == 1
    assert repo.get_by_id(novel._id).title == "Messy Dup (fixed)"


# ── Wuxiaworld locked chapters in simple mode ────────────────────────────────

def test_locked_list_is_kept_without_a_chapter_list():
    novel = Novel(title="Against the Gods", current_chapter="2190", latest_chapter="2190")
    result = ScraperResult(
        source_name="wuxiaworld", success=True,
        latest_chapter="2200", chapter_list=[], locked_list=["2191", "2192"],
    )
    assert apply_scrape_result(novel, result) is True
    assert novel.locked_list == "2191-2192"


# ── Chapter URLs are canonicalised, and old ones still match ────────────────

def test_scraper_canonical_page_url():
    scraper = get_scraper_for_url("https://novelfire.net/book/shadow-slave/chapter-5")
    assert scraper.canonical_page_url(
        "https://novelfire.net/book/shadow-slave/chapter-5") == \
        "https://novelfire.net/book/shadow-slave"


def test_legacy_chapter_url_matches_a_later_chapter():
    stored = Novel(_id="nf", title="Shadow Slave",
                   source_url="https://novelfire.net/book/shadow-slave/chapter-5")
    match = api._find_by_url([stored], "https://novelfire.net/book/shadow-slave/chapter-6")
    assert match is stored


# ── Empty status filter means nothing, not everything ────────────────────────

def test_empty_status_filter_returns_no_novels():
    repo = NovelRepository()
    repo.insert(Novel(title="Filter Test A", status="ongoing"))
    repo.insert(Novel(title="Filter Test B", status="completed"))
    assert repo.get_all(status_filter=[]) == []
    assert len(repo.get_all()) >= 2


# ── API port collision ───────────────────────────────────────────────────────

def test_api_start_reports_port_in_use(monkeypatch):
    monkeypatch.setattr(api, "_server_instance", None)

    def boom(*args, **kwargs):
        raise OSError("address already in use")

    monkeypatch.setattr(api, "HTTPServer", boom)
    with pytest.raises(OSError):
        api.start()


# ── Scraper detection by hostname ────────────────────────────────────────────

def test_lookalike_domain_is_not_claimed():
    assert get_scraper_for_url("https://novelfire.net.evil.example/book/x") is None
    assert get_scraper_for_url("https://novelfire.net/book/x") is not None


# ── Unknown site status stays unknown, and site-dropped is separate ──────────

def test_unknown_status_is_not_guessed():
    scraper = NovelfireScraper()
    assert scraper._normalize_status("") == ""
    assert scraper._normalize_status("side story") == ""
    assert scraper._normalize_status("Ongoing") == "ongoing"


def test_site_dropped_does_not_become_a_reader_only_status():
    novel = Novel(title="Cancelled", status="ongoing")
    assert apply_site_status(novel, "dropped") is True
    assert novel.site_status == "dropped"
    assert novel.status == "ongoing"  # still updatable by the site later


# ── Cover files match their content ─────────────────────────────────────────

def test_saved_cover_is_really_a_jpeg():
    buffer = io.BytesIO()
    Image.new("RGB", (8, 12), "blue").save(buffer, format="PNG")

    repo = NovelRepository()
    cover_id = repo.save_cover(buffer.getvalue())

    assert cover_id.endswith(".jpg")
    assert repo.get_cover(cover_id)[:3] == b"\xff\xd8\xff"


# ── Start-with-Windows command and config ────────────────────────────────────

def test_startup_command_includes_startup_flag():
    assert startup.STARTUP_ARG in startup.launch_command()


def test_startup_enable_writes_the_run_value(monkeypatch):
    written = {}

    class FakeKey:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    class FakeWinreg:
        HKEY_CURRENT_USER = 0
        KEY_READ = 1
        KEY_SET_VALUE = 2
        REG_SZ = 3

        def CreateKeyEx(self, *args, **kwargs):
            return FakeKey()

        def SetValueEx(self, key, name, reserved, kind, value):
            written[name] = value

    monkeypatch.setattr(startup, "is_supported", lambda: True)
    monkeypatch.setattr(startup, "launch_command", lambda: '"app.exe" --startup')
    monkeypatch.setitem(sys.modules, "winreg", FakeWinreg())

    assert startup.enable() is True
    assert written[startup.VALUE_NAME] == '"app.exe" --startup'


def test_startup_disable_removes_the_run_value(monkeypatch):
    deleted = []

    class FakeKey:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    class FakeWinreg:
        HKEY_CURRENT_USER = 0
        KEY_SET_VALUE = 2

        def OpenKey(self, *args, **kwargs):
            return FakeKey()

        def DeleteValue(self, key, name):
            deleted.append(name)

    monkeypatch.setattr(startup, "is_supported", lambda: True)
    monkeypatch.setitem(sys.modules, "winreg", FakeWinreg())

    assert startup.disable() is True
    assert deleted == [startup.VALUE_NAME]


def test_save_config_is_atomic_and_round_trips():
    cfg = config.load_config()
    cfg["startup_prompt_shown"] = True
    config.save_config(cfg)

    assert config.load_config()["startup_prompt_shown"] is True
    assert not config.CONFIG_FILE.with_name(config.CONFIG_FILE.name + ".tmp").exists()
