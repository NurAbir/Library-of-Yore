# Library of Yore — User Manual

A complete guide to using Library of Yore, your personal web novel bookmark tracker.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [First Launch](#first-launch)
3. [Adding a Novel](#adding-a-novel)
4. [The Main Library](#the-main-library)
5. [Editing a Novel](#editing-a-novel)
6. [Tracking Progress](#tracking-progress)
7. [Search & Filter](#search--filter)
8. [Exporting Your Library](#exporting-your-library)
9. [Settings & Configuration](#settings--configuration)
10. [Troubleshooting](#troubleshooting)

---

## Getting Started

### System Requirements

- **Operating System:** Windows 10 or Windows 11
- **RAM:** 4 GB minimum (8 GB recommended)
- **Storage:** 200 MB for the app + space for your library
- **Internet:** Required for scraping novel metadata and downloading covers
- **Database:** MongoDB Community Server (installed separately)

### Installing MongoDB

Library of Yore requires MongoDB to store your novel data. Here is how to install it:

1. Go to https://www.mongodb.com/try/download/community
2. Download the **MongoDB Community Server MSI** for Windows
3. Run the installer
4. When prompted, check **"Install MongoDB as a Service"**
5. Complete the installation
6. MongoDB will now run automatically when Windows starts

To verify MongoDB is running, open Command Prompt as Administrator and type:

```cmd
net start MongoDB
```

If it says "The requested service has already been started," you are good to go.

### Installing Library of Yore

**Option A: Installer (Recommended)**

1. Download `LibraryOfYore_Setup.exe` from the Releases page
2. Run the installer
3. Follow the setup wizard
4. Launch Library of Yore from the Start Menu or Desktop

**Option B: Portable (No Install)**

1. Download the portable ZIP from the Releases page
2. Extract to any folder
3. Run `LibraryOfYore.exe`

---

## First Launch

When you open Library of Yore for the first time, it will check if MongoDB is available on `localhost:27017`.

### If MongoDB is Running

The main window opens immediately. You are ready to add novels.

### If MongoDB is Not Found

A **Setup Wizard** appears with these options:

| Button | What It Does |
|--------|--------------|
| **Download MongoDB** | Opens the official MongoDB download page in your browser |
| **Start MongoDB Service** | Attempts to start the MongoDB Windows service |
| **Retry Connection** | Tests the connection again |
| **MongoDB URI** | Edit the connection string if MongoDB is on a custom port |

Once connected, click **Continue** to open the main window.

---

## Adding a Novel

### Method 1: Auto-Scrape from URL (Recommended)

1. Click the **Add Novel** button in the toolbar
2. Paste the novel URL into the **Source URL** field
   - Supported: `https://www.webnovel.com/book/...`
   - Supported: `https://novelfire.net/book/...`
3. Click **Fetch Metadata**
4. Wait a few seconds while the app scrapes the page
5. The following fields auto-fill:
   - Title
   - Author
   - Cover image
   - Total chapters
   - Synopsis
   - Genres
   - Status (ongoing/completed)
6. Enter your **Current Chapter** (where you left off)
7. Adjust any fields as needed
8. Click **Save Novel**

### Method 2: Manual Entry

1. Click **Add Novel**
2. Leave the URL field empty (or fill it for reference)
3. Manually enter:
   - **Title** (required)
   - Author
   - Current / Total chapters
   - Status
   - Rating
   - Genres
   - Synopsis and Notes
4. Optionally load a cover image from your computer
5. Click **Save Novel**

### Loading a Cover Image

| Method | Steps |
|--------|-------|
| **From File** | Click **Load from File**, select an image (.png, .jpg, .jpeg, .webp, .bmp) |
| **From URL** | After fetching metadata, the cover auto-downloads. Or click **Download from URL** |
| **Clear** | Click **Clear Cover** to remove the image |

---

## The Main Library

The main window is divided into three areas:

### Left Sidebar

| Control | Purpose |
|---------|---------|
| **Search** | Type to filter novels by title, author, or notes |
| **Status Filters** | Check/uncheck statuses to show/hide novels |
| **Sort By** | Choose how to order your library: Last Read, Title, Rating, Date Added, Progress % |

### Top Toolbar

| Button | Action |
|--------|--------|
| **Add Novel** | Open the add/edit dialog |
| **Grid / List** | Toggle between cover grid and compact list view |
| **Export Excel** | Save your library to a spreadsheet |

### Novel Grid

Each novel appears as a card showing:

- **Cover image** (or "No Cover" placeholder)
- **Title**
- **Status badge** (colored: blue=ongoing, gold=completed, orange=hiatus, red=dropped, purple=planned)
- **Current chapter**
- **Progress bar** with percentage

### Card Actions

| Action | How |
|--------|-----|
| **Open details** | Left-click the card |
| **Quick +1 chapter** | Click the "+1" button |
| **Open source URL** | Click the "Link" button |
| **Edit / Delete** | Right-click the card for context menu |

---

## Editing a Novel

1. **Left-click** any novel card, or **right-click > Edit**
2. The same dialog as "Add Novel" opens, pre-filled with current data
3. Make your changes
4. Click **Save Novel**

You can edit anything: title, chapter progress, status, rating, notes, or replace the cover image.

---

## Tracking Progress

### Updating Your Current Chapter

**Quick method:**
- Click the **+1** button on any card to increment by one chapter

**Precise method:**
- Open the novel (left-click card)
- Change the **Current** chapter number
- Save

### Understanding Progress

| Indicator | Meaning |
|-----------|---------|
| **Progress bar** | Visual fill showing `current / total` |
| **Percentage** | Exact completion % |
| **Up to date** | When current chapter equals total chapters |

### Reading History

Every time you update a novel, Library of Yore records:
- **Last Read** timestamp
- **Read Count** (how many times you have opened/edited it)

Use **Sort By: Last Read** to quickly find where you left off.

---

## Search & Filter

### Search

Type in the search box to find novels by:
- Title
- Author
- Notes content

Search is case-insensitive and updates instantly as you type.

### Filter by Status

Check or uncheck status boxes in the sidebar:

- Ongoing
- Completed
- Hiatus
- Dropped
- Planned

Only checked statuses are shown.

### Sorting

| Sort Option | Order |
|-------------|-------|
| **Last Read** | Most recently read first |
| **Title** | Alphabetical (A-Z) |
| **Rating** | Highest rated first |
| **Date Added** | Newest first |
| **Progress %** | Most complete first |

---

## Exporting Your Library

Library of Yore can export all your novels to an Excel spreadsheet.

### How to Export

1. Click **Export Excel** in the toolbar
2. Choose where to save the file
3. The export includes these columns:

| Column | Description |
|--------|-------------|
| Title | Novel title |
| Author | Author name |
| Status | ongoing / completed / hiatus / dropped / planned |
| Current Chapter | Where you left off |
| Total Chapters | Total known chapters (blank if unknown) |
| % Complete | Calculated progress |
| Source URL | Link back to the novel |
| Source | webnovel / novelfire / manual |
| Last Read | ISO timestamp |
| Date Added | When you added it |
| Rating | Your 0-10 rating |
| Genres | Comma-separated tags |
| Notes | Your personal notes |

### Use Cases

- **Backup** your library outside MongoDB
- **Share** your reading list with friends
- **Analyze** your reading habits in Excel
- **Import** into other tools

---

## Settings & Configuration

Library of Yore stores settings in:

```
%LOCALAPPDATA%\LibraryOfYore\config.json
```

### Configuration Options

| Setting | Default | Description |
|---------|---------|-------------|
| `mongo_uri` | `mongodb://localhost:27017` | MongoDB connection string |
| `db_name` | `libraryofyore` | Database name |
| `theme` | `dark` | UI theme (currently only dark) |
| `window_size` | `[1200, 800]` | Last window dimensions |
| `default_sort` | `last_read` | Default sort column |
| `grid_view` | `true` | Default to grid vs list view |

### Resetting Settings

If the app misbehaves, delete `config.json` and restart. It will recreate with defaults.

---

## Troubleshooting

### Cannot Connect to MongoDB

**Symptoms:** Setup wizard appears on every launch, or "Cannot reach MongoDB server" error.

**Solutions:**

1. **Check if MongoDB service is running:**
   ```cmd
   net start MongoDB
   ```
   If it says the service does not exist, reinstall MongoDB and check "Install as Service."

2. **Start the service manually:**
   ```cmd
   sc start MongoDB
   ```

3. **Check the port:** Open `config.json` and verify `mongo_uri` is `mongodb://localhost:27017`

4. **Firewall:** Ensure Windows Firewall allows MongoDB on port 27017

### Scraping Fails

**Symptoms:** "Scrape Failed" or "Could not extract title" when fetching metadata.

**Solutions:**

- The website may have changed its layout. Use **manual entry** instead.
- Check your internet connection.
- Some sites block automated access. There is no workaround — manual entry is required.
- Try the **Open** button to verify the URL loads in your browser.

### Cover Image Won't Load

**Symptoms:** "No Cover" displayed, or download fails.

**Solutions:**

- Check internet connection
- The cover URL may have expired. Try **Fetch Metadata** again
- Manually load a cover from your computer

### App Won't Start

**Solutions:**

1. Delete `%LOCALAPPDATA%\LibraryOfYore\config.json`
2. Restart the app
3. If still broken, check `logs/` folder for error details

### Excel Export Fails

**Symptoms:** "Export Failed" error.

**Solutions:**

- Ensure you have write permission to the chosen folder
- Try saving to Desktop or Documents
- Check if the file is open in another program

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + N` | Add new novel |
| `Ctrl + R` | Refresh library |
| `Ctrl + E` | Export to Excel |
| `F5` | Refresh library |
| `Delete` | Delete selected novel (when card is focused) |
| `Enter` | Open selected novel |

---

## Data Backup & Migration

### Backing Up

**Method 1: MongoDB Dump (Complete)**
```bash
mongodump --db libraryofyore --out C:\backup\libraryofyore-$(Get-Date -Format yyyy-MM-dd)
```

**Method 2: Excel Export (Readable)**
Use the **Export Excel** button in the app.

### Restoring

```bash
mongorestore --db libraryofyore C:\backup\libraryofyore-YYYY-MM-DD\libraryofyore
```

### Moving to Another PC

1. Export your library to Excel
2. Install Library of Yore and MongoDB on the new PC
3. Re-add novels manually, or
4. Use the Excel file as reference

---

## FAQ

**Q: Is my data stored online?**  
A: No. Everything is stored locally in your MongoDB database. No accounts, no cloud, no tracking.

**Q: Can I use this on Mac or Linux?**  
A: The code is Python and could run on any OS, but the build scripts and installer are Windows-only. You would need to install dependencies manually and run `python main.py`.

**Q: How many novels can I store?**  
A: MongoDB handles millions of documents. Your limit is your disk space.

**Q: Can I add support for other novel sites?**  
A: Yes. Create a new scraper in `scrapers/` that inherits from `BaseScraper`, then add it to the factory in `scrapers/__init__.py`.

**Q: Is there a mobile app?**  
A: Not currently. Library of Yore is desktop-only.

---

## Getting Help

- **Bug reports:** Open an issue on GitHub
- **Feature requests:** Open an issue with the "enhancement" label
- **Questions:** Start a Discussion on GitHub

---

<div align="center">

**Happy Reading!**

</div>
