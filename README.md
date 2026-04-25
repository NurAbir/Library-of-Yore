<div align="center">

<img src="assets/logo.png" width="120" alt="Library of Yore Logo">

# Library of Yore

**A desktop bookmark tracker for web novels.**

Built with Python, PyQt6, and MongoDB.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.4+-green.svg)](https://riverbankcomputing.com/software/pyqt)
[![MongoDB](https://img.shields.io/badge/MongoDB-Community-brightgreen.svg)](https://mongodb.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.1.0-orange.svg)](CHANGELOG.md)

</div>

---

## Description

**Library of Yore** is a desktop application for tracking your web novel reading progress. Paste a novel URL and it automatically fetches the title, author, cover, synopsis, and chapter count. Track where you left off, filter by status, and export your library to Excel.

A companion **browser extension** lets your reading progress update automatically as you read — even when the app window is closed, since Library of Yore runs quietly in the system tray.

Supports **Novelfire**, **Wuxiaworld**, **FreeWebNovel**, and **NovelUpdates**.

---

## Features

| Feature | Description |
|---------|-------------|
| **Visual Library** | Grid view with cover images, progress bars, and status badges |
| **Auto-Scrape Metadata** | Paste a URL and fetch title, author, cover, synopsis, and chapter count automatically |
| **Chapter Tracking** | Track current chapter, total chapters, and completion percentage |
| **Status Management** | Ongoing, Completed, Hiatus, Dropped, Planned |
| **Search & Filter** | Filter by status, search by title/author/notes, sort by last read / rating / progress |
| **Cover Storage** | Images stored in MongoDB GridFS — your entire library is one database |
| **Excel Export** | Export your entire library to `.xlsx` with one click |
| **Dark Theme** | Gold and navy palette — easy on the eyes for long reading sessions |
| **System Tray** | Closing the window hides the app to the tray — the API server keeps running in the background |
| **Browser Extension** | Auto-updates your chapter progress as you read — works even with the window hidden |
| **Single-File Portable** | Distributes as one standalone `.exe` — no installation required |

---

## Supported Sites

| Site | URL Example |
|------|-------------|
| [Novelfire](https://novelfire.net) | `https://novelfire.net/book/shadow-slave` |
| [Wuxiaworld](https://www.wuxiaworld.com) | `https://www.wuxiaworld.com/novel/renegade-immortal` |
| [FreeWebNovel](https://freewebnovel.com) | `https://freewebnovel.com/novel/lord-of-the-mysteries` |
| [NovelUpdates](https://www.novelupdates.com) | `https://www.novelupdates.com/series/lord-of-the-mysteries/` |

---

## Browser Extension

The **Library of Yore Browser Extension** detects which chapter you are reading and automatically updates your progress in the app — no manual entry needed.

> **Download:** The extension is available in the [Releases](https://github.com/NurAbir/Library-of-Yore/releases) section of this repository. Look for `Library.of.Yore.Browser.Extension.zip` attached to the latest release.

### How It Works

1. Library of Yore runs a small local API server on `localhost:7337`
2. The extension watches the current tab URL and detects chapter numbers
3. When you advance to a new chapter it sends the update to the app
4. The app writes it to MongoDB and refreshes the card — even if the main window is hidden

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
5. The extension icon appears in your toolbar — click it to confirm it shows **Connected**

**Firefox:**

1. Go to `about:debugging#/runtime/this-firefox`
2. Click **Load Temporary Add-on**
3. Select the `manifest.json` file inside the unzipped folder

> Firefox temporary add-ons are removed on browser restart. For permanent install, the extension must be submitted to AMO or side-loaded via a policy.

---

## Requirements

- **Windows 10/11**
- **MongoDB Community Server** (separate install — see [Quick Start](#quick-start))
- **Python 3.10+** (development only — not needed to run the `.exe`)

---

## Quick Start

### 1. Install MongoDB

Download and install MongoDB Community Server:
https://www.mongodb.com/try/download/community

During install, choose **"Install MongoDB as a Service"** so it starts automatically with Windows.

### 2. Get Library of Yore

**Option A — Portable (Recommended)**
Download `LibraryOfYore.exe` from the [Releases](https://github.com/NurAbir/Library-of-Yore/releases) page. Drop it anywhere and run it. No installation needed.

**Option B — Installer**
Download `LibraryOfYore_Setup.exe` and run it to install to Program Files with a Start Menu shortcut.

### 3. First Launch

On first run, the app checks `localhost:27017` for MongoDB.

- **Connected** → main window opens immediately
- **Not found** → setup wizard guides you to download or start MongoDB

### 4. Install the Browser Extension (Optional)

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
│   ├── connection.py       # MongoDB client singleton + connection test
│   └── models.py           # Novel dataclass + NovelRepository (CRUD + GridFS)
│
├── scrapers/
│   ├── __init__.py         # Scraper factory (get_scraper_for_url)
│   ├── base.py             # BaseScraper + ScraperResult dataclass
│   ├── novelfire.py        # Novelfire.net scraper (requests + Playwright fallback)
│   ├── wuxiaworld.py       # Wuxiaworld.com scraper
│   ├── freewebnovel.py     # FreeWebNovel.com scraper
│   └── novelupdates.py     # NovelUpdates.com scraper
│
├── ui/
│   ├── setup_wizard.py     # First-time MongoDB setup dialog
│   ├── main_window.py      # Primary window (grid, sidebar, toolbar, system tray)
│   ├── novel_card.py       # Individual novel card widget
│   └── add_novel_dialog.py # Add/Edit novel with live scraping
│
└── utils/
    └── helpers.py          # Image download, resize, bytes-to-pixmap
```

---

## Data Storage

All data is stored **locally** in your MongoDB instance — nothing leaves your machine.

| | |
|---|---|
| **Database** | `libraryofyore` |
| **Collection** | `novels` — metadata, progress, reading history |
| **GridFS** | `covers.files` / `covers.chunks` — cover images |

**Backup:** `mongodump --db libraryofyore --out C:\backup\`
**Restore:** `mongorestore --db libraryofyore C:\backup\libraryofyore\`
**Portable backup:** Use the Excel export feature.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Cannot reach MongoDB server" | Run `net start MongoDB` in an admin Command Prompt |
| Scraping fails | Site layout may have changed — use Manual Entry instead |
| Covers don't load | Check internet; try Fetch Metadata again |
| App won't start (no window) | Check `crash_log.txt` next to the `.exe` for the error |
| App settings corrupted | Delete `%LOCALAPPDATA%\LibraryOfYore\config.json` to reset |
| Chapters show wrong number | Update to v1.0.1+ — the 4-digit chapter bug is fixed |
| Extension shows "Disconnected" | Make sure Library of Yore is running (check the system tray) |
| Card not updating from extension | Confirm the novel's Source URL matches the site you are reading on |

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
