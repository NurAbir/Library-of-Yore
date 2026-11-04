"""The add dialog's status line after a MangaFire fetch: what was found and what was not."""
import pytest
from PyQt6.QtWidgets import QApplication

from database.models import NovelRepository
from scrapers.base import ScraperResult
from ui.add_novel_dialog import AddNovelDialog


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def dialog(app):
    d = AddNovelDialog(NovelRepository())
    yield d
    d.close()


def _result(**kw):
    r = ScraperResult(source_name="mangafire", content_type="manga", success=True, title="I Am the Fated Villain")
    r.raw_data = {"saved_page": r"C:\logs\mangafire_last_page.html"}
    for k, v in kw.items():
        setattr(r, k, v)
    return r


def _status(d):
    return d.fetch_status_label.text()


def test_everything_found_adds_no_note(dialog):
    r = _result(author="Liu Mang", genres=["Action"], cover_url="https://x/c.jpg", latest_chapter="341")
    dialog._on_scrape_finished(r, b"")
    dialog._on_scrape_finished(r, b"\xff\xd8")
    assert "Not found" not in _status(dialog)


def test_missing_details_are_listed_with_the_saved_page_path(dialog):
    dialog._on_scrape_finished(_result(), None)
    text = _status(dialog)
    assert text.startswith("✓  I Am the Fated Villain")
    assert "Not found: author, genres, cover, latest chapter." in text
    assert r"C:\logs\mangafire_last_page.html" in text
    assert dialog.title_input.text() == "I Am the Fated Villain"


def test_a_cover_that_was_found_but_not_downloaded_is_called_out(dialog):
    r = _result(author="A", genres=["G"], latest_chapter="3", cover_url="https://x/c.jpg")
    dialog._on_scrape_finished(r, None)
    assert "cover (found, but the image couldn't be downloaded)" in _status(dialog)
    assert "author" not in _status(dialog).split("Not found:")[1]


def test_other_sites_get_no_note(dialog):
    r = ScraperResult(source_name="novelfire", content_type="novel", success=True, title="X")
    dialog._on_scrape_finished(r, None)
    assert "Not found" not in _status(dialog)
