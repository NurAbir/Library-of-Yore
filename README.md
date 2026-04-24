<div align="center">

<img src="assets/logo.png" width="120" alt="Library of Yore Logo">

# Library of Yore

**A desktop bookmark tracker for web novels.**

Built with Python, PyQt6, and MongoDB.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.4+-green.svg)](https://riverbankcomputing.com/software/pyqt)
[![MongoDB](https://img.shields.io/badge/MongoDB-Community-brightgreen.svg)](https://mongodb.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## Features

| Feature | Description |
|---------|-------------|
| **Visual Library** | Grid view with cover images, progress bars, and status badges |
| **Auto-Scrape Metadata** | Paste a URL from Webnovel.com or Novelfire.net and fetch title, author, cover, synopsis, and chapter count automatically |
| **Chapter Tracking** | Track current chapter, total chapters, and completion percentage |
| **Status Management** | Ongoing, Completed, Hiatus, Dropped, Planned |
| **Search & Filter** | Filter by status, search by title/author/notes, sort by last read / rating / progress |
| **Cover Storage** | Images stored in MongoDB GridFS — your entire library is one database |
| **Excel Export** | Export your entire library to `.xlsx` with one click |
| **Dark Theme** | Gold and navy palette — easy on the eyes for long reading sessions |

---

## Screenshots

*(Add screenshots here once you have them)*

---

## Requirements

- **Windows 10/11**
- **MongoDB Community Server** (separate install)
- **Python 3.10+** (for development only)

---

## Quick Start

### 1. Install MongoDB

Download and install MongoDB Community Server:  
https://www.mongodb.com/try/download/community

During install, choose **"Install MongoDB as a Service"**.

### 2. Install Library of Yore

Download the latest release from [Releases](https://github.com/yourusername/libraryofyore/releases) and run `LibraryOfYore_Setup.exe`.

### 3. First Launch

On first run, the app checks `localhost:27017` for MongoDB.

- **Connected** → main window opens
- **Not found** → setup wizard guides you to download or start MongoDB

---

## Development Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/libraryofyore.git
cd libraryofyore

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Run the app
python main.py
```

---

## Building from Source

```bash
# Build standalone executable (folder mode recommended)
python build.py --folder

# Or single-file .exe
python build.py

# Create Windows installer (requires Inno Setup)
# Open installer.iss in Inno Setup Compiler and click Build
```

---

## Project Structure

```
libraryofyore/
├── main.py                 # Entry point
├── config.py               # App configuration, paths, asset loader
├── requirements.txt        # Python dependencies
├── build.py                # PyInstaller build script
├── installer.iss           # Inno Setup installer config
├── .gitignore              # Git ignore rules
├── LICENSE                 # MIT License
├── README.md               # This file
├── USER_MANUAL.md          # Detailed user guide
│
├── assets/
│   ├── logo.png            # App logo (PNG)
│   └── logo.ico            # Windows icon
│
├── database/
│   ├── connection.py       # MongoDB client + first-time setup
│   └── models.py           # Novel dataclass + NovelRepository (CRUD + GridFS)
│
├── scrapers/
│   ├── __init__.py         # Scraper factory
│   ├── base.py             # BaseScraper + ScraperResult
│   ├── webnovel.py         # Webnovel.com scraper (Playwright)
│   └── novelfire.py        # Novelfire.net scraper (requests + BS4 fallback)
│
├── ui/
│   ├── setup_wizard.py     # First-time MongoDB setup dialog
│   ├── main_window.py      # Primary window (grid, sidebar, toolbar)
│   ├── novel_card.py       # Individual novel card widget
│   └── add_novel_dialog.py # Add/Edit novel with live scraping
│
└── utils/
    └── helpers.py          # Image download, resize, bytes-to-pixmap
```

---

## Data Storage

All data is stored locally in your MongoDB instance:

| Database | `libraryofyore` |
|----------|----------------|
| **Collection** | `novels` — novel metadata, progress, history |
| **GridFS** | `covers.files` / `covers.chunks` — cover images |

Your data never leaves your machine. Backup with `mongodump` or export to Excel anytime.

---

## Supported Sites

| Site | Scraper Method | Notes |
|------|---------------|-------|
| [webnovel.com](https://www.webnovel.com) | Playwright (headless Chromium) | JavaScript-rendered SPA |
| [novelfire.net](https://novelfire.net) | requests + BeautifulSoup, Playwright fallback | Static HTML with JS hydration |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Cannot reach MongoDB server" | Start the service: `net start MongoDB` in admin CMD |
| Scraping fails | The site may have changed. Use manual entry or report an issue |
| Covers don't load | Check internet connection; covers download on first fetch |
| App won't start | Delete `%LOCALAPPDATA%\LibraryOfYore\config.json` to reset |

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -am 'Add new feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

---

## License

[MIT](LICENSE) — free to use, modify, and distribute.

---

<div align="center">

Made with for readers everywhere.

</div>