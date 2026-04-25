"""NovelUpdates.com scraper using requests + BeautifulSoup."""
import re
import requests
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, ScraperResult
from config import USER_AGENT, REQUEST_TIMEOUT


class NovelUpdatesScraper(BaseScraper):
    """Scraper for https://www.novelupdates.com

    NovelUpdates is an aggregator/catalog site. It provides metadata
    but chapters link out to external translation sites.
    """

    SOURCE_NAME = "novelupdates"
    DOMAIN_PATTERNS = ["novelupdates.com"]

    def scrape(self, url: str) -> ScraperResult:
        result = ScraperResult(source_name=self.SOURCE_NAME)

        if not self.can_handle(url):
            result.error_message = "Invalid NovelUpdates URL"
            return result

        try:
            headers = {"User-Agent": USER_AGENT}
            resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            result = self._parse_soup(soup, url, result)
            result.success = bool(result.title)
            if not result.title:
                result.error_message = "Could not extract title from NovelUpdates."
        except Exception as e:
            result.error_message = "Scraping failed: " + str(e)

        return result

    def _parse_soup(self, soup, url: str, result: ScraperResult) -> ScraperResult:
        # Title
        title_selectors = [
            "h1.novel-title",
            "h1",
            ".seriestitlenew",
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

        # Author (Original)
        author_selectors = [
            "#authtag",
            ".author a",
            "[property='og:author']",
        ]
        for sel in author_selectors:
            el = soup.select_one(sel)
            if el:
                result.author = el.get_text(strip=True) if not sel.startswith("[") else el.get("content", "")
                if result.author:
                    break

        # Cover
        cover_selectors = [
            ".seriesimg img",
            ".novel-cover img",
            "img[alt*='cover']",
            "meta[property='og:image']",
        ]
        for sel in cover_selectors:
            el = soup.select_one(sel)
            if el:
                src = el.get("src") or el.get("content") or el.get("data-src")
                if src:
                    result.cover_url = src
                    break

        # Synopsis
        synopsis_selectors = [
            "#editdescription",
            ".description",
            "meta[property='og:description']",
        ]
        for sel in synopsis_selectors:
            el = soup.select_one(sel)
            if el:
                result.synopsis = el.get_text(strip=True) if not sel.startswith("meta") else el.get("content", "")
                if result.synopsis:
                    break

        # Chapter count & status from text
        text_blob = soup.get_text(separator=" ", strip=True)

        # NovelUpdates shows "XXX Chapters" or "Completed" etc.
        result.total_chapters = self._extract_chapter_number(text_blob)

        # Also look for specific NU fields
        if not result.total_chapters:
            # Look for "Chapters" row in the info table
            for row in soup.select("#seriesinfo div, .series-info div"):
                text = row.get_text(strip=True)
                if "chapter" in text.lower():
                    m = re.search(r"(\d+)", text)
                    if m:
                        result.total_chapters = int(m.group(1))
                        break

        # Status - NovelUpdates has specific status fields
        status_selectors = [
            "#editstatus",
            ".status",
        ]
        status_found = False
        for sel in status_selectors:
            el = soup.select_one(sel)
            if el:
                status_text = el.get_text(strip=True)
                result.status = self._normalize_status(status_text)
                status_found = True
                break
        if not status_found:
            result.status = self._normalize_status(text_blob)

        # Genres
        genre_selectors = [
            "#seriesgenre a",
            ".genre a",
            "#tags a",
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
