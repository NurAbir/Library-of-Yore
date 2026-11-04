"""Shared utility functions."""
import io
import requests
from PIL import Image
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

from config import USER_AGENT, REQUEST_TIMEOUT


def download_image(url: str, max_size: int = 800, fallback_referer: str = "") -> bytes:
    """Download image from URL and resize if needed. Returns JPEG bytes.

    The request first sends the image's own URL as the Referer (what has always
    worked). Some image hosts only serve pictures requested from their own site;
    if that attempt fails and `fallback_referer` (the novel's page URL) is given,
    it is retried the way a browser would, with the page as the Referer.
    """
    def fetch(referer: str) -> bytes:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT, "Referer": referer},
                            timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.content

    try:
        content = fetch(url)
    except requests.RequestException:
        if not fallback_referer:
            raise
        content = fetch(fallback_referer)
    img = Image.open(io.BytesIO(content))
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
