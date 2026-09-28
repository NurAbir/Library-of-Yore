"""Novel data model and repository pattern (local JSON storage, since v2.0)."""
import datetime
import uuid
from dataclasses import dataclass, field
from typing import Optional, List

from tinydb import Query

from database.connection import get_db, get_lock, backup_library_file
from config import COVERS_DIR


def _dt_to_str(dt: Optional[datetime.datetime]) -> Optional[str]:
    """JSON has no datetime type, so dates are stored as ISO-8601 strings."""
    if dt is None:
        return None
    if isinstance(dt, str):  # already serialized (e.g. re-saving a loaded doc)
        return dt
    return dt.isoformat()


def _str_to_dt(s) -> Optional[datetime.datetime]:
    if not s:
        return None
    if isinstance(s, datetime.datetime):
        return s
    try:
        return datetime.datetime.fromisoformat(s)
    except (TypeError, ValueError):
        return None


@dataclass
class Novel:
    """Domain model for a tracked novel."""
    title: str
    author: str = ""
    source_name: str = "manual"          # webnovel, novelfire, manual
    source_url: str = ""
    cover_image_id: Optional[str] = None # local cover filename under config.COVERS_DIR
    cover_url: str = ""                  # Original URL for re-fetch
    current_chapter: int = 0
    total_chapters: Optional[int] = None
    status: str = "ongoing"              # ongoing, completed, hiatus, dropped, planned (your status)
    site_status: str = ""                # what the source site says: ongoing/completed/hiatus ("" = unknown)
    rating: int = 0                      # 0-10
    genres: List[str] = field(default_factory=list)
    synopsis: str = ""
    notes: str = ""
    date_added: datetime.datetime = field(default_factory=datetime.datetime.utcnow)
    last_read: Optional[datetime.datetime] = None
    read_count: int = 0
    last_scraped: Optional[datetime.datetime] = None
    scrape_error: Optional[str] = None
    _id: Optional[str] = None

    @property
    def percent_complete(self) -> float:
        if self.total_chapters and self.total_chapters > 0:
            return round((self.current_chapter / self.total_chapters) * 100, 1)
        return 0.0

    @property
    def is_up_to_date(self) -> bool:
        if self.total_chapters and self.total_chapters > 0:
            return self.current_chapter >= self.total_chapters
        return False

    @classmethod
    def from_dict(cls, data: dict) -> "Novel":
        """Create a Novel from a stored document (see NovelRepository._to_doc
        for the shape). Nested sections are flattened back onto the dataclass
        and ISO date strings are parsed back into datetimes."""
        data = dict(data)  # copy
        if "source" in data:
            src = data.pop("source")
            data["source_name"] = src.get("name", "manual")
            data["source_url"] = src.get("url", "")
            data["last_scraped"] = _str_to_dt(src.get("last_scraped"))
            data["scrape_error"] = src.get("scrape_error")
        if "progress" in data:
            prog = data.pop("progress")
            data["current_chapter"] = prog.get("current_chapter", 0)
            data["total_chapters"] = prog.get("total_chapters")
            data["status"] = prog.get("status", "ongoing")
            data["site_status"] = prog.get("site_status", "")
        if "metadata" in data:
            meta = data.pop("metadata")
            data["rating"] = meta.get("rating", 0)
            data["genres"] = meta.get("genres", [])
            data["synopsis"] = meta.get("synopsis", "")
        if "history" in data:
            hist = data.pop("history")
            data["date_added"] = _str_to_dt(hist.get("date_added")) or datetime.datetime.utcnow()
            data["last_read"] = _str_to_dt(hist.get("last_read"))
            data["read_count"] = hist.get("read_count", 0)
        if "cover_image" in data:
            cov = data.pop("cover_image")
            data["cover_image_id"] = cov.get("file")
            data["cover_url"] = cov.get("url", "")
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# Statuses that describe *your* relationship with a novel rather than its
# publication state. The startup auto-refresh never overwrites these with
# whatever the source site says (before v2.0.2 it did, so a novel you had
# marked Dropped flipped back to Ongoing on the next launch).
READER_ONLY_STATUSES = ("dropped", "planned")


def apply_site_status(novel: Novel, site_status: str) -> bool:
    """Record the source site's publication status on a novel. The novel's
    own status follows it (e.g. Ongoing -> Completed) unless you marked the
    novel Dropped or Planned. Returns True if anything changed."""
    if not site_status:
        return False
    changed = False
    if site_status != novel.site_status:
        novel.site_status = site_status
        changed = True
    if novel.status not in READER_ONLY_STATUSES and novel.status != site_status:
        novel.status = site_status
        changed = True
    return changed


class NovelRepository:
    """CRUD and query operations for Novels, backed by a local JSON file
    (TinyDB) with cover images stored as plain files on disk."""

    def __init__(self):
        self.db = get_db()
        self.table = self.db.table("novels")

    def _to_doc(self, novel: Novel) -> dict:
        """Serialize a Novel to the stored document shape. Kept nested
        (source/progress/metadata/history/cover_image) for readability of the
        underlying JSON file and for continuity with earlier versions."""
        return {
            "_id": novel._id,
            "title": novel.title,
            "author": novel.author,
            "source": {
                "name": novel.source_name,
                "url": novel.source_url,
                "last_scraped": _dt_to_str(novel.last_scraped),
                "scrape_error": novel.scrape_error,
            },
            "cover_image": {
                "file": novel.cover_image_id,
                "url": novel.cover_url,
            },
            "progress": {
                "current_chapter": novel.current_chapter,
                "total_chapters": novel.total_chapters,
                "status": novel.status,
                "site_status": novel.site_status,
                "percent_complete": novel.percent_complete,
                "is_up_to_date": novel.is_up_to_date,
            },
            "metadata": {
                "rating": novel.rating,
                "genres": novel.genres,
                "synopsis": novel.synopsis,
            },
            "history": {
                "date_added": _dt_to_str(novel.date_added),
                "last_read": _dt_to_str(novel.last_read),
                "read_count": novel.read_count,
            },
            "notes": novel.notes,
        }

    def insert(self, novel: Novel) -> str:
        """Insert a new novel. Returns the new (or preserved) id."""
        if not novel._id:
            novel._id = uuid.uuid4().hex
        doc = self._to_doc(novel)
        with get_lock():
            backup_library_file()
            self.table.insert(doc)
        return novel._id

    def update(self, novel: Novel) -> bool:
        """Update existing novel by _id.

        Saves the novel exactly as given. It does NOT touch last_read: before
        v2.0.2 every save (including the startup auto-refresh and plain edits)
        stamped last_read, which scrambled the "Last Read" sort. Callers that
        record real reading progress set novel.last_read themselves."""
        if not novel._id:
            return False
        doc = self._to_doc(novel)
        with get_lock():
            backup_library_file()
            updated = self.table.update(doc, Query()._id == novel._id)
        return len(updated) > 0

    def delete(self, novel_id: str) -> bool:
        """Delete a novel and its cover file, if any."""
        with get_lock():
            novel = self.get_by_id(novel_id)
            if novel and novel.cover_image_id:
                self.delete_cover(novel.cover_image_id)
            backup_library_file()
            removed = self.table.remove(Query()._id == novel_id)
        return len(removed) > 0

    def get_by_id(self, novel_id: str) -> Optional[Novel]:
        with get_lock():
            doc = self.table.get(Query()._id == novel_id)
        return Novel.from_dict(doc) if doc else None

    def get_all(self, status_filter: Optional[List[str]] = None,
                genre_filter: Optional[List[str]] = None,
                search_text: str = "",
                sort_by: str = "last_read",
                sort_order: str = "desc") -> List[Novel]:
        """Query novels with filters and sorting (done in-process over the
        loaded list — plenty fast for a personal library's scale)."""
        with get_lock():
            docs = self.table.all()
        novels = [Novel.from_dict(d) for d in docs]

        if status_filter:
            novels = [n for n in novels if n.status in status_filter]
        if genre_filter:
            novels = [n for n in novels if any(g in n.genres for g in genre_filter)]
        if search_text:
            needle = search_text.lower()
            novels = [
                n for n in novels
                if needle in n.title.lower()
                or needle in n.author.lower()
                or needle in n.notes.lower()
            ]

        min_dt = datetime.datetime.min
        sort_key_map = {
            "last_read": lambda n: n.last_read or min_dt,
            "title": lambda n: n.title.lower(),
            "rating": lambda n: n.rating,
            "date_added": lambda n: n.date_added or min_dt,
            "percent_complete": lambda n: n.percent_complete,
        }
        key_fn = sort_key_map.get(sort_by, sort_key_map["last_read"])
        novels.sort(key=key_fn, reverse=(sort_order == "desc"))
        return novels

    def save_cover(self, image_bytes: bytes, filename: str = "", content_type: str = "image/jpeg") -> str:
        """Save a cover image as a local file. Returns its filename (used as
        the id passed around as Novel.cover_image_id)."""
        cover_id = f"{uuid.uuid4().hex}.jpg"
        (COVERS_DIR / cover_id).write_bytes(image_bytes)
        return cover_id

    def get_cover(self, file_id: str) -> Optional[bytes]:
        """Retrieve cover image bytes from the covers folder."""
        path = COVERS_DIR / file_id
        try:
            return path.read_bytes() if path.exists() else None
        except Exception:
            return None

    def delete_cover(self, file_id: str) -> None:
        """Remove a cover image file. Safe to call even if it's already gone."""
        try:
            path = COVERS_DIR / file_id
            if path.exists():
                path.unlink()
        except Exception:
            pass

    def update_chapter_progress(self, novel_id: str, new_chapter: int, increment_read: bool = True):
        """Quick update for chapter progress."""
        with get_lock():
            doc = self.table.get(Query()._id == novel_id)
            if not doc:
                return
            backup_library_file()
            novel = Novel.from_dict(doc)
            novel.current_chapter = new_chapter
            novel.last_read = datetime.datetime.utcnow()
            if increment_read:
                novel.read_count += 1
            # Re-serialize the whole record so derived fields stored in the
            # file (percent_complete, is_up_to_date) stay in step.
            self.table.update(self._to_doc(novel), Query()._id == novel_id)

    def export_to_list(self) -> List[dict]:
        """Export all novels as flat dicts for spreadsheet."""
        novels = self.get_all(sort_by="title", sort_order="asc")
        result = []
        for n in novels:
            result.append({
                "Title": n.title,
                "Author": n.author,
                "Status": n.status,
                "Current Chapter": n.current_chapter,
                "Total Chapters": n.total_chapters or "",
                "% Complete": n.percent_complete,
                "Source URL": n.source_url,
                "Source": n.source_name,
                "Last Read": n.last_read.isoformat() if n.last_read else "",
                "Date Added": n.date_added.isoformat() if n.date_added else "",
                "Rating": n.rating,
                "Genres": ", ".join(n.genres),
                "Notes": n.notes,
            })
        return result
