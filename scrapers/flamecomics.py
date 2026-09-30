"""Flame Comics (flamecomics.xyz) scraper, for both web novels and manga.

Flame is a Next.js site. Every novel page (/novel/{id}) and series page
(/series/{id}) ships its full data as JSON inside
<script id="__NEXT_DATA__">, including every chapter, locked ones too. This
scraper reads that JSON instead of the page text: flattened text runs labels
together (the chapter number "621" next to the price "50 embers" reads as
"Chapter 62150 embers"), so parsing text would produce wrong numbers.

Shape observed on the live site (September 2026):
  props.pageProps.novels   (novel pages)  or  props.pageProps.series (manga)
      title, author [list], description (HTML), status ("Ongoing"/"Hiatus"/...),
      tags [list], cover (file name), series_id / novel_id (the linked
      manhwa/novel), locked_chapter_count, ...
  props.pageProps.chapters  [newest first]
      chapter ("621.00", "16.50", "0.01"), title, token (16 hex chars; the
      chapter page is /novel/{id}/{token}), price ("50.00" = locked/paid,
      "0.00" = free; novel chapters only), release_date, ...

Chapter pages carry no chapter number in their URL; the browser extension
reads it from the page title instead (see content.js).
"""
import json
import re
from typing import Optional, Tuple

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, ScraperResult, fetch_html, FetchError
from utils import chapters

BASE_URL = "https://flamecomics.xyz"
_URL_RE = re.compile(r"^https?://(?:www\.)?flamecomics\.xyz/(novel|series)/(\d+)(?:[/?#]|$)", re.IGNORECASE)


def canonical_url(url: str) -> Optional[Tuple[str, str, str]]:
    """(kind, id, canonical page URL) for any Flame novel/series/chapter URL.
    A chapter link such as /novel/8/f48067c3fe28e0a0 maps to /novel/8."""
    m = _URL_RE.match((url or "").strip())
    if not m:
        return None
    kind, item_id = m.group(1).lower(), m.group(2)
    return kind, item_id, f"{BASE_URL}/{kind}/{item_id}"


def _join(value) -> str:
    if isinstance(value, list):
        return ", ".join(str(v).strip() for v in value if str(v).strip())
    return str(value or "").strip()


def parse_page(html: str, kind: str, item_id: str, result: ScraperResult) -> ScraperResult:
    """Fill a ScraperResult from a Flame novel/series page's HTML."""
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    if not script or not script.string:
        result.error_message = "Flame Comics page had no embedded data (__NEXT_DATA__)."
        return result
    try:
        page_props = json.loads(script.string)["props"]["pageProps"]
    except (ValueError, KeyError, TypeError) as e:
        result.error_message = f"Couldn't read Flame Comics page data: {e}"
        return result

    info = page_props.get("novels") if kind == "novel" else page_props.get("series")
    if isinstance(info, list):
        info = info[0] if info else None
    if not isinstance(info, dict):
        result.error_message = "Flame Comics page data had no novel/series details."
        return result

    result.content_type = "novel" if kind == "novel" else "manga"
    result.title = str(info.get("title") or "").strip()
    result.author = _join(info.get("author"))
    description = info.get("description") or ""
    result.synopsis = BeautifulSoup(description, "html.parser").get_text("\n", strip=True)
    site_status_text = str(info.get("status") or "")
    result.status = site_status_text
    tags = info.get("tags")
    result.genres = [str(t) for t in tags][:5] if isinstance(tags, list) else []

    og_image = soup.find("meta", attrs={"property": "og:image"})
    if og_image and og_image.get("content"):
        result.cover_url = og_image["content"]
    elif info.get("cover"):
        folder = "novels" if kind == "novel" else "series"
        result.cover_url = f"https://cdn.flamecomics.xyz/uploads/images/{folder}/{item_id}/{info['cover']}"

    raw_chapters = page_props.get("chapters") or []
    numbers = [c.get("chapter") for c in raw_chapters if isinstance(c, dict)]
    chapter_list, trusted = chapters.normalize_list(numbers)
    if chapter_list:
        result.latest_chapter = chapter_list[-1]
    # Only keep the list if every chapter number is distinct; otherwise
    # progress falls back to simple mode for this title.
    result.chapter_list = chapter_list if trusted else []
    locked = []
    for c in raw_chapters:
        if not isinstance(c, dict):
            continue
        try:
            price = float(c.get("price") or 0)
        except (TypeError, ValueError):
            price = 0
        if price > 0:
            locked.append(c.get("chapter"))
    result.locked_list, _ = chapters.normalize_list(locked)

    result.raw_data = {
        "url": f"{BASE_URL}/{kind}/{item_id}",
        "site_status_text": site_status_text,
        "linked_series_id": info.get("series_id"),
        "linked_novel_id": info.get("novel_id"),
        "chapter_count": len(chapter_list),
    }
    result.success = bool(result.title)
    if not result.success:
        result.error_message = "Could not extract a title from Flame Comics."
    return result


class FlameComicsScraper(BaseScraper):
    """Scraper for https://flamecomics.xyz (novels and manga)."""

    SOURCE_NAME = "flamecomics"
    DOMAIN_PATTERNS = ["flamecomics.xyz"]

    def scrape(self, url: str) -> ScraperResult:
        result = ScraperResult(source_name=self.SOURCE_NAME)
        parsed = canonical_url(url)
        if not parsed:
            result.error_message = (
                "Use a Flame Comics novel or series link, e.g. "
                "https://flamecomics.xyz/novel/8 or https://flamecomics.xyz/series/2"
            )
            return result
        kind, item_id, page_url = parsed

        try:
            # Plain request first; a real browser if the site blocks it
            html = fetch_html(page_url, must_contain="__NEXT_DATA__")
        except FetchError as e:
            result.error_message = f"Scraping failed: {e}"
            return result

        result = parse_page(html, kind, item_id, result)
        result.status = self._normalize_status(result.status)
        return result
