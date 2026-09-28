"""Local JSON-file storage management (replaces MongoDB as of v2.0).

Novels are stored in one TinyDB-backed JSON file (config.LIBRARY_FILE) inside
the app's data directory instead of a MongoDB server. TinyDB gives the same
"insert/query a dict" ergonomics MongoDB did, just without anything to
install, start, or keep running in the background.

Since v2.0.2 the file is written atomically (write a temp file, then swap it
into place) instead of through TinyDB's stock JSONStorage. The stock storage
keeps one file handle open and shares it between every thread; a read from
the browser-extension API thread landing in the middle of a UI-thread write
moved that shared handle's position and could leave the file truncated or
with stale bytes at the end (invalid JSON). Every read and write now also goes
through one shared re-entrant lock (see get_lock()).
"""
import datetime
import json
import os
import shutil
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional

from tinydb import TinyDB
from tinydb.storages import Storage

from config import LIBRARY_FILE, LIBRARY_BACKUP_FILE, BACKUPS_DIR, DAILY_BACKUPS_TO_KEEP

_db = None
# Guards every read AND write of library.json, from the UI thread, the
# browser-extension API thread, and background workers. Re-entrant so a
# repository method that reads and then writes can hold it throughout.
_db_lock = threading.RLock()

# Windows (and antivirus / cloud-sync tools) can briefly hold the file open,
# which makes open/replace fail with PermissionError. Retry a few times
# before giving up.
_RETRIES = 8
_RETRY_DELAY_S = 0.05


def _with_retries(fn):
    last_exc = None
    for attempt in range(_RETRIES):
        try:
            return fn()
        except PermissionError as e:
            last_exc = e
            time.sleep(_RETRY_DELAY_S * (attempt + 1))
    raise last_exc


class AtomicJSONStorage(Storage):
    """TinyDB storage that opens the file fresh for each read and replaces it
    atomically on each write, so a reader can never observe (or cause) a
    half-written file. Callers must still serialize access with get_lock()."""

    def __init__(self, path, encoding: str = "utf-8", **json_kwargs):
        self.path = Path(path)
        self.encoding = encoding
        self.json_kwargs = json_kwargs
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def read(self):
        if not self.path.exists():
            return None

        def _read():
            with open(self.path, "r", encoding=self.encoding) as f:
                return f.read()

        text = _with_retries(_read)
        if not text.strip():
            return None
        return json.loads(text)

    def write(self, data):
        serialized = json.dumps(data, **self.json_kwargs)
        fd, tmp_path = tempfile.mkstemp(
            prefix=self.path.name + ".", suffix=".tmp", dir=str(self.path.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding=self.encoding, newline="") as f:
                f.write(serialized)
                f.flush()
                os.fsync(f.fileno())
            _with_retries(lambda: os.replace(tmp_path, self.path))
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def close(self):
        pass


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
        _remove_stale_temp_files()
        # encoding='utf-8' is required here: without it the file would be
        # opened using the OS's default locale encoding, which on
        # Windows is often a legacy codepage (e.g. cp1252/"charmap") rather
        # than UTF-8. Novel titles, synopses, and notes scraped from real
        # sites regularly contain characters that codepage can't represent
        # (accented letters, CJK, smart quotes, emoji), which crashes the
        # write with "'charmap' codec can't encode character ...".
        _db = TinyDB(LIBRARY_FILE, storage=AtomicJSONStorage, indent=2, ensure_ascii=False, encoding="utf-8")
    return _db


def _remove_stale_temp_files():
    """A crash between writing the temp file and swapping it into place can
    leave a library.json.*.tmp behind. The real library.json is untouched in
    that case, so the leftover is safe to delete."""
    for leftover in LIBRARY_FILE.parent.glob(LIBRARY_FILE.name + ".*.tmp"):
        try:
            leftover.unlink()
        except OSError:
            pass


def get_lock() -> threading.RLock:
    """Shared lock for every read and write of library.json, so the UI, the
    local API server thread and background workers never touch the file at
    the same instant."""
    return _db_lock


# Kept for backward compatibility with older call sites.
get_write_lock = get_lock


def _daily_snapshot():
    """Keep one dated copy of library.json per day in backups/, newest
    DAILY_BACKUPS_TO_KEEP only. library.json.bak is overwritten on every save,
    so on its own it can't bring back anything older than one save; these
    snapshots can."""
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    target = BACKUPS_DIR / f"library-{today}.json"
    if not target.exists():
        shutil.copyfile(LIBRARY_FILE, target)
    snapshots = sorted(BACKUPS_DIR.glob("library-????-??-??.json"))
    for old in snapshots[:-DAILY_BACKUPS_TO_KEEP]:
        try:
            old.unlink()
        except OSError:
            pass


def backup_library_file():
    """Copy library.json to library.json.bak just before a write, and take
    the day's dated snapshot if there isn't one yet. Best-effort safety net:
    a failure here never blocks the actual save."""
    try:
        if LIBRARY_FILE.exists():
            shutil.copyfile(LIBRARY_FILE, LIBRARY_BACKUP_FILE)
            _daily_snapshot()
    except Exception:
        pass


def close_db():
    """Flush and release the TinyDB file handle."""
    global _db
    if _db is not None:
        with _db_lock:
            _db.close()
            _db = None
