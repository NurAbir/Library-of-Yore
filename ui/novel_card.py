"""Novel card widget for grid view."""
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QMenu,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from database.models import Novel
from utils.helpers import bytes_to_pixmap
from ui import theme


class NovelCard(QFrame):
    """Visual card representing a novel in the library grid."""

    clicked = pyqtSignal(str)
    edit_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    open_url_requested = pyqtSignal(str)
    chapter_plus = pyqtSignal(str)

    def __init__(self, novel: Novel, cover_bytes: bytes = None, parent=None):
        super().__init__(parent)
        self.novel_id = novel._id
        self.novel = novel
        self.setObjectName("NovelCard")
        self.setFixedSize(208, 336)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build_ui(cover_bytes)
        self._apply_style()
        self._apply_shadow()

    def _apply_shadow(self):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 110))
        self.setGraphicsEffect(shadow)

    def _build_ui(self, cover_bytes: bytes):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Cover image
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(188, 236)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setObjectName("coverLabel")

        if cover_bytes:
            pixmap = bytes_to_pixmap(cover_bytes, 188, 236)
            self.cover_label.setPixmap(pixmap)
        else:
            self.cover_label.setText("📖\nNo Cover")
        layout.addWidget(self.cover_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # "Updated" badge — overlaid on the top-right of the cover, hidden until mark_updated()
        self.update_badge = QLabel("✦ Updated", self)
        self.update_badge.setStyleSheet(f"""
            background-color: {theme.ACCENT};
            color: {theme.ACCENT_TEXT_ON};
            border-radius: 4px;
            padding: 3px 7px;
            font-size: 9px;
            font-weight: 700;
        """)
        self.update_badge.adjustSize()
        self.update_badge.move(self.width() - self.update_badge.width() - 12, 12)
        self.update_badge.hide()
        self.update_badge.raise_()

        self.title_label = QLabel(self.novel.title)
        self.title_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.title_label.setStyleSheet(f"color: {theme.TEXT_PRIMARY};")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        self.title_label.setMaximumHeight(40)
        layout.addWidget(self.title_label)

        # Status badge + chapter info
        info_layout = QHBoxLayout()
        info_layout.setSpacing(6)
        self.status_label = QLabel(self.novel.status.upper())
        self.status_label.setStyleSheet(theme.status_badge_style(self.novel.status))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(self.status_label)

        info_layout.addStretch()

        self.chapter_label = QLabel("Ch. " + str(self.novel.current_chapter))
        self.chapter_label.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 11px; font-weight: 600;")
        self.chapter_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        info_layout.addWidget(self.chapter_label)
        layout.addLayout(info_layout)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(int(self.novel.percent_complete))
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        layout.addWidget(self.progress)

        # Quick action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        self.plus_btn = QPushButton("+1 Chapter")
        self.plus_btn.setToolTip("Increment chapter")
        self.plus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.plus_btn.clicked.connect(lambda: self.chapter_plus.emit(self.novel_id))
        btn_layout.addWidget(self.plus_btn, stretch=2)

        self.link_btn = QPushButton("🔗")
        self.link_btn.setToolTip("Open source URL")
        self.link_btn.setFixedWidth(34)
        self.link_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.link_btn.clicked.connect(lambda: self.open_url_requested.emit(self.novel.source_url))
        btn_layout.addWidget(self.link_btn, stretch=1)

        layout.addLayout(btn_layout)

    def _apply_style(self):
        self.setStyleSheet(f"""
            #NovelCard {{
                background-color: {theme.BG_SURFACE};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.RADIUS_LG}px;
            }}
            #NovelCard:hover {{
                border: 1px solid {theme.ACCENT}77;
                background-color: {theme.BG_SURFACE_2};
            }}
            #coverLabel {{
                background-color: {theme.BG_SUNKEN};
                color: {theme.TEXT_MUTED};
                font-size: 12px;
                border-radius: {theme.RADIUS}px;
                border: 1px solid {theme.BORDER};
            }}
            QProgressBar {{
                border: none;
                border-radius: 3px;
                background-color: {theme.BG_SUNKEN};
            }}
            QProgressBar::chunk {{
                background-color: {theme.ACCENT};
                border-radius: 3px;
            }}
            QPushButton {{
                background-color: {theme.BG_SURFACE_2};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER_STRONG};
                border-radius: {theme.RADIUS_SM}px;
                padding: 5px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {theme.ACCENT}22;
                border-color: {theme.ACCENT};
                color: {theme.ACCENT};
            }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.novel_id)
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.addAction("Edit", lambda: self.edit_requested.emit(self.novel_id))
        menu.addAction("Open Source URL", lambda: self.open_url_requested.emit(self.novel.source_url))
        menu.addSeparator()
        menu.addAction("Delete", lambda: self.delete_requested.emit(self.novel_id))
        menu.exec(pos)

    def update_progress(self, current: int, total: int = None):
        self.novel.current_chapter = current
        if total:
            self.novel.total_chapters = total
        self.chapter_label.setText("Ch. " + str(current))
        self.progress.setValue(int(self.novel.percent_complete))

    def update_status(self, status: str):
        """Update the status badge without a full card rebuild."""
        self.novel.status = status
        self.status_label.setText(status.upper())
        self.status_label.setStyleSheet(theme.status_badge_style(status))

    def update_latest_chapter(self, total: int):
        """Update total/latest chapter count and refresh progress bar."""
        if total and total != self.novel.total_chapters:
            self.novel.total_chapters = total
            self.progress.setValue(int(self.novel.percent_complete))

    def mark_updated(self):
        """Show a gold badge on the card to signal that new data was auto-fetched."""
        self.update_badge.adjustSize()
        self.update_badge.move(self.width() - self.update_badge.width() - 12, 12)
        self.update_badge.show()
        self.update_badge.raise_()
