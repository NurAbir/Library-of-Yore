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
4. Test locally: `python main.py`
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
3. Implement `scrape(self, url) -> ScraperResult`
4. Add to `scrapers/__init__.py` factory
5. Test with real URLs

Example:

```python
from scrapers.base import BaseScraper, ScraperResult

class MySiteScraper(BaseScraper):
    SOURCE_NAME = "mysite"
    DOMAIN_PATTERNS = ["mysite.com", "mysite.net"]

    def scrape(self, url: str) -> ScraperResult:
        result = ScraperResult(source_name=self.SOURCE_NAME)
        # ... scraping logic ...
        result.success = True
        return result
```

## Development Setup

See [README.md](README.md) for full setup instructions.

## Questions?

Open a GitHub Discussion.
