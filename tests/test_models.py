"""Novel model and repository behaviour fixed in 2.0.2."""
import dataclasses
import datetime

from database.models import Novel, NovelRepository, apply_site_status


def test_update_does_not_touch_last_read():
    repo = NovelRepository()
    n = Novel(title="Shadow Slave", source_url="https://novelfire.net/book/shadow-slave")
    n._id = repo.insert(n)
    before = repo.get_by_id(n._id)
    assert before.last_read is None

    before.latest_chapter = "2000"        # e.g. startup refresh found new chapters
    repo.update(before)
    assert repo.get_by_id(n._id).last_read is None


def test_chapter_progress_sets_last_read_and_count():
    repo = NovelRepository()
    n = Novel(title="Lord of the Mysteries", latest_chapter="100")
    n._id = repo.insert(n)
    repo.update_chapter_progress(n._id, 10)
    got = repo.get_by_id(n._id)
    assert got.current_chapter == "10"
    assert got.read_count == 1
    assert got.last_read is not None
    doc = repo.table.get(lambda d: d["_id"] == n._id)
    assert doc["progress"]["percent_complete"] == 10.0   # derived field kept in step


def test_edit_style_replace_preserves_untouched_fields():
    """The Edit dialog now builds its result with dataclasses.replace on the
    stored novel, so fields the form doesn't show survive a save."""
    repo = NovelRepository()
    added = datetime.datetime(2025, 1, 2, 3, 4, 5)
    n = Novel(title="ORV", date_added=added, read_count=42, cover_url="https://x/cover.jpg",
              last_scraped=added, site_status="ongoing")
    n._id = repo.insert(n)
    stored = repo.get_by_id(n._id)
    edited = dataclasses.replace(stored, notes="great", rating=9)
    repo.update(edited)
    got = repo.get_by_id(n._id)
    assert got.date_added == added
    assert got.read_count == 42
    assert got.cover_url == "https://x/cover.jpg"
    assert got.last_scraped == added
    assert got.notes == "great" and got.rating == 9


def test_site_status_never_overrides_dropped_or_planned():
    for mine in ("dropped", "planned"):
        n = Novel(title="t", status=mine)
        assert apply_site_status(n, "ongoing") is True   # site_status recorded
        assert n.status == mine
        assert n.site_status == "ongoing"


def test_site_status_still_moves_ongoing_to_completed():
    n = Novel(title="t", status="ongoing")
    assert apply_site_status(n, "completed")
    assert n.status == "completed"
    assert not apply_site_status(n, "completed")  # nothing new
    assert not apply_site_status(n, "")           # unknown site status is ignored


def test_old_records_without_site_status_load():
    doc = {"_id": "x", "title": "Old", "progress": {"current_chapter": 3, "status": "hiatus"}}
    n = Novel.from_dict(doc)
    assert n.site_status == "" and n.status == "hiatus"
