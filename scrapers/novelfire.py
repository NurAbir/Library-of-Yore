"""Novelfire.net scraper (also the base for NovelPhoenix, which runs the same
site template).

Verified against the live site (September 2026):
  - The novel page's header shows the chapter count and status:
      <div class="header-stats"><span>3200 Chapters</span> ... <span>Ongoing Status</span></div>
  - Chapter URLs are /book/{slug}/chapter-{N} where N is the chapter's
    position, running 1, 2, 3 ... up to the chapter count with no gaps (the
    chapter list pages end exactly at chapter-{count}), even when a chapter's
    own title says "Epilogue" or carries a different number.
  - So the full chapter list is 1..count, known from the novel page alone.
    Fetching the real list would take one request per 100 chapters (32 for a
    3200-chapter novel) and wouldn't add anything.
The browser extension records the same N from the chapter URL, so progress
and the list always use the same numbering.
"""
import re

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, ScraperResult, fetch_html, parse_chapter_label, FetchError
from utils import chapters


class NovelfireScraper(BaseScraper):
    """Scraper for https://novelfire.net"""

    SOURCE_NAME = "novelfire"
    DOMAIN_PATTERNS = ["novelfire.net", "novelfire.com"]
    SITE_NAME = "Novelfire"
    BOOK_PATH = "book"          # /book/{slug}

    def canonical_url(self, url: str) -> str:
        """Novel page URL for any novel or chapter URL on this site."""
        m = re.match(rf"^(https?://[^/]+)/{self.BOOK_PATH}/([^/?#]+)", url.strip(), re.IGNORECASE)
        return f"{m.group(1)}/{self.BOOK_PATH}/{m.group(2)}" if m else url.strip()

    def scrape(self, url: str) -> ScraperResult:
        result = ScraperResult(source_name=self.SOURCE_NAME)
        if not self.can_handle(url):
            result.error_message = f"Invalid {self.SITE_NAME} URL"
            return result
        page_url = self.canonical_url(url)
        try:
            html = fetch_html(page_url, must_contain="header-stats")
        except FetchError as e:
            result.error_message = f"Scraping failed: {e}"
            return result

        result = self._parse_soup(BeautifulSoup(html, "html.parser"), page_url, result)
        result.success = bool(result.title)
        if not result.success:
            result.error_message = f"Could not extract title from {self.SITE_NAME}."
        return result

    def _parse_soup(self, soup, url: str, result: ScraperResult) -> ScraperResult:
        """Extract data from a Novelfire-template novel page."""
        def text(el):
            return el.get_text(" ", strip=True) if el else ""

        # Title
        for sel in ["h1.novel-title", "h1", ".novel-title"]:
            result.title = text(soup.select_one(sel))
            if result.title:
                break
        if not result.title:
            og = soup.select_one("meta[property='og:title']")
            result.title = (og.get("content", "") if og else "").split(" - ")[0].strip()

        # Author
        for sel in [".author a", "[itemprop='author']", ".novel-author"]:
            result.author = text(soup.select_one(sel))
            if result.author:
                break

        # Cover: og:image is always the real cover on this template
        og_image = soup.select_one("meta[property='og:image']")
        if og_image and og_image.get("content"):
            result.cover_url = og_image["content"]
        else:
            img = soup.select_one(".novel-cover img, .img-cover img")
            if img:
                result.cover_url = img.get("data-src") or img.get("src") or ""

        # Synopsis
        for sel in [".summary", ".description", ".novel-description"]:
            result.synopsis = soup.select_one(sel).get_text(" ", strip=True) if soup.select_one(sel) else ""
            if result.synopsis:
                break
        if not result.synopsis:
            og = soup.select_one("meta[property='og:description']")
            result.synopsis = og.get("content", "") if og else ""
        if result.synopsis:
            # Strip "Summary"/"Description" labels and "Show More" button text
            result.synopsis = re.sub(r"^(summary|description|synopsis)\s*[:\-]?\s*", "", result.synopsis,
                                     flags=re.IGNORECASE).strip()
            result.synopsis = re.sub(r"\s*(show\s+more|show\s+less|read\s+more|\.{3}more)\s*$", "",
                                     result.synopsis, flags=re.IGNORECASE).strip()

        # Chapter count and status from the header stats
        count = None
        status_text = ""
        for span in soup.select(".header-stats > span, .header-stats span"):
            t = span.get_text(" ", strip=True)
            if count is None and re.search(r"chapters?", t, re.IGNORECASE):
                digits = re.sub(r"[^\d]", "", t)
                count = int(digits) if digits else None
            elif not status_text and re.search(r"status", t, re.IGNORECASE):
                status_text = re.sub(r"status", "", t, flags=re.IGNORECASE).strip()
        result.status = self._normalize_status(status_text) if status_text else "ongoing"

        if count:
            # Chapters are numbered by position 1..count (see module docstring)
            result.latest_chapter = str(count)
            result.chapter_list = [str(n) for n in range(1, count + 1)]
            result.raw_data["chapter_list_source"] = "sequential chapter URLs 1..count"
        else:
            latest_label = soup.select_one("a[href$='/chapters'] .latest")
            result.latest_chapter = parse_chapter_label(text(latest_label)) if latest_label else None
            if not result.latest_chapter:
                result.latest_chapter = self._extract_chapter_number(soup.get_text(" ", strip=True))

        # Genres
        genres = []
        for el in soup.select(".categories a, .genre a, .tags a"):
            g = el.get_text(strip=True)
            if g and len(g) < 30 and g not in genres:
                genres.append(g)
        result.genres = genres[:5]

        result.raw_data["url"] = url
        if result.latest_chapter:
            result.latest_chapter = chapters.parse_chapter(result.latest_chapter)
        return result
