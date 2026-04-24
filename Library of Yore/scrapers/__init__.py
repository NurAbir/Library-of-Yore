"""Scraper package for fetching novel metadata."""
from .base import ScraperResult, BaseScraper
from .webnovel import WebnovelScraper
from .novelfire import NovelfireScraper

def get_scraper_for_url(url: str):
    """Factory: return appropriate scraper for a URL."""
    domain = url.lower()
    if "webnovel.com" in domain:
        return WebnovelScraper()
    elif "novelfire.net" in domain or "novelfire.com" in domain:
        return NovelfireScraper()
    return None

__all__ = ["ScraperResult", "BaseScraper", "WebnovelScraper", "NovelfireScraper", "get_scraper_for_url"]
