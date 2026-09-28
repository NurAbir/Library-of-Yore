"""
Local HTTP API server for Library of Yore.
Listens on 127.0.0.1:7337 so the browser extension can read and update progress.
Uses only stdlib (http.server) — no extra dependencies.
"""
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import List, Optional
from urllib.parse import urlparse, parse_qs

from database.models import NovelRepository
from config import APP_VERSION

PORT = 7337
_server_instance = None
_progress_callback = None  # Called with (novel_id: str, chapter: int, total: int) after a successful update


def set_progress_callback(fn):
    """Register a thread-safe callback invoked whenever the extension updates progress."""
    global _progress_callback
    _progress_callback = fn


# ── CORS & extension origins ───────────────────────────────────────────────────
#
# Only the browser extension (and pages served from this machine itself) may
# read or write through this API from a browser. Before v2.0.2 this was a
# plain string-prefix check, so an origin like "http://localhost.example.com"
# passed as if it were localhost.

EXTENSION_SCHEMES = ("chrome-extension", "moz-extension", "safari-web-extension")
LOCAL_HOSTNAMES = ("localhost", "127.0.0.1", "::1")
MAX_BODY_BYTES = 64 * 1024


def _cors_origin(origin: str) -> Optional[str]:
    """Return the origin to echo back in Access-Control-Allow-Origin, or None
    to send no CORS header at all (the browser then blocks the response)."""
    if not origin:
        return None
    try:
        parsed = urlparse(origin)
    except ValueError:
        return None
    if parsed.scheme in EXTENSION_SCHEMES and parsed.netloc:
        return origin
    if parsed.scheme in ("http", "https") and parsed.hostname in LOCAL_HOSTNAMES:
        return origin
    return None


# ── Request handler ────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # Silence default access log

    # ── Shared helpers ─────────────────────────────────────────────────────────

    def _send_cors_headers(self):
        allowed = _cors_origin(self.headers.get("Origin", ""))
        if allowed:
            self.send_header("Access-Control-Allow-Origin", allowed)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Vary", "Origin")

    def _send(self, data, status=200):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._send_cors_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, msg, status=400):
        self._send({"error": msg}, status)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if not length:
            return {}
        if length > MAX_BODY_BYTES:
            raise ValueError("request body too large")
        data = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("request body must be a JSON object")
        return data

    # ── OPTIONS (preflight) ────────────────────────────────────────────────────

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    # ── GET ────────────────────────────────────────────────────────────────────

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/health":
            self._send({"status": "ok", "app": "Library of Yore", "version": APP_VERSION})

        elif parsed.path == "/novels":
            repo = NovelRepository()
            novels = repo.get_all()
            self._send([_novel_dict(n) for n in novels])

        elif parsed.path == "/find":
            url   = params.get("url",   [""])[0].strip()
            title = params.get("title", [""])[0].strip()
            repo  = NovelRepository()
            novels = repo.get_all()

            match, match_type = None, None
            if url:
                match = _find_by_url(novels, url)
                match_type = "url" if match else None
            if not match and title:
                match = _find_by_title(novels, title, _domain(url) if url else "")
                match_type = "title" if match else None

            if match:
                # "match" tells the extension how sure this is: it only
                # auto-syncs on a "url" match; a "title" match needs a click.
                self._send({"found": True, "novel": _novel_dict(match), "match": match_type})
            else:
                self._send({"found": False, "novel": None, "match": None})

        else:
            self._error("Not found", 404)

    # ── POST ───────────────────────────────────────────────────────────────────

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/progress":
            # Requiring a JSON content type forces browsers to send a CORS
            # preflight first, so an arbitrary web page can't fire a
            # "simple" text/plain POST at this endpoint and change progress.
            content_type = self.headers.get("Content-Type", "").split(";")[0].strip().lower()
            if content_type != "application/json":
                return self._error("Content-Type must be application/json", 415)
            try:
                data = self._read_json()
            except (ValueError, UnicodeDecodeError) as e:
                return self._error(f"invalid JSON body: {e}")
            novel_id   = str(data.get("novel_id") or "").strip()
            chapter    = data.get("chapter")
            if not novel_id or chapter is None:
                return self._error("novel_id and chapter are required")
            try:
                chapter = int(chapter)
            except (TypeError, ValueError):
                return self._error("chapter must be an integer")

            repo = NovelRepository()
            novel = repo.get_by_id(novel_id)
            if not novel:
                return self._error("Novel not found", 404)

            # Only update if chapter is newer than stored
            if chapter > novel.current_chapter:
                repo.update_chapter_progress(novel_id, chapter, increment_read=True)
                # Notify the UI (callback is a Qt signal emit — thread-safe)
                if _progress_callback:
                    _progress_callback(novel_id, chapter, novel.total_chapters)
                self._send({"success": True, "updated": True,
                            "previous": novel.current_chapter, "current": chapter})
            else:
                self._send({"success": True, "updated": False,
                            "message": "Chapter not newer than stored value",
                            "stored": novel.current_chapter})
        else:
            self._error("Not found", 404)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _novel_dict(n) -> dict:
    return {
        "id":              n._id,
        "title":           n.title,
        "author":          n.author,
        "current_chapter": n.current_chapter,
        "total_chapters":  n.total_chapters,
        "status":          n.status,
        "source_url":      n.source_url,
        "percent_complete": n.percent_complete,
    }


def _domain(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def _path_segments(url: str) -> List[str]:
    """Path of a URL as a list of lowercase segments, with a trailing .html
    dropped from each, e.g. "/Book/Shadow-Slave/chapter-5.html" ->
    ["book", "shadow-slave", "chapter-5"]."""
    try:
        path = urlparse(url).path
    except ValueError:
        return []
    return [re.sub(r"\.html?$", "", seg.lower()) for seg in path.split("/") if seg]


# Path segments that never identify a specific novel on their own.
_GENERIC_SEGMENTS = {
    "novel", "novels", "book", "books", "series", "manga", "comic", "comics",
    "read", "chapter", "chapters", "index", "home",
}


def _is_distinctive_slug(slug: str) -> bool:
    """True if a path segment is specific enough to identify one novel when
    found anywhere in a chapter URL. Rejects numeric ids ("12") and hex
    chapter tokens ("f48067c3fe28e0a0"): before v2.0.2 a stored slug like "2"
    matched any chapter URL containing the digit 2."""
    if len(slug) < 4 or slug in _GENERIC_SEGMENTS:
        return False
    if not re.search(r"[a-z]", slug):
        return False
    if re.fullmatch(r"[0-9a-f]{8,}", slug):
        return False
    return True


def _find_by_url(novels, browser_url: str):
    """
    Match a browser chapter URL back to a stored novel. Same domain required.
      1. The stored novel page's path is a whole-segment prefix of the
         chapter URL's path (/book/shadow-slave -> /book/shadow-slave/chapter-5,
         but /series/1 does NOT match /series/12/...). Longest prefix wins.
      2. Otherwise, the stored URL's last path segment appears as a whole
         segment of the chapter URL, if it is distinctive (see
         _is_distinctive_slug). Covers sites whose chapter URLs drop a
         /novel/ prefix, e.g. FreeWebNovel.
    """
    browser_domain = _domain(browser_url)
    browser_segs = _path_segments(browser_url)
    if not browser_domain or not browser_segs:
        return None

    best, best_len = None, 0
    slug_match = None
    for n in novels:
        if not n.source_url or _domain(n.source_url) != browser_domain:
            continue
        stored_segs = _path_segments(n.source_url)
        if not stored_segs:
            continue  # a bare site URL can't identify a novel

        if browser_segs[:len(stored_segs)] == stored_segs and len(stored_segs) > best_len:
            best, best_len = n, len(stored_segs)
            continue

        slug = stored_segs[-1]
        if slug_match is None and _is_distinctive_slug(slug) and slug in browser_segs:
            slug_match = n

    return best or slug_match


def _normalize_title(title: str) -> str:
    return re.sub(r"[^\w]+", " ", (title or "").lower()).strip()


def _find_by_title(novels, title: str, browser_domain: str = ""):
    """Title fallback, used only when the URL didn't match. Looks at titles
    only (before v2.0.2 it also searched author and notes), and when the
    browser's site is known, only at novels saved from that site or with no
    source URL at all. Returns a match only if it is unambiguous."""
    wanted = _normalize_title(title)
    if not wanted:
        return None
    pool = [
        n for n in novels
        if not browser_domain or not n.source_url or _domain(n.source_url) == browser_domain
    ]
    exact = [n for n in pool if _normalize_title(n.title) == wanted]
    if len(exact) == 1:
        return exact[0]
    if exact:
        return None  # several novels share this title; don't guess
    partial = [
        n for n in pool
        if _normalize_title(n.title)
        and (_normalize_title(n.title) in wanted or wanted in _normalize_title(n.title))
    ]
    return partial[0] if len(partial) == 1 else None


# ── Server lifecycle ───────────────────────────────────────────────────────────

def start():
    """Start the API server in a daemon thread. Safe to call multiple times."""
    global _server_instance
    if _server_instance:
        return

    server = HTTPServer(("127.0.0.1", PORT), Handler)
    _server_instance = server

    t = threading.Thread(target=server.serve_forever, daemon=True, name="LoY-API")
    t.start()
    return t


def stop():
    global _server_instance
    if _server_instance:
        _server_instance.shutdown()
        _server_instance = None
