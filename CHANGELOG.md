# Changelog

All notable changes to Library of Yore.

## [1.0.1] - 2026-04-25

### Fixed
- **Chapter numbers with 4+ digits** (e.g. 2111) no longer truncate to the last 3 digits — `novelfire.py` was using `\d{1,3}` regex (max 3 digits); now uses the shared `_extract_chapter_number()` method from `BaseScraper` which handles any digit length
- **Read count never incremented** — `update_chapter_progress()` in `models.py` was nesting `$inc` inside `$set`, making MongoDB treat it as a literal field value; fixed to use `$inc` as a top-level update operator
- **`build.bat` missing hidden imports** — `database.connection` and `database.models` were absent, causing `ModuleNotFoundError` on launch of the built `.exe`
- **`build.py` inverted `--folder` flag** — passing `--folder` was triggering the single-file build and vice versa; logic corrected
- **`build.py` `build_folder()` missing hidden imports** — `scrapers.wuxiaworld`, `scrapers.freewebnovel`, `scrapers.novelupdates`, `database.connection`, `database.models` were absent from the folder build path
- **`build_release.bat` broken echo lines** — two pairs of `echo` statements were concatenated on one line, garbling console output
- **`installer.iss` build mode mismatch** — `[Files]` section pointed to `dist\LibraryOfYore.exe` (single-file) while `build_release.bat` uses `--onedir`; switched to folder-mode source line
- **`novelupdates.py` status fallback unreachable** — `if not result.status` was always `False` because `ScraperResult` initialises `status = "ongoing"`; replaced with a `status_found` flag

### Changed
- **`build.bat` now produces a single portable `.exe`** — switched from `--onedir` (folder + `_internal/`) to `--onefile`; output is `dist\LibraryOfYore.exe` with no extra files
- **`build.py` hidden imports unified** — both `build()` and `build_folder()` now share a single `COMMON_HIDDEN_IMPORTS` list to prevent future drift
- **`main.py` startup crash logging** — uncaught exceptions now write a full traceback to `crash_log.txt` next to the `.exe` and show an error dialog, making silent startup failures diagnosable

### Added
- Wuxiaworld.com scraper
- FreeWebNovel.com scraper
- NovelUpdates.com scraper

## [1.0.0] - 2026-04-24

### Added
- Initial release
- Visual library grid with cover images and progress bars
- Auto-scrape metadata from Novelfire.net
- Chapter tracking with +1 quick button
- Status management: Ongoing, Completed, Hiatus, Dropped, Planned
- Search, filter, and sort
- MongoDB GridFS cover storage
- Excel export
- Dark theme with gold/navy palette
- First-time MongoDB setup wizard
- Windows installer (Inno Setup)
