"""Application configuration and constants."""
import os
import sys
import json
from pathlib import Path

APP_NAME = "LibraryOfYore"
DISPLAY_NAME = "Library of Yore"
APP_VERSION = "2.0.0"

# Paths
APP_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / APP_NAME
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

EXPORTS_DIR = APP_DATA_DIR / "exports"
EXPORTS_DIR.mkdir(exist_ok=True)

LOGS_DIR = APP_DATA_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

CONFIG_FILE = APP_DATA_DIR / "config.json"

# ── Local library storage (since v2.0) ───────────────────────────────────────
# Replaces MongoDB: novels live in one JSON file, covers live in a folder next
# to it. No server, no separate install, no service to keep running.
LIBRARY_FILE = APP_DATA_DIR / "library.json"
LIBRARY_BACKUP_FILE = APP_DATA_DIR / "library.json.bak"

COVERS_DIR = APP_DATA_DIR / "covers"
COVERS_DIR.mkdir(exist_ok=True)

# ── Legacy MongoDB settings (pre-2.0 only) ───────────────────────────────────
# Used solely by database/legacy_mongo.py to detect and one-time-import a
# library created by a version of Library of Yore before 2.0. Nothing else in
# the app touches these, and a machine with no MongoDB installed is completely
# unaffected by their presence here.
LEGACY_MONGO_URI = "mongodb://localhost:27017"
LEGACY_DB_NAME = "libraryofyore"
LEGACY_GRIDFS_BUCKET = "covers"

# Scraping
SCRAPER_CACHE_DURATION_HOURS = 24
REQUEST_TIMEOUT = 30
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# UI
COVER_GRID_SIZE = 180  # pixels
COVER_THUMB_SIZE = 300

# Novel statuses
STATUSES = ["ongoing", "completed", "hiatus", "dropped", "planned"]


def load_config():
    """Load user config from JSON."""
    defaults = {
        "theme": "dark",
        "window_size": [1200, 800],
        "default_sort": "last_read",
    }
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            defaults.update(saved)
        except Exception:
            pass
    return defaults


def save_config(cfg):
    """Save user config to JSON."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def get_asset_path(filename: str) -> str:
    """Get path to an asset file. Works in dev and PyInstaller onefile/onedir bundle."""
    if getattr(sys, "frozen", False):
        # PyInstaller onefile: files are extracted to sys._MEIPASS temp folder
        # PyInstaller onedir: files are next to exe in _internal folder
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        # Development mode
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "assets", filename)
