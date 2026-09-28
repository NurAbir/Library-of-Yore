# Library of Yore — User Manual

**Version 2.1.0**

A complete guide to installing, using, and troubleshooting Library of Yore, your personal desktop tracker for web novels and manga.

---

## Table of Contents

1. [System Requirements](#1-system-requirements)
2. [Data Storage](#2-data-storage)
3. [Installing Library of Yore](#3-installing-library-of-yore)
4. [First Launch & Import Wizard](#4-first-launch--import-wizard)
5. [Adding a Novel](#5-adding-a-novel)
6. [The Main Library](#6-the-main-library)
7. [Editing a Novel](#7-editing-a-novel)
8. [Tracking Reading Progress](#8-tracking-reading-progress)
9. [Auto-Refresh on Startup](#9-auto-refresh-on-startup)
10. [Browser Extension](#10-browser-extension)
11. [System Tray & Background Mode](#11-system-tray--background-mode)
12. [Search, Filter & Sort](#12-search-filter--sort)
13. [Exporting Your Library](#13-exporting-your-library)
14. [Settings & Configuration](#14-settings--configuration)
15. [Data Backup & Migration](#15-data-backup--migration)
16. [Building from Source](#16-building-from-source)
17. [Troubleshooting](#17-troubleshooting)
18. [Keyboard Shortcuts](#18-keyboard-shortcuts)
19. [FAQ](#19-faq)

---

## 1. System Requirements

| Component | Minimum |
|-----------|---------|
| **OS** | Windows 10 or Windows 11 (64-bit) |
| **RAM** | 4 GB (8 GB recommended) |
| **Storage** | 200 MB for the app + space for cover images |
| **Internet** | Required for scraping metadata and downloading covers |
| **Database** | None — your library is stored locally in a JSON file, no separate install |
| **Browser** | Chrome, Edge, Brave, or Firefox (for the browser extension) |

Python is **not** required to run the portable `.exe` or the installer build.

---

## 2. Data Storage

Library of Yore stores your entire library locally on your machine — no database server to install, start, or keep running. Since v2.0 this replaces the MongoDB-based storage earlier versions used.

### Where Your Data Lives

```
%LOCALAPPDATA%\LibraryOfYore\
├── library.json        ← all novel metadata and reading history
├── library.json.bak     ← automatic snapshot written before every save
├── backups\             ← one dated snapshot per day, newest 7 kept (since 2.0.2)
├── covers\              ← one cover image file per novel
├── config.json          ← app settings (see Section 14)
└── exports\             ← Excel exports land here by default
```

### Upgrading from Before 2.0?

If you previously used Library of Yore with MongoDB, nothing is lost. On first launch, the app checks for an existing MongoDB library and — if it finds one — offers to import every novel and cover image into the new local format. See [Section 4](#4-first-launch--import-wizard).

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

## 4. First Launch & Import Wizard

On the very first launch, Library of Yore checks whether a local library file (`library.json`) already exists.

### Typical Case — Fresh Install, No Previous MongoDB Library

The main window opens immediately with an empty library, and Novelfire, NovelPhoenix and Flame Comics titles (once you've added some) begin auto-refreshing in the background on future launches (see [Section 9](#9-auto-refresh-on-startup)). Skip ahead to [Section 5](#5-adding-a-novel).

### If an Existing MongoDB Library Is Found

If no local library exists yet, the app briefly checks `localhost:27017` for a pre-2.0 MongoDB library. If one is found, the **Import Wizard** appears:

| Button | What It Does |
|--------|--------------|
| **Import Now →** | Copies every novel and cover image from MongoDB into your new local library, with progress shown live |
| **Skip — Start Fresh** | Closes the wizard and starts with an empty local library instead |

This check only happens once — after your local library exists (even if you skipped), the app never probes MongoDB automatically again. If you skipped by mistake and haven't added any novels yet, you can trigger the same import at any time from **File → Import Existing MongoDB Library…**.

---

## 5. Adding a Novel

Click **Add Novel** in the toolbar to open the Add Novel dialog.

### Method 1 — Auto-Scrape from URL (Recommended)

This is the fastest way to add a novel with full metadata.

1. Paste the novel's page URL into the **Source URL** field
2. Press **Enter** or click **Fetch Metadata**
3. Wait a few seconds while the app downloads and extracts data
4. The following fields fill in automatically:
   - Title
   - Author
   - Cover image
   - Latest chapter (the highest chapter number the site lists, decimals included)
   - For Flame Comics: the full chapter list, which chapters are locked, and whether it's a novel or manga
   - Synopsis (any leading "Summary" or "Description" label is stripped automatically)
   - Genres
   - Status (Ongoing / Completed / Hiatus)
5. A green confirmation line appears below the URL field — no pop-up dialog
6. Enter your **Current Chapter**, the last chapter you read (decimals such as `2.5` are fine). Leave it empty if you haven't started: that's different from chapter 0
7. Adjust any fields if needed
8. Click **Save Novel**

**Supported URLs:**

| Site | Example URL |
|------|-------------|
| Novelfire | `https://novelfire.net/book/shadow-slave` |
| NovelPhoenix | `https://novelphoenix.com/novel/shadow-slave` |
| Wuxiaworld | `https://www.wuxiaworld.com/novel/renegade-immortal` |
| FreeWebNovel | `https://freewebnovel.com/novel/lord-of-the-mysteries` |
| NovelUpdates | `https://www.novelupdates.com/series/lord-of-the-mysteries/` |
| Flame Comics (novel) | `https://flamecomics.xyz/novel/8` |
| Flame Comics (manga) | `https://flamecomics.xyz/series/2` |

> **Note:** NovelUpdates is a catalog site. It provides metadata but does not host chapters directly.

> **Flame Comics:** pasting a chapter link (e.g. `https://flamecomics.xyz/novel/8/f48067c3fe28e0a0`) works too; it's turned into the title's main page. Flame hosts some titles as both a novel and a manhwa: add each as its own entry. Manga are tracked for progress only; pages aren't downloaded.

### Method 2 — Manual Entry

Use this when a site isn't supported or scraping fails.

1. Click **Add Novel**
2. Leave the URL field empty (or fill it as a reference link)
3. Fill in:
   - **Title** *(required)*
   - Author
   - Current chapter (empty = not started) / Latest chapter
   - Type (Novel or Manga)
   - Status, Rating, Genres
   - Synopsis and personal Notes
4. Optionally add a cover (see below)
5. Click **Save Novel**

### Cover Images

| Method | How |
|--------|-----|
| **Auto** | Fetched automatically when you use Fetch Metadata |
| **From File** | Click **Load from File** and pick a `.jpg`, `.png`, `.webp`, or `.bmp` |
| **From URL** | Paste a direct image link (or a novel page on a supported site) into the **Source URL** field, then click **Download from URL** |
| **Clear** | Click **Clear Cover** to remove the current image |

All covers are saved as local files in your `covers\` folder (see [Section 2](#2-data-storage)) — they travel along whenever you back up the `%LOCALAPPDATA%\LibraryOfYore\` folder.

### Keyboard Behaviour in the Add Novel Dialog

Pressing **Enter** anywhere in the dialog does **not** trigger Save. This is intentional — it prevents accidentally saving an incomplete form. The only place Enter has an action is the **Source URL field**, where it triggers Fetch Metadata (same as clicking the button). To save, always click **Save Novel** directly.

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
| **+ Add Novel** | Open the Add Novel dialog |
| **Export Excel** | Save your full library to a `.xlsx` spreadsheet |

> To manually reload novels from the database, use **View → Refresh** in the menu bar.

### Novel Cards

The library is always shown as a responsive cover grid — the number of columns adapts automatically to your window size, so resizing or maximizing the window rearranges cards rather than clipping them.

Each novel card shows:

- **Cover image** (or a "No Cover" placeholder)
- **✦ Updated badge** — a small gold badge in the top-right corner of the cover, visible on cards that received new data during the current session's auto-refresh
- **Title**
- **Status badge** — colour coded:

| Colour | Status |
|--------|--------|
| Blue | Ongoing |
| Gold | Completed |
| Orange | Hiatus |
| Red | Dropped |
| Purple | Planned |

- **MANGA tag** for manga entries, so a novel and its manhwa are easy to tell apart
- **Chapter**: current / latest, e.g. "Ch 120 / 621" ("Ch – / 621" when not started). Shown in green when you're up to date
- **Progress bar**: how far through the site's chapters you are
- **Tooltip** (hover the card): chapters behind, how many of those are locked, and how many chapters the site lists

### Card Actions

| Action | How |
|--------|-----|
| Open full details / edit | Left-click the card |
| Mark the next chapter read | Click the **+1** button on the card (hover it to see which chapter it will record) |
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

Saving an edit changes only the fields shown in the dialog. **Date Added**, **Read Count** and the cover are kept as they were unless you change them, and **Last Read** only moves if you changed **Current Chapter**.

To delete a novel: right-click its card → **Delete**. This also removes its cover image file from the `covers\` folder.

---

## 8. Tracking Reading Progress

### Updating Your Chapter

**Quick (one click):** Click the **+1** button on any card. It records the *next* chapter and updates the last-read timestamp:
- When the site's chapter list is known (Flame Comics), +1 follows that list: 2 → 2.5 → 3, skips numbers the site doesn't have, and from **Not started** goes to the first chapter the site lists (0 or 0.01 if it has one)
- Otherwise it goes to the next whole chapter (45.5 → 46), and from Not started to chapter 1

**Precise:** Open the novel → change the **Current Chapter** number → Save. Decimals are allowed; clear the field to mark the novel as not started.

**Automatic (browser extension):** If you have the browser extension installed, your chapter updates as you read in the browser — see [Section 10](#10-browser-extension).

### Progress Indicators

| Indicator | Meaning |
|-----------|---------|
| Progress bar | With a chapter list: chapters read ÷ chapters the site lists (so gaps, chapter 0 and decimals count correctly). Without one: current ÷ latest |
| Chapters behind | How many chapters are left (card tooltip, Excel export) |
| Locked | How many of the chapters left are locked/paid on the site (Flame Comics); they still count as "behind" |
| Up to date | Nothing left to read: the chapter label turns green |
| Percentage | Exact completion %, shown in the browser extension popup and the Excel export |

> **Upgrading from 2.0.x:** your library is converted automatically the first time 2.1.0 opens. Novels that were at chapter 0 become **Not started**, and the old "total chapters" becomes the latest chapter. After that, the library can't be opened by an older version: keep the dated copies in `backups\` if you might go back.

### Reading History

Every change to your reading progress (the **+1** button, the browser extension, or changing **Current Chapter** in the Edit dialog) records:
- **Last Read**: the timestamp of that update
- **Read Count**: total number of progress updates

Other edits and the startup auto-refresh don't change either value, so sorting by **Last Read** reliably brings back whatever you were reading most recently.

---

## 9. Auto-Refresh on Startup

Every time Library of Yore opens, it silently re-scrapes your **Novelfire, NovelPhoenix and Flame Comics** titles in the background to check for new chapters, status changes, or updated synopsis text. No action is required: it happens automatically. Titles the site already marks **Completed** are skipped, since they won't get new chapters.

### What Gets Updated

| Field | Updated? |
|-------|---------|
| Latest chapter | ✅ Yes: the highest chapter the site lists |
| Chapter list and locked chapters | ✅ Yes (Flame Comics) |
| Status | ✅ Yes: picks up Ongoing → Completed transitions automatically. A novel you marked **Dropped** or **Planned** keeps your status |
| Synopsis | ✅ Yes — pulls the current synopsis text from the novel page |
| Cover image | ❌ No — covers are not re-downloaded on auto-refresh |
| Your current chapter | ❌ No — your reading progress is never overwritten |

### The ✦ Updated Badge

Any card that received a change during auto-refresh shows a small gold **✦ Updated** badge in the top-right corner of its cover image. The badge stays visible for the rest of the session and disappears the next time the library is fully reloaded.

### Status Bar

While auto-refresh is running, the status bar at the bottom of the window shows:

> *Auto-refreshing 3 novel(s) in background…*

When complete, it changes to:

> *Auto-refresh complete — 3 novel(s) checked.*

Cards that changed show the ✦ Updated badge. All changes are saved together once the refresh finishes.

### Notes

- Auto-refresh runs entirely in the background — the UI stays fully responsive
- Novelfire, NovelPhoenix and Flame Comics titles are refreshed. Wuxiaworld, FreeWebNovel and NovelUpdates entries are only updated when you click **Fetch Metadata** in the Edit dialog
- If a scrape fails for an individual novel (network error, site unavailable), it is silently skipped and the rest continue
- Novels are refreshed one at a time with a short pause between them, so a large library takes a little while to finish

---

## 10. Browser Extension

The **Library of Yore Browser Extension** tracks the chapter you are reading in your browser and automatically updates your progress in the app — no clicking +1, no manual entry.

It works on **Novelfire**, **NovelPhoenix**, **Wuxiaworld**, **FreeWebNovel** and **Flame Comics** (both novels and manga). NovelUpdates is a catalog site with no chapters to read, so there's nothing to track there.

> **Download:** The extension is available in the [Releases](https://github.com/NurAbir/Library-of-Yore/releases) section on GitHub. Download `Library.of.Yore.Browser.Extension.zip` from the latest release.

### How It Works

The extension communicates with Library of Yore through a small local API server the app runs on `localhost:7337`. When you navigate to a new chapter, the extension:

1. Reads the current page URL and the novel title
2. Matches the URL against the novels stored in your library (same site, and the saved novel page's path must lead into the chapter's path). Only if that fails does it try the title, among novels saved from the same site
3. Extracts the chapter number from the URL or page content (on Flame Comics, from the page title, because Flame's chapter links contain no number). Decimal chapters such as 2.5 are kept. A number read from a URL like `chapter-2-5` could mean 2.5 or part 5 of chapter 2: the app keeps 2.5 only if the site's chapter list has it, otherwise it records chapter 2
4. If **Auto-sync** is on (it's off by default, see the popup's Settings) and the novel was matched **by URL**, sends a progress update when the chapter is newer than what is stored. A match by title alone is shown in the popup with a note, and waits for you to press **Sync**
5. The app updates the card immediately: chapter label and progress bar refresh in real time

Progress only ever moves forward: opening an older chapter never lowers what's stored. From **Not started**, any chapter counts, including chapter 0.

On sites that change chapters without reloading the page (Flame Comics' Previous/Next buttons), the extension notices each change and reports the new chapter too.

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
| 🟢 Green dot | Library of Yore is running and the API server is reachable |
| 🔴 Red dot, "App not running" | The app is not running. Launch Library of Yore first |

### Matching Novels

For the extension to update a novel, that novel must be saved in your library with a **Source URL** that matches the site you are reading on. The extension matches by domain and URL path — for example, if you saved `https://novelfire.net/book/shadow-slave`, reading any chapter URL under that path will be recognised as the same novel. The same applies to NovelPhoenix, e.g. `https://novelphoenix.com/novel/shadow-slave`, and to Flame Comics, e.g. `https://flamecomics.xyz/series/2` for the manhwa and `https://flamecomics.xyz/novel/8` for the novel (a manhwa chapter never updates the novel entry, and vice versa).

If a novel is not being detected, open the Edit dialog and confirm the Source URL is set to the novel's main page on the supported site.

---

## 11. System Tray & Background Mode

Library of Yore is designed to run quietly in the background so the browser extension always has somewhere to send updates — even when you are not actively using the app.

### Hiding to the Tray

When you click the **✕ close button** on the main window, the app does **not** quit. Instead it hides to the Windows system tray (bottom-right corner of the taskbar, near the clock). The API server keeps running, so the browser extension continues working normally.

The first time you close the window in a session, a notification balloon appears:

> *"Still tracking in the background. Right-click the tray icon to quit."*

### Tray Icon Actions

| Action | Result |
|--------|--------|
| **Single-click** the tray icon | Reopens the main window |
| **Double-click** the tray icon | Reopens the main window |
| **Right-click → Open Library** | Reopens the main window |
| **Right-click → Quit** | Fully exits the app, stops the API server, and flushes the local library file |

### Fully Quitting

To stop Library of Yore completely, right-click its icon in the system tray and choose **Quit**. Simply closing the window is not enough — that only hides it.

### Starting with Windows (Optional)

If you want Library of Yore to launch automatically on login so the extension is always ready:

1. Press `Win + R`, type `shell:startup`, press Enter
2. Create a shortcut to `LibraryOfYore.exe` in that folder

The app opens its window on each login; close it to send it to the tray.

---

## 12. Search, Filter & Sort

### Search

Type in the search box (left sidebar). Matches novels where the search text appears in the **title**, **author**, or **notes** fields. Case-insensitive. Results update as soon as you pause typing.

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

## 13. Exporting Your Library

Click **Export Excel** in the toolbar. Choose a save location. The file opens in Excel or any spreadsheet app.

### Exported Columns

| Column | Description |
|--------|-------------|
| Title | Novel title |
| Author | Author name |
| Status | ongoing / completed / hiatus / dropped / planned |
| Type | Novel / Manga |
| Current Chapter | Your last read chapter ("Not started" if none) |
| Latest Chapter | Highest chapter the site lists (blank if unknown) |
| Chapters Behind | Chapters left to read (blank if unknown) |
| Locked Behind | How many of those are locked on the site |
| % Complete | Calculated completion percentage |
| Source URL | Link to the novel page |
| Source | novelfire / novelphoenix / wuxiaworld / freewebnovel / novelupdates / flamecomics / manual |
| Last Read | ISO 8601 timestamp |
| Date Added | When you first added it |
| Rating | Your 0–10 rating |
| Genres | Comma-separated |
| Notes | Your personal notes |

### Uses

- Human-readable backup alongside your local library file
- Share your reading list
- Analyse your reading history in Excel/Sheets
- Reference when setting up on a new machine

---

## 14. Settings & Configuration

Settings are saved to:

```
%LOCALAPPDATA%\LibraryOfYore\config.json
```

Open this file in any text editor to edit manually.

### Available Settings

| Key | Default | Description |
|-----|---------|-------------|
| `theme` | `dark` | Reserved for future use, not currently read (the app always uses its dark theme) |
| `window_size` | `[1200, 800]` | Reserved for future use — the app now detects your screen size on launch and opens maximized automatically, so this value isn't currently read |
| `default_sort` | `last_read` | Reserved for future use, not currently read (the app always starts sorted by Last Read) |

### Reset to Defaults

Delete `config.json` and restart the app. It recreates the file with all defaults.

---

## 15. Data Backup & Migration

### Full Backup

Copy the entire folder:

```
%LOCALAPPDATA%\LibraryOfYore\
```

This includes `library.json` (all novel metadata and reading history), the `covers\` folder (every cover image) and the `backups\` folder (daily snapshots).

### Restore

Copy that same folder back to `%LOCALAPPDATA%\LibraryOfYore\` — on the same PC or a new one — and launch Library of Yore.

### Moving to Another PC

1. On the old PC: copy the `%LOCALAPPDATA%\LibraryOfYore\` folder to a USB drive or cloud folder
2. On the new PC: install Library of Yore
3. Copy the folder to `%LOCALAPPDATA%\LibraryOfYore\` on the new PC (overwriting the empty one created on first launch)
4. Launch Library of Yore — your full library appears

### Upgrading from a Pre-2.0 (MongoDB) Install

You don't need to do this manually — see [Section 4](#4-first-launch--import-wizard). If you skipped the import and want to run it again, use **File → Import Existing MongoDB Library…** from the menu bar (as long as MongoDB is still installed and running).

### Lightweight Backup (Excel)

Use **Export Excel** from the toolbar. This gives you a readable spreadsheet but does not include cover images. Use it as a readable reference or to re-add novels on a new machine.

---

## 16. Building from Source

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

> **Note on `--exclude-module`:** as of v1.4.0, all three build paths pass `--exclude-module numpy --exclude-module pandas --exclude-module matplotlib`. None of these are used by the app — `openpyxl` only imports numpy *optionally*, and PyInstaller has a history of bundling numpy incompletely, which can crash the built exe with `AttributeError: module 'numpy' has no attribute 'short'`. Excluding it lets openpyxl's own fallback handle the missing import cleanly.

### Adding a New Scraper

1. Create `scrapers/mysite.py` inheriting from `BaseScraper`
2. Implement `SOURCE_NAME`, `DOMAIN_PATTERNS`, and `scrape(url)`
3. Register it in `scrapers/__init__.py` → `get_scraper_for_url()`
4. Add `--hidden-import scrapers.mysite` in **all three** build paths — `build.bat`, `build_release.bat`, and `build.py`'s `COMMON_HIDDEN_IMPORTS` list. These are maintained separately and drift easily; a scraper missing from just one still works when run from source but silently breaks in that one built `.exe`
5. Set `result.latest_chapter` as a chapter string (use `utils.chapters.parse_chapter`). If the site shows its full chapter list, also fill `result.chapter_list` (and `locked_list`) so progress follows the real list; see `scrapers/flamecomics.py`
6. If the site should also support the browser extension's live chapter tracking, add its domain to `Library of Yore Browser Extension/manifest.json` (content-script matches), a detector function in `content.js`, and the domain to `background.js`'s `novelHosts` list

---

## 17. Troubleshooting

### App Won't Open (Silent Crash)

If double-clicking the `.exe` does nothing or the window flashes and disappears:

1. Look for **`crash_log.txt`** in the same folder as `LibraryOfYore.exe`
2. Open it — the full Python traceback is there
3. The most common causes are listed below

| Error in crash_log.txt | Fix |
|------------------------|-----|
| `ModuleNotFoundError` | Rebuild with the latest `build.bat` (v1.0.1+) |
| `AttributeError: module 'numpy' has no attribute 'short'` | Rebuild with v1.4.0+ — `numpy`/`pandas`/`matplotlib` are now excluded from the build since they're unused and PyInstaller was bundling numpy incompletely |
| `UnicodeDecodeError` / `charmap codec` / `PermissionError` / `FileNotFoundError` on `library.json` | Since v2.0, this is repaired automatically on the next launch (see below) — only worth checking `%LOCALAPPDATA%\LibraryOfYore\` isn't read-only or locked by a sync tool if the automatic repair itself reports failure |
| `FileNotFoundError: assets/logo.ico` | Make sure the `assets/` folder is present when building |
| Qt platform plugin error | Reinstall from a fresh build |

### Library File Won't Load / Looks Corrupted

**Symptom:** The app used to crash right on startup with an error about `library.json` (e.g. `UnicodeDecodeError` or `charmap`), or opens with an unexpectedly empty library.

Since v2.0, Library of Yore checks `library.json` on every startup and repairs it automatically — you shouldn't need to do anything by hand:

1. **Wrong-encoding file** (the most common cause — usually a file saved by an early 2.0 build on Windows): re-decoded and repaired **in place**. Nothing is lost; you'll see a one-time message confirming this.
2. **Genuinely unreadable main file, but the automatic backup is fine**: restored from `library.json.bak` (a snapshot taken before every save). A few very recent changes might be missing.

If you need to go back further than the last save (for example, to undo a change you regret), the `backups\` folder holds one dated copy of `library.json` per day for the last 7 days. Quit the app from the tray, copy the dated file over `library.json`, and relaunch.
3. **Neither the file nor the backup can be read**: set aside as `library.json.broken-<timestamp>` so the app can still start with an empty library. If you have an existing MongoDB library, use **File → Import Existing MongoDB Library…** to bring your novels back (see [Section 4](#4-first-launch--import-wizard)).

If you ever see a message saying the file **couldn't** be moved or repaired automatically (rare — usually because something else has it locked, e.g. a cloud-sync tool actively writing to it):

1. Close Library of Yore completely (right-click the tray icon → Quit)
2. Make sure nothing else has `%LOCALAPPDATA%\LibraryOfYore\library.json` open (check antivirus/sync-tool activity)
3. Relaunch — the same automatic repair described above will run again

If a cloud-sync tool (OneDrive, Dropbox, etc.) is set to sync `%LOCALAPPDATA%`, it can occasionally lock the file mid-write — excluding that folder from sync avoids this.

### Existing MongoDB Library Not Detected

**Symptom:** You upgraded from a pre-2.0 version, but the Import Wizard never appeared.

- The check only looks at `localhost:27017` (or a custom URI saved in an old `config.json`) — make sure MongoDB is installed **and running** the first time you launch 2.0
- The automatic check only runs once, before `library.json` exists. If you already have an (empty) local library, use **File → Import Existing MongoDB Library…** instead

### Extension Shows "Disconnected"

**Symptom:** The extension popup shows a red Disconnected status.

- Library of Yore is not running. Launch it from your Start Menu, Desktop shortcut, or the startup folder.
- Check the Windows system tray — the app may already be running hidden there. Click the tray icon to confirm.
- If the app is running and the extension still shows disconnected, check Windows Firewall isn't blocking `localhost:7337`.

### Card Not Updating from the Extension

**Symptom:** You read a new chapter in the browser but the card in the app does not update.

- Open the novel's Edit dialog and confirm the **Source URL** is set to the novel's main page URL on the reading site (not a chapter URL)
- Verify the URL domain matches — e.g. the novel must be saved with a `novelfire.net` source URL if you are reading on Novelfire
- Check the extension popup: it should show the novel title it detected. If it says "This novel isn't in your library yet", neither the URL nor the title matched a saved novel
- Auto-sync is **off** by default: turn it on in the popup's **Settings**. It only syncs automatically when the novel was matched by its URL; a title-only match needs a click on **Sync**

### Scraping Fails

**Symptom:** "Scrape Failed" or "Could not extract title" message.

- Verify the URL opens correctly in your browser
- The website may have changed its layout — use **Manual Entry** instead
- Novelfire uses JavaScript rendering; scraping it requires Playwright/Chromium (bundled in the exe)
- Webnovel.com is not supported — it uses aggressive anti-bot protection

### Synopsis Shows a "Summary" Prefix

**Symptom:** Synopsis text starts with "SummaryThe story begins..." or "DescriptionIn a world where...".

Update to **v1.3.0** — the scraper now strips leading `Summary`, `Description`, and `Synopsis` labels automatically, including variants with or without a colon separator.

### Novel Status Is Wrong (Shows Ongoing When Completed)

**Symptom:** A completed novel is still marked Ongoing after adding.

Update to **v1.3.0** — earlier versions read status from the entire page text blob, which caused story synopsis words like "completed his journey" to false-match. v1.3.0 uses targeted CSS selectors on the status badge element only.

### Chapter Count Is Wrong

**Symptom:** A novel with 2111 chapters shows as 111, or shows 0.

- Update to **v1.0.1** — this was a regex bug in `novelfire.py` where `\d{1,3}` capped at 3 digits
- After updating, delete and re-add the novel to re-scrape the correct count

### App Crashes on Launch with a numpy AttributeError

**Symptom:** `crash_log.txt` shows `AttributeError: module 'numpy' has no attribute 'short'`, traced through `openpyxl\compat\numbers.py`.

- `openpyxl` optionally uses numpy if it's present, but PyInstaller can bundle numpy incompletely, leaving a broken copy that crashes on import
- Update to **v1.4.0** — the build now excludes numpy, pandas, and matplotlib entirely (none of which the app actually uses), so `openpyxl` falls back cleanly instead
- If you're building from source yourself, do a clean rebuild (`python build.py --clean` or delete `dist\`/`build\` first) so the excluded modules actually drop out of the new build

### Installer Says "LibraryOfYore.exe Not Found" Even Though It's There

**Symptom:** Compiling `installer.iss` directly (not via `build_release.bat`) fails at compile time with a "could not find LibraryOfYore.exe" error, even though the exe is sitting right there in `dist\`.

- This was an Inno Setup preprocessor quirk — its relative `FileExists()` checks resolve against the compiler's *current working directory*, not the script's own folder, so it could fail depending on how you launched the compile
- Update to **v1.4.0** — `installer.iss` now anchors those checks to its own folder and also auto-detects onefile vs. folder builds, so it finds the exe regardless of how or where you compile from
- If you still hit this (e.g. a build living in a completely different location), pass the folder containing the exe manually: `ISCC.exe installer.iss /DMyDistDir="C:\path\to\folder"`

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

### "Title is required" Error When Saving

**Symptom:** Clicking Save Novel immediately shows a "Title is required" validation error before any data is filled in.

Update to **v1.3.0** — earlier versions had Qt's `autoDefault` button behaviour triggered when pressing Enter in any field (including the URL input after scraping), which fired Save before the form was populated. v1.3.0 fully blocks Enter from triggering any button in the dialog.

---

## 18. Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + N` | Add new novel |
| `Ctrl + R` | Refresh library |
| `Ctrl + E` | Export to Excel |
| `F5` | Refresh library |
| `Enter` (in Add/Edit dialog URL field) | Trigger Fetch Metadata |

---

## 19. FAQ

**Q: Is my data stored online or shared with anyone?**
No. Everything is stored locally in a JSON file on your own machine. There are no accounts, no cloud sync, and no telemetry.

**Q: Can I run this on macOS or Linux?**
The source code is cross-platform Python, so `python main.py` works on any OS after installing dependencies. However, the `.bat` build scripts and installer are Windows-only. Mac/Linux users would build manually with `pyinstaller` directly.

**Q: How many novels can I store?**
Comfortably into the thousands — a personal reading list is tiny by JSON-file standards. Your practical limit is disk space for cover images.

**Q: The exe is slow to open. Is something wrong?**
No — this is expected on the first launch of the single-file build. PyInstaller unpacks itself to `%TEMP%`. It's faster from the second launch onward. Use `python build.py --folder` for a faster-starting folder build if you prefer.

**Q: Does it work with manga?**
Yes, on Flame Comics. Add a series link such as `https://flamecomics.xyz/series/2`: it's saved as a **Manga** entry (with a MANGA tag on its card), the full chapter list is fetched, and the browser extension tracks the chapter you're reading, including when you use Flame's Previous/Next buttons. Progress is tracked; chapter pages aren't downloaded. If you follow both a novel and its manhwa (e.g. Omniscient Reader's Viewpoint), add each separately: they're kept apart and never update each other.

**Q: Can I add support for other novel sites?**
Yes. See [Section 16 — Adding a New Scraper](#adding-a-new-scraper).

**Q: Why was Webnovel.com removed?**
Webnovel uses Cloudflare and JavaScript-heavy anti-bot protection that makes reliable scraping impossible without constant maintenance.

**Q: How do I back up my library?**
Copy the `%LOCALAPPDATA%\LibraryOfYore\` folder for a complete backup (includes covers), or use **Export Excel** from the toolbar for a human-readable reference copy. See [Section 15](#15-data-backup--migration).

**Q: Can I edit the config file directly?**
Yes. `%LOCALAPPDATA%\LibraryOfYore\config.json` is plain JSON. Edit with any text editor. Delete it to reset all settings to defaults.

**Q: Do I need to keep the app window open for the browser extension to work?**
No. Close the window and Library of Yore hides to the system tray. The API server stays running and the extension keeps tracking your chapters. Only use **Quit** from the tray menu when you want to fully stop the app.

**Q: Where do I download the browser extension?**
From the [Releases](https://github.com/NurAbir/Library-of-Yore/releases) page on GitHub. Download `Library.of.Yore.Browser.Extension.zip` from the latest release and follow the instructions in [Section 10](#10-browser-extension).

**Q: Which novels get auto-refreshed on startup?**
**Novelfire**, **NovelPhoenix** and **Flame Comics** titles, except those the site marks Completed.

**Q: Why does a Flame title show chapters as "behind" that I can't read for free?**
Locked (paid) chapters still exist on the site, so they count as behind. The card tooltip shows how many of them are locked, e.g. "12 behind · 8 locked".

**Q: Can I turn off auto-refresh?**
There is no toggle yet. The refresh runs in the background and is non-intrusive — the UI remains fully responsive throughout. A setting to disable it is planned for a future release.

**Q: The synopsis still shows "Summary..." after updating.**
Make sure you replaced `scrapers/novelfire.py` with the v1.3.0 version and rebuilt (or replaced the `.exe`). For novels already in your library, trigger a re-fetch by opening Edit and clicking Fetch Metadata again.

---

<div align="center">

**Happy Reading!**

*Library of Yore v2.1.0*

</div>
