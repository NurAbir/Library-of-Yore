# Changelog

All notable changes to Library of Yore.

## [2.0.2] - 2026-09-28

Bug-fix release. No new features and no change to the library file format beyond one added field; 2.0.x libraries open as-is.

### Fixed
- **Library file could be corrupted by a background read.** The browser-extension API thread read `library.json` without the lock, through the same open file handle the app writes with. A read landing mid-save moved that shared handle and could leave the file truncated or with stale bytes at the end (invalid JSON), which the startup repair then "fixed" by rolling back to `library.json.bak`. `library.json` is now written atomically (temp file, then swapped into place), no file handle is shared, and every read and write goes through one lock. A regression test reproduces the old failure.
- **Editing a novel wiped fields the form doesn't show.** Every save from the Edit dialog reset **Date Added** to now and **Read Count** to 0, and dropped the cover's source URL and scrape info. Edits now change only the fields on the form. The cover file is only rewritten when you actually change the cover, and **Clear Cover** now deletes the old file instead of leaving it behind.
- **"Last Read" was set by every save**, including the startup auto-refresh and plain edits, so sorting by Last Read was scrambled on every launch. It now changes only on real reading progress: **+1**, the browser extension, or changing Current Chapter in the Edit dialog.
- **Auto-refresh overwrote your own status.** A novel you marked **Dropped** or **Planned** flipped back to the site's status (e.g. Ongoing) on the next launch. The site's status is now stored separately (`site_status`); your Dropped/Planned is never overwritten, while other statuses still follow the site (e.g. Ongoing → Completed) as before.
- **Wrong novel matched from a chapter URL.** The extension's URL matching compared raw string prefixes and looked for the stored slug anywhere in the path, so `/series/1` matched `/series/12/…`, and a slug like `2` matched any chapter URL containing the digit 2. Matching is now by whole path segments; the slug fallback ignores numeric ids and hex chapter tokens.
- **Title fallback was too loose.** It searched author and notes as well as titles and took whichever hit was read most recently. It now compares titles only, stays on the same site, and refuses to guess when two entries share a title (e.g. a novel and its manhwa).
- **Local API origin check.** `http://localhost.<anything>` passed the check meant for `http://localhost`. Origins are now matched exactly (extension origins, `localhost`, `127.0.0.1`), and progress updates must be sent as JSON, which stops an ordinary web page from firing a silent cross-site update.
- **Add/Edit dialog froze while downloading a cover.** Cover downloads now run in the background.
- **Search re-read the library and every cover file on each keystroke.** Search now waits for a short pause in typing, and cover images are cached in memory.
- **Keyboard shortcuts documented in the manual didn't exist.** Added **Ctrl+N** (Add Novel), **Ctrl+E** (Export), **Ctrl+R** / **F5** (Refresh). The manual's "Delete selected novel" shortcut was removed (the grid has no selection).
- About dialog listed Webnovel.com (removed long ago) and omitted three supported sites.
- The "still running in the tray" notification now shows once per session instead of on every close.

### Changed
- **Browser extension:** looks up a novel with one request carrying both the chapter URL and the title. **Auto-sync now only happens when the novel was matched by its URL**; a title-only match shows a note in the popup and waits for you to press Sync.
- **Startup auto-refresh** pauses 1.5 s between novels instead of requesting them back to back.
- The **+1** button now also counts toward Read Count, the same as an extension update.
- `source_name` is now set correctly for all five supported sites (Wuxiaworld, FreeWebNovel and NovelUpdates entries were saved as "manual").

### Added
- **Daily backups:** besides `library.json.bak` (the previous save), one dated snapshot per day is kept in `%LOCALAPPDATA%\LibraryOfYore\backups\`, newest 7.
- **Tests** (`tests/`, run with `python -m pytest tests`) covering storage concurrency, edit field preservation, status handling, URL/title matching and the API's origin and content-type checks.
- **`tools/check_version.py`:** fails if the version in `config.py`, the extension manifest, `installer.iss`, README, user manual and this changelog disagree. Both the tests and the version check now run in CI.

> Note: v2.0.1 was tagged on GitHub without a changelog entry.

## [2.0.0] - 2026-09-26

### Removed
- **MongoDB dependency.** The app no longer requires an external database server of any kind.

### Added
- **Local JSON storage.** Novels now live in `library.json` inside the app's data folder (`%LOCALAPPDATA%\LibraryOfYore\`), backed by TinyDB — same "insert/query a dict" model as before, just without a server to install or keep running. A `library.json.bak` snapshot is written before every save as a crash safety net.
- **Local cover images.** Cover files are now saved directly under a `covers\` folder next to `library.json`, instead of MongoDB's GridFS.
- **One-time MongoDB import.** On first launch, if a pre-2.0 MongoDB library is detected on the machine, an import wizard offers to copy every novel and cover image into the new local store before you continue — skippable, and safe to leave MongoDB uninstalled afterward. Also available any time from **File → Import Existing MongoDB Library…**.
- **New app logo/icon** — `assets/logo.png` and `assets/logo.ico` replaced with a new circular emblem (open book + archway design); the `.ico` was regenerated at the same six sizes as before (16/32/48/64/128/256) so the taskbar, window, and installer icons stay crisp.

### Changed
- `database/connection.py` and `database/models.py` rewritten around TinyDB + local cover files; `NovelRepository`'s public methods (`insert`, `update`, `delete`, `get_by_id`, `get_all`, `save_cover`, `get_cover`, `update_chapter_progress`, `export_to_list`) keep the same signatures, so the API server, Add/Edit dialog, and novel cards needed no changes.
- The first-run **Setup Wizard** is now an **Import Wizard** (`ui/setup_wizard.py`) — it no longer asks anyone to install or start anything; it only appears when an old MongoDB library is actually found.
- `requirements.txt` / `build.py` / `build.bat` / `build_release.bat`: added `tinydb`. `pymongo` and `gridfs` are kept for now, solely to power the one-time legacy import inside the built `.exe`.
- Version bumped to **2.0.0** (major bump reflecting the storage-engine change) across `config.py`, `installer.iss`, and the browser extension's `manifest.json`.

### Fixed
- Deleting a novel's cover image when replacing it in the Add/Edit dialog previously reached directly into the database layer (`self.repo.fs.delete(...)`) with a raw string id, which GridFS silently rejected. Replaced with a proper `NovelRepository.delete_cover()` method that actually removes the file.
- `library.json` writes now explicitly use UTF-8 (`database/connection.py`). Without this, TinyDB opens the file using the OS's default locale encoding — a legacy codepage like `cp1252` on many Windows machines — which cannot represent many characters that real scraped novel titles/authors/synopses contain (CJK, accented letters, smart quotes, emoji), crashing with `'charmap' codec can't encode character...`. This affected both normal saves and the MongoDB import wizard.
- An unreadable `library.json` (most commonly a file saved by a build with the encoding bug above, still holding raw `cp1252` bytes on Windows) no longer hard-crashes the app on every launch, and no longer requires re-importing from MongoDB either: startup now re-decodes it as `cp1252` and, if that parses cleanly, repairs it in place as proper UTF-8 — the exact same novels, losslessly. Only if that isn't possible does it fall back to the automatic `.bak` snapshot (repairing that the same way if needed), and only as a last resort does it quarantine the file as `library.json.broken-<timestamp>` so the app can at least start. The quarantine step also no longer claims success if the move itself fails (e.g. a locked file) — it now says so plainly instead.
- `ui/__init__.py` still imported the old `SetupWizard` name after it was renamed to `ImportWizard` — fixed.

## [1.5.0] - 2026-07-20

### Added
- **Screen-aware launch** — the app now detects the primary screen's available geometry on startup and opens maximized (windowed full-screen) to fill it, instead of a hardcoded 1300×850 window
- **Responsive grid** — the novel grid's column count is now computed from the actual scroll-viewport width and recalculated (debounced) on window resize, so the layout adapts whether you're on a small laptop screen or an ultrawide monitor
- **`ui/theme.py`** — a centralized design-system module (palette, radii, typography, shared QSS fragments) used by the main window, novel cards, Add Novel dialog, and setup wizard, so all four stay visually consistent going forward
- Refined dark theme: antique-gold accent on a charcoal-slate palette, drop-shadowed novel cards, a branded sidebar header, and a primary-styled "+ Add Novel" button

### Changed
- **List view removed** — the app now only offers the cover grid; the Grid/List toggle button and the `View → Grid View / List View` menu items have been removed
- First-run **setup wizard** now uses the shared dark theme (previously it had no styling at all and looked out of place next to the rest of the app)
- App version is now read from `config.APP_VERSION` everywhere (window title/about dialog, `main.py`, browser extension manifest, installer) instead of being hardcoded separately in each place

### Fixed
- **Version drift** — `config.py` reported `1.0.0`, the installer reported `1.4.0`, and the About dialog reported `v1.0`, all simultaneously; now a single source of truth
- **Tray restore bug** — reopening the window from the system tray called `showNormal()` unconditionally, silently un-maximizing it every time even if it had been maximized before being hidden
- **Fixed 5-column grid** — the novel grid previously always laid out 5 columns regardless of window size, wasting space on large screens and risking clipped/overlapping cards on narrow ones (the horizontal scrollbar is intentionally disabled); columns are now computed from the real available width
- Removed the orphaned `grid_view` config default, which was never actually read by the app

## [1.4.0] - 2026-07-10

### Added
- **NovelPhoenix.com scraper** (`scrapers/novelphoenix.py`) — NovelPhoenix runs on the same underlying site template as Novelfire, so this mirrors `novelfire.py`'s parsing strategy (title/author/cover/synopsis/status/genre selector cascade, chapter-count regex); registered in `scrapers/__init__.py` and added to PyInstaller hidden-imports in `build.bat`, `build_release.bat`, and `build.py`
- **Browser extension support for NovelPhoenix.com** — new detector in `content.js` matching NovelPhoenix's `/novel/{slug}/chapter-{N}` URL pattern (Novelfire uses `/book/{slug}/chapter-{N}` — similar but not identical); domain added to `manifest.json` content-script matches, `background.js`'s tab-tracking host list, and the popup's supported-sites badge list
- **`installer.iss` build-mode auto-detection** — the installer script now detects whether `dist\LibraryOfYore\LibraryOfYore.exe` (folder build) or `dist\LibraryOfYore.exe` (onefile build) exists and adapts automatically, instead of hardcoding one layout; a build living elsewhere can be pointed to manually with `ISCC.exe installer.iss /DMyDistDir=<folder containing LibraryOfYore.exe>`

### Changed
- Startup auto-refresh (previously Novelfire-only) now also re-scrapes NovelPhoenix novels in the background
- `add_novel_dialog.py` now tags novels added from a NovelPhoenix URL with `source_name = "novelphoenix"`
- `installer.iss`'s build-detection checks are now anchored to ISPP's `SourcePath` instead of plain relative paths

### Fixed
- **`AttributeError: module 'numpy' has no attribute 'short'` crash on startup** — `openpyxl`'s compat layer optionally imports `numpy` if present, but PyInstaller frequently bundles a broken/partial copy of it. Library of Yore never uses numpy directly, so `build.bat`, `build_release.bat`, and `build.py` now pass `--exclude-module numpy` (plus `pandas` and `matplotlib`, also unused) so `openpyxl` cleanly falls back to `NUMPY = False` instead of crashing on a half-imported module
- **`installer.iss` failing to find `LibraryOfYore.exe` when compiled standalone** — Inno Setup's preprocessor resolves relative `FileExists()` checks against the compiler's *current working directory*, not the script's own folder. This made the installer work when `build_release.bat` called `ISCC.exe` from the project root, but fail with a false "exe not found" error when the script was compiled on its own (e.g. via the Inno Setup IDE) from a different working directory
- `build.bat` and `build_release.bat` were each missing `--hidden-import scrapers.novelphoenix` — hidden imports are now consistent across all three build paths (`build.py`'s shared list, `build.bat`, `build_release.bat`)

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
