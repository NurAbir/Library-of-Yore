"""Shared utility functions."""
import io
import requests
from PIL import Image
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

from config import USER_AGENT, REQUEST_TIMEOUT


def download_image(url: str, max_size: int = 800) -> bytes:
    """Download image from URL and resize if needed. Returns JPEG bytes."""
    headers = {"User-Agent": USER_AGENT, "Referer": url}
    resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    img = Image.open(io.BytesIO(resp.content))
    img = img.convert("RGB")
    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def bytes_to_pixmap(image_bytes: bytes, width: int = 200, height: int = 300) -> QPixmap:
    """Convert image bytes to scaled QPixmap."""
    pixmap = QPixmap()
    pixmap.loadFromData(image_bytes)
    if not pixmap.isNull():
        pixmap = pixmap.scaled(
            width, height,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )
    return pixmap


def truncate_text(text: str, max_len: int = 120) -> str:
    """Truncate long text with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0] + "..."
