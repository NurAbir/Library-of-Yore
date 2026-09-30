"""Wuxiaworld.com scraper.

Verified against the live site (September 2026). Each novel page ships its
data inside a script as `window.__REACT_QUERY_STATE__ = {...}`. The query
whose key starts with "novel" holds the novel:
  item.name, item.authorName.value, item.synopsis.value (HTML),
  item.coverUrl.value, item.genres [..],
  item.tags ["Chinese", "Ongoing"]         <- publication status lives here
  (item.status is NOT the publication status: it's 0 for Emperor's
  Domination, which the site lists as Ongoing),
  item.chapterInfo.latestChapter.number   {"units": 2089, "nanos": 0}
  item.chapterInfo.chapterGroups[]        one per book:
      fromChapterNumber / toChapterNumber {"units","nanos"}
      counts {"total", "advance", "normal"}   ("advance" = paid early access)
Numbers are units + nanos/1e9. Most novels number chapters 1, 2, 3 ... and
the book ranges then add up to the full chapter list. Some older novels use
book.chapter numbers instead (Coiling Dragon's latest is 21.044, i.e. book 21
chapter 44, from a URL like cd-book-21-chapter-44); those get no list and use
simple mode, and the browser extension reads such URLs as 21.044 too.
"""
import json
import re
from decimal import Decimal
from typing import Optional

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, ScraperResult, fetch_html, latest_from_labels, FetchError
from utils import chapters

_STATE_MARKER = "__REACT_QUERY_STATE__"
_STATUS_TAGS = {"ongoing": "ongoing", "completed": "completed", "hiatus": "hiatus",
                "dropped": "dropped", "cancelled": "dropped"}


def _number(value) -> Optional[Decimal]:
    """{"units": 21, "nanos": 44000000} -> Decimal("21.044")."""
    if isinstance(value, dict):
        units = Decimal(int(value.get("units") or 0))
        nanos = Decimal(int(value.get("nanos") or 0))
        return units + nanos / Decimal(1_000_000_000)
    try:
        return Decimal(str(value)) if value is not None else None
    except Exception:
        return None


def extract_state(html: str) -> Optional[dict]:
    """Parse the JSON assigned to window.__REACT_QUERY_STATE__."""
    idx = html.find(_STATE_MARKER)
    if idx < 0:
        return None
    start = html.find("{", idx)
    if start < 0:
        return None
    try:
        state, _ = json.JSONDecoder().raw_decode(html, start)
        return state
    except ValueError:
        return None


def novel_item(state: dict) -> Optional[dict]:
    for query in (state or {}).get("queries", []):
        key = query.get("queryKey") or []
        if key and key[0] == "novel":
            item = (((query.get("state") or {}).get("data") or {}).get("item"))
            if isinstance(item, dict):
                return item
    return None


def chapter_data(item: dict):
    """(latest, chapter_list, locked_list) from item.chapterInfo. The list is
    only returned when every book range is whole-numbered and its size
    matches the site's own chapter count for that book."""
    info = item.get("chapterInfo") or {}
    latest = _number((info.get("latestChapter") or {}).get("number"))
    groups = info.get("chapterGroups") or []

    chapter_list, locked, consistent = [], [], bool(groups)
    for index, g in enumerate(groups):
        is_last = index == len(groups) - 1
        start = _number(g.get("fromChapterNumber"))
        end = _number(g.get("toChapterNumber"))
        counts = g.get("counts") or {}
        total = int(counts.get("total") or 0)
        advance = int(counts.get("advance") or 0)
        if start is None or total <= 0 or start != start.to_integral_value():
            consistent = False
            break
        # The last book's "to" can be a placeholder (9999); the count is
        # authoritative. Advance (paid) chapters come after the free ones.
        real_end = start + total - 1
        if end is None or end != end.to_integral_value():
            consistent = False
            break
        # Every book must be exactly as long as its count says (no gaps);
        # only the last book's end may be a larger placeholder.
        if end < real_end or (end > real_end and not is_last):
            consistent = False
            break
        numbers = [str(int(start) + i) for i in range(total)]
        chapter_list.extend(numbers)
        if advance:
            locked.extend(numbers[-advance:])

    if consistent and chapter_list:
        normalized, trusted = chapters.normalize_list(chapter_list)
        if trusted:
            last = chapters.key(normalized[-1])
            latest = max(latest, last) if latest is not None else last
            return chapters.parse_chapter(latest), normalized, chapters.normalize_list(locked)[0]

    # No reliable list. latestChapter is the newest *free* chapter; paid
    # "advance" chapters of the newest book come right after it.
    advance = int(((groups[-1].get("counts") or {}).get("advance") or 0)) if groups else 0
    locked_simple = []
    if latest is not None and advance and latest == latest.to_integral_value():
        locked_simple = [str(int(latest) + i) for i in range(1, advance + 1)]
        latest = latest + advance
    return (chapters.parse_chapter(latest) if latest is not None else None), [], locked_simple


class WuxiaworldScraper(BaseScraper):
    """Scraper for https://www.wuxiaworld.com"""

    SOURCE_NAME = "wuxiaworld"
    DOMAIN_PATTERNS = ["wuxiaworld.com"]

    @staticmethod
    def canonical_url(url: str) -> str:
        m = re.match(r"^(https?://[^/]+)/novel/([^/?#]+)", url.strip(), re.IGNORECASE)
        return f"{m.group(1)}/novel/{m.group(2)}" if m else url.strip()

    def scrape(self, url: str) -> ScraperResult:
        result = ScraperResult(source_name=self.SOURCE_NAME)
        if not self.can_handle(url):
            result.error_message = "Invalid Wuxiaworld URL"
            return result
        page_url = self.canonical_url(url)
        try:
            html = fetch_html(page_url, must_contain=_STATE_MARKER)
        except FetchError as e:
            result.error_message = f"Scraping failed: {e}"
            return result

        item = novel_item(extract_state(html))
        if item:
            result = self._parse_item(item, result)
        else:
            result = self._parse_soup(BeautifulSoup(html, "html.parser"), result)
        result.raw_data["url"] = page_url
        result.success = bool(result.title)
        if not result.success:
            result.error_message = "Could not extract title from Wuxiaworld."
        return result

    def _parse_item(self, item: dict, result: ScraperResult) -> ScraperResult:
        def value(v):
            return (v.get("value") if isinstance(v, dict) else v) or ""

        result.title = str(item.get("name") or "").strip()
        result.author = str(value(item.get("authorName"))).strip()
        result.cover_url = str(value(item.get("coverUrl"))).strip()
        synopsis = value(item.get("synopsis")) or value(item.get("description"))
        result.synopsis = BeautifulSoup(synopsis, "html.parser").get_text("\n", strip=True)
        genres = item.get("genres")
        result.genres = [str(g) for g in genres][:5] if isinstance(genres, list) else []
        tags = [str(t).strip().lower() for t in (item.get("tags") or [])]
        result.status = next((_STATUS_TAGS[t] for t in tags if t in _STATUS_TAGS), "")
        result.latest_chapter, result.chapter_list, result.locked_list = chapter_data(item)
        return result

    def _parse_soup(self, soup, result: ScraperResult) -> ScraperResult:
        """Fallback when the embedded data is missing."""
        h1 = soup.select_one("h1")
        og = soup.select_one("meta[property='og:title']")
        result.title = h1.get_text(strip=True) if h1 else (og.get("content", "").split("|")[0].strip() if og else "")
        img = soup.select_one("meta[property='og:image']")
        result.cover_url = img.get("content", "") if img else ""
        desc = soup.select_one("meta[property='og:description']")
        result.synopsis = desc.get("content", "") if desc else ""
        text_blob = soup.get_text(" ", strip=True)
        result.latest_chapter = self._extract_chapter_number(text_blob) or latest_from_labels(
            a.get_text(strip=True) for a in soup.select("a[href*='chapter']"))
        result.status = ""
        return result
