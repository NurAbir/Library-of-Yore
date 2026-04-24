"""Novelfire.net scraper using requests + BeautifulSoup with Playwright fallback."""
import re
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from scrapers.base import BaseScraper, ScraperResult
from config import USER_AGENT, REQUEST_TIMEOUT


class NovelfireScraper(BaseScraper):
    """Scraper for https://novelfire.net"""

    SOURCE_NAME = "novelfire"
    DOMAIN_PATTERNS = ["novelfire.net", "novelfire.com"]

    def scrape(self, url: str) -> ScraperResult:
        result = ScraperResult(source_name=self.SOURCE_NAME)

        if not self.can_handle(url):
            result.error_message = "Invalid Novelfire URL"
            return result

        # Try lightweight requests first
        try:
            headers = {"User-Agent": USER_AGENT}
            resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            result = self._parse_soup(soup, url, result)
            if result.title:
                result.success = True
                return result
        except Exception:
            pass  # Fallback to Playwright

        # Playwright fallback
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent=USER_AGENT)
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=REQUEST_TIMEOUT * 1000)
                page.wait_for_timeout(3000)  # Let JS hydrate
                html = page.content()
                browser.close()

            soup = BeautifulSoup(html, "html.parser")
            result = self._parse_soup(soup, url, result)
            result.success = bool(result.title)
            if not result.title:
                result.error_message = "Could not extract title from Novelfire."

        except PlaywrightTimeout:
            result.error_message = "Timeout: Novelfire took too long to load."
        except Exception as e:
            result.error_message = f"Scraping failed: {str(e)}"

        return result

    def _parse_soup(self, soup, url: str, result: ScraperResult) -> ScraperResult:
        """Extract data from Novelfire HTML."""
        # Title
        title_selectors = [
            "h1.novel-title",
            "h1",
            ".novel-title",
            "[property='og:title']",
        ]
        for sel in title_selectors:
            el = soup.select_one(sel)
            if el:
                if sel.startswith("[property"):
                    result.title = el.get("content", "").strip()
                else:
                    result.title = el.get_text(strip=True)
                if result.title:
                    break

        # Author
        author_selectors = [
            ".author a",
            ".novel-author",
            "[property='og:author']",
            "a[href*='author']",
        ]
        for sel in author_selectors:
            el = soup.select_one(sel)
            if el:
                result.author = el.get_text(strip=True) if not sel.startswith("[property") else el.get("content", "")
                if result.author:
                    break

        # Cover
        cover_selectors = [
            ".novel-cover img",
            ".img-cover img",
            "img[alt*='cover']",
            "[property='og:image']",
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
            ".description",
            ".novel-description",
            ".summary",
            "[property='og:description']",
        ]
        for sel in synopsis_selectors:
            el = soup.select_one(sel)
            if el:
                result.synopsis = el.get_text(strip=True) if not sel.startswith("[property") else el.get("content", "")
                if result.synopsis:
                    break

        # Chapter count & status from text
        text_blob = soup.get_text(separator=" ", strip=True)

        # Novelfire often shows "XXX Chapters" or "Chapter XXX"
        chap_match = re.search(r"(\d{1,3}(?:,\d{3})*)\s*Chapters?", text_blob, re.IGNORECASE)
        if chap_match:
            result.total_chapters = int(chap_match.group(1).replace(",", ""))

        latest_match = re.search(r"Latest\s*Chapter\s*(\d+)", text_blob, re.IGNORECASE)
        if latest_match and not result.total_chapters:
            result.total_chapters = int(latest_match.group(1))

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
