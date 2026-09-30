"""Main application window for LibraryOfYore."""
import webbrowser
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QListWidget, QListWidgetItem,
    QScrollArea, QGridLayout, QFrame, QMessageBox, QFileDialog,
    QStatusBar, QMenuBar, QMenu, QCheckBox, QGroupBox, QSplitter,
    QSystemTrayIcon, QApplication
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QFont, QIcon, QKeySequence

from database.models import NovelRepository, Novel, apply_scrape_result
import api_server
from ui.setup_wizard import ImportWizard
from ui.add_novel_dialog import AddNovelDialog
from ui.novel_card import NovelCard
from ui import theme
from config import STATUSES, EXPORTS_DIR, load_config, save_config, get_asset_path
from utils.helpers import bytes_to_pixmap

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment


class ExportWorker(QThread):
    """Background export to Excel."""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, repo: NovelRepository, filepath: str):
        super().__init__()
        self.repo = repo
        self.filepath = filepath

    def run(self):
        try:
            data = self.repo.export_to_list()
            if not data:
                self.error.emit("No novels to export.")
                return

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Novel Library"

            # Header
            headers = list(data[0].keys())
            ws.append(headers)
            header_fill = PatternFill(start_color="4caf50", end_color="4caf50", fill_type="solid")
            header_font = Font(bold=True, color="FFFFFF")
            for col in range(1, len(headers) + 1):
                cell = ws.cell(row=1, column=col)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center")

            # Data rows
            for row in data:
                ws.append(list(row.values()))

            # Auto-width
            for col in ws.columns:
                max_length = 0
                column = col[0].column_letter
                for cell in col:
                    try:
                        max_length = max(max_length, len(str(cell.value)))
                    except Exception:
                        pass
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column].width = adjusted_width

            wb.save(self.filepath)
            self.finished.emit(self.filepath)
        except Exception as e:
            self.error.emit(str(e))


class NovelRefreshWorker(QThread):
    """Background worker that re-scrapes novels on startup to get the latest
    chapter, chapter list and status without blocking the UI."""

    # novel_id, ScraperResult. Sent as a whole object: before v2.1.0 chapter
    # numbers travelled through int-typed signals, which turn a decimal such
    # as 2.5 into a garbage number without any error.
    novel_updated = pyqtSignal(str, object)
    finished = pyqtSignal(int)              # number of novels successfully scraped

    # Pause between novels so a large library doesn't hit the site with a
    # burst of back-to-back requests on every launch.
    DELAY_BETWEEN_NOVELS_MS = 1500

    def __init__(self, novels):
        super().__init__()
        self.novels = novels  # list of Novel objects with a novelfire source_url

    def run(self):
        from scrapers import get_scraper_for_url
        updated = 0
        for i, novel in enumerate(self.novels):
            if not novel.source_url:
                continue
            if i > 0:
                self.msleep(self.DELAY_BETWEEN_NOVELS_MS)
            scraper = get_scraper_for_url(novel.source_url)
            if not scraper:
                continue
            try:
                result = scraper.scrape(novel.source_url)
                if result.success:
                    self.novel_updated.emit(novel._id, result)
                    updated += 1
            except Exception:
                pass  # Non-fatal — skip silently and move to next novel
        self.finished.emit(updated)


class MainWindow(QMainWindow):
    """Primary application window."""

    # Emitted from the API-server thread via api_server.set_progress_callback;
    # Qt routes it safely to the main thread.
    chapter_updated = pyqtSignal(str, str)  # novel_id, chapter (e.g. "12" or "2.5")

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Library of Yore")
        self.setWindowIcon(QIcon(get_asset_path("logo.ico")))
        self._apply_screen_geometry()
        self.repo = None
        self.novel_cards = {}  # novel_id -> NovelCard, insertion order == display order
        self.current_sort = "last_read"
        self._current_cols = None
        self._force_quit = False  # True only when user picks Quit from tray

        # Debounce grid reflow on window resize so we don't re-layout on every pixel
        self._reflow_timer = QTimer(self)
        self._reflow_timer.setSingleShot(True)
        self._reflow_timer.timeout.connect(self._reflow_grid)

        # Debounce search: rebuild the grid once typing pauses, not per keystroke
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._refresh_library)

        # Cover image bytes by cover file id, so rebuilding the grid (search,
        # filter, sort) doesn't re-read every cover file from disk each time.
        # Cover ids are unique per saved image, so entries never go stale.
        self._cover_cache = {}
        self._tray_hint_shown = False
        # Startup auto-refresh results waiting to be saved: novel_id -> ScraperResult.
        # Saved together (one file write) when the refresh finishes.
        self._pending_refresh = {}

        self._check_db_connection()
        self._build_ui()
        self._apply_theme()
        self._setup_tray()
        self._refresh_library()
        self._start_novelfire_refresh()   # auto-fetch latest chapters/status on open

    def _apply_screen_geometry(self):
        """Detect the screen the app will open on and size the window to fill
        its available area (windowed full-screen, i.e. maximized — not an
        exclusive/kiosk fullscreen mode) rather than a hardcoded resolution."""
        screen = QApplication.primaryScreen()
        if screen:
            available = screen.availableGeometry()
            self.setGeometry(available)
        # Sensible floor so the layout doesn't break on very small/virtual screens
        self.setMinimumSize(1000, 650)

    def _check_db_connection(self):
        """Set up local storage. The very first time the app runs (no
        library.json yet), silently check whether a pre-2.0 MongoDB library
        exists on this machine and, if so, offer to import it — see
        database/legacy_mongo.py. A fresh install with no MongoDB at all
        skips straight past this with no delay."""
        from config import LIBRARY_FILE
        from database.connection import recover_library_file
        from database.legacy_mongo import detect_legacy_library

        recovery_msg = recover_library_file()
        if recovery_msg:
            QMessageBox.warning(self, "Library File Recovered", recovery_msg)

        if not LIBRARY_FILE.exists():
            legacy_count = detect_legacy_library()
            if legacy_count:
                wizard = ImportWizard(legacy_count, self)
                wizard.exec()  # Skip is fine too — either way we continue with local storage below

        self.repo = NovelRepository()
        # Start local API server for the browser extension
        api_server.start()
        # Wire the extension → UI bridge: signal is thread-safe across Qt threads
        self.chapter_updated.connect(self._on_extension_chapter_update)
        api_server.set_progress_callback(
            lambda novel_id, chapter, latest=None: self.chapter_updated.emit(novel_id, str(chapter))
        )

    def _import_legacy_library(self):
        """Manual counterpart to the automatic first-run check — lets someone
        who clicked Skip (or added MongoDB back later) trigger the import at
        any time from the File menu."""
        from database.legacy_mongo import detect_legacy_library
        legacy_count = detect_legacy_library()
        if not legacy_count:
            QMessageBox.information(
                self, "No Existing Library Found",
                "No MongoDB library was found on this machine (checked localhost:27017)."
            )
            return
        wizard = ImportWizard(legacy_count, self)
        if wizard.exec() == ImportWizard.DialogCode.Accepted:
            self._refresh_library()

    def _build_ui(self):
        # Menu bar
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        add_action = file_menu.addAction("Add Novel", self._add_novel)
        add_action.setShortcut(QKeySequence("Ctrl+N"))
        export_action = file_menu.addAction("Export to Excel", self._export_excel)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        file_menu.addSeparator()
        file_menu.addAction("Import Existing MongoDB Library…", self._import_legacy_library)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)

        view_menu = menubar.addMenu("View")
        refresh_action = view_menu.addAction("Refresh", self._refresh_library)
        refresh_action.setShortcuts([QKeySequence("Ctrl+R"), QKeySequence("F5")])

        help_menu = menubar.addMenu("Help")
        help_menu.addAction("About", self._show_about)

        # Central widget with splitter
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # === LEFT SIDEBAR ===
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setMaximumWidth(270)
        sidebar.setMinimumWidth(220)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 20, 16, 16)
        sidebar_layout.setSpacing(16)

        # Brand header
        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        # 46px (was 30px, which made the round badge hard to make out on the
        # dark sidebar). logo_icon.png is the logo cropped tightly to its
        # circle, so the badge fills the space instead of a fuzzy margin.
        logo_label = QLabel()
        logo_label.setPixmap(QIcon(get_asset_path("logo_icon.png")).pixmap(46, 46))
        logo_label.setFixedSize(46, 46)
        brand_row.addWidget(logo_label)
        brand_label = QLabel("Library of Yore")
        brand_label.setObjectName("sidebarBrand")
        brand_row.addWidget(brand_label)
        brand_row.addStretch()
        sidebar_layout.addLayout(brand_row)

        # Search
        search_box = QGroupBox("Search")
        search_layout = QVBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Title, author, notes...")
        self.search_input.textChanged.connect(lambda _text: self._search_timer.start(250))
        search_layout.addWidget(self.search_input)
        search_box.setLayout(search_layout)
        sidebar_layout.addWidget(search_box)

        # Filters
        filter_box = QGroupBox("Filters")
        filter_layout = QVBoxLayout()
        filter_layout.setSpacing(8)
        self.status_checks = {}
        for status in STATUSES:
            cb = QCheckBox(status.title())
            cb.setChecked(True)
            cb.setCursor(Qt.CursorShape.PointingHandCursor)
            cb.stateChanged.connect(self._refresh_library)
            self.status_checks[status] = cb
            filter_layout.addWidget(cb)
        filter_box.setLayout(filter_layout)
        sidebar_layout.addWidget(filter_box)

        # Sort
        sort_box = QGroupBox("Sort By")
        sort_layout = QVBoxLayout()
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "Last Read", "Title", "Rating", "Date Added", "Progress %"
        ])
        self.sort_combo.currentTextChanged.connect(self._on_sort_changed)
        sort_layout.addWidget(self.sort_combo)
        sort_box.setLayout(sort_layout)
        sidebar_layout.addWidget(sort_box)

        sidebar_layout.addStretch()

        # Stats
        self.stats_label = QLabel("0 novels")
        self.stats_label.setObjectName("statsLabel")
        sidebar_layout.addWidget(self.stats_label)

        splitter.addWidget(sidebar)

        # === RIGHT CONTENT ===
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 18, 20, 16)
        content_layout.setSpacing(14)

        # Top toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        page_title = QLabel("My Library")
        page_title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {theme.TEXT_PRIMARY};")
        toolbar.addWidget(page_title)

        toolbar.addStretch()

        self.add_btn = QPushButton("+  Add Novel")
        self.add_btn.setObjectName("primaryButton")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.setMinimumHeight(36)
        self.add_btn.clicked.connect(self._add_novel)
        toolbar.addWidget(self.add_btn)

        self.export_btn = QPushButton("Export Excel")
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.setMinimumHeight(36)
        self.export_btn.clicked.connect(self._export_excel)
        toolbar.addWidget(self.export_btn)

        content_layout.addLayout(toolbar)

        # Thin divider under the toolbar
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet(f"color: {theme.BORDER}; max-height: 1px;")
        content_layout.addWidget(divider)

        # Scroll area for novel grid
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(18)
        self.grid_layout.setContentsMargins(4, 12, 4, 12)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        self.scroll.setWidget(self.grid_container)
        content_layout.addWidget(self.scroll)

        splitter.addWidget(content)
        splitter.setSizes([250, 1050])

        # Status bar
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage(f"Ready  •  Browser extension API: localhost:{api_server.PORT}")

    def _apply_theme(self):
        """Apply the shared dark theme stylesheet."""
        self.setStyleSheet(theme.main_window_stylesheet())

    def _on_sort_changed(self, text: str):
        mapping = {
            "Last Read": "last_read",
            "Title": "title",
            "Rating": "rating",
            "Date Added": "date_added",
            "Progress %": "percent_complete",
        }
        self.current_sort = mapping.get(text, "last_read")
        self._refresh_library()

    def _get_active_filters(self):
        statuses = [s for s, cb in self.status_checks.items() if cb.isChecked()]
        return statuses

    def _compute_grid_columns(self) -> int:
        """How many card columns fit the current scroll viewport width."""
        card_span = NovelCard.CARD_WIDTH + self.grid_layout.spacing()  # card width + grid gap
        viewport_width = self.scroll.viewport().width()
        if viewport_width <= 0:
            return 4  # sane fallback before the window has been laid out/shown
        margins = self.grid_layout.contentsMargins()
        usable = viewport_width - margins.left() - margins.right()
        return max(1, usable // card_span)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Debounce: only reflow once the user stops dragging/resizing
        self._reflow_timer.start(120)

    def _reflow_grid(self):
        """Reposition existing cards into the current column count without
        re-fetching from the database or rebuilding the widgets."""
        if not self.novel_cards:
            return
        cols = self._compute_grid_columns()
        if cols == self._current_cols:
            return
        self._current_cols = cols
        for card in self.novel_cards.values():
            self.grid_layout.removeWidget(card)
        for i, card in enumerate(self.novel_cards.values()):
            row, col = divmod(i, cols)
            self.grid_layout.addWidget(card, row, col)

    def _refresh_library(self):
        """Reload and display novels from database."""
        if not self.repo:
            return

        # Clear existing
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().hide()   # don't leave it painted until deletion runs
                item.widget().deleteLater()
        self.novel_cards.clear()

        # Fetch
        search = self.search_input.text().strip()
        statuses = self._get_active_filters()
        novels = self.repo.get_all(
            status_filter=statuses if statuses else None,
            search_text=search,
            sort_by=self.current_sort,
            sort_order="desc"
        )

        self.stats_label.setText(f"{len(novels)} novel{'s' if len(novels) != 1 else ''}")
        self.statusbar.showMessage(f"Loaded {len(novels)} novels")

        if not novels:
            empty_label = QLabel("📚\nNo novels found — click \u201c+ Add Novel\u201d to get started!")
            empty_label.setObjectName("emptyState")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setContentsMargins(0, 60, 0, 0)
            self.grid_layout.addWidget(empty_label, 0, 0)
            return

        # Populate grid
        cols = self._compute_grid_columns()
        self._current_cols = cols
        for i, novel in enumerate(novels):
            cover_bytes = None
            if novel.cover_image_id:
                cover_bytes = self._cover_cache.get(novel.cover_image_id)
                if cover_bytes is None:
                    cover_bytes = self.repo.get_cover(novel.cover_image_id)
                    if cover_bytes:
                        self._cover_cache[novel.cover_image_id] = cover_bytes

            card = NovelCard(novel, cover_bytes)
            card.clicked.connect(self._on_card_clicked)
            card.edit_requested.connect(self._on_card_edit)
            card.delete_requested.connect(self._on_card_delete)
            card.open_url_requested.connect(self._open_url)
            card.chapter_plus.connect(self._on_chapter_plus)
            self.novel_cards[novel._id] = card

            row = i // cols
            col = i % cols
            self.grid_layout.addWidget(card, row, col)

    def _on_card_clicked(self, novel_id: str):
        self._on_card_edit(novel_id)

    def _on_card_edit(self, novel_id: str):
        novel = self.repo.get_by_id(novel_id)
        if not novel:
            return
        dialog = AddNovelDialog(self.repo, novel, self)
        dialog.novel_saved.connect(self._refresh_library)
        dialog.exec()

    def _on_card_delete(self, novel_id: str):
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this novel? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.repo.delete(novel_id)
            self._refresh_library()

    def _open_url(self, url: str):
        if url:
            webbrowser.open(url)

    def _update_card(self, novel_id: str):
        """Re-read one novel and refresh its card in place."""
        card = self.novel_cards.get(novel_id)
        novel = self.repo.get_by_id(novel_id)
        if card and novel:
            card.set_novel(novel)
        return novel

    def _on_extension_chapter_update(self, novel_id: str, chapter: str):
        """Slot called (on the main thread) when the browser extension updates progress."""
        self._update_card(novel_id)
        self.statusbar.showMessage(f"Extension updated chapter → {chapter}", 3000)

    def _on_chapter_plus(self, novel_id: str):
        novel = self.repo.get_by_id(novel_id)
        if novel:
            # The real next chapter from the site's list when known (2 -> 2.5
            # -> 3, gaps skipped, chapter 0 first from Not started), otherwise
            # the next whole chapter.
            next_chapter = novel.next_chapter
            # Records last_read and read_count the same way the browser
            # extension does
            self.repo.update_chapter_progress(novel_id, next_chapter, increment_read=True)
            self._update_card(novel_id)
            self.statusbar.showMessage(f"Updated '{novel.title}' to chapter {next_chapter}", 3000)

    def _start_novelfire_refresh(self):
        """On startup, silently re-scrape every novel saved from a supported
        site to pull in the latest chapter, chapter list and status, then
        update each card. Novels the site already marks Completed are
        skipped: they don't get new chapters."""
        if not self.repo:
            return
        from scrapers import get_scraper_for_url
        all_novels = self.repo.get_all()
        # Every novel saved from a supported site (since v2.2.0 that's all of
        # them: Novelfire, NovelPhoenix, Wuxiaworld, FreeWebNovel, Flame).
        novelfire_novels = [
            n for n in all_novels
            if n.source_url and get_scraper_for_url(n.source_url) is not None
            and n.site_status != "completed"
        ]
        if not novelfire_novels:
            return

        self.statusbar.showMessage(
            f"Auto-refreshing {len(novelfire_novels)} novel(s) in background…"
        )
        self.refresh_worker = NovelRefreshWorker(novelfire_novels)
        self.refresh_worker.novel_updated.connect(self._on_novel_refreshed)
        self.refresh_worker.finished.connect(self._on_refresh_finished)
        self.refresh_worker.start()

    def _on_novel_refreshed(self, novel_id: str, result):
        """Called (on main thread) for each novel the refresh worker finishes.
        Shows the new site data on the card right away; the save happens once,
        for all novels, when the refresh finishes (see _flush_refresh).
        Updates site data only: never your current chapter, never last_read,
        and never a status you set to Dropped or Planned."""
        novel = self.repo.get_by_id(novel_id)
        if not novel or not apply_scrape_result(novel, result):
            return
        self._pending_refresh[novel_id] = result
        card = self.novel_cards.get(novel_id)
        if card:
            card.set_novel(novel)
            card.mark_updated()
        if len(self._pending_refresh) >= 25:
            self._flush_refresh()  # bound what an interrupted refresh could lose

    def _flush_refresh(self) -> int:
        """Save pending auto-refresh results in one write. Each novel is
        re-read first, so progress the extension recorded (or an edit you
        saved) while the refresh was running isn't overwritten."""
        pending, self._pending_refresh = self._pending_refresh, {}
        to_save = []
        for novel_id, result in pending.items():
            novel = self.repo.get_by_id(novel_id)
            if novel and apply_scrape_result(novel, result):
                to_save.append(novel)
        return self.repo.update_many(to_save)

    def _on_refresh_finished(self, count: int):
        self._flush_refresh()
        msg = (
            f"Auto-refresh complete — {count} novel(s) checked."
            if count else "Auto-refresh complete — no novels could be checked."
        )
        self.statusbar.showMessage(msg, 6000)

    def _add_novel(self):
        dialog = AddNovelDialog(self.repo, parent=self)
        dialog.novel_saved.connect(self._refresh_library)
        dialog.exec()

    def _export_excel(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Library",
            str(EXPORTS_DIR / "novel_library.xlsx"),
            "Excel Files (*.xlsx)"
        )
        if not path:
            return

        self.export_btn.setEnabled(False)
        self.export_btn.setText("⏳ Exporting...")

        self.export_worker = ExportWorker(self.repo, path)
        self.export_worker.finished.connect(self._on_export_done)
        self.export_worker.error.connect(self._on_export_error)
        self.export_worker.start()

    def _on_export_done(self, path: str):
        self.export_btn.setEnabled(True)
        self.export_btn.setText("Export Excel")
        msg = "Library exported to:" + chr(10) + path
        QMessageBox.information(self, "Export Complete", msg)

    def _on_export_error(self, msg: str):
        self.export_btn.setEnabled(True)
        self.export_btn.setText("Export Excel")
        QMessageBox.critical(self, "Export Failed", msg)

    def _show_about(self):
        from config import APP_VERSION
        QMessageBox.about(
            self, "About Library of Yore",
            f"<h2>Library of Yore v{APP_VERSION}</h2>"
            "<p>A desktop bookmark tracker for web novels.</p>"
            "<p>Supports: Novelfire, NovelPhoenix, Wuxiaworld, FreeWebNovel, "
            "Flame Comics (novels and manga)</p>"
            "<p>Built with Python and PyQt6. Stored locally — no database server required.</p>"
            f"<p><b>Browser Extension API:</b> localhost:{api_server.PORT}</p>"
        )

    def _setup_tray(self):
        """Create the system tray icon so the app keeps running when the window is closed."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self.tray_icon = QSystemTrayIcon(QIcon(get_asset_path("logo.ico")), self)
        self.tray_icon.setToolTip("Library of Yore — tracking in background")

        tray_menu = QMenu()

        open_action = QAction("Open Library", self)
        open_action.triggered.connect(self._show_window)
        tray_menu.addAction(open_action)

        tray_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        # Single-click or double-click the tray icon → reopen window
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _show_window(self):
        if self.isMaximized():
            self.showMaximized()
        else:
            self.showNormal()
        self.raise_()
        self.activateWindow()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self._show_window()

    def _quit_app(self):
        self._force_quit = True
        QApplication.quit()

    def closeEvent(self, event):
        if self._force_quit:
            # Real quit — clean up and exit
            if self._pending_refresh:
                self._flush_refresh()
            from database.connection import close_db
            close_db()
            event.accept()
        else:
            # Hide to tray instead of closing
            event.ignore()
            self.hide()
            if hasattr(self, "tray_icon") and not self._tray_hint_shown:
                self._tray_hint_shown = True
                self.tray_icon.showMessage(
                    "Library of Yore",
                    "Still tracking in the background. Right-click the tray icon to quit.",
                    QSystemTrayIcon.MessageIcon.Information,
                    3000
                )
