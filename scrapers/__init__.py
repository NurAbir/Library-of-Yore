"""Scraper package for fetching novel metadata."""
from .base import ScraperResult, BaseScraper
from .novelfire import NovelfireScraper
from .wuxiaworld import WuxiaworldScraper
from .freewebnovel import FreeWebNovelScraper
from .novelupdates import NovelUpdatesScraper

def get_scraper_for_url(url: str):
    """Factory: return appropriate scraper for a URL."""
    domain = url.lower()
    if "novelfire.net" in domain or "novelfire.com" in domain:
        return NovelfireScraper()
    elif "wuxiaworld.com" in domain:
        return WuxiaworldScraper()
    elif "freewebnovel.com" in domain:
        return FreeWebNovelScraper()
    elif "novelupdates.com" in domain:
        return NovelUpdatesScraper()
    return None

__all__ = ["ScraperResult", "BaseScraper", "NovelfireScraper", "WuxiaworldScraper", 
           "FreeWebNovelScraper", "NovelUpdatesScraper", "get_scraper_for_url"]