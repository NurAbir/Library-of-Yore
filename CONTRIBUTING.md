# Contributing to Library of Yore

Thank you for your interest in contributing!

## How to Contribute

### Reporting Bugs

1. Check if the issue already exists
2. Open a new issue with:
   - Clear title
   - Steps to reproduce
   - Expected vs actual behavior
   - Screenshots if applicable
   - Windows version and app version

### Suggesting Features

1. Open a GitHub Discussion or Issue
2. Describe the feature and why it would be useful
3. Mockups or examples are welcome

### Code Contributions

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Test locally: `python main.py`, and run the test suite: `pip install pytest`, then `python -m pytest tests`
5. Commit with clear messages
6. Push and open a Pull Request

### Code Style

- Follow PEP 8
- Use type hints where practical
- Add docstrings to public functions
- Keep UI code separate from business logic

### Adding a New Scraper

To add support for a new novel site:

1. Create `scrapers/yoursite.py`
2. Inherit from `BaseScraper`
3. Implement `scrape(self, url) -> ScraperResult`. Load pages with `fetch_html()` / `fetch_json()` from `scrapers/base.py`: they try a plain request first and fall back to a real browser (Edge, Chrome or Playwright's Chromium) when a site blocks it
4. Add to `scrapers/__init__.py` factory, and add `--hidden-import scrapers.yoursite` to `build.py`, `build.bat` and `build_release.bat`
5. Chapter numbers are strings, never floats: set `result.latest_chapter` with `utils.chapters.parse_chapter(...)` (e.g. `"621"`, `"2.5"`)
6. If the site lists every chapter, also fill `result.chapter_list` (and `result.locked_list` for paid chapters) so progress follows the real list. For a manga site, set `result.content_type = "manga"`. `scrapers/flamecomics.py` is the reference for both
7. Add tests in `tests/` using a saved copy of a real page, and test with real URLs
8. For live tracking, add a detector for the site in the browser extension's `content.js`, its domain to `manifest.json` and `background.js`. If the site changes chapters without reloading the page (like Flame Comics), the existing watcher in `content.js` already handles that

Example:

```python
from scrapers.base import BaseScraper, ScraperResult
from utils.chapters import parse_chapter

class MySiteScraper(BaseScraper):
    SOURCE_NAME = "mysite"
    DOMAIN_PATTERNS = ["mysite.com", "mysite.net"]

    def scrape(self, url: str) -> ScraperResult:
        result = ScraperResult(source_name=self.SOURCE_NAME)
        # ... scraping logic ...
        result.latest_chapter = parse_chapter("621")   # a string, e.g. "621" or "2.5"
        result.success = True
        return result
```

## Development Setup

See [README.md](README.md) for full setup instructions.

## Questions?

Open a GitHub Discussion.
