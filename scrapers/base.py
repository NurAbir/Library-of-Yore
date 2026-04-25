"""Base scraper interface and shared utilities."""
import re
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class ScraperResult:
    """Normalized result from any scraper."""
    title: str = ""
    author: str = ""
    cover_url: str = ""
    synopsis: str = ""
    total_chapters: Optional[int] = None
    status: str = "ongoing"          # ongoing, completed, hiatus
    genres: List[str] = field(default_factory=list)
    source_name: str = ""
    success: bool = False
    error_message: str = ""
    raw_data: dict = field(default_factory=dict)


class BaseScraper:
    """Abstract base for all novel site scrapers."""

    SOURCE_NAME = "unknown"
    DOMAIN_PATTERNS = []

    def can_handle(self, url: str) -> bool:
        """Check if this scraper supports the given URL."""
        url_lower = url.lower()
        return any(pat in url_lower for pat in self.DOMAIN_PATTERNS)

    def scrape(self, url: str) -> ScraperResult:
        """Main entry point. Override in subclasses."""
        raise NotImplementedError

    def _extract_chapter_number(self, text: str) -> Optional[int]:
        """Try to extract a chapter count from text like '1,234 Chapters' or '2111 Chapters'."""
        if not text:
            return None
        # Try to find chapter-specific patterns first
        patterns = [
            r"(\d{1,3}(?:,\d{3})+|\d+)\s*[Cc]hapters?",
            r"(\d{1,3}(?:,\d{3})+|\d+)\s*[Cc]hs?",
            r"[Ll]atest\s*:?\s*[Cc]hapter\s*(\d+)",
            r"[Cc]hapter\s*(\d{1,3}(?:,\d{3})+|\d+)",
            r"(\d{1,3}(?:,\d{3})+|\d+)\s*\|\s*(?:Ongoing|Completed|Hiatus)",
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                num_str = m.group(1).replace(",", "")
                return int(num_str)
        # Fallback: grab the largest number in the text
        matches = re.findall(r"(\d{1,3}(?:,\d{3})+|\d+)", text)
        if matches:
            return max(int(m.replace(",", "")) for m in matches)
        return None

    def _normalize_status(self, text: str) -> str:
        """Map various status strings to canonical values."""
        if not text:
            return "ongoing"
        t = text.lower()
        if any(w in t for w in ["complete", "finished", "ended"]):
            return "completed"
        if any(w in t for w in ["hiatus", "paused", "on hold"]):
            return "hiatus"
        if any(w in t for w in ["drop", "cancel"]):
            return "dropped"
        return "ongoing"
