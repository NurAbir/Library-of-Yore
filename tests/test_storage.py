"""library.json storage: concurrent access, atomic writes, backups."""
import json
import threading

import pytest
from tinydb import TinyDB, Query

from database.connection import AtomicJSONStorage


def _db(path):
    return TinyDB(path, storage=AtomicJSONStorage, indent=2, ensure_ascii=False, encoding="utf-8")


def test_concurrent_reads_during_writes_never_corrupt_file(tmp_path):
    """Regression for the pre-2.0.2 race: an unlocked read on the shared file
    handle during a write left invalid JSON behind. Here reads take the same
    lock the repository uses, and storage never shares a handle."""
    from database.connection import get_lock

    path = tmp_path / "lib.json"
    db = _db(path)
    table = db.table("novels")
    for i in range(60):
        table.insert({"_id": str(i), "title": "x" * 50, "notes": ""})

    stop = threading.Event()
    errors = []

    def writer():
        for k in range(300):
            with get_lock():
                table.update({"notes": "n" * 3000 if k % 2 else ""}, Query()._id == "5")

    def reader():
        while not stop.is_set():
            try:
                with get_lock():
                    assert len(table.all()) == 60
            except Exception as e:  # pragma: no cover - failure path
                errors.append(repr(e))

    readers = [threading.Thread(target=reader) for _ in range(2)]
    for r in readers:
        r.start()
    writer()
    stop.set()
    for r in readers:
        r.join()

    assert errors == []
    json.loads(path.read_text(encoding="utf-8"))  # file is valid JSON


def test_atomic_storage_survives_even_without_lock(tmp_path):
    """Even a reader that skips the lock only ever sees a complete file,
    because writes swap a finished temp file into place."""
    path = tmp_path / "lib.json"
    db = _db(path)
    table = db.table("novels")
    table.insert({"_id": "a", "notes": ""})
    reader_db = _db(path)  # separate storage object, like a second thread would use
    stop = threading.Event()
    errors = []

    def reader():
        while not stop.is_set():
            try:
                reader_db.table("novels").all()
            except PermissionError:
                pass  # Windows-only: file mid-replace; real code holds the lock
            except Exception as e:  # pragma: no cover
                errors.append(repr(e))

    t = threading.Thread(target=reader)
    t.start()
    for k in range(200):
        table.update({"notes": "n" * 2000 if k % 2 else ""}, Query()._id == "a")
    stop.set()
    t.join()
    assert errors == []
    json.loads(path.read_text(encoding="utf-8"))


def test_no_temp_files_left_behind(tmp_path):
    path = tmp_path / "lib.json"
    table = _db(path).table("novels")
    for i in range(20):
        table.insert({"i": i})
    assert [p.name for p in tmp_path.iterdir()] == ["lib.json"]


def test_utf8_round_trip(tmp_path):
    path = tmp_path / "lib.json"
    table = _db(path).table("novels")
    table.insert({"title": "全知読者視点 — “Café” ✨"})
    assert _db(path).table("novels").all()[0]["title"] == "全知読者視点 — “Café” ✨"
    assert "全知" in path.read_text(encoding="utf-8")


def test_daily_snapshots_keep_newest_seven(monkeypatch, tmp_path):
    import database.connection as conn

    lib = tmp_path / "library.json"
    lib.write_text("{}", encoding="utf-8")
    backups = tmp_path / "backups"
    backups.mkdir()
    for day in range(1, 11):
        (backups / f"library-2026-01-{day:02d}.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(conn, "LIBRARY_FILE", lib)
    monkeypatch.setattr(conn, "LIBRARY_BACKUP_FILE", tmp_path / "library.json.bak")
    monkeypatch.setattr(conn, "BACKUPS_DIR", backups)
    conn.backup_library_file()

    names = sorted(p.name for p in backups.iterdir())
    assert len(names) == 7
    assert (tmp_path / "library.json.bak").exists()
    # today's snapshot exists and the oldest ones were pruned
    assert "library-2026-01-01.json" not in names
