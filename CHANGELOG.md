# Changelog

All notable changes to Library of Yore.

## [1.3.0] - 2026-05-22

### Added
- **Auto-refresh on startup** — all Novelfire novels are silently re-scraped in a background thread when the app opens; latest chapter count, status, and synopsis are written to the database and reflected on cards immediately, with no UI blocking
- **✦ Updated badge** — cards that received new data during auto-refresh display a gold badge in the top-right corner of their cover image for the duration of the session
- **`NovelRefreshWorker` (QThread)** — dedicated background worker that drives the startup refresh; emits `novel_updated(novel_id, total_chapters, status, synopsis)` per novel and `finished(count)` when done; status bar shows progress and completion message
- **`update_status()` on `NovelCard`** — updates the status badge label and colour in place without rebuilding the card
- **`update_latest_chapter()` on `NovelCard`** — updates total chapters and recalculates the progress bar percentage live
- **`mark_updated()` on `NovelCard`** — shows the gold ✦ Updated badge overlay

### Fixed
- **Synopsis shows "Summary..." prefix** — `novelfire.py` now strips any leading `Summary`, `Description`, or `Synopsis` label (with or without a colon) from the scraped synopsis text
- **Synopsis includes "Show More" button text** — trailing `Show More`, `Show Less`, `Read More`, and `...more` strings are stripped from the synopsis after extraction
- **Novel status detected incorrectly** — status is now extracted using targeted CSS selectors (`.status`, `.novel-status`, `.label-status`, etc.) rather than scanning the entire page text, preventing synopsis words like "completed his journey" from false-matching as a Completed status
- **"Title is required" fires before the form is filled** — `keyPressEvent` is now overridden on the Add Novel dialog to fully block Enter/Return from triggering any button; Enter in the Source URL field still triggers Fetch Metadata via `returnPressed`
- **`QMessageBox` confirmation after scrape leaks Enter key to Save** — the blocking information pop-up after a successful scrape has been replaced with an inline green status label below the URL field
- **`setDefault(True)` / `autoDefault` on dialog buttons** — `setDefault` removed and `setAutoDefault(False)` applied to all seven buttons in the Add Novel dialog as a secondary safeguard

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
