"""NovelPhoenix.com scraper.

NovelPhoenix runs the same site template as Novelfire (identical novel page,
same header stats, same position-numbered chapter URLs), just with /novel/
instead of /book/ in its URLs, so it reuses the Novelfire scraper.
"""
from scrapers.novelfire import NovelfireScraper


class NovelPhoenixScraper(NovelfireScraper):
    """Scraper for https://novelphoenix.com"""

    SOURCE_NAME = "novelphoenix"
    DOMAIN_PATTERNS = ["novelphoenix.com"]
    SITE_NAME = "NovelPhoenix"
    BOOK_PATH = "novel"         # /novel/{slug}
