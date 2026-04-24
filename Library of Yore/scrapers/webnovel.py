"""Webnovel.com scraper using Playwright for JS-rendered pages."""
import re
from typing import Optional
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, ScraperResult
from config import USER_AGENT, REQUEST_TIMEOUT


class WebnovelScraper(BaseScraper):
    """Scraper for https://www.webnovel.com"""

    SOURCE_NAME = "webnovel"
    DOMAIN_PATTERNS = ["webnovel.com"]

    def scrape(self, url: str) -> ScraperResult:
        result = ScraperResult(source_name=self.SOURCE_NAME)

        # Validate URL format
        if not self.can_handle(url):
            result.error_message = "Invalid Webnovel URL"
            return result

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=USER_AGENT,
                    viewport={"width": 1920, "height": 1080},
                    locale="en-US",
                )
                page = context.new_page()

                # Navigate with timeout
                page.goto(url, wait_until="networkidle", timeout=REQUEST_TIMEOUT * 1000)

                # Wait for content to load (Webnovel uses React)
                page.wait_for_selector("h1, .book-info__name, .g_title, [data-testid='book-name']", timeout=15000)

                # Get fully rendered HTML
                html = page.content()
                browser.close()

            soup = BeautifulSoup(html, "html.parser")
            result = self._parse_soup(soup, url, result)
            result.success = True

        except PlaywrightTimeout:
            result.error_message = "Timeout: Webnovel took too long to load. The site may be blocking automated access."
        except Exception as e:
            result.error_message = f"Scraping failed: {str(e)}"

        return result

    def _parse_soup(self, soup, url: str, result: ScraperResult) -> ScraperResult:
        """Extract data from parsed HTML."""
        # Title — multiple possible selectors
        title_selectors = [
            "h1.book-info__name",
            "h1.g_title",
            "h1[data-testid='book-name']",
            "h1",
            ".book-name",
        ]
        for sel in title_selectors:
            el = soup.select_one(sel)
            if el:
                result.title = el.get_text(strip=True)
                break

        # Author
        author_selectors = [
            ".book-info__author a",
            ".author a",
            "[data-testid='author-name']",
            "a[href*='author']",
        ]
        for sel in author_selectors:
            el = soup.select_one(sel)
            if el:
                result.author = el.get_text(strip=True)
                break

        # Cover image
        cover_selectors = [
            "._img img",
            ".book-cover img",
            "img[alt*='cover']",
            ".g_thumb img",
        ]
        for sel in cover_selectors:
            el = soup.select_one(sel)
            if el:
                src = el.get("src") or el.get("data-src")
                if src:
                    result.cover_url = src
                    break

        # Synopsis / description
        synopsis_selectors = [
            ".book-info__desc",
            ".g_desc",
            ".description",
            "[data-testid='book-description']",
            "#about",
        ]
        for sel in synopsis_selectors:
            el = soup.select_one(sel)
            if el:
                result.synopsis = el.get_text(strip=True)
                break

        # Chapter count & status
        # Webnovel often shows these in detail rows or stats
        text_blob = soup.get_text(separator=" ", strip=True)

        # Look for chapter patterns
        chapter_patterns = [
            r"(\d{1,3}(?:,\d{3})*)\s*Chapters",
            r"(\d{1,3}(?:,\d{3})*)\s*Chs",
            r"Latest:\s*Chapter\s*(\d+)",
            r"(\d+)\s*\|\s*Ongoing",
            r"(\d+)\s*\|\s*Completed",
        ]
        for pat in chapter_patterns:
            m = re.search(pat, text_blob, re.IGNORECASE)
            if m:
                num_str = m.group(1).replace(",", "")
                result.total_chapters = int(num_str)
                break

        # Status detection
        if "completed" in text_blob.lower() or "finished" in text_blob.lower():
            result.status = "completed"
        elif "hiatus" in text_blob.lower() or "paused" in text_blob.lower():
            result.status = "hiatus"
        else:
            result.status = "ongoing"

        # Genres — often in tag links
        genre_selectors = [
            ".book-info__tag a",
            ".tags a",
            ".genre a",
            "[data-testid='genre-tag']",
        ]
        genres = set()
        for sel in genre_selectors:
            for el in soup.select(sel):
                txt = el.get_text(strip=True)
                if txt and len(txt) < 30:
                    genres.add(txt)
        result.genres = list(genres)[:5]  # limit to 5

        # Fallback: if no title found, mark as failed
        if not result.title:
            result.success = False
            result.error_message = "Could not extract title. Webnovel layout may have changed."
        else:
            result.success = True

        result.raw_data = {"url": url, "parsed_text_sample": text_blob[:500]}
        return result
