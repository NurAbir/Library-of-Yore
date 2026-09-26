"""Local JSON-file storage management (replaces MongoDB as of v2.0).

Novels are stored in one TinyDB-backed JSON file (config.LIBRARY_FILE) inside
the app's data directory instead of a MongoDB server. TinyDB gives the same
"insert/query a dict" ergonomics MongoDB did, just without anything to
install, start, or keep running in the background.
"""
import datetime
import json
import shutil
import threading
from typing import Optional

from tinydb import TinyDB
from tinydb.storages import JSONStorage

from config import LIBRARY_FILE, LIBRARY_BACKUP_FILE

_db = None
_write_lock = threading.Lock()  # guards writes from the UI thread and the browser-extension API thread


def _try_load(path, encoding) -> Optional[dict]:
    """Return parsed JSON content read with the given encoding, or None if
    the file doesn't exist, isn't valid at that encoding, or isn't valid
    JSON once decoded."""
    if not path.exists():
        return None
    try:
        with open(path, encoding=encoding) as f:
            return json.load(f)
    except Exception:
        return None


def recover_library_file() -> Optional[str]:
    """Call once, before the first get_db(), so an unreadable library.json
    can't hard-crash the app on every single launch.

    The most likely cause is a file saved by a build before the 2.0 UTF-8
    fix, using Windows' default locale codepage (commonly cp1252) instead of
    UTF-8 — that's a *lossless* problem: the exact same data is still in
    there, just decoded wrong. So the first thing this tries is re-reading
    with cp1252 and, if that parses cleanly, simply re-saving the same data
    as proper UTF-8 in place — no data lost, nothing quarantined. Only if
    that fails does it fall back to the automatic .bak snapshot, and only if
    that fails too does it quarantine the broken file so the app can at
    least start with an empty library instead of crashing.

    Returns a human-readable message describing what happened, so the
    caller can show it to the person — or None if the file was already fine
    (or simply doesn't exist yet, e.g. first launch).
    """
    if not LIBRARY_FILE.exists():
        return None
    if _try_load(LIBRARY_FILE, "utf-8") is not None:
        return None

    # Most likely case: wrong encoding, not actually corrupted — repair losslessly.
    data = _try_load(LIBRARY_FILE, "cp1252")
    if data is not None:
        try:
            with open(LIBRARY_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return (
                "Your library file was saved with the wrong text encoding by an "
                "earlier version and has been repaired in place — your novels "
                "should be exactly as you left them."
            )
        except Exception:
            pass  # couldn't rewrite it — fall through to backup/quarantine below

    # Fall back to the automatic .bak snapshot.
    if _try_load(LIBRARY_BACKUP_FILE, "utf-8") is not None:
        shutil.copyfile(LIBRARY_BACKUP_FILE, LIBRARY_FILE)
        return (
            "Your library file couldn't be read, so it was restored from its "
            "most recent automatic backup (library.json.bak). A few very "
            "recent changes may be missing."
        )
    backup_data = _try_load(LIBRARY_BACKUP_FILE, "cp1252")
    if backup_data is not None:
        try:
            with open(LIBRARY_FILE, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            return (
                "Your library file couldn't be read, so it was restored from its "
                "most recent automatic backup and repaired from the same "
                "wrong-encoding issue. A few very recent changes may be missing."
            )
        except Exception:
            pass

    # Last resort — quarantine the broken file. Only report success if the
    # move actually succeeded; if it didn't (e.g. the file is locked), say so
    # plainly instead of claiming a fix that didn't happen.
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    quarantined = LIBRARY_FILE.with_name(f"library.json.broken-{timestamp}")
    try:
        shutil.move(str(LIBRARY_FILE), str(quarantined))
    except Exception as e:
        return (
            "Your library file couldn't be read, and Library of Yore couldn't "
            f"automatically move it aside either ({e}). Please fully close the "
            "app (check the system tray), then manually rename or delete "
            "library.json in the app data folder before relaunching."
        )
    return (
        "Your library file couldn't be read and has been set aside as "
        f'"{quarantined.name}" in the app data folder so Library of Yore '
        "could start. If you have an existing MongoDB library, use "
        "File \u2192 Import Existing MongoDB Library\u2026 to bring your novels back."
    )


def get_db() -> TinyDB:
    """Get or create the TinyDB singleton backed by library.json."""
    global _db
    if _db is None:
        # encoding='utf-8' is required here: TinyDB's JSONStorage otherwise
        # opens the file using the OS's default locale encoding, which on
        # Windows is often a legacy codepage (e.g. cp1252/"charmap") rather
        # than UTF-8. Novel titles, synopses, and notes scraped from real
        # sites regularly contain characters that codepage can't represent
        # (accented letters, CJK, smart quotes, emoji), which crashes the
        # write with "'charmap' codec can't encode character ...".
        _db = TinyDB(LIBRARY_FILE, storage=JSONStorage, indent=2, ensure_ascii=False, encoding="utf-8")
    return _db


def get_write_lock() -> threading.Lock:
    """Shared lock so the UI and the local API server thread never write to
    the JSON file at the same instant."""
    return _write_lock


def backup_library_file():
    """Copy library.json to library.json.bak just before a write. Best-effort
    safety net — a crash or corrupted write on shutdown never loses the whole
    library, just rolls back to the previous save."""
    try:
        if LIBRARY_FILE.exists():
            shutil.copyfile(LIBRARY_FILE, LIBRARY_BACKUP_FILE)
    except Exception:
        pass  # never let a backup failure block an actual save


def close_db():
    """Flush and release the TinyDB file handle."""
    global _db
    if _db is not None:
        _db.close()
        _db = None
