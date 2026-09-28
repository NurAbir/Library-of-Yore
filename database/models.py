"""Novel data model and repository pattern (local JSON storage, since v2.0)."""
import datetime
import uuid
from dataclasses import dataclass, field
from typing import Optional, List

from tinydb import Query

from database.connection import get_db, get_lock, backup_library_file
from config import COVERS_DIR
from utils import chapters as ch

# Bumped when the stored document shape changes. 2 = v2.1.0: chapter numbers
# stored as strings, "not started" stored as null, chapter/locked lists.
SCHEMA_VERSION = 2

CONTENT_TYPES = ("novel", "manga")


def _migrate_chapter(value, zero_means_none: bool) -> Optional[str]:
    """Old libraries stored chapters as plain numbers, where 0 meant both
    "not started" (current chapter) and "unknown" (total). A numeric 0 from
    such a record therefore becomes None; a string "0" is a real chapter 0."""
    if zero_means_none and not isinstance(value, str) and value == 0:
        return None
    return ch.parse_chapter(value)


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
    current_chapter: Optional[str] = None  # canonical chapter string; None = not started
    latest_chapter: Optional[str] = None   # highest chapter the site lists; None = unknown
    chapter_list: str = ""                 # every chapter the site lists, as ranges ("0.01,1-755"); "" = unknown
    locked_list: str = ""                  # chapters the site marks locked/paid, as ranges
    content_type: str = "novel"            # "novel" or "manga"
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

    def __post_init__(self):
        # Accept numbers from older code paths (legacy MongoDB import, old
        # records) and normalize everything to canonical chapter strings.
        self.current_chapter = _migrate_chapter(self.current_chapter, zero_means_none=True)
        self.latest_chapter = _migrate_chapter(self.latest_chapter, zero_means_none=True)
        if self.content_type not in CONTENT_TYPES:
            self.content_type = "novel"

    @property
    def progress(self) -> "ch.Progress":
        return ch.compute_progress(self.current_chapter, self.latest_chapter,
                                   self.chapter_list, self.locked_list)

    @property
    def percent_complete(self) -> float:
        return self.progress.percent

    @property
    def is_up_to_date(self) -> bool:
        return self.progress.up_to_date

    @property
    def next_chapter(self) -> str:
        return self.progress.next_chapter

    @property
    def total_chapters(self) -> Optional[str]:
        """Backward-compatible alias: before v2.1.0 this held a chapter count
        or number; it now means the latest chapter the site lists."""
        return self.latest_chapter

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
            data["current_chapter"] = prog.get("current_chapter")
            # pre-2.1.0 records stored "total_chapters" (a number)
            data["latest_chapter"] = prog.get("latest_chapter", prog.get("total_chapters"))
            data["chapter_list"] = prog.get("chapter_list", "") or ""
            data["locked_list"] = prog.get("locked_list", "") or ""
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


def apply_scrape_result(novel: Novel, result) -> bool:
    """Copy fresh site data from a successful ScraperResult onto a novel:
    latest chapter, chapter/locked lists, site status, synopsis and (for
    Flame Comics, which knows it) novel vs manga. Never touches your current
    chapter, last_read or a Dropped/Planned status. Returns True if anything
    you'd see changed."""
    changed = False
    latest = ch.parse_chapter(result.latest_chapter)
    if latest is not None and latest != novel.latest_chapter:
        novel.latest_chapter = latest
        changed = True
    if result.chapter_list:
        chapter_list = ch.encode_ranges(result.chapter_list)
        locked_list = ch.encode_ranges(result.locked_list)
        if chapter_list != novel.chapter_list:
            novel.chapter_list = chapter_list
            changed = True
        if locked_list != novel.locked_list:
            novel.locked_list = locked_list
            changed = True
    if apply_site_status(novel, result.status):
        changed = True
    if result.synopsis and result.synopsis != novel.synopsis:
        novel.synopsis = result.synopsis
        changed = True
    if result.source_name == "flamecomics" and result.content_type in CONTENT_TYPES \
            and result.content_type != novel.content_type:
        novel.content_type = result.content_type
        changed = True
    novel.last_scraped = datetime.datetime.utcnow()
    novel.scrape_error = None
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
        progress = novel.progress
        return {
            "_id": novel._id,
            "schema": SCHEMA_VERSION,
            "title": novel.title,
            "content_type": novel.content_type,
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
                "latest_chapter": novel.latest_chapter,
                "chapter_list": novel.chapter_list,
                "locked_list": novel.locked_list,
                "status": novel.status,
                "site_status": novel.site_status,
                # derived, stored for readability of the JSON file only
                "percent_complete": progress.percent,
                "is_up_to_date": progress.up_to_date,
                "chapters_behind": progress.behind,
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

    def update_many(self, novels: List[Novel]) -> int:
        """Save several novels with one file write (used by the startup
        auto-refresh, which before v2.1.0 rewrote the whole file once per
        novel). Like update(), does not touch last_read."""
        novels = [n for n in novels if n._id]
        if not novels:
            return 0
        with get_lock():
            backup_library_file()
            updated = self.table.update_multiple(
                [(self._to_doc(n), Query()._id == n._id) for n in novels]
            )
        return len(updated)

    def update_chapter_progress(self, novel_id: str, new_chapter, increment_read: bool = True):
        """Quick update for chapter progress. new_chapter may be a chapter
        string or number; it is normalized to a canonical chapter string."""
        new_chapter = ch.parse_chapter(new_chapter)
        if new_chapter is None:
            return
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

    def advance_progress(self, novel_id: str, reported, ambiguous: bool = False):
        """Record a chapter reported by the browser extension, only if it is
        further along than what's stored (progress never moves backwards;
        from "not started" any chapter counts, including 0). The check and
        the write happen under one lock.

        `ambiguous` marks a number read from a URL like ".../chapter-2-5":
        it is kept only if the site's chapter list has exactly that chapter,
        otherwise it becomes the whole chapter (2).

        Returns (novel or None, updated: bool, previous, recorded)."""
        chapter = ch.parse_chapter(reported)
        with get_lock():
            novel = self.get_by_id(novel_id)
            if not novel or chapter is None:
                return novel, False, None, None
            chapter = ch.resolve_reported(chapter, ambiguous, novel.chapter_list)
            previous = novel.current_chapter
            if not ch.is_newer(chapter, previous):
                return novel, False, previous, chapter
            self.update_chapter_progress(novel_id, chapter, increment_read=True)
            return self.get_by_id(novel_id), True, previous, chapter

    def export_to_list(self) -> List[dict]:
        """Export all novels as flat dicts for spreadsheet."""
        novels = self.get_all(sort_by="title", sort_order="asc")
        result = []
        for n in novels:
            result.append({
                "Title": n.title,
                "Author": n.author,
                "Status": n.status,
                "Type": n.content_type.title(),
                "Current Chapter": n.current_chapter if n.current_chapter is not None else "Not started",
                "Latest Chapter": n.latest_chapter or "",
                "Chapters Behind": "" if n.progress.behind is None else n.progress.behind,
                "Locked Behind": n.progress.locked_behind or "",
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
