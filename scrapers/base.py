"""Base scraper interface and shared utilities."""
import re
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime

from utils import chapters


@dataclass
class ScraperResult:
    """Normalized result from any scraper."""
    title: str = ""
    author: str = ""
    cover_url: str = ""
    synopsis: str = ""
    # Highest chapter number the site lists, as a canonical chapter string
    # ("755", "16.5"); None if it couldn't be found. Before v2.1.0 this was
    # "total_chapters", an int that was sometimes a count and sometimes a
    # chapter number.
    latest_chapter: Optional[str] = None
    # Every chapter number the site lists, ascending (only scrapers that can
    # read the real list fill these in; the rest leave them empty).
    chapter_list: List[str] = field(default_factory=list)
    locked_list: List[str] = field(default_factory=list)
    content_type: str = "novel"      # "novel" or "manga"
    status: str = "ongoing"          # ongoing, completed, hiatus
    genres: List[str] = field(default_factory=list)
    source_name: str = ""
    success: bool = False
    error_message: str = ""
    raw_data: dict = field(default_factory=dict)


# A chapter *label* such as "Chapter 12", "Ch. 45.5" or "Chapter 220 - Side
# Story". Anchored at the start so "Extra Chapter 3", "Prologue", "Epilogue 2"
# and titles that merely contain numbers ("Night (4)") never count.
_LABEL_RE = re.compile(r"^\s*(?:chapter|ch\.?)\s*(\d+(?:\.\d+)?)(?!\d)(?!\.\d)", re.IGNORECASE)

# "Latest Chapter: 755", "Latest release: Ch. 45.5"
_LATEST_RE = re.compile(
    r"\blatest\s*(?:release|update)?\s*[:\-]?\s*(?:chapter|ch\.?)\s*[:\-#]?\s*(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(?![\d])",
    re.IGNORECASE,
)
# "756 Chapters", "1,234 chapters" (plural, whole word)
_COUNT_RE = re.compile(r"\b(\d{1,3}(?:,\d{3})+|\d+)\s*chapters\b", re.IGNORECASE)


def parse_chapter_label(label: str) -> Optional[str]:
    """Chapter number from a single chapter label, or None if the label
    isn't a plain numbered chapter."""
    m = _LABEL_RE.match(label or "")
    return chapters.parse_chapter(m.group(1)) if m else None


def latest_from_labels(labels) -> Optional[str]:
    """Highest numbered chapter among chapter labels, regardless of whether
    the page lists them newest-first or oldest-first."""
    nums = [c for c in (parse_chapter_label(t) for t in labels) if c is not None]
    return max(nums, key=chapters.key) if nums else None


class BaseScraper:
    """Abstract base for all novel site scrapers."""

    SOURCE_NAME = "unknown"
    DOMAIN_PATTERNS = []

    def can_handle(self, url: str) -> bool:
        """Check if this scraper supports the given URL."""
        url_lower = url.lower()
        return any(pat in url_lower for pat in self.DOMAIN_PATTERNS)

    def scrape(self, url: str) -> ScraperResult:
        """Main entry point. Override in subclasses."""
        raise NotImplementedError

    def _extract_chapter_number(self, text: str) -> Optional[str]:
        """Best-effort latest chapter from a page's flattened text, for sites
        without a readable chapter list. Returns a canonical chapter string.

        Rewritten in v2.1.0. The old version kept decimals out ("45.5" became
        45), matched any word starting with "ch" after a number ("2024 chess"),
        and as a last resort took the biggest number anywhere on the page.
        Now, in order:
          1. an explicit "Latest ... Chapter N" (decimals kept);
          2. an "N Chapters" count (plural, whole word);
          3. nothing, rather than a guess.
        """
        if not text:
            return None
        m = _LATEST_RE.search(text)
        if m:
            return chapters.parse_chapter(m.group(1).replace(",", "") + (m.group(2) or ""))
        m = _COUNT_RE.search(text)
        if m:
            return chapters.parse_chapter(m.group(1).replace(",", ""))
        return None
    def _normalize_status(self, text: str) -> str:
        """Map various status strings to canonical values."""
        if not text:
            return "ongoing"
        t = text.lower()
        if any(w in t for w in ["complete", "finished", "ended"]):
            return "completed"
        if any(w in t for w in ["hiatus", "paused", "on hold"]):
            return "hiatus"
        if any(w in t for w in ["drop", "cancel"]):
            return "dropped"
        return "ongoing"


# ── Fetching, with a real-browser fallback ───────────────────────────────────
#
# Every scraper fetches through these helpers (since v2.2.0). They try a plain
# HTTP request first (fast, no browser needed) and, if the site blocks it or
# answers with a bot-check page (e.g. Cloudflare's "Just a moment..."), load
# the page in a headless Chromium via Playwright instead, which passes those
# checks the way a normal browser does.

_BLOCK_MARKERS = (
    "Just a moment...",
    "cf-browser-verification",
    "challenges.cloudflare.com",
    "Attention Required! | Cloudflare",
    "Enable JavaScript and cookies to continue",
)


class FetchError(Exception):
    """A page couldn't be loaded, even through the browser fallback."""


def looks_blocked(text: str) -> bool:
    head = (text or "")[:20000]
    return any(marker in head for marker in _BLOCK_MARKERS)


def _request_headers(referer: Optional[str] = None) -> dict:
    from config import USER_AGENT
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
    }
    if referer:
        headers["Referer"] = referer
    return headers


def fetch_html(url: str, must_contain: Optional[str] = None, use_browser_fallback: bool = True) -> str:
    """Return a page's HTML. `must_contain` is a marker the real page always
    has (e.g. "__NEXT_DATA__"); a response without it counts as blocked."""
    import requests
    from config import REQUEST_TIMEOUT

    try:
        resp = requests.get(url, headers=_request_headers(), timeout=REQUEST_TIMEOUT)
        if resp.status_code < 400 and not looks_blocked(resp.text) \
                and (must_contain is None or must_contain in resp.text):
            return resp.text
        problem = f"HTTP {resp.status_code}" if resp.status_code >= 400 else "bot check / unexpected page"
    except Exception as e:  # network error, timeout, TLS, ...
        problem = str(e)

    if not use_browser_fallback:
        raise FetchError(f"Couldn't load {url}: {problem}")
    return _browser_fetch(url, must_contain)


def _launch_browser(p):
    """Start a headless browser: Microsoft Edge (installed on every Windows
    10/11 PC), then Google Chrome, then Playwright's own Chromium if someone
    ran `playwright install chromium`. The packaged .exe doesn't ship a
    browser of its own, so the installed ones come first."""
    errors = []
    for options in ({"channel": "msedge"}, {"channel": "chrome"}, {}):
        try:
            return p.chromium.launch(headless=True, **options)
        except Exception as e:
            errors.append(f"{options.get('channel', 'playwright chromium')}: {str(e).splitlines()[0]}")
    raise FetchError(
        "No browser available for sites that block plain requests. Install Microsoft Edge "
        "or Google Chrome (or run `playwright install chromium`). Details: " + "; ".join(errors)
    )


def _browser_fetch(url: str, must_contain: Optional[str] = None, json_url: Optional[str] = None):
    """Load `url` in headless Chromium. Returns the page HTML, or, when
    `json_url` is given, the text of fetching json_url from inside that page
    (so it carries the same cookies the page earned)."""
    from config import REQUEST_TIMEOUT, USER_AGENT
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise FetchError(f"Site blocked the request and the browser fallback isn't available ({e})")

    try:
        with sync_playwright() as p:
            browser = _launch_browser(p)
            try:
                page = browser.new_context(user_agent=USER_AGENT).new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=REQUEST_TIMEOUT * 1000)
                # Give a bot check up to ~15 s to clear itself
                for _ in range(15):
                    html = page.content()
                    if not looks_blocked(html) and (must_contain is None or must_contain in html):
                        break
                    page.wait_for_timeout(1000)
                else:
                    raise FetchError(f"{url} kept showing a bot check in the browser too")
                if json_url:
                    return page.evaluate(
                        "async (u) => { const r = await fetch(u, {credentials: 'include'}); return await r.text(); }",
                        json_url,
                    )
                return html
            finally:
                browser.close()
    except FetchError:
        raise
    except Exception as e:
        raise FetchError(f"Browser fallback failed for {url}: {e}")


def fetch_json(url: str, params: dict, page_url: str):
    """GET a JSON endpoint; falls back to calling it from inside the site's
    own page in the browser if the plain request is blocked."""
    import json as _json
    import requests
    from urllib.parse import urlencode
    from config import REQUEST_TIMEOUT

    full_url = url + ("&" if "?" in url else "?") + urlencode(params)
    try:
        resp = requests.get(full_url, headers=_request_headers(referer=page_url), timeout=REQUEST_TIMEOUT)
        if resp.status_code < 400 and not looks_blocked(resp.text):
            return resp.json()
    except Exception:
        pass
    return _json.loads(_browser_fetch(page_url, json_url=full_url))
