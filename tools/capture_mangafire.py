"""Capture a real MangaFire series page and show what the scraper makes of it.

    python tools/capture_mangafire.py https://mangafire.to/title/<id>-<slug>
    python tools/capture_mangafire.py <url> --html my_saved_page.html

(The app also keeps the last MangaFire page it fetched, as logs/mangafire_last_page.html in its data
folder, so this tool is only needed for a page the app can't load.)

Without --html it loads the page the same way the app does (plain request, then a
real browser: Microsoft Edge or Google Chrome must be installed). It saves the
HTML it got to tests/fixtures/mangafire_series.html, so the scraper can be tested
against a real page, and prints a report of what was extracted. Use --html to
report on a page you saved yourself (browser DevTools -> right-click <html> in
Elements -> Copy -> Copy outerHTML).
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bs4 import BeautifulSoup  # noqa: E402

from scrapers import mangafire as mf  # noqa: E402
from scrapers.base import FetchError, ScraperResult  # noqa: E402

DEFAULT_OUT = ROOT / "tests" / "fixtures" / "mangafire_series.html"


def pager_counts(soup: BeautifulSoup):
    """(links with ?page=N, elements with a pager-like class): hints that the chapter
    list is split into pages, in which case one render isn't the whole list."""
    return (len(soup.find_all("a", href=re.compile(r"[?&]page=\d", re.I))),
            len(soup.find_all(class_=re.compile(r"pagin|pager", re.I))))


def report(html: str, sid: str, lang, page_url: str) -> None:
    result = mf.parse_page(html, sid, lang, ScraperResult(source_name="mangafire"), page_url)
    soup = BeautifulSoup(html, "html.parser")
    by_lang, tier = mf._chapter_sets(soup, sid)
    raw = result.raw_data or {}

    print(f"\n--- What the scraper extracted from {page_url}")
    print(f"success:           {result.success}  {result.error_message}".rstrip())
    print(f"title:             {result.title!r}")
    print(f"cover:             {result.cover_url or '(none)'}")
    print(f"author:            {result.author or '(none)'}")
    print(f"genres:            {', '.join(result.genres) or '(none)'}")
    print("chapter links:     "
          + (", ".join(f"{k}: {len(v)}" for k, v in sorted(by_lang.items())) or "(none found)"))
    print(f"synopsis:          {(result.synopsis[:60] + '...') if result.synopsis else '(none)'}")
    print(f"chapters found by: {tier}")
    print(f"language used:     {raw.get('language')}")
    print(f"latest chapter:    {result.latest_chapter or '(unknown)'}  (from: {raw.get('latest_from')})")
    print(f"link order in page: {raw.get('link_order')}")
    paged_links, pager_boxes = pager_counts(soup)
    print(f"pager hints:       {paged_links} links with ?page=, {pager_boxes} elements with a pager-like class")

    notes = []
    if not by_lang:
        notes.append("No chapter links found: the list probably didn't render (bot check, or the "
                     "site's layout changed). The latest chapter will stay unknown.")
    elif result.latest_chapter is None:
        notes.append("Only one chapter link: treated as 'latest unknown'.")
    if raw.get("link_order") == "asc":
        notes.append("Links run oldest-first. If the list is paged, 'latest' may be the end of the "
                     "FIRST page, not the newest chapter. Compare it with the site.")
    if paged_links or pager_boxes:
        notes.append("The page shows pager markup, so one render may not hold every chapter.")
    if not result.title:
        notes.append("No title found.")
    for n in notes:
        print(f"NOTE: {n}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", help="a mangafire.to series or chapter link")
    ap.add_argument("--html", help="report on this saved HTML file instead of loading the page")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="where to save the captured HTML")
    args = ap.parse_args()

    parsed = mf.canonical_url(args.url)
    if not parsed:
        print("That doesn't look like a MangaFire series or chapter link, e.g. "
              "https://mangafire.to/title/zl363-lagg")
        return 2
    sid, lang, page_url = parsed

    if args.html:
        html = Path(args.html).read_text(encoding="utf-8", errors="replace")
        print(f"Read {len(html):,} characters from {args.html}")
    else:
        print(f"Loading {page_url} (plain request first, then a browser; this can take ~20 s)...")
        try:
            html = mf.MangaFireScraper.fetch_series_html(sid, page_url)
        except FetchError as e:
            print(f"\nCould not load the page: {e}\n"
                  "Make sure Microsoft Edge or Google Chrome is installed and `pip install playwright` "
                  "has been run. If the site keeps showing a verification page to automated browsers, "
                  "save the page yourself and use --html (see --help).")
            return 1
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
        print(f"Saved {len(html):,} characters to {out}")

    report(html, sid, lang, page_url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
