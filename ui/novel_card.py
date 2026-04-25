"""Novel card widget for grid view."""
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QFont

from database.models import Novel
from utils.helpers import bytes_to_pixmap


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
        self.setFixedSize(200, 320)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build_ui(cover_bytes)
        self._apply_style()

    def _build_ui(self, cover_bytes: bytes):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Cover image
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(184, 230)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setStyleSheet("background-color: #2a2a2a; border-radius: 4px;")

        if cover_bytes:
            pixmap = bytes_to_pixmap(cover_bytes, 184, 230)
            self.cover_label.setPixmap(pixmap)
        else:
            self.cover_label.setText("No Cover")
            self.cover_label.setStyleSheet(
                "background-color: #2a2a2a; color: #666; font-size: 14px; border-radius: 4px;"
            )
        layout.addWidget(self.cover_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Title
        self.title_label = QLabel(self.novel.title)
        self.title_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        self.title_label.setMaximumHeight(40)
        layout.addWidget(self.title_label)

        # Status badge + chapter info
        info_layout = QHBoxLayout()
        self.status_label = QLabel(self.novel.status.upper())
        self.status_label.setStyleSheet(self._status_style(self.novel.status))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(self.status_label)

        self.chapter_label = QLabel("Ch " + str(self.novel.current_chapter))
        self.chapter_label.setStyleSheet("color: #aaa; font-size: 11px;")
        self.chapter_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        info_layout.addWidget(self.chapter_label)
        layout.addLayout(info_layout)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(int(self.novel.percent_complete))
        self.progress.setTextVisible(True)
        self.progress.setFormat(str(int(self.novel.percent_complete)) + "%")
        self.progress.setMaximumHeight(14)
        layout.addWidget(self.progress)

        # Quick action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)

        self.plus_btn = QPushButton("+1")
        self.plus_btn.setToolTip("Increment chapter")
        self.plus_btn.setMaximumWidth(36)
        self.plus_btn.clicked.connect(lambda: self.chapter_plus.emit(self.novel_id))
        btn_layout.addWidget(self.plus_btn)

        self.link_btn = QPushButton("Link")
        self.link_btn.setToolTip("Open source URL")
        self.link_btn.setMaximumWidth(40)
        self.link_btn.clicked.connect(lambda: self.open_url_requested.emit(self.novel.source_url))
        btn_layout.addWidget(self.link_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _apply_style(self):
        self.setStyleSheet("""
            NovelCard {
                background-color: #1e1e1e;
                border: 1px solid #333;
                border-radius: 8px;
            }
            NovelCard:hover {
                border: 1px solid #555;
                background-color: #252525;
            }
            QProgressBar {
                border: none;
                border-radius: 3px;
                background-color: #333;
                text-align: center;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background-color: #d4af37;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #333;
                color: #ddd;
                border: none;
                border-radius: 4px;
                padding: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #444;
            }
        """)

    def _status_style(self, status: str) -> str:
        colors = {
            "ongoing": "#2196f3",
            "completed": "#d4af37",
            "hiatus": "#ff9800",
            "dropped": "#f44336",
            "planned": "#9c27b0",
        }
        color = colors.get(status, "#666")
        return """
            background-color: """ + color + """22;
            color: """ + color + """;
            border: 1px solid """ + color + """;
            border-radius: 4px;
            padding: 2px 6px;
            font-size: 10px;
            font-weight: bold;
        """

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
        self.chapter_label.setText("Ch " + str(current))
        self.progress.setValue(int(self.novel.percent_complete))
        self.progress.setFormat(str(int(self.novel.percent_complete)) + "%")
