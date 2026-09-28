<div align="center">

<img src="assets/logo_icon.png" width="120" alt="Library of Yore Logo">

# Library of Yore

**A desktop bookmark tracker for web novels and manga.**

Built with Python and PyQt6 — stored locally, no database server required.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.4+-green.svg)](https://riverbankcomputing.com/software/pyqt)
[![Storage](https://img.shields.io/badge/Storage-Local%20JSON-lightgrey.svg)]()
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-2.1.0-orange.svg)](CHANGELOG.md)

</div>

---

## Description

**Library of Yore** is a desktop application for tracking your web novel and manga reading progress. Paste a novel or series URL and it automatically fetches the title, author, cover, synopsis, and latest chapter. Track where you left off, filter by status, and export your library to Excel.

A companion **browser extension** lets your reading progress update automatically as you read, on every supported reading site including **Flame Comics novels and manga**, even when the app window is closed, since Library of Yore runs quietly in the system tray.

Supports **Novelfire**, **NovelPhoenix**, **Wuxiaworld**, **FreeWebNovel**, **NovelUpdates**, and **Flame Comics** (web novels and manga).

---

## Features

| Feature | Description |
|---------|-------------|
| **Visual Library** | Responsive grid view with cover images, progress bars, and status badges — column count adapts to your window size |
| **Auto-Scrape Metadata** | Paste a URL and fetch title, author, cover, synopsis, and chapter count automatically |
| **Auto-Refresh on Startup** | Novelfire, NovelPhoenix and Flame Comics titles are silently re-scraped in the background when the app opens: latest chapter, chapter list, status, and synopsis update automatically |
| **Updated Badge** | Cards that received new data during auto-refresh show a gold ✦ Updated badge |
| **Chapter Tracking** | Decimal chapters (2.5, 0.01), a real "Not started" state, chapters behind, and completion %. Where the site's full chapter list is known (Flame Comics), +1 and progress follow that list, including gaps, chapter 0 and locked chapters |
| **Novels and Manga** | Each entry is a novel or a manga; a novel and its manhwa adaptation are tracked separately and never mixed up |
| **Status Management** | Ongoing, Completed, Hiatus, Dropped, Planned. Auto-refresh never overrides a novel you marked Dropped or Planned |
| **Search & Filter** | Filter by status, search by title/author/notes, sort by last read / rating / progress |
| **Cover Storage** | Images stored as local files — your entire library lives in one JSON file plus a covers folder, no server required |
| **Excel Export** | Export your entire library to `.xlsx` with one click |
| **Dark Theme** | Antique-gold accent on a charcoal slate palette — easy on the eyes for long reading sessions |
| **Opens Maximized** | Detects your screen size on launch and opens windowed full-screen, so you're never stuck with a cramped default window |
| **System Tray** | Closing the window hides the app to the tray — the API server keeps running in the background |
| **Browser Extension** | Auto-updates your chapter progress as you read on Novelfire, NovelPhoenix, Wuxiaworld, FreeWebNovel and Flame Comics (novels and manga), even with the window hidden |
| **Single-File Portable** | Distributes as one standalone `.exe` — no installation required |

---

## Supported Sites

| Site | Type | URL Example | Extension tracking | Auto-refresh | Full chapter list |
|------|------|-------------|:--:|:--:|:--:|
| [Novelfire](https://novelfire.net) | Novels | `https://novelfire.net/book/shadow-slave` | ✅ | ✅ | |
| [NovelPhoenix](https://novelphoenix.com) | Novels | `https://novelphoenix.com/novel/shadow-slave` | ✅ | ✅ | |
| [Wuxiaworld](https://www.wuxiaworld.com) | Novels | `https://www.wuxiaworld.com/novel/renegade-immortal` | ✅ | | |
| [FreeWebNovel](https://freewebnovel.com) | Novels | `https://freewebnovel.com/novel/lord-of-the-mysteries` | ✅ | | |
| [NovelUpdates](https://www.novelupdates.com) | Novels (catalog) | `https://www.novelupdates.com/series/lord-of-the-mysteries/` | | | |
| [Flame Comics](https://flamecomics.xyz) | Novels | `https://flamecomics.xyz/novel/8` | ✅ | ✅ | ✅ |
| [Flame Comics](https://flamecomics.xyz) | Manga / manhwa | `https://flamecomics.xyz/series/2` | ✅ | ✅ | ✅ |

- **Extension tracking:** the browser extension records the chapter you're reading. On Flame Comics it reads the chapter number from the page title and also catches chapter changes made with Flame's Previous/Next buttons, which don't reload the page.
- **Full chapter list:** the app stores every chapter the site lists, so **+1** follows the real list (2 → 2.5 → 3, gaps skipped), progress counts real chapters, and locked (paid) chapters are counted separately. Other sites use the next whole chapter.
- **Manga** are tracked for progress only (chapter pages aren't downloaded). A novel and its manhwa adaptation, such as ORV on Flame, are separate entries and never update each other.

---

## Browser Extension

The **Library of Yore Browser Extension** detects which chapter you are reading and automatically updates your progress in the app — no manual entry needed.

> **Download:** The extension is available in the [Releases](https://github.com/NurAbir/Library-of-Yore/releases) section of this repository. Look for `Library.of.Yore.Browser.Extension.zip` attached to the latest release.

### How It Works

1. Library of Yore runs a small local API server on `localhost:7337`
2. The extension watches the current tab and detects the chapter number, from the URL or, on Flame Comics, from the page title. It also notices chapter changes that happen without a page reload (Flame's Previous/Next buttons)
3. When you advance to a new chapter it sends the update to the app (with **Auto-sync** turned on in the popup's settings, and only for novels matched by their URL; otherwise press **Sync**)
4. The app writes it to your local library file and refreshes the card — even if the main window is hidden

### Background Tracking (System Tray)

You do **not** need to keep the Library of Yore window open. When you click the ✕ close button, the app hides itself to the **Windows system tray** instead of quitting. The API server stays alive in the background, so the extension keeps working normally.

| Tray Action | Result |
|-------------|--------|
| Single or double-click the tray icon | Reopens the main window |
| Right-click → **Open Library** | Reopens the main window |
| Right-click → **Quit** | Fully exits the app and stops the server |

A notification balloon appears the first time you close the window to let you know it is still running.

### Installing the Extension

**Chrome / Edge / Brave:**

1. Download and unzip `Library.of.Yore.Browser.Extension.zip` from the [Releases](https://github.com/NurAbir/Library-of-Yore/releases) page
2. Go to `chrome://extensions/` (or `edge://extensions/`)
3. Enable **Developer mode** (toggle, top-right)
4. Click **Load unpacked** and select the unzipped folder
5. The extension icon appears in your toolbar. Click it: a green dot means it's connected to the app

**Firefox:**

1. Go to `about:debugging#/runtime/this-firefox`
2. Click **Load Temporary Add-on**
3. Select the `manifest.json` file inside the unzipped folder

> Firefox temporary add-ons are removed on browser restart. For permanent install, the extension must be submitted to AMO or side-loaded via a policy.

---

## Requirements

- **Windows 10/11**
- **Python 3.10+** (development only — not needed to run the `.exe`)

No database server to install — everything is stored locally in a JSON file.

---

## Quick Start

### 1. Get Library of Yore

**Option A — Portable (Recommended)**
Download `LibraryOfYore.exe` from the [Releases](https://github.com/NurAbir/Library-of-Yore/releases) page. Drop it anywhere and run it. No installation needed.

**Option B — Installer**
Download `LibraryOfYore_Setup.exe` and run it to install to Program Files with a Start Menu shortcut.

### 2. First Launch

The main window opens immediately — there's nothing to install or configure first. Novelfire, NovelPhoenix and Flame Comics titles begin auto-refreshing in the background.

> **Upgrading to 2.1.0?** Your library is converted automatically on first launch (chapter 0 becomes "Not started"). Older versions can't open it afterwards; the dated copies in `backups\` are your way back.

> **Upgrading from a version before 2.0?** If Library of Yore finds an existing MongoDB library on your machine, it offers to import it automatically on first launch (or any time from **File → Import Existing MongoDB Library…**). See the [Changelog](CHANGELOG.md).

### 3. Install the Browser Extension (Optional)

Download `Library.of.Yore.Browser.Extension.zip` from the same [Releases](https://github.com/NurAbir/Library-of-Yore/releases) page and follow the [installation steps](#installing-the-extension) above.

See the [User Manual](USER_MANUAL.md) for detailed instructions.

---

## Development Setup

```bash
# Clone the repository
git clone https://github.com/NurAbir/Library-of-Yore
cd libraryofyore

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (needed for Novelfire fallback)
playwright install chromium

# Run the app
python main.py

# Run the tests
pip install pytest
python -m pytest tests
```

---

## Building from Source

```bash
# Build single-file portable .exe (default)
python build.py

# Build as folder — faster startup, useful for debugging
python build.py --folder

# Clean old build artifacts first
python build.py --clean

# Or just double-click the batch file
build.bat
```

> **Note:** `build.bat` produces a single `dist\LibraryOfYore.exe`. The first launch after a fresh build is ~2–4 seconds slower as PyInstaller extracts itself; subsequent launches are faster.

### Creating a Windows Installer (optional)

1. Install [Inno Setup 6](https://jrsoftware.org/isdl.php)
2. Run `build_release.bat` — it builds the exe and then calls Inno Setup automatically
3. Output: `installer\LibraryOfYore_Setup.exe`

---

## Project Structure

```
libraryofyore/
├── main.py                 # Entry point — also writes crash_log.txt on startup failure
├── api_server.py           # Local HTTP server (localhost:7337) for the browser extension
├── config.py               # App configuration, paths, asset loader
├── requirements.txt        # Python dependencies
├── build.py                # PyInstaller build script (--folder / default onefile)
├── build.bat               # One-click single-file portable build
├── build_release.bat       # Full automated build + Inno Setup installer
├── installer.iss           # Inno Setup installer config (folder-mode build)
├── .gitignore
├── LICENSE
├── README.md               # This file
├── USER_MANUAL.md          # Detailed user guide
│
├── assets/
│   ├── logo.png            # App logo
│   └── logo.ico            # Windows icon
│
├── Library of Yore Browser Extension/   # Browser extension source (also in Releases as a zip)
│   ├── manifest.json
│   ├── background.js
│   ├── content.js
│   ├── popup.html
│   ├── popup.css
│   ├── popup.js
│   └── icons/
│
├── database/
│   ├── connection.py       # Local JSON storage (TinyDB) singleton, write lock, auto-repair on read failure
│   ├── models.py           # Novel dataclass + NovelRepository (CRUD + local cover files)
│   └── legacy_mongo.py     # One-time MongoDB → local import, for pre-2.0 upgraders only
│
├── scrapers/
│   ├── __init__.py         # Scraper factory (get_scraper_for_url)
│   ├── base.py             # BaseScraper + ScraperResult dataclass
│   ├── novelfire.py        # Novelfire.net scraper (requests + Playwright fallback)
│   ├── novelphoenix.py     # NovelPhoenix.com scraper (requests + Playwright fallback)
│   ├── wuxiaworld.py       # Wuxiaworld.com scraper
│   ├── freewebnovel.py     # FreeWebNovel.com scraper
│   ├── novelupdates.py     # NovelUpdates.com scraper
│   └── flamecomics.py      # Flame Comics scraper (novels + manga, reads the page's embedded chapter data)
│
├── ui/
│   ├── setup_wizard.py     # Import Wizard — only shown if a pre-2.0 MongoDB library is found
│   ├── main_window.py      # Primary window (grid, sidebar, toolbar, system tray)
│   ├── novel_card.py       # Individual novel card widget
│   └── add_novel_dialog.py # Add/Edit novel with live scraping
│
├── utils/
│   ├── helpers.py          # Image download, resize, bytes-to-pixmap
│   └── chapters.py         # Chapter numbers, chapter-list ranges, progress (next / behind / %)
│
├── tests/                  # pytest suite: python -m pytest tests
└── tools/
    └── check_version.py    # Fails if the version differs between config.py, manifest, installer, docs
```

---

## Data Storage

All data is stored **locally** — nothing leaves your machine, and no database server is required.

| | |
|---|---|
| **Library file** | `%LOCALAPPDATA%\LibraryOfYore\library.json` — metadata, progress, reading history |
| **Cover images** | `%LOCALAPPDATA%\LibraryOfYore\covers\` — one file per novel cover |
| **Crash safety** | `library.json` is written atomically; `library.json.bak` holds the previous save |
| **Daily backups** | `%LOCALAPPDATA%\LibraryOfYore\backups\`: one dated snapshot per day, newest 7 kept |

**Backup:** Copy the entire `%LOCALAPPDATA%\LibraryOfYore\` folder.
**Restore:** Copy it back to the same location on any machine.
**Portable backup:** Use the Excel export feature.

> Upgrading from before 2.0? See [Quick Start](#quick-start) — Library of Yore can import your existing MongoDB library automatically.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Scraping fails | Site layout may have changed — use Manual Entry instead |
| Covers don't load | Check internet; try Fetch Metadata again |
| App won't start (no window) | Check `crash_log.txt` next to the `.exe` for the error |
| App settings corrupted | Delete `%LOCALAPPDATA%\LibraryOfYore\config.json` to reset |
| Library looks empty / won't load on startup | Since v2.0 this is repaired automatically on next launch (wrong-encoding files are fixed in place, then `.bak`, then quarantine as a last resort) — see [User Manual](USER_MANUAL.md#17-troubleshooting) if you see a message saying the automatic repair itself failed |
| Existing MongoDB library not detected | The import check only looks at `localhost:27017` (or a custom URI from an old `config.json`) — make sure MongoDB is still running the first time you launch 2.0, then use **File → Import Existing MongoDB Library…** |
| Chapters show wrong number | Update to v1.0.1+ — the 4-digit chapter bug is fixed |
| Extension shows "Disconnected" | Make sure Library of Yore is running (check the system tray) |
| Card not updating from extension | Confirm the novel's Source URL matches the site you are reading on, and that Auto-sync is on in the extension's settings |
| Flame Comics chapter not detected | Save the title with its main page URL (`/novel/N` for the novel, `/series/N` for the manga), and reload the extension after updating it. The novel and the manga are separate entries |
| Card shows chapters "behind" that I can't read for free | Locked (paid) chapters on Flame still count as behind; hover the card to see how many are locked |
| Synopsis shows "Summary..." prefix | Update to v1.3.0 — the leading label is now stripped automatically |
| `AttributeError: module 'numpy' has no attribute 'short'` on startup | Update to v1.4.0 — the build now excludes numpy/pandas/matplotlib, which openpyxl only used optionally and which PyInstaller was bundling incompletely |
| Compiling `installer.iss` says exe not found even though it's there | Update to v1.4.0 — the installer script now anchors its path checks to the script's own folder instead of the compiler's working directory |

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -am 'Add new feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

To add a new scraper site, inherit from `BaseScraper` in `scrapers/`, implement `scrape()`, and register it in `scrapers/__init__.py`.

See [CONTRIBUTING.md](CONTRIBUTING.md) for full details.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

---

## License

[MIT](LICENSE) — free to use, modify, and distribute.

---

<div align="center">

Made with care for readers everywhere.

</div>
