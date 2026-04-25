"""
Local HTTP API server for Library of Yore.
Listens on 127.0.0.1:7337 so the browser extension can read and update progress.
Uses only stdlib (http.server) — no extra dependencies.
"""
import json
import threading
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
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

ALLOWED_ORIGINS = (
    "chrome-extension://",
    "moz-extension://",
    "http://localhost",
    "http://127.0.0.1",
)


def _cors_origin(origin: str) -> str:
    if not origin:
        return "*"
    if any(origin.startswith(p) for p in ALLOWED_ORIGINS):
        return origin
    return "null"


# ── Request handler ────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # Silence default access log

    # ── Shared helpers ─────────────────────────────────────────────────────────

    def _send(self, data, status=200):
        body = json.dumps(data, default=str).encode("utf-8")
        origin = self.headers.get("Origin", "")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", _cors_origin(origin))
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, msg, status=400):
        self._send({"error": msg}, status)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    # ── OPTIONS (preflight) ────────────────────────────────────────────────────

    def do_OPTIONS(self):
        origin = self.headers.get("Origin", "")
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", _cors_origin(origin))
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
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

            match = None
            if url:
                match = _find_by_url(repo, url)
            if not match and title:
                results = repo.get_all(search_text=title)
                if results:
                    match = results[0]

            if match:
                self._send({"found": True,  "novel": _novel_dict(match)})
            else:
                self._send({"found": False, "novel": None})

        else:
            self._error("Not found", 404)

    # ── POST ───────────────────────────────────────────────────────────────────

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/progress":
            data       = self._read_json()
            novel_id   = data.get("novel_id", "").strip()
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


def _slug(url: str) -> str:
    """Extract the last meaningful path segment from a URL."""
    path = urlparse(url).path.rstrip("/")
    return path.split("/")[-1] if path else ""


def _find_by_url(repo: NovelRepository, browser_url: str):
    """
    Match a browser chapter URL back to a stored novel.
    Strategy:
      1. Direct source_url prefix match (e.g. novel info page URL is a prefix of chapter URL)
      2. Domain + slug comparison
    """
    novels = repo.get_all()
    parsed_browser = urlparse(browser_url)
    browser_domain = parsed_browser.netloc.replace("www.", "")
    browser_path   = parsed_browser.path

    for n in novels:
        if not n.source_url:
            continue
        parsed_stored = urlparse(n.source_url)
        stored_domain = parsed_stored.netloc.replace("www.", "")
        stored_path   = parsed_stored.path.rstrip("/")

        # Domain must match first
        if browser_domain != stored_domain:
            continue

        # Novel info page URL is a prefix of the chapter URL
        if browser_path.startswith(stored_path):
            return n

        # Slug comparison: last path segment of stored URL appears in chapter URL
        stored_slug = stored_path.split("/")[-1]
        if stored_slug and stored_slug in browser_path:
            return n

    return None


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
