"""Novel data model and repository pattern."""
import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, List
from bson import ObjectId
from gridfs import GridFS
from pymongo import DESCENDING, ASCENDING

from database.connection import get_db, get_client
from config import DEFAULT_DB_NAME, GRIDFS_BUCKET


@dataclass
class Novel:
    """Domain model for a tracked novel."""
    title: str
    author: str = ""
    source_name: str = "manual"          # webnovel, novelfire, manual
    source_url: str = ""
    cover_image_id: Optional[str] = None # GridFS file_id as string
    cover_url: str = ""                  # Original URL for re-fetch
    current_chapter: int = 0
    total_chapters: Optional[int] = None
    status: str = "ongoing"              # ongoing, completed, hiatus, dropped, planned
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

    def to_dict(self) -> dict:
        """Convert to MongoDB-compatible dict."""
        d = asdict(self)
        d.pop("_id")
        if self._id:
            d["_id"] = ObjectId(self._id)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Novel":
        """Create Novel from MongoDB document."""
        data = dict(data)  # copy
        if "_id" in data:
            data["_id"] = str(data["_id"])
        # Map nested fields back to flat dataclass
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
            data["date_added"] = hist.get("date_added", datetime.datetime.utcnow())
            data["last_read"] = hist.get("last_read")
            data["read_count"] = hist.get("read_count", 0)
        if "cover_image" in data:
            cov = data.pop("cover_image")
            data["cover_image_id"] = cov.get("gridfs_id")
            data["cover_url"] = cov.get("url", "")
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class NovelRepository:
    """CRUD and query operations for Novels."""

    def __init__(self):
        self.db = get_db()
        self.collection = self.db["novels"]
        self.fs = GridFS(self.db, collection=GRIDFS_BUCKET)

    def _to_doc(self, novel: Novel) -> dict:
        """Serialize Novel to MongoDB document with nested structure."""
        return {
            "title": novel.title,
            "author": novel.author,
            "source": {
                "name": novel.source_name,
                "url": novel.source_url,
                "last_scraped": novel.last_scraped,
                "scrape_error": novel.scrape_error,
            },
            "cover_image": {
                "gridfs_id": novel.cover_image_id,
                "url": novel.cover_url,
            },
            "progress": {
                "current_chapter": novel.current_chapter,
                "total_chapters": novel.total_chapters,
                "status": novel.status,
                "percent_complete": novel.percent_complete,
                "is_up_to_date": novel.is_up_to_date,
            },
            "metadata": {
                "rating": novel.rating,
                "genres": novel.genres,
                "synopsis": novel.synopsis,
            },
            "history": {
                "date_added": novel.date_added,
                "last_read": novel.last_read,
                "read_count": novel.read_count,
            },
            "notes": novel.notes,
        }

    def insert(self, novel: Novel) -> str:
        """Insert a new novel. Returns inserted ID."""
        doc = self._to_doc(novel)
        result = self.collection.insert_one(doc)
        return str(result.inserted_id)

    def update(self, novel: Novel) -> bool:
        """Update existing novel by _id."""
        if not novel._id:
            return False
        doc = self._to_doc(novel)
        doc["history"]["last_read"] = datetime.datetime.utcnow()
        result = self.collection.update_one(
            {"_id": ObjectId(novel._id)}, {"$set": doc}
        )
        return result.modified_count > 0

    def delete(self, novel_id: str) -> bool:
        """Delete novel and its cover from GridFS."""
        novel = self.get_by_id(novel_id)
        if novel and novel.cover_image_id:
            try:
                self.fs.delete(ObjectId(novel.cover_image_id))
            except Exception:
                pass
        result = self.collection.delete_one({"_id": ObjectId(novel_id)})
        return result.deleted_count > 0

    def get_by_id(self, novel_id: str) -> Optional[Novel]:
        data = self.collection.find_one({"_id": ObjectId(novel_id)})
        return Novel.from_dict(data) if data else None

    def get_all(self, status_filter: Optional[List[str]] = None,
                genre_filter: Optional[List[str]] = None,
                search_text: str = "",
                sort_by: str = "last_read",
                sort_order: str = "desc") -> List[Novel]:
        """Query novels with filters and sorting."""
        query = {}
        if status_filter:
            query["progress.status"] = {"$in": status_filter}
        if genre_filter:
            query["metadata.genres"] = {"$in": genre_filter}
        if search_text:
            query["$or"] = [
                {"title": {"$regex": search_text, "$options": "i"}},
                {"author": {"$regex": search_text, "$options": "i"}},
                {"notes": {"$regex": search_text, "$options": "i"}},
            ]

        sort_field_map = {
            "last_read": "history.last_read",
            "title": "title",
            "rating": "metadata.rating",
            "date_added": "history.date_added",
            "percent_complete": "progress.percent_complete",
        }
        sort_field = sort_field_map.get(sort_by, "history.last_read")
        direction = DESCENDING if sort_order == "desc" else ASCENDING

        cursor = self.collection.find(query).sort(sort_field, direction)
        return [Novel.from_dict(d) for d in cursor]

    def save_cover(self, image_bytes: bytes, filename: str, content_type: str = "image/jpeg") -> str:
        """Save cover image to GridFS. Returns file_id string."""
        file_id = self.fs.put(image_bytes, filename=filename, content_type=content_type)
        return str(file_id)

    def get_cover(self, file_id: str) -> Optional[bytes]:
        """Retrieve cover image bytes from GridFS."""
        try:
            return self.fs.get(ObjectId(file_id)).read()
        except Exception:
            return None

    def update_chapter_progress(self, novel_id: str, new_chapter: int, increment_read: bool = True):
        """Quick update for chapter progress."""
        updates = {
            "progress.current_chapter": new_chapter,
            "history.last_read": datetime.datetime.utcnow(),
        }
        if increment_read:
            updates["$inc"] = {"history.read_count": 1}
        self.collection.update_one({"_id": ObjectId(novel_id)}, {"$set": updates})

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
