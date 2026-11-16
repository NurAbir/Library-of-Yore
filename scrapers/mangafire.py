"""MangaFire (mangafire.to) scraper: manga, manhwa, manhua and one-shots.

A series is identified by its short id ("zl363", "zkw8p"), which never changes,
never by its slug, which can:
  /title/{id}-{slug}                        current series page
  /manga/{slug}.{id}                        older series page
  /read/{slug}.{id}/{lang}/chapter-{N}      older reader
  /title/{id}-{slug}/chapter/{internal id}  current reader (the id is not a chapter number)
The older forms redirect to the current one. Because the current reader URL
carries only an internal id, chapter numbers come from link text and visible text,
one language at a time (see _chapter_sets); decimals (7.1, 7.2) are supported.

The chapter list is filled in by JavaScript from a token-gated API, so a plain
request only gets the page shell; fetch_html loads such a page in a real browser
until a real list appears. Only the newest chapter is trusted (a partly loaded
list would corrupt progress), a lone chapter counts as "latest unknown" (it is
usually just the "read first chapter" button), and the generic shell title is
rejected. Anything not found is left empty, never guessed. The fetched page is
kept in the logs folder for inspection.
"""
import re
from typing import Dict, Iterable, Iterator, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from config import LOGS_DIR
from scrapers.base import BaseScraper, ScraperResult, fetch_html, FetchError
from utils import chapters

BASE_URL = "https://mangafire.to"
DEBUG_PAGE_NAME = "mangafire_last_page.html"

_HOST_RE = re.compile(r"^(?:www\.)?mangafire\.to$", re.IGNORECASE)
_PREFIXES = ("title", "manga", "read")          # first path segment of a series or reader URL
_ID = r"[a-z0-9]{2,8}"
_OLD_SEG_RE = re.compile(rf"^(?P<slug>.+)\.(?P<id>{_ID})$", re.IGNORECASE)    # slug.id
_NEW_SEG_RE = re.compile(rf"^(?P<id>{_ID})-(?P<slug>.+)$", re.IGNORECASE)     # id-slug
_BARE_SEG_RE = re.compile(rf"^(?P<id>(?=[a-z]*\d){_ID})$", re.IGNORECASE)     # id alone (needs a digit)
_LANG_SEG_RE = re.compile(r"^[a-z]{2}(?:-[a-z]{2})?$", re.IGNORECASE)          # en, es-la, pt-br
# chapter-7, chapter-7.2, chapter-7-2, chapter7, ch-7 ("7-2" is read as 7.2, as the site labels it "Chap 7.2")
_CHAPTER_SEG_RE = re.compile(r"^(?:chapter|chap|ch)[-_.]?(?P<num>\d+(?:[.-]\d+)?)$", re.IGNORECASE)
# A chapter label on a link: "Chapter 341: ...", "Chap 8", "Ch. 12.5"
_LABEL_RE = re.compile(r"^\s*(?:chapter|chap|ch)\.?\s*(\d+(?:\.\d+)?)(?!\d)(?!\.\d)", re.IGNORECASE)
# A chapter list line in the page's visible text: "Chapter 341: Jul 01, 2026"
_LIST_LINE_RE = re.compile(r"^Chapter\s+(\d+(?:\.\d+)?)\s*:", re.IGNORECASE)
# The site's own sentence: "... the latest chapter 341 is available."
_LATEST_SENTENCE_RE = re.compile(r"\blatest\s+chapter\s+(\d+(?:\.\d+)?)\b", re.IGNORECASE)
_GENERIC_TEXT_RE = re.compile(r"mangafire|read manga|manga online|free online|free read", re.IGNORECASE)

UNKNOWN_LANG = "und"      # chapters that carry no language


# URLs

def split_series_segment(seg: str) -> Optional[Tuple[str, str]]:
    """(id, slug) from a series path segment, in any of the forms, else None.
    A segment with a dot is the older slug.id form; otherwise id-slug; a bare id
    (which needs a digit, so words like "updated" never count) has an empty slug."""
    seg = (seg or "").lower()
    m = _OLD_SEG_RE.match(seg) or _NEW_SEG_RE.match(seg) or _BARE_SEG_RE.match(seg)
    return (m.group("id"), m.groupdict().get("slug") or "") if m else None


def _path_parts(url: str) -> Optional[List[str]]:
    """Path segments of a mangafire.to URL (relative paths allowed), or None
    if the URL points at a different site."""
    try:
        u = urlparse((url or "").strip())
    except ValueError:
        return None
    if u.netloc and not _HOST_RE.match(u.netloc):
        return None
    if u.scheme and u.scheme not in ("http", "https"):
        return None
    return [s for s in u.path.split("/") if s]


def _chapter_in(rest: List[str]) -> Optional[str]:
    """The chapter number in the path segments after the series segment, for the
    older reader URLs that end in chapter-N. The current reader URL,
    /title/{id}-{slug}/chapter/{internal id}, carries only an internal chapter id
    (e.g. 8205410), which is NOT the chapter number: it yields None here, and a bare
    number is never taken as a chapter."""
    for seg in rest:
        m = _CHAPTER_SEG_RE.match(seg)
        if m:
            return m.group("num").replace("-", ".")
    return None


def parse_url(url: str) -> Optional[dict]:
    """Everything a MangaFire series or reader URL says about the series:
    {id, slug, lang, chapter, page_url}. `lang`/`chapter` are None when the URL
    doesn't carry them. `page_url` is the series page to fetch: /title/{id}-{slug}
    for current links, /manga/{slug}.{id} for older ones (which redirect)."""
    segs = _path_parts(url) if re.match(r"^https?://", (url or "").strip(), re.I) else None
    if not segs or len(segs) < 2 or segs[0].lower() not in _PREFIXES:
        return None
    series = split_series_segment(segs[1])
    if not series:
        return None
    sid, slug = series
    rest = segs[2:]
    lang = next((s.lower() for s in rest if _LANG_SEG_RE.match(s)), None)
    chapter = _chapter_in(rest)
    if _OLD_SEG_RE.match(segs[1].lower()):
        page_url = f"{BASE_URL}/manga/{slug}.{sid}"
    else:
        page_url = f"{BASE_URL}/title/{sid}-{slug}" if slug else f"{BASE_URL}/title/{sid}"
    return {"id": sid, "slug": slug, "lang": lang, "chapter": chapter, "page_url": page_url}


def series_id(url: str) -> Optional[str]:
    """The stable series id in a MangaFire URL, or None (other sites, home page, ...)."""
    info = parse_url(url)
    return info["id"] if info else None


def canonical_url(url: str) -> Optional[Tuple[str, Optional[str], str]]:
    """(series id, language or None, series page URL) for any MangaFire series or
    reader URL; None for anything else."""
    info = parse_url(url)
    return (info["id"], info["lang"], info["page_url"]) if info else None


# Chapters

def _chapter_links(hrefs: Iterable[str], sid: str) -> Iterator[Tuple[str, str]]:
    """(language, chapter number) for each link whose URL has the shape of a chapter of series `sid`."""
    for href in hrefs:
        segs = _path_parts(href)
        if not segs or len(segs) < 3 or segs[0].lower() not in _PREFIXES:
            continue
        series = split_series_segment(segs[1])
        if not series or series[0] != sid:
            continue
        rest = segs[2:]
        num = _chapter_in(rest)
        if num is None:
            continue                       # a volume, a page, or the series itself
        number = chapters.parse_chapter(num)
        if number is not None:
            lang = next((s.lower() for s in rest if _LANG_SEG_RE.match(s)), UNKNOWN_LANG)
            yield lang, number


def _chapters_by_language(hrefs: Iterable[str], sid: str) -> Dict[str, set]:
    found: Dict[str, set] = {}
    for lang, number in _chapter_links(hrefs, sid):
        found.setdefault(lang, set()).add(number)
    return found


def _hrefs(soup: BeautifulSoup) -> List[str]:
    return [a["href"] for a in soup.find_all("a", href=True)]


def _has_list(by_lang: Dict[str, set]) -> bool:
    """Two or more distinct chapters in one language: a real list, not a lone button."""
    return any(len(v) >= 2 for v in by_lang.values())


def _mentions_id(href: str, sid: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(sid)}(?![a-z0-9])", (href or "").lower()) is not None


def _chapter_sets(soup: BeautifulSoup, sid: str) -> Tuple[Dict[str, set], str]:
    """{language: {chapter numbers}} and which tier found it. The first tier that
    yields a real list wins; none of them depends on class names:
      links      hrefs shaped like a chapter of this series (/read/.../chapter-N)
      link-text  links whose URL mentions this series' id and whose text reads
                 "Chapter N" / "Chap N" (works whatever the URL shape)
      page-text  "Chapter N: ..." lines in the page's visible text
    """
    by_links = _chapters_by_language(_hrefs(soup), sid)
    if _has_list(by_links):
        return by_links, "links"

    by_text: Dict[str, set] = {}
    for a in soup.find_all("a", href=True):
        if not _mentions_id(a["href"], sid):
            continue
        m = _LABEL_RE.match(a.get_text(" ", strip=True))
        number = chapters.parse_chapter(m.group(1)) if m else None
        if number is None:
            continue
        segs = _path_parts(a["href"]) or []
        lang = next((s.lower() for s in segs[2:] if _LANG_SEG_RE.match(s)), UNKNOWN_LANG)
        by_text.setdefault(lang, set()).add(number)
    if _has_list(by_text):
        return by_text, "link-text"

    lines = {chapters.parse_chapter(m.group(1)) for m in
             (_LIST_LINE_RE.match(t) for t in soup.get_text("\n", strip=True).splitlines()) if m}
    lines.discard(None)
    by_lines = {UNKNOWN_LANG: lines} if lines else {}
    if _has_list(by_lines):
        return by_lines, "page-text"

    return (by_links or by_text or by_lines), "none"


def _pick_language(by_lang: dict, wanted: Optional[str]) -> Optional[str]:
    """Which language's chapter list to read. A language that holds a single
    chapter is just the "read first chapter" button and says nothing about the
    latest chapter, so one with a real list is preferred: the asked-for language
    first, then English, then the fullest list."""
    if not by_lang:
        return None
    listed = [lang for lang, nums in by_lang.items() if len(nums) >= 2]
    if listed:
        if wanted in listed:
            return wanted
        if "en" in listed:
            return "en"
        return max(listed, key=lambda lang: len(by_lang[lang]))
    for lang in (wanted, "en"):
        if lang in by_lang:
            return lang
    return max(by_lang, key=lambda lang: len(by_lang[lang]))


def chapters_rendered(sid: str):
    """A `ready` check for fetch_html: True once the HTML holds a real chapter
    list of this series (see _chapter_sets), not just the page shell's single
    "read first chapter" button."""
    def ready(html: str) -> bool:
        if not html or "<" not in html:
            return False
        return _has_list(_chapter_sets(BeautifulSoup(html, "html.parser"), sid)[0])
    return ready


def _link_order(hrefs: List[str], sid: str, lang: Optional[str]) -> str:
    """"desc" / "asc" / "mixed" / "n/a": the order chapter links appear in the page.
    Diagnostic only; nothing in the app depends on it."""
    nums: List[str] = []
    for found_lang, number in _chapter_links(hrefs, sid):
        if found_lang == lang and (not nums or nums[-1] != number):
            nums.append(number)
    if len(nums) < 2:
        return "n/a"
    keys = [chapters.key(n) for n in nums]
    if keys == sorted(keys, reverse=True):
        return "desc"
    return "asc" if keys == sorted(keys) else "mixed"


# Page details

def _clean_title(text: str) -> str:
    """Strip site boilerplate from a <title> / og:title style string. Returns ""
    for the site's own generic title, which every un-rendered page carries."""
    t = re.sub(r"\s*[-|\u2013]\s*MangaFire.*$", "", text or "", flags=re.IGNORECASE)
    t = re.sub(r"^Read\s+", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+Manga(?:\s+Online.*)?$", "", t, flags=re.IGNORECASE)
    t = t.strip()
    return "" if not t or _GENERIC_TEXT_RE.search(t) else t


def _labelled_value(soup: BeautifulSoup, label: str) -> str:
    """The value after a visible "Label: value" line such as "Author: Liu Mang, Mu Tou Ren".
    Takes the shortest match, which is the innermost element holding both label and value."""
    rx = re.compile(rf"^{label}s?\s*:\s*(.+)$", re.IGNORECASE)
    best = ""
    for el in soup.find_all(["p", "div", "li", "span", "dd", "td", "section"]):
        text = el.get_text(" ", strip=True)
        if len(text) > 300:
            continue
        m = rx.match(text)
        if m:
            value = re.sub(r"\s+([,;])", r"\1", m.group(1)).strip()
            if value and (not best or len(value) < len(best)):
                best = value
    return best


_CHROME_TAGS = {"nav", "footer", "aside", "form", "select", "menu"}
_CHROME_CLASS_RE = re.compile(r"(?:^|[\s_-])(?:nav|navbar|menu|sidebar|footer|filter|dropdown)(?:$|[\s_-])", re.IGNORECASE)


def _in_page_chrome(el) -> bool:
    """True for an element inside a menu, sidebar, footer or filter: links there
    (e.g. the site-wide genre list) say nothing about this series."""
    for node in [el] + list(el.parents):
        if getattr(node, "name", None) in _CHROME_TAGS:
            return True
        attrs = getattr(node, "attrs", None) or {}
        if _CHROME_CLASS_RE.search(" ".join(attrs.get("class") or []) + " " + str(attrs.get("id") or "")):
            return True
    return False


def _link_names(soup: BeautifulSoup, keyword: str) -> List[str]:
    """Texts of links whose URL contains `keyword` (author, genre), outside menus and sidebars."""
    return _names(", ".join(a.get_text(" ", strip=True) for a in soup.find_all("a", href=re.compile(keyword, re.I))
                            if not _in_page_chrome(a)))


def _sibling_value(soup: BeautifulSoup, label: str) -> str:
    """Value for a label that is its own element ("Author" / "Author:"), taken from
    the element that follows it (or follows its parent), however the row is built."""
    for el in soup.find_all(["span", "div", "dt", "p", "b", "strong", "label", "h3", "h4", "th", "td"]):
        if not re.fullmatch(rf"{label}s?\s*:?", el.get_text(" ", strip=True), re.IGNORECASE):
            continue
        for holder in (el, el.parent):
            sib = holder.find_next_sibling() if holder is not None else None
            text = re.sub(r"\s+([,;])", r"\1", sib.get_text(" ", strip=True)) if sib else ""
            if text and len(text) <= 150 and not _GENERIC_TEXT_RE.search(text) and ":" not in text:
                return text
    return ""


def _json_ld(soup: BeautifulSoup) -> List[dict]:
    """schema.org objects embedded in the page, flattened."""
    import json
    found: List[dict] = []

    def walk(node):
        if isinstance(node, dict):
            found.append(node)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            walk(json.loads(tag.string or tag.get_text() or ""))
        except ValueError:
            continue
    return found


def _ld_names(objects: List[dict], key: str) -> List[str]:
    out: List[str] = []
    for obj in objects:
        value = obj.get(key)
        items = value if isinstance(value, list) else [value]
        for item in items:
            name = item.get("name") if isinstance(item, dict) else item
            if isinstance(name, str):
                out.extend(_names(name))
    return [n for n in out if not _GENERIC_TEXT_RE.search(n)]


def _find_authors(soup: BeautifulSoup) -> List[str]:
    """Author names, from the most to the least structured source:
    links, itemprop, JSON-LD, "Author: ..." text, a label element + its sibling, <meta>."""
    names = _link_names(soup, "author")
    if not names:
        names = _names(", ".join(e.get_text(" ", strip=True) for e in soup.select('[itemprop="author"]')))
    if not names:
        names = _ld_names(_json_ld(soup), "author")
    if not names:
        names = _names(_labelled_value(soup, "Author"))
    if not names:
        names = _names(_sibling_value(soup, "Author"))
    if not names:
        meta = soup.find("meta", attrs={"name": "author"})
        names = [n for n in _names((meta or {}).get("content", "")) if not _GENERIC_TEXT_RE.search(n)]
    return names


def _find_genres(soup: BeautifulSoup) -> List[str]:
    links = _link_names(soup, "genre")
    if 0 < len(links) <= 12:                    # a longer run is a site-wide genre list, not this series'
        return links
    return (_ld_names(_json_ld(soup), "genre") or _names(_labelled_value(soup, "Genre"))
            or _names(_sibling_value(soup, "Genre")))


def _names(value: str) -> List[str]:
    out: List[str] = []
    for part in re.split(r"[,;]", value or ""):
        name = part.strip()
        if name and name not in out:
            out.append(name)
    return out


def _find_cover(soup: BeautifulSoup, title: str, page_url: str) -> str:
    og = soup.find("meta", attrs={"property": "og:image"})
    if og and og.get("content"):
        return urljoin(page_url, og["content"])

    def src_of(img) -> str:
        for attr in ("src", "data-src", "data-lazy-src"):
            v = (img.get(attr) or "").strip()
            if v and not v.startswith("data:"):
                return urljoin(page_url, v)
        return ""

    want = re.sub(r"\s+", " ", (title or "")).strip().lower()
    if want:                                    # a poster is usually captioned with the title
        for img in soup.find_all("img"):
            if re.sub(r"\s+", " ", img.get("alt") or "").strip().lower() == want and src_of(img):
                return src_of(img)
    for img in soup.find_all("img"):            # or sits in an element named poster/cover
        holders = [img] + list(img.parents)[:3]
        if any(re.search(r"poster|cover", " ".join(h.get("class") or []), re.IGNORECASE)
               for h in holders if getattr(h, "get", None)) and src_of(img):
            return src_of(img)
    return ""


def _find_synopsis(soup: BeautifulSoup) -> str:
    for sel in ('[itemprop="description"]', '[class*="synopsis"]', '[id*="synopsis"]', '[class*="description"]'):
        for el in soup.select(sel):
            text = re.sub(r"\s*(?:read|show|view)\s+more\s*$", "", el.get_text(" ", strip=True), flags=re.IGNORECASE)
            if len(text) >= 40 and not _GENERIC_TEXT_RE.search(text[:200]):
                return text
    return ""


def parse_page(html: str, sid: str, wanted_lang: Optional[str], result: ScraperResult,
               page_url: Optional[str] = None) -> ScraperResult:
    """Fill a ScraperResult from a MangaFire series page's HTML."""
    base = page_url or f"{BASE_URL}/title/{sid}"
    soup = BeautifulSoup(html, "html.parser")

    h1 = soup.find("h1")
    title = h1.get_text(" ", strip=True) if h1 else ""
    if not title:
        og = soup.find("meta", attrs={"property": "og:title"})
        title = _clean_title(og["content"]) if og and og.get("content") else ""
    if not title and soup.title and soup.title.string:
        title = _clean_title(soup.title.string)
    result.title = title

    result.cover_url = _find_cover(soup, title, base)
    result.synopsis = _find_synopsis(soup)

    result.author = ", ".join(_find_authors(soup))
    result.genres = _find_genres(soup)[:5]

    # Status is left empty on purpose: an empty status changes nothing on
    # refresh, whereas a wrong guess would overwrite your own status. The
    # site's filter menu uses the same words (Completed, Releasing, ...)
    # as a series' real status label, so text matching is not safe yet.
    result.status = ""

    by_lang, source = _chapter_sets(soup, sid)
    lang = _pick_language(by_lang, wanted_lang)
    nums = sorted(by_lang.get(lang, ()), key=chapters.key) if lang else []
    # A single entry is almost always the "read first chapter" button, not a list
    latest = nums[-1] if len(nums) >= 2 else None
    latest_source = source if latest else None
    if latest is None:                          # the site's own "latest chapter N" sentence
        m = _LATEST_SENTENCE_RE.search(soup.get_text(" ", strip=True))
        latest = chapters.parse_chapter(m.group(1)) if m else None
        latest_source = "page-sentence" if latest else None
    result.latest_chapter = latest
    result.chapter_list = []
    result.locked_list = []

    result.content_type = "manga"
    result.raw_data = {
        "url": base,
        "series_id": sid,
        "language": lang,
        "languages_found": sorted(by_lang),
        "chapter_links_found": len(nums),
        "latest_from": latest_source,
        "link_order": _link_order(_hrefs(soup), sid, lang),
    }
    result.success = bool(result.title)
    if not result.success:
        result.error_message = "Could not extract a title from MangaFire."
    return result


def save_debug_page(html: str) -> Optional[str]:
    """Keep the last fetched page in the logs folder so a bad parse can be inspected.
    Best effort: returns the path, or None if it couldn't be written."""
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        path = LOGS_DIR / DEBUG_PAGE_NAME
        path.write_text(html or "", encoding="utf-8")
        return str(path)
    except OSError:
        return None


class MangaFireScraper(BaseScraper):
    """Scraper for https://mangafire.to (manga, manhwa, manhua, one-shots)."""

    SOURCE_NAME = "mangafire"
    DOMAIN_PATTERNS = ["mangafire.to"]

    def canonical_page_url(self, url: str) -> str:
        parsed = canonical_url(url)
        return parsed[2] if parsed else (url or "").strip()

    def scrape(self, url: str) -> ScraperResult:
        result = ScraperResult(source_name=self.SOURCE_NAME, content_type="manga")
        parsed = canonical_url(url)
        if not parsed:
            result.error_message = (
                "Use a MangaFire series or chapter link, e.g. "
                "https://mangafire.to/title/zl363-lagg"
            )
            return result
        sid, lang, page_url = parsed

        try:
            html = self.fetch_series_html(sid, page_url)
        except FetchError as e:
            result.error_message = f"Scraping failed: {e}"
            return result

        saved = save_debug_page(html)
        parse_page(html, sid, lang, result, page_url)
        result.raw_data["saved_page"] = saved
        return result

    @staticmethod
    def fetch_series_html(sid: str, page_url: str) -> str:
        """The series page with its chapter list rendered (see module notes).
        Shared with tools/capture_mangafire.py so it exercises the same path."""
        return fetch_html(page_url, ready=chapters_rendered(sid))
