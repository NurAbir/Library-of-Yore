"""FreeWebNovel.com scraper.

Verified against the live site (September 2026):
  - Novel pages are /novel/{slug}; chapters are /novel/{slug}/chapter-{N},
    where N is the chapter's position, 1..total with no gaps.
  - The page carries reliable meta tags: og:novel:status,
    og:novel:author, og:novel:genre, og:novel:lastest_chapter_name (sic).
  - The chapter list is served by the page itself as JSON:
      /novel/{slug}?ajax=chapters&page=1&pageSize=200
      -> {"code":200, "totalChapters":1432, "totalPage":8, "html":"..."}
    One request gives the total, so the full list is 1..totalChapters
    without downloading every page.
"""
import re

from bs4 import BeautifulSoup

from scrapers.base import (BaseScraper, ScraperResult, fetch_html, fetch_json,
                           parse_chapter_label, latest_from_labels, FetchError)
from utils import chapters


class FreeWebNovelScraper(BaseScraper):
    """Scraper for https://freewebnovel.com"""

    SOURCE_NAME = "freewebnovel"
    DOMAIN_PATTERNS = ["freewebnovel.com"]

    @staticmethod
    def canonical_url(url: str) -> str:
        """https://freewebnovel.com/novel/{slug} for a novel page, a chapter
        link, or the older https://freewebnovel.com/{slug}.html form."""
        url = url.strip()
        m = re.match(r"^(https?://[^/]+)/novel/([^/?#]+)", url, re.IGNORECASE)
        if m:
            return f"{m.group(1)}/novel/{m.group(2)}"
        m = re.match(r"^(https?://[^/]+)/([^/?#]+?)(?:\.html)?(?:/chapter[^/]*)?/?$", url, re.IGNORECASE)
        if m and m.group(2):
            return f"{m.group(1)}/novel/{m.group(2)}"
        return url

    def scrape(self, url: str) -> ScraperResult:
        result = ScraperResult(source_name=self.SOURCE_NAME)
        if not self.can_handle(url):
            result.error_message = "Invalid FreeWebNovel URL"
            return result
        page_url = self.canonical_url(url)
        try:
            html = fetch_html(page_url, must_contain="og:novel")
        except FetchError as e:
            result.error_message = f"Scraping failed: {e}"
            return result

        result = self._parse_soup(BeautifulSoup(html, "html.parser"), page_url, result)
        result.success = bool(result.title)
        if not result.success:
            result.error_message = "Could not extract title from FreeWebNovel."
            return result

        # Total chapters from the site's own chapter-list endpoint (one request)
        try:
            data = fetch_json(page_url, {"ajax": "chapters", "page": 1, "pageSize": 200}, page_url)
            self._apply_chapter_total(result, data)
        except Exception:
            pass  # keep the latest chapter from the meta tags; simple mode
        return result

    @staticmethod
    def _apply_chapter_total(result: ScraperResult, data) -> None:
        total = data.get("totalChapters") if isinstance(data, dict) else None
        try:
            total = int(total)
        except (TypeError, ValueError):
            return
        if total > 0:
            result.latest_chapter = str(total)
            result.chapter_list = [str(n) for n in range(1, total + 1)]
            result.raw_data["chapter_list_source"] = "sequential chapter URLs 1..totalChapters"

    def _parse_soup(self, soup, url: str, result: ScraperResult) -> ScraperResult:
        def meta(prop):
            el = soup.select_one(f"meta[property='{prop}']")
            return (el.get("content") or "").strip() if el else ""

        result.title = meta("og:novel:novel_name")
        if not result.title:
            for sel in ["h1.tit", "h1"]:
                el = soup.select_one(sel)
                if el and el.get_text(strip=True):
                    result.title = el.get_text(strip=True)
                    break

        result.author = ", ".join(a.strip() for a in meta("og:novel:author").split(",") if a.strip())
        result.cover_url = meta("og:image")

        inner = soup.select_one(".m-desc .txt .inner")
        result.synopsis = inner.get_text("\n", strip=True) if inner else ""

        status = meta("og:novel:status")
        result.status = self._normalize_status(status) if status else "ongoing"

        result.genres = [g.strip() for g in meta("og:novel:genre").split(",") if g.strip()][:5]

        # Latest chapter: from the meta tag until the chapter endpoint answers
        result.latest_chapter = parse_chapter_label(meta("og:novel:lastest_chapter_name")) \
            or latest_from_labels(a.get_text(strip=True) for a in soup.select("ul.ul-list5 a"))
        if result.latest_chapter:
            result.latest_chapter = chapters.parse_chapter(result.latest_chapter)

        result.raw_data = {"url": url}
        return result
