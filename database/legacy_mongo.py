"""One-time importer for libraries created by Library of Yore before v2.0,
which stored novels in MongoDB (with cover images in GridFS).

This module is only ever touched by the first-run check in
ui/main_window.py and the manual "Import Existing MongoDB Library..." menu
action — normal use of the app (querying, saving, editing novels) never
imports pymongo at all. A machine with no MongoDB installed, or without
pymongo available, is completely unaffected: detect_legacy_library() simply
returns None and nothing else runs.
"""
import datetime
from typing import Optional, Callable

from config import LEGACY_MONGO_URI, LEGACY_DB_NAME, LEGACY_GRIDFS_BUCKET, load_config


def _legacy_connection_settings():
    """Honor a custom mongo_uri/db_name if one is still sitting in an old
    config.json from a previous version; fall back to the stock defaults."""
    cfg = load_config()
    uri = cfg.get("mongo_uri", LEGACY_MONGO_URI)
    db_name = cfg.get("db_name", LEGACY_DB_NAME)
    return uri, db_name


def detect_legacy_library() -> Optional[int]:
    """Return the number of novels found in a pre-2.0 MongoDB library, or
    None if MongoDB isn't reachable, isn't installed, or pymongo isn't
    available. Uses a short timeout so a machine with no MongoDB at all
    never feels this check on startup."""
    try:
        from pymongo import MongoClient
        from pymongo.errors import PyMongoError
    except ImportError:
        return None

    uri, db_name = _legacy_connection_settings()
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=1000)
        client.admin.command("ping")
        count = client[db_name]["novels"].count_documents({})
        client.close()
        return count
    except PyMongoError:
        return None
    except Exception:
        return None


def _legacy_doc_to_novel(doc: dict):
    """Translate a raw MongoDB novel document (nested shape, ObjectId _id,
    real datetime objects) into a Novel with a plain string id — the same
    flattening the old Novel.from_dict used to do, kept here since it's now
    specific to reading the *old* format."""
    from database.models import Novel  # local import avoids a hard dependency at module load

    data = dict(doc)
    data["_id"] = str(data["_id"])
    if "source" in data:
        src = data.pop("source")
        data["source_name"] = src.get("name", "manual")
        data["source_url"] = src.get("url", "")
        data["last_scraped"] = src.get("last_scraped")
        data["scrape_error"] = src.get("scrape_error")
    if "progress" in data:
        prog = data.pop("progress")
        data["current_chapter"] = prog.get("current_chapter", 0)
        data["total_chapters"] = prog.get("total_chapters")
        data["status"] = prog.get("status", "ongoing")
    if "metadata" in data:
        meta = data.pop("metadata")
        data["rating"] = meta.get("rating", 0)
        data["genres"] = meta.get("genres", [])
        data["synopsis"] = meta.get("synopsis", "")
    if "history" in data:
        hist = data.pop("history")
        data["date_added"] = hist.get("date_added") or datetime.datetime.utcnow()
        data["last_read"] = hist.get("last_read")
        data["read_count"] = hist.get("read_count", 0)
    data.pop("cover_image", None)  # cover is migrated separately, from GridFS to a local file
    return Novel(**{k: v for k, v in data.items() if k in Novel.__dataclass_fields__})


def import_legacy_library(progress_cb: Optional[Callable[[int, int], None]] = None) -> int:
    """Copy every novel and cover image from the old MongoDB library into the
    new local JSON store. Returns the number of novels imported.

    Intended to run once, on a fresh (empty) local library — see
    ui/main_window.py's first-run check — but is harmless to re-run; novels
    are always inserted with their original MongoDB id preserved, so the
    browser extension's previously-cached novel ids keep matching afterward.
    """
    from pymongo import MongoClient
    from bson import ObjectId
    from gridfs import GridFS

    from database.models import NovelRepository

    uri, db_name = _legacy_connection_settings()

    client = MongoClient(uri, serverSelectionTimeoutMS=3000)
    mongo_db = client[db_name]
    fs = GridFS(mongo_db, collection=LEGACY_GRIDFS_BUCKET)
    docs = list(mongo_db["novels"].find({}))
    total = len(docs)

    repo = NovelRepository()
    imported = 0
    for doc in docs:
        novel = _legacy_doc_to_novel(doc)

        old_cover_id = (doc.get("cover_image") or {}).get("gridfs_id")
        if old_cover_id:
            try:
                cover_bytes = fs.get(ObjectId(old_cover_id)).read()
                novel.cover_image_id = repo.save_cover(cover_bytes, novel.title + ".jpg")
            except Exception:
                novel.cover_image_id = None  # cover couldn't be read — novel itself still imports fine

        repo.insert(novel)
        imported += 1
        if progress_cb:
            progress_cb(imported, total)

    client.close()
    return imported
