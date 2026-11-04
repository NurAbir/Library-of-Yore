"""Scraper package for fetching novel metadata."""
from .base import ScraperResult, BaseScraper
from .novelfire import NovelfireScraper
from .novelphoenix import NovelPhoenixScraper
from .wuxiaworld import WuxiaworldScraper
from .freewebnovel import FreeWebNovelScraper
from .flamecomics import FlameComicsScraper
from .mangafire import MangaFireScraper

# Tried in order. Each scraper checks the URL's hostname (not a substring of
# the whole URL), so a look-alike domain can't claim another site's links.
_SCRAPER_CLASSES = (
    NovelfireScraper,
    NovelPhoenixScraper,
    WuxiaworldScraper,
    FreeWebNovelScraper,
    FlameComicsScraper,
    MangaFireScraper,
)


def get_scraper_for_url(url: str):
    """Factory: return appropriate scraper for a URL, or None."""
    for scraper_class in _SCRAPER_CLASSES:
        scraper = scraper_class()
        if scraper.can_handle(url):
            return scraper
    return None


__all__ = [
    "ScraperResult", "BaseScraper", "NovelfireScraper", "NovelPhoenixScraper",
    "WuxiaworldScraper", "FreeWebNovelScraper", "FlameComicsScraper",
    "MangaFireScraper", "get_scraper_for_url",
]
