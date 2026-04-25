"""FreeWebNovel.com scraper using requests + BeautifulSoup."""
import re
import requests
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, ScraperResult
from config import USER_AGENT, REQUEST_TIMEOUT


class FreeWebNovelScraper(BaseScraper):
    """Scraper for https://freewebnovel.com"""

    SOURCE_NAME = "freewebnovel"
    DOMAIN_PATTERNS = ["freewebnovel.com"]

    def scrape(self, url: str) -> ScraperResult:
        result = ScraperResult(source_name=self.SOURCE_NAME)

        if not self.can_handle(url):
            result.error_message = "Invalid FreeWebNovel URL"
            return result

        try:
            headers = {"User-Agent": USER_AGENT}
            resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            result = self._parse_soup(soup, url, result)
            result.success = bool(result.title)
            if not result.title:
                result.error_message = "Could not extract title from FreeWebNovel."
        except Exception as e:
            result.error_message = "Scraping failed: " + str(e)

        return result

    def _parse_soup(self, soup, url: str, result: ScraperResult) -> ScraperResult:
        # Title
        title_selectors = [
            "h1.title",
            "h1",
            ".manga-detail h1",
            "meta[property='og:title']",
        ]
        for sel in title_selectors:
            el = soup.select_one(sel)
            if el:
                if sel.startswith("meta"):
                    result.title = el.get("content", "").strip()
                else:
                    result.title = el.get_text(strip=True)
                if result.title:
                    break

        # Author
        author_selectors = [
            ".author a",
            ".manga-detail .author",
            "[property='og:author']",
            "a[href*='author']",
        ]
        for sel in author_selectors:
            el = soup.select_one(sel)
            if el:
                result.author = el.get_text(strip=True) if not sel.startswith("[") else el.get("content", "")
                if result.author:
                    break

        # Cover
        cover_selectors = [
            ".manga-detail .img-cover img",
            ".cover img",
            "img[alt*='cover']",
            "meta[property='og:image']",
        ]
        for sel in cover_selectors:
            el = soup.select_one(sel)
            if el:
                src = el.get("src") or el.get("content") or el.get("data-src")
                if src:
                    if src.startswith("//"):
                        src = "https:" + src
                    result.cover_url = src
                    break

        # Synopsis
        synopsis_selectors = [
            ".summary",
            ".description",
            ".manga-detail .summary",
            "meta[property='og:description']",
        ]
        for sel in synopsis_selectors:
            el = soup.select_one(sel)
            if el:
                result.synopsis = el.get_text(strip=True) if not sel.startswith("meta") else el.get("content", "")
                if result.synopsis:
                    break

        # Chapter count
        text_blob = soup.get_text(separator=" ", strip=True)
        result.total_chapters = self._extract_chapter_number(text_blob)

        # Also try chapter list count
        if not result.total_chapters:
            chapter_links = soup.select(".chapter-list a, .manga-chapter a")
            if chapter_links:
                nums = []
                for link in chapter_links:
                    text = link.get_text(strip=True)
                    m = re.search(r"[Cc]hapter\s*(\d+)", text)
                    if m:
                        nums.append(int(m.group(1)))
                if nums:
                    result.total_chapters = max(nums)

        # Status
        result.status = self._normalize_status(text_blob)

        # Genres
        genre_selectors = [
            ".genre a",
            ".tags a",
            ".categories a",
        ]
        genres = set()
        for sel in genre_selectors:
            for el in soup.select(sel):
                txt = el.get_text(strip=True)
                if txt and len(txt) < 30:
                    genres.add(txt)
        result.genres = list(genres)[:5]

        result.raw_data = {"url": url}
        return result
