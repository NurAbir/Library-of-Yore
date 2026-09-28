"""Base scraper interface and shared utilities."""
import re
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime

from utils import chapters


@dataclass
class ScraperResult:
    """Normalized result from any scraper."""
    title: str = ""
    author: str = ""
    cover_url: str = ""
    synopsis: str = ""
    # Highest chapter number the site lists, as a canonical chapter string
    # ("755", "16.5"); None if it couldn't be found. Before v2.1.0 this was
    # "total_chapters", an int that was sometimes a count and sometimes a
    # chapter number.
    latest_chapter: Optional[str] = None
    # Every chapter number the site lists, ascending (only scrapers that can
    # read the real list fill these in; the rest leave them empty).
    chapter_list: List[str] = field(default_factory=list)
    locked_list: List[str] = field(default_factory=list)
    content_type: str = "novel"      # "novel" or "manga"
    status: str = "ongoing"          # ongoing, completed, hiatus
    genres: List[str] = field(default_factory=list)
    source_name: str = ""
    success: bool = False
    error_message: str = ""
    raw_data: dict = field(default_factory=dict)


# A chapter *label* such as "Chapter 12", "Ch. 45.5" or "Chapter 220 - Side
# Story". Anchored at the start so "Extra Chapter 3", "Prologue", "Epilogue 2"
# and titles that merely contain numbers ("Night (4)") never count.
_LABEL_RE = re.compile(r"^\s*(?:chapter|ch\.?)\s*(\d+(?:\.\d+)?)(?!\d)(?!\.\d)", re.IGNORECASE)

# "Latest Chapter: 755", "Latest release: Ch. 45.5"
_LATEST_RE = re.compile(
    r"\blatest\s*(?:release|update)?\s*[:\-]?\s*(?:chapter|ch\.?)\s*[:\-#]?\s*(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(?![\d])",
    re.IGNORECASE,
)
# "756 Chapters", "1,234 chapters" (plural, whole word)
_COUNT_RE = re.compile(r"\b(\d{1,3}(?:,\d{3})+|\d+)\s*chapters\b", re.IGNORECASE)


def parse_chapter_label(label: str) -> Optional[str]:
    """Chapter number from a single chapter label, or None if the label
    isn't a plain numbered chapter."""
    m = _LABEL_RE.match(label or "")
    return chapters.parse_chapter(m.group(1)) if m else None


def latest_from_labels(labels) -> Optional[str]:
    """Highest numbered chapter among chapter labels, regardless of whether
    the page lists them newest-first or oldest-first."""
    nums = [c for c in (parse_chapter_label(t) for t in labels) if c is not None]
    return max(nums, key=chapters.key) if nums else None


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

    def _extract_chapter_number(self, text: str) -> Optional[str]:
        """Best-effort latest chapter from a page's flattened text, for sites
        without a readable chapter list. Returns a canonical chapter string.

        Rewritten in v2.1.0. The old version kept decimals out ("45.5" became
        45), matched any word starting with "ch" after a number ("2024 chess"),
        and as a last resort took the biggest number anywhere on the page.
        Now, in order:
          1. an explicit "Latest ... Chapter N" (decimals kept);
          2. an "N Chapters" count (plural, whole word);
          3. nothing, rather than a guess.
        """
        if not text:
            return None
        m = _LATEST_RE.search(text)
        if m:
            return chapters.parse_chapter(m.group(1).replace(",", "") + (m.group(2) or ""))
        m = _COUNT_RE.search(text)
        if m:
            return chapters.parse_chapter(m.group(1).replace(",", ""))
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
