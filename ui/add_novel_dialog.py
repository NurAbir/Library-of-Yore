"""Dialog for adding or editing a novel with scraping support."""
import webbrowser
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTextEdit, QSpinBox, QComboBox, QFormLayout, QGroupBox,
    QMessageBox, QProgressDialog, QFileDialog, QCompleter, QSplitter,
    QFrame, QSizePolicy, QScrollArea, QWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap

from database.models import Novel, NovelRepository
from scrapers import get_scraper_for_url
from utils.helpers import download_image, bytes_to_pixmap
from config import STATUSES, get_asset_path


class ScrapeWorker(QThread):
    """Background worker to scrape novel metadata."""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        scraper = get_scraper_for_url(self.url)
        if not scraper:
            self.error.emit("No scraper available for this URL.")
            return
        try:
            result = scraper.scrape(self.url)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class AddNovelDialog(QDialog):
    """Dialog to add a new novel or edit existing one."""

    novel_saved = pyqtSignal()

    def __init__(self, repo: NovelRepository, novel: Novel = None, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.novel = novel
        self.is_edit = novel is not None
        self.cover_image_bytes = None
        self.scraped_cover_url = ""

        self.setWindowTitle("Edit Novel" if self.is_edit else "Add Novel")
        self.setMinimumSize(750, 850)
        self.resize(800, 900)
        self._build_ui()
        if self.is_edit:
            self._load_novel_data()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 24, 24, 24)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(20)
        layout.setContentsMargins(0, 0, 12, 0)

        # === SOURCE URL SECTION ===
        url_group = QGroupBox("Source URL (Auto-Fill)")
        url_group.setStyleSheet(self._groupbox_style())
        url_layout = QHBoxLayout()
        url_layout.setSpacing(10)
        url_layout.setContentsMargins(16, 20, 16, 16)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.webnovel.com/book/...  or  https://novelfire.net/novel/...")
        self.url_input.setMinimumHeight(36)
        self.url_input.textChanged.connect(self._on_url_changed)
        url_layout.addWidget(self.url_input, stretch=3)

        self.fetch_btn = QPushButton("Fetch Metadata")
        self.fetch_btn.setToolTip("Scrape title, cover, chapters from the URL")
        self.fetch_btn.setMinimumHeight(36)
        self.fetch_btn.setEnabled(False)
        self.fetch_btn.clicked.connect(self._start_scrape)
        url_layout.addWidget(self.fetch_btn, stretch=1)

        self.open_url_btn = QPushButton("Open")
        self.open_url_btn.setMinimumHeight(36)
        self.open_url_btn.setEnabled(False)
        self.open_url_btn.clicked.connect(self._open_source_url)
        url_layout.addWidget(self.open_url_btn, stretch=0)

        url_group.setLayout(url_layout)
        layout.addWidget(url_group)

        # === COVER + DETAILS SPLIT ===
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Cover
        cover_widget = QWidget()
        cover_layout = QVBoxLayout(cover_widget)
        cover_layout.setContentsMargins(0, 0, 0, 0)
        cover_layout.setSpacing(12)

        cover_group = QGroupBox("Cover Image")
        cover_group.setStyleSheet(self._groupbox_style())
        cover_inner = QVBoxLayout()
        cover_inner.setContentsMargins(16, 20, 16, 16)
        cover_inner.setSpacing(12)

        self.cover_label = QLabel("No cover")
        self.cover_label.setFixedSize(200, 300)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setStyleSheet("background-color: #252525; border-radius: 8px; color: #666; font-size: 14px;")
        cover_inner.addWidget(self.cover_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.load_cover_btn = QPushButton("Load from File")
        self.load_cover_btn.setMinimumHeight(32)
        self.load_cover_btn.clicked.connect(self._load_cover_from_file)
        cover_inner.addWidget(self.load_cover_btn)

        self.download_cover_btn = QPushButton("Download from URL")
        self.download_cover_btn.setMinimumHeight(32)
        self.download_cover_btn.clicked.connect(self._download_cover_from_url)
        self.download_cover_btn.setEnabled(False)
        cover_inner.addWidget(self.download_cover_btn)

        self.clear_cover_btn = QPushButton("Clear Cover")
        self.clear_cover_btn.setMinimumHeight(32)
        self.clear_cover_btn.clicked.connect(self._clear_cover)
        cover_inner.addWidget(self.clear_cover_btn)

        cover_group.setLayout(cover_inner)
        cover_layout.addWidget(cover_group)
        cover_layout.addStretch()

        splitter.addWidget(cover_widget)

        # Right: Form Fields
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(16)

        details_group = QGroupBox("Novel Details")
        details_group.setStyleSheet(self._groupbox_style())
        form = QFormLayout()
        form.setSpacing(14)
        form.setContentsMargins(16, 20, 16, 16)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Novel title")
        self.title_input.setMinimumHeight(32)
        form.addRow("Title *", self.title_input)

        self.author_input = QLineEdit()
        self.author_input.setPlaceholderText("Author name")
        self.author_input.setMinimumHeight(32)
        form.addRow("Author", self.author_input)

        # Chapter inputs
        chapter_widget = QWidget()
        chapter_layout = QHBoxLayout(chapter_widget)
        chapter_layout.setContentsMargins(0, 0, 0, 0)
        chapter_layout.setSpacing(16)

        self.current_chapter_spin = QSpinBox()
        self.current_chapter_spin.setRange(0, 99999)
        self.current_chapter_spin.setValue(0)
        self.current_chapter_spin.setMinimumHeight(32)
        self.current_chapter_spin.setMinimumWidth(100)
        chapter_layout.addWidget(QLabel("Current:"))
        chapter_layout.addWidget(self.current_chapter_spin)

        self.total_chapter_spin = QSpinBox()
        self.total_chapter_spin.setRange(0, 99999)
        self.total_chapter_spin.setValue(0)
        self.total_chapter_spin.setSpecialValueText("Unknown")
        self.total_chapter_spin.setMinimumHeight(32)
        self.total_chapter_spin.setMinimumWidth(100)
        chapter_layout.addWidget(QLabel("Total:"))
        chapter_layout.addWidget(self.total_chapter_spin)

        chapter_layout.addStretch()
        form.addRow("Chapters", chapter_widget)

        # Status
        self.status_combo = QComboBox()
        self.status_combo.addItems([s.title() for s in STATUSES])
        self.status_combo.setMinimumHeight(32)
        form.addRow("Status", self.status_combo)

        # Rating
        self.rating_spin = QSpinBox()
        self.rating_spin.setRange(0, 10)
        self.rating_spin.setSuffix(" / 10")
        self.rating_spin.setMinimumHeight(32)
        self.rating_spin.setMinimumWidth(80)
        form.addRow("Your Rating", self.rating_spin)

        # Genres
        self.genres_input = QLineEdit()
        self.genres_input.setPlaceholderText("Fantasy, Romance, Action (comma separated)")
        self.genres_input.setMinimumHeight(32)
        form.addRow("Genres", self.genres_input)

        details_group.setLayout(form)
        form_layout.addWidget(details_group)

        # Text sections
        text_group = QGroupBox("Description & Notes")
        text_group.setStyleSheet(self._groupbox_style())
        text_inner = QVBoxLayout()
        text_inner.setContentsMargins(16, 20, 16, 16)
        text_inner.setSpacing(12)

        self.synopsis_input = QTextEdit()
        self.synopsis_input.setPlaceholderText("Auto-fetched synopsis will appear here...")
        self.synopsis_input.setMinimumHeight(100)
        self.synopsis_input.setMaximumHeight(150)
        text_inner.addWidget(QLabel("Synopsis"))
        text_inner.addWidget(self.synopsis_input)

        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Your personal notes about this novel...")
        self.notes_input.setMinimumHeight(80)
        self.notes_input.setMaximumHeight(120)
        text_inner.addWidget(QLabel("Notes"))
        text_inner.addWidget(self.notes_input)

        text_group.setLayout(text_inner)
        form_layout.addWidget(text_group)
        form_layout.addStretch()

        splitter.addWidget(form_widget)
        splitter.setSizes([260, 540])
        layout.addWidget(splitter)

        # === BUTTONS ===
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        btn_layout.addStretch()

        self.save_btn = QPushButton("Save Novel")
        self.save_btn.setDefault(True)
        self.save_btn.setMinimumHeight(40)
        self.save_btn.setMinimumWidth(140)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #d4af37;
                color: #1a1a1a;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #b8962e; }
            QPushButton:pressed { background-color: #a08028; }
        """)
        self.save_btn.clicked.connect(self._save_novel)
        btn_layout.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.setMinimumWidth(100)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Global style
        self.setStyleSheet("""
            QDialog { background-color: #121212; color: #eee; }
            QGroupBox {
                color: #d4af37;
                font-weight: bold;
                font-size: 13px;
                border: 1px solid #333;
                border-radius: 8px;
                margin-top: 14px;
                padding-top: 10px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
            QLineEdit, QTextEdit, QSpinBox, QComboBox {
                background-color: #1e1e1e;
                color: #eee;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
            }
            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {
                border: 1px solid #d4af37;
            }
            QPushButton {
                background-color: #2a2a2a;
                color: #eee;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #333; border-color: #555; }
            QLabel { color: #ccc; font-size: 13px; }
            QScrollBar:vertical {
                background: #1a1a1a;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #444;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover { background: #555; }
        """)

    def _groupbox_style(self):
        return """
            QGroupBox {
                color: #d4af37;
                font-weight: bold;
                font-size: 13px;
                border: 1px solid #333;
                border-radius: 8px;
                margin-top: 14px;
                padding-top: 10px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
        """

    def _on_url_changed(self, text: str):
        has_url = bool(text.strip())
        self.fetch_btn.setEnabled(has_url)
        self.open_url_btn.setEnabled(has_url)

    def _start_scrape(self):
        url = self.url_input.text().strip()
        if not url:
            return

        self.fetch_btn.setEnabled(False)
        self.fetch_btn.setText("Fetching...")

        self.scrape_worker = ScrapeWorker(url)
        self.scrape_worker.finished.connect(self._on_scrape_finished)
        self.scrape_worker.error.connect(self._on_scrape_error)
        self.scrape_worker.start()

    def _on_scrape_finished(self, result):
        self.fetch_btn.setEnabled(True)
        self.fetch_btn.setText("Fetch Metadata")

        if not result.success:
            QMessageBox.warning(self, "Scrape Failed", result.error_message or "Unknown error")
            return

        if result.title and not self.title_input.text():
            self.title_input.setText(result.title)
        if result.author and not self.author_input.text():
            self.author_input.setText(result.author)
        if result.synopsis and not self.synopsis_input.toPlainText():
            self.synopsis_input.setPlainText(result.synopsis)
        if result.total_chapters and self.total_chapter_spin.value() == 0:
            self.total_chapter_spin.setValue(result.total_chapters)
        if result.genres:
            self.genres_input.setText(", ".join(result.genres))
        if result.status:
            idx = self.status_combo.findText(result.status.title())
            if idx >= 0:
                self.status_combo.setCurrentIndex(idx)

        if result.cover_url:
            self.scraped_cover_url = result.cover_url
            self.download_cover_btn.setEnabled(True)
            self._download_cover_from_url()

        msg = "Title: " + result.title + chr(10) + "Author: " + result.author + chr(10) + "Chapters: " + str(result.total_chapters or "N/A")
        QMessageBox.information(self, "Metadata Fetched", msg)

    def _on_scrape_error(self, msg: str):
        self.fetch_btn.setEnabled(True)
        self.fetch_btn.setText("Fetch Metadata")
        QMessageBox.critical(self, "Scrape Error", msg)

    def _load_cover_from_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Cover Image", "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if path:
            with open(path, "rb") as f:
                self.cover_image_bytes = f.read()
            self._update_cover_preview(self.cover_image_bytes)
            self.scraped_cover_url = ""

    def _download_cover_from_url(self):
        url = self.scraped_cover_url or self.url_input.text().strip()
        if not url:
            return
        try:
            if self.scraped_cover_url:
                self.cover_image_bytes = download_image(self.scraped_cover_url)
            else:
                scraper = get_scraper_for_url(url)
                if scraper:
                    result = scraper.scrape(url)
                    if result.cover_url:
                        self.cover_image_bytes = download_image(result.cover_url)
            if self.cover_image_bytes:
                self._update_cover_preview(self.cover_image_bytes)
        except Exception as e:
            QMessageBox.warning(self, "Cover Download Failed", str(e))

    def _clear_cover(self):
        self.cover_image_bytes = None
        self.scraped_cover_url = ""
        self.cover_label.setText("No cover")
        self.cover_label.setPixmap(QPixmap())
        self.cover_label.setStyleSheet("background-color: #252525; border-radius: 8px; color: #666; font-size: 14px;")

    def _update_cover_preview(self, image_bytes: bytes):
        pixmap = bytes_to_pixmap(image_bytes, 200, 300)
        self.cover_label.setPixmap(pixmap)
        self.cover_label.setText("")

    def _open_source_url(self):
        url = self.url_input.text().strip()
        if url:
            webbrowser.open(url)

    def _load_novel_data(self):
        self.title_input.setText(self.novel.title)
        self.author_input.setText(self.novel.author)
        self.url_input.setText(self.novel.source_url)
        self.current_chapter_spin.setValue(self.novel.current_chapter)
        if self.novel.total_chapters:
            self.total_chapter_spin.setValue(self.novel.total_chapters)
        idx = self.status_combo.findText(self.novel.status.title())
        if idx >= 0:
            self.status_combo.setCurrentIndex(idx)
        self.rating_spin.setValue(self.novel.rating)
        self.genres_input.setText(", ".join(self.novel.genres))
        self.synopsis_input.setPlainText(self.novel.synopsis)
        self.notes_input.setPlainText(self.novel.notes)

        if self.novel.cover_image_id:
            cover_bytes = self.repo.get_cover(self.novel.cover_image_id)
            if cover_bytes:
                self.cover_image_bytes = cover_bytes
                self._update_cover_preview(cover_bytes)

    def _save_novel(self):
        title = self.title_input.text().strip()
        if not title:
            QMessageBox.warning(self, "Validation Error", "Title is required.")
            return

        novel = Novel(
            _id=self.novel._id if self.is_edit else None,
            title=title,
            author=self.author_input.text().strip(),
            source_url=self.url_input.text().strip(),
            source_name="manual",
            current_chapter=self.current_chapter_spin.value(),
            total_chapters=self.total_chapter_spin.value() if self.total_chapter_spin.value() > 0 else None,
            status=self.status_combo.currentText().lower(),
            rating=self.rating_spin.value(),
            genres=[g.strip() for g in self.genres_input.text().split(",") if g.strip()],
            synopsis=self.synopsis_input.toPlainText().strip(),
            notes=self.notes_input.toPlainText().strip(),
        )

        if novel.source_url:
            if "webnovel.com" in novel.source_url.lower():
                novel.source_name = "webnovel"
            elif "novelfire" in novel.source_url.lower():
                novel.source_name = "novelfire"

        if self.cover_image_bytes:
            if self.is_edit and self.novel.cover_image_id:
                try:
                    self.repo.fs.delete(self.novel.cover_image_id)
                except Exception:
                    pass
            cover_id = self.repo.save_cover(self.cover_image_bytes, title + ".jpg")
            novel.cover_image_id = cover_id

        if self.is_edit:
            self.repo.update(novel)
        else:
            novel_id = self.repo.insert(novel)
            novel._id = novel_id

        self.novel = novel
        self.novel_saved.emit()
        QMessageBox.information(self, "Saved", "'" + novel.title + "' saved successfully!")
        self.accept()
