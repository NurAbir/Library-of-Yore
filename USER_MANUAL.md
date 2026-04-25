# Library of Yore — User Manual

**Version 1.2.0**

A complete guide to installing, using, and troubleshooting Library of Yore — your personal desktop web novel tracker.

---

## Table of Contents

1. [System Requirements](#1-system-requirements)
2. [Installing MongoDB](#2-installing-mongodb)
3. [Installing Library of Yore](#3-installing-library-of-yore)
4. [First Launch & Setup Wizard](#4-first-launch--setup-wizard)
5. [Adding a Novel](#5-adding-a-novel)
6. [The Main Library](#6-the-main-library)
7. [Editing a Novel](#7-editing-a-novel)
8. [Tracking Reading Progress](#8-tracking-reading-progress)
9. [Browser Extension](#9-browser-extension)
10. [System Tray & Background Mode](#10-system-tray--background-mode)
11. [Search, Filter & Sort](#11-search-filter--sort)
12. [Exporting Your Library](#12-exporting-your-library)
13. [Settings & Configuration](#13-settings--configuration)
14. [Data Backup & Migration](#14-data-backup--migration)
15. [Building from Source](#15-building-from-source)
16. [Troubleshooting](#16-troubleshooting)
17. [Keyboard Shortcuts](#17-keyboard-shortcuts)
18. [FAQ](#18-faq)

---

## 1. System Requirements

| Component | Minimum |
|-----------|---------|
| **OS** | Windows 10 or Windows 11 (64-bit) |
| **RAM** | 4 GB (8 GB recommended) |
| **Storage** | 200 MB for the app + space for cover images |
| **Internet** | Required for scraping metadata and downloading covers |
| **Database** | MongoDB Community Server (free, separate install) |
| **Browser** | Chrome, Edge, Brave, or Firefox (for the browser extension) |

Python is **not** required to run the portable `.exe` or the installer build.

---

## 2. Installing MongoDB

Library of Yore uses MongoDB as its local database. Your data never leaves your machine.

### Steps

1. Go to: https://www.mongodb.com/try/download/community
2. Download the **MongoDB Community Server MSI** for Windows
3. Run the installer
4. On the **Service Configuration** screen, check **"Install MongoDB as a Service"**
   - This makes MongoDB start automatically every time Windows boots
5. Complete the installation

### Verify MongoDB is Running

Open Command Prompt as Administrator and run:

```cmd
net start MongoDB
```

You will see one of two responses:

| Response | Meaning |
|----------|---------|
| `The MongoDB Server service is starting` | Starting now — wait a moment |
| `The requested service has already been started` | Already running — you're good |
| `The service name is invalid` | MongoDB is not installed as a service — reinstall and check the Service option |

### If You Need a Custom Port

By default MongoDB runs on port `27017`. If you need a different port, update the connection string in Settings after launch (see [Section 13](#13-settings--configuration)).

---

## 3. Installing Library of Yore

### Option A — Portable Executable (Recommended)

The portable version is a **single `.exe` file** — no installer, no admin rights needed.

1. Download `LibraryOfYore.exe` from the [Releases](https://github.com/NurAbir/Library-of-Yore/releases) page
2. Place it anywhere (Desktop, a USB drive, a folder of your choice)
3. Double-click to run

> **First launch note:** The first time you open the portable exe it takes 3–5 seconds to unpack itself. Every launch after that is faster.

If the app crashes silently on startup, look for a file called `crash_log.txt` in the same folder as the `.exe`. It contains the full error message.

### Option B — Windows Installer

1. Download `LibraryOfYore_Setup.exe` from the [Releases](https://github.com/NurAbir/Library-of-Yore/releases) page
2. Double-click and follow the wizard
3. Launch from the Start Menu or the optional Desktop shortcut

---

## 4. First Launch & Setup Wizard

On the very first launch, Library of Yore checks for MongoDB at `localhost:27017`.

### If MongoDB is Found

The main window opens immediately. Skip ahead to [Section 5](#5-adding-a-novel).

### If MongoDB is Not Found

The **Setup Wizard** appears. It offers the following actions:

| Button | What It Does |
|--------|--------------|
| **Download MongoDB** | Opens the official MongoDB download page in your browser |
| **Start MongoDB Service** | Tries to start the MongoDB Windows service right now |
| **Retry Connection** | Tests the connection again after you've started MongoDB |
| **Change URI** | Edit the connection string (useful for non-default ports or remote hosts) |
| **Continue** | Proceed once the connection test passes |

**Common fix:** Click **Start MongoDB Service**, wait 5 seconds, then click **Retry Connection**.

---

## 5. Adding a Novel

Click **Add Novel** in the toolbar to open the Add Novel dialog.

### Method 1 — Auto-Scrape from URL (Recommended)

This is the fastest way to add a novel with full metadata.

1. Paste the novel's page URL into the **Source URL** field
2. Click **Fetch Metadata**
3. Wait a few seconds (the app downloads the page and extracts data)
4. The following fields fill in automatically:
   - Title
   - Author
   - Cover image
   - Total chapters (supports any number, including 1000+ chapter series)
   - Synopsis
   - Genres
   - Status (Ongoing / Completed / Hiatus)
5. Enter your **Current Chapter** — where you left off
6. Adjust any fields if needed
7. Click **Save Novel**

**Supported URLs:**

| Site | Example URL |
|------|-------------|
| Novelfire | `https://novelfire.net/book/shadow-slave` |
| Wuxiaworld | `https://www.wuxiaworld.com/novel/renegade-immortal` |
| FreeWebNovel | `https://freewebnovel.com/novel/lord-of-the-mysteries` |
| NovelUpdates | `https://www.novelupdates.com/series/lord-of-the-mysteries/` |

> **Note:** NovelUpdates is a catalog site. It provides metadata but does not host chapters directly.

### Method 2 — Manual Entry

Use this when a site isn't supported or scraping fails.

1. Click **Add Novel**
2. Leave the URL field empty (or fill it as a reference link)
3. Fill in:
   - **Title** *(required)*
   - Author
   - Current chapter / Total chapters
   - Status, Rating, Genres
   - Synopsis and personal Notes
4. Optionally add a cover (see below)
5. Click **Save Novel**

### Cover Images

| Method | How |
|--------|-----|
| **Auto** | Fetched automatically when you use Fetch Metadata |
| **From File** | Click **Load from File** and pick a `.jpg`, `.png`, `.webp`, or `.bmp` |
| **From URL** | Click **Download from URL** and paste a direct image link |
| **Clear** | Click **Clear Cover** to remove the current image |

All covers are stored inside MongoDB (GridFS) — they travel with your database backup.

---

## 6. The Main Library

The main window has three sections.

### Left Sidebar

| Control | Purpose |
|---------|---------|
| **Search box** | Filter by title, author, or notes content |
| **Status checkboxes** | Show/hide novels by status |
| **Sort By dropdown** | Change the ordering of results |

### Top Toolbar

| Button | Action |
|--------|--------|
| **Add Novel** | Open the Add Novel dialog |
| **Grid / List** | Toggle between cover grid and compact list view |
| **Export Excel** | Save your full library to a `.xlsx` spreadsheet |
| **Refresh** | Reload novels from the database |

### Novel Cards (Grid View)

Each novel card shows:

- **Cover image** (or a "No Cover" placeholder)
- **Title**
- **Status badge** — color coded:

| Color | Status |
|-------|--------|
| Blue | Ongoing |
| Gold | Completed |
| Orange | Hiatus |
| Red | Dropped |
| Purple | Planned |

- **Chapter** (current / total)
- **Progress bar** with completion percentage

### Card Actions

| Action | How |
|--------|-----|
| Open full details / edit | Left-click the card |
| Increment chapter by 1 | Click the **+1** button on the card |
| Open source URL in browser | Click the **Link** button |
| Edit or Delete | Right-click for context menu |

---

## 7. Editing a Novel

1. Left-click any card, or right-click → **Edit**
2. The Edit dialog opens pre-filled with all current data
3. Change whatever you need:
   - Chapter progress
   - Status, rating, notes
   - Cover image
   - Title, author, synopsis
4. Click **Save Novel**

To delete a novel: right-click its card → **Delete**. This also removes its cover image from GridFS.

---

## 8. Tracking Reading Progress

### Updating Your Chapter

**Quick (one click):** Click the **+1** button on any card. The chapter count increments and the last-read timestamp updates.

**Precise:** Open the novel → change the **Current Chapter** number → Save.

**Automatic (browser extension):** If you have the browser extension installed, your chapter updates as you read in the browser — see [Section 9](#9-browser-extension).

### Progress Indicators

| Indicator | Meaning |
|-----------|---------|
| Progress bar | Visual fill: `current ÷ total` |
| Percentage | Exact completion % |
| "Up to date" | Current chapter equals total chapters |

### Reading History

Every save records:
- **Last Read** — the timestamp of your latest update
- **Read Count** — total number of times you've updated the novel

Sort by **Last Read** to jump back to whatever you were reading most recently.

---

## 9. Browser Extension

The **Library of Yore Browser Extension** tracks the chapter you are reading in your browser and automatically updates your progress in the app — no clicking +1, no manual entry.

> **Download:** The extension is available in the [Releases](https://github.com/NurAbir/Library-of-Yore/releases) section on GitHub. Download `Library.of.Yore.Browser.Extension.zip` from the latest release.

### How It Works

The extension communicates with Library of Yore through a small local API server the app runs on `localhost:7337`. When you navigate to a new chapter, the extension:

1. Reads the current page URL
2. Matches it against the novels stored in your library by domain and URL slug
3. Extracts the chapter number from the URL or page content
4. Sends a progress update to the app if the chapter is newer than what is stored
5. The app updates the card immediately — chapter label, progress bar, and percentage all refresh in real time

The card updates **live** even if the main window is hidden in the system tray.

### Installing the Extension

**Chrome, Edge, or Brave:**

1. Download and unzip `Library.of.Yore.Browser.Extension.zip` from the [Releases](https://github.com/NurAbir/Library-of-Yore/releases) page
2. Open your browser and go to:
   - Chrome: `chrome://extensions/`
   - Edge: `edge://extensions/`
   - Brave: `brave://extensions/`
3. Turn on **Developer mode** using the toggle in the top-right corner
4. Click **Load unpacked**
5. Select the unzipped `Library of Yore Browser Extension` folder
6. The Library of Yore icon appears in your browser toolbar

**Firefox:**

1. Go to `about:debugging#/runtime/this-firefox`
2. Click **Load Temporary Add-on**
3. Browse into the unzipped folder and select `manifest.json`

> **Firefox note:** Temporary add-ons are removed when Firefox restarts. For a permanent install the extension would need to be submitted to Mozilla Add-ons (AMO).

### Checking the Connection

Click the extension icon in your browser toolbar. The popup shows:

| Status | Meaning |
|--------|---------|
| 🟢 **Connected** | Library of Yore is running and the API server is reachable |
| 🔴 **Disconnected** | The app is not running — launch Library of Yore first |

### Matching Novels

For the extension to update a novel, that novel must be saved in your library with a **Source URL** that matches the site you are reading on. The extension matches by domain and URL path — for example, if you saved `https://novelfire.net/book/shadow-slave`, reading any chapter URL under that path will be recognised as the same novel.

If a novel is not being detected, open the Edit dialog and confirm the Source URL is set to the novel's main page on the supported site.

---

## 10. System Tray & Background Mode

Library of Yore is designed to run quietly in the background so the browser extension always has somewhere to send updates — even when you are not actively using the app.

### Hiding to the Tray

When you click the **✕ close button** on the main window, the app does **not** quit. Instead it hides to the Windows system tray (bottom-right corner of the taskbar, near the clock). The API server keeps running, so the browser extension continues working normally.

The first time you close the window, a notification balloon appears:

> *"Still tracking in the background. Right-click the tray icon to quit."*

### Tray Icon Actions

| Action | Result |
|--------|--------|
| **Single-click** the tray icon | Reopens the main window |
| **Double-click** the tray icon | Reopens the main window |
| **Right-click → Open Library** | Reopens the main window |
| **Right-click → Quit** | Fully exits the app, stops the API server, and closes the MongoDB connection |

### Fully Quitting

To stop Library of Yore completely, right-click its icon in the system tray and choose **Quit**. Simply closing the window is not enough — that only hides it.

### Starting with Windows (Optional)

If you want Library of Yore to launch automatically on login so the extension is always ready:

1. Press `Win + R`, type `shell:startup`, press Enter
2. Create a shortcut to `LibraryOfYore.exe` in that folder

The app will start minimised to the tray on each login.

---

## 11. Search, Filter & Sort

### Search

Type in the search box (left sidebar). Matches novels where the search text appears in the **title**, **author**, or **notes** fields. Case-insensitive. Updates instantly as you type.

### Filter by Status

Toggle the checkboxes to show or hide novels in each status:

- ✅ Ongoing
- ✅ Completed
- ✅ Hiatus
- ✅ Dropped
- ✅ Planned

Only checked statuses are displayed.

### Sort Options

| Option | Order |
|--------|-------|
| **Last Read** | Most recently updated first |
| **Title** | A → Z alphabetical |
| **Rating** | Highest rated first |
| **Date Added** | Newest additions first |
| **Progress %** | Most complete first |

---

## 12. Exporting Your Library

Click **Export Excel** in the toolbar. Choose a save location. The file opens in Excel or any spreadsheet app.

### Exported Columns

| Column | Description |
|--------|-------------|
| Title | Novel title |
| Author | Author name |
| Status | ongoing / completed / hiatus / dropped / planned |
| Current Chapter | Your last read chapter |
| Total Chapters | Known total (blank if unknown) |
| % Complete | Calculated completion percentage |
| Source URL | Link to the novel page |
| Source | novelfire / wuxiaworld / freewebnovel / novelupdates / manual |
| Last Read | ISO 8601 timestamp |
| Date Added | When you first added it |
| Rating | Your 0–10 rating |
| Genres | Comma-separated |
| Notes | Your personal notes |

### Uses

- Human-readable backup outside MongoDB
- Share your reading list
- Analyse your reading history in Excel/Sheets
- Reference when setting up on a new machine

---

## 13. Settings & Configuration

Settings are saved to:

```
%LOCALAPPDATA%\LibraryOfYore\config.json
```

Open this file in any text editor to edit manually.

### Available Settings

| Key | Default | Description |
|-----|---------|-------------|
| `mongo_uri` | `mongodb://localhost:27017` | MongoDB connection string |
| `db_name` | `libraryofyore` | Database name |
| `theme` | `dark` | UI colour theme |
| `window_size` | `[1200, 800]` | Saved window size |
| `default_sort` | `last_read` | Default sort field |
| `grid_view` | `true` | Start in grid view if true, list view if false |

### Reset to Defaults

Delete `config.json` and restart the app. It recreates the file with all defaults.

---

## 14. Data Backup & Migration

### Full Backup (MongoDB Dump)

```cmd
mongodump --db libraryofyore --out C:\Backup\LibraryOfYore
```

This backs up all novels **and** all cover images stored in GridFS.

### Restore

```cmd
mongorestore --db libraryofyore C:\Backup\LibraryOfYore\libraryofyore
```

### Moving to Another PC

1. On the old PC: run `mongodump` as above
2. On the new PC: install MongoDB and Library of Yore
3. Copy the dump folder to the new PC
4. Run `mongorestore`
5. Launch Library of Yore — your full library appears

### Lightweight Backup (Excel)

Use **Export Excel** from the toolbar. This gives you a readable spreadsheet but does not include cover images. Use it as a readable reference or to re-add novels on a new machine.

---

## 15. Building from Source

This section is for developers who want to modify and rebuild the app.

### Prerequisites

```cmd
pip install -r requirements.txt
playwright install chromium
```

### Running in Development

```cmd
python main.py
```

### Build Commands

| Command | Output |
|---------|--------|
| `build.bat` | `dist\LibraryOfYore.exe` — single portable file |
| `python build.py` | Same as above |
| `python build.py --folder` | `dist\LibraryOfYore\` — folder build, faster startup |
| `python build.py --clean` | Cleans build artifacts, then builds |
| `build_release.bat` | Full build + Inno Setup installer |

> **Single-file vs folder build:**
> `--onefile` (default for `build.bat`) packs everything into one `.exe`. It extracts itself to a temp folder on each launch, adding ~3–5 seconds to startup. `--folder` is faster to launch but produces a folder with many files. Choose `--onefile` for distribution, `--folder` for development/debugging.

### Adding a New Scraper

1. Create `scrapers/mysite.py` inheriting from `BaseScraper`
2. Implement `SOURCE_NAME`, `DOMAIN_PATTERNS`, and `scrape(url)`
3. Register it in `scrapers/__init__.py` → `get_scraper_for_url()`
4. Add `--hidden-import scrapers.mysite` to `build.bat` and `build.py`

---

## 16. Troubleshooting

### App Won't Open (Silent Crash)

If double-clicking the `.exe` does nothing or the window flashes and disappears:

1. Look for **`crash_log.txt`** in the same folder as `LibraryOfYore.exe`
2. Open it — the full Python traceback is there
3. The most common causes are listed below

| Error in crash_log.txt | Fix |
|------------------------|-----|
| `ModuleNotFoundError` | Rebuild with the latest `build.bat` (v1.0.1+) |
| `Cannot connect to MongoDB` | Start MongoDB service (see below) |
| `FileNotFoundError: assets/logo.ico` | Make sure the `assets/` folder is present when building |
| Qt platform plugin error | Reinstall from a fresh build |

### Cannot Connect to MongoDB

**Symptom:** Setup Wizard appears every launch, or "Cannot reach MongoDB server."

```cmd
REM Open Command Prompt as Administrator, then:
net start MongoDB
```

If the service doesn't exist:
- Reinstall MongoDB and enable "Install as a Service"

If using a non-default port:
- Edit `%LOCALAPPDATA%\LibraryOfYore\config.json`
- Change `mongo_uri` to your actual URI, e.g. `mongodb://localhost:27018`

### Extension Shows "Disconnected"

**Symptom:** The extension popup shows a red Disconnected status.

- Library of Yore is not running. Launch it from your Start Menu, Desktop shortcut, or the startup folder.
- Check the Windows system tray — the app may already be running hidden there. Click the tray icon to confirm.
- If the app is running and the extension still shows disconnected, check Windows Firewall isn't blocking `localhost:7337`.

### Card Not Updating from the Extension

**Symptom:** You read a new chapter in the browser but the card in the app does not update.

- Open the novel's Edit dialog and confirm the **Source URL** is set to the novel's main page URL on the reading site (not a chapter URL)
- Verify the URL domain matches — e.g. the novel must be saved with a `novelfire.net` source URL if you are reading on Novelfire
- Check the extension popup — it should show the novel title it detected. If it shows "No match found", the URL could not be matched to any saved novel

### Scraping Fails

**Symptom:** "Scrape Failed" or "Could not extract title" message.

- Verify the URL opens correctly in your browser
- The website may have changed its layout — use **Manual Entry** instead
- Novelfire uses JavaScript rendering; scraping it requires Playwright/Chromium (bundled in the exe)
- Webnovel.com is not supported — it uses aggressive anti-bot protection

### Chapter Count Is Wrong

**Symptom:** A novel with 2111 chapters shows as 111, or shows 0.

- Update to **v1.0.1** — this was a regex bug in `novelfire.py` where `\d{1,3}` capped at 3 digits
- After updating, delete and re-add the novel to re-scrape the correct count

### Cover Image Won't Load

- Check your internet connection
- Click **Fetch Metadata** again — the cover URL may have expired
- Use **Load from File** to manually set a local image

### Excel Export Fails

- Make sure the target folder is writable (try Desktop or Documents)
- Check that the file isn't already open in Excel
- Ensure you have at least one novel in your library

### App Is Slow to Start

This is normal for the single-file portable `.exe` on first launch — PyInstaller extracts ~30 MB to a temp folder. Subsequent launches are faster because the temp folder is cached. If you need faster startup, use the `--folder` build from source instead.

---

## 17. Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + N` | Add new novel |
| `Ctrl + R` | Refresh library |
| `Ctrl + E` | Export to Excel |
| `F5` | Refresh library |
| `Delete` | Delete selected novel |
| `Enter` | Open / edit selected novel |

---

## 18. FAQ

**Q: Is my data stored online or shared with anyone?**
No. Everything is stored locally in MongoDB on your own machine. There are no accounts, no cloud sync, and no telemetry.

**Q: Can I run this on macOS or Linux?**
The source code is cross-platform Python, so `python main.py` works on any OS after installing dependencies. However, the `.bat` build scripts and installer are Windows-only. Mac/Linux users would build manually with `pyinstaller` directly.

**Q: How many novels can I store?**
MongoDB handles tens of millions of documents with ease. Your practical limit is disk space for cover images.

**Q: The exe is slow to open. Is something wrong?**
No — this is expected on the first launch of the single-file build. PyInstaller unpacks itself to `%TEMP%`. It's faster from the second launch onward. Use `python build.py --folder` for a faster-starting folder build if you prefer.

**Q: Can I add support for other novel sites?**
Yes. See [Section 15 — Adding a New Scraper](#adding-a-new-scraper).

**Q: Why was Webnovel.com removed?**
Webnovel uses Cloudflare and JavaScript-heavy anti-bot protection that makes reliable scraping impossible without constant maintenance.

**Q: How do I back up my library?**
Use `mongodump` for a complete backup (includes covers), or **Export Excel** from the toolbar for a human-readable reference copy. See [Section 14](#14-data-backup--migration).

**Q: Can I edit the config file directly?**
Yes. `%LOCALAPPDATA%\LibraryOfYore\config.json` is plain JSON. Edit with any text editor. Delete it to reset all settings to defaults.

**Q: Do I need to keep the app window open for the browser extension to work?**
No. Close the window and Library of Yore hides to the system tray. The API server stays running and the extension keeps tracking your chapters. Only use **Quit** from the tray menu when you want to fully stop the app.

**Q: Where do I download the browser extension?**
From the [Releases](https://github.com/NurAbir/Library-of-Yore/releases) page on GitHub. Download `Library.of.Yore.Browser.Extension.zip` from the latest release and follow the instructions in [Section 9](#9-browser-extension).

---

<div align="center">

**Happy Reading!**

*Library of Yore v1.2.0*

</div>