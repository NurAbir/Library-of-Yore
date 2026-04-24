"""MongoDB connection management with first-time setup handling."""
import sys
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure

from config import load_config, DEFAULT_MONGO_URI, DEFAULT_DB_NAME

_client = None
_db = None


def get_client(force_new=False):
    """Get or create MongoDB client singleton."""
    global _client
    if _client is None or force_new:
        cfg = load_config()
        uri = cfg.get("mongo_uri", DEFAULT_MONGO_URI)
        _client = MongoClient(uri, serverSelectionTimeoutMS=3000)
    return _client


def get_db():
    """Get database instance."""
    global _db
    if _db is None:
        cfg = load_config()
        db_name = cfg.get("db_name", DEFAULT_DB_NAME)
        _db = get_client()[db_name]
    return _db


def test_connection(uri=None):
    """Test MongoDB connectivity. Returns (ok: bool, message: str)."""
    test_uri = uri or load_config().get("mongo_uri", DEFAULT_MONGO_URI)
    try:
        client = MongoClient(test_uri, serverSelectionTimeoutMS=3000)
        client.admin.command("ping")
        client.close()
        return True, "Connected successfully"
    except ServerSelectionTimeoutError:
        return False, "Cannot reach MongoDB server. Is it running?"
    except ConnectionFailure as e:
        return False, f"Connection failed: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def ensure_indexes():
    """Create necessary indexes for performance."""
    db = get_db()
    novels = db["novels"]
    novels.create_index("title", name="title_idx")
    novels.create_index("source.url", name="source_url_idx")
    novels.create_index("progress.status", name="status_idx")
    novels.create_index("history.last_read", name="last_read_idx")
    novels.create_index("metadata.genres", name="genres_idx")
    print("Database indexes ensured.")


def close_connection():
    """Gracefully close MongoDB connection."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
