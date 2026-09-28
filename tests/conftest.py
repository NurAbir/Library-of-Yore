"""Test setup: point the app's data directory at a throwaway folder BEFORE
config.py is imported, so tests never touch a real library."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_tmp = tempfile.mkdtemp(prefix="loy-tests-")
os.environ["LOCALAPPDATA"] = _tmp
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
