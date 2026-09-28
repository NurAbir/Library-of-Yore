"""Novel card widget for grid view."""
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QMenu,
    QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt6.QtCore import Qt, QRect, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QFontMetrics

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

    # Card geometry. The height leaves room for a two-line title, the status
    # row, the progress bar and the buttons without Qt squeezing anything
    # (at 336px the rows were compressed and badges/titles got clipped).
    CARD_WIDTH = 208
    CARD_HEIGHT = 372
    INNER_WIDTH = CARD_WIDTH - 20   # minus left/right margins

    def __init__(self, novel: Novel, cover_bytes: bytes = None, parent=None):
        super().__init__(parent)
        self.novel_id = novel._id
        self.novel = novel
        self.setObjectName("NovelCard")
        self.setFixedSize(self.CARD_WIDTH, self.CARD_HEIGHT)
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
        layout.setSpacing(7)

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
        self.update_badge.move(self.width() - self.update_badge.width() - 16, 16)
        self.update_badge.hide()
        self.update_badge.raise_()

        # "MANGA" tag, overlaid on the top-left of the cover like the Updated
        # badge, so a novel and its manhwa adaptation are easy to tell apart
        # without taking space from the status row.
        self.type_label = QLabel("MANGA", self)
        self.type_label.setStyleSheet(theme.type_tag_style())
        self.type_label.adjustSize()
        self.type_label.move(16, 16)
        self.type_label.setVisible(self.novel.content_type == "manga")
        self.type_label.raise_()

        # Title: always two lines tall, elided with "…" if longer (the full
        # title is in the card's tooltip).
        title_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        self.title_label = QLabel()
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet(f"color: {theme.TEXT_PRIMARY}; background: transparent;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.title_label.setWordWrap(True)
        fm = QFontMetrics(title_font)
        self.title_label.setFixedHeight(self._two_line_height(fm) + 2)
        self.title_label.setText(self._elide_title(self.novel.title, fm))
        layout.addWidget(self.title_label)

        # Status badge + chapter info
        info_layout = QHBoxLayout()
        info_layout.setSpacing(6)
        self.status_label = QLabel(self.novel.status.upper())
        self.status_label.setStyleSheet(theme.status_badge_style(self.novel.status))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Never let the badge be squeezed (that clipped "ONGOING" to "NGOIN")
        self.status_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        info_layout.addWidget(self.status_label)

        info_layout.addStretch()

        self.chapter_label = QLabel()
        self.chapter_label.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 11px; font-weight: 600;")
        self.chapter_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        info_layout.addWidget(self.chapter_label)
        layout.addLayout(info_layout)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        layout.addWidget(self.progress)

        # Quick action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        self.plus_btn = QPushButton("+1 Chapter")
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
        self._render_progress()

    def _elide_title(self, title: str, fm: QFontMetrics) -> str:
        """Shorten a title so it fits in two word-wrapped lines, ending with
        "…" when cut. Measured with the same wrapping the label uses, so the
        last word is never silently hidden on a third line."""
        max_height = self._two_line_height(fm)

        def fits(text):
            rect = fm.boundingRect(QRect(0, 0, self.INNER_WIDTH, 10_000),
                                   int(Qt.TextFlag.TextWordWrap), text)
            return rect.height() <= max_height

        if fits(title):
            return title
        words = title.split()
        while len(words) > 1:
            words.pop()
            candidate = " ".join(words).rstrip(",:;-") + "…"
            if fits(candidate):
                return candidate
        return fm.elidedText(title, Qt.TextElideMode.ElideRight, self.INNER_WIDTH * 2 - 20)

    def _two_line_height(self, fm: QFontMetrics) -> int:
        """Height of exactly two wrapped lines, measured the way the label
        lays text out (can be a pixel or two more than 2 x lineSpacing)."""
        return fm.boundingRect(QRect(0, 0, self.INNER_WIDTH, 10_000),
                               int(Qt.TextFlag.TextWordWrap), "Ag\nAg").height()

    def _fit_chapter_text(self, current: str, latest) -> str:
        """Longest chapter text that fits beside the status badge:
        "Ch 1234.5 / 2100" -> "1234.5 / 2100" -> "1234.5"."""
        font = QFont(self.font())
        font.setPixelSize(11)
        font.setWeight(QFont.Weight.DemiBold)
        fm = QFontMetrics(font)
        available = self.INNER_WIDTH - self.status_label.sizeHint().width() - 10
        options = [f"Ch {current} / {latest}", f"{current} / {latest}", f"Ch {current}", current] \
            if latest else [f"Ch {current}", current]
        for text in options:
            if fm.horizontalAdvance(text) <= available:
                return text
        return options[-1]

    def _render_progress(self):
        """Refresh the chapter label, progress bar and tooltips from
        self.novel (chapter numbers are strings such as "12" or "2.5")."""
        n = self.novel
        p = n.progress
        current = n.current_chapter if n.current_chapter is not None else "–"
        latest = n.latest_chapter
        self.chapter_label.setText(self._fit_chapter_text(current, latest))
        self.progress.setValue(int(p.percent))

        if n.current_chapter is None:
            state = "Not started"
        elif p.up_to_date:
            state = "Up to date"
        elif p.behind is not None:
            state = f"{p.behind} chapter{'s' if p.behind != 1 else ''} behind"
        else:
            state = "Latest chapter unknown"
        if p.locked_behind:
            state += f" · {p.locked_behind} locked"
        tip = f"{n.title}\nChapter {current}" + (f" of {latest}" if latest else "") + f"\n{state}"
        if p.mode == "list":
            tip += f"\n{p.total} chapters listed on the site"
        self.setToolTip(tip)
        self.progress.setToolTip(state)
        self.plus_btn.setToolTip(f"Mark chapter {p.next_chapter} as read")
        color = theme.SUCCESS if p.up_to_date else theme.TEXT_SECONDARY
        self.chapter_label.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 600; background: transparent;")

    def set_novel(self, novel: Novel):
        """Show fresh data for this card's novel without rebuilding it."""
        self.novel = novel
        self.status_label.setText(novel.status.upper())
        self.status_label.setStyleSheet(theme.status_badge_style(novel.status))
        self.status_label.adjustSize()
        self.type_label.setVisible(novel.content_type == "manga")
        self.title_label.setText(self._elide_title(novel.title, QFontMetrics(self.title_label.font())))
        self._render_progress()

    def _apply_style(self):
        self.setStyleSheet(f"""
            #NovelCard {{
                background-color: {theme.BG_SURFACE};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.RADIUS_LG}px;
            }}
            #NovelCard:hover {{
                border: 1px solid {theme.rgba(theme.ACCENT, "77")};
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
                background-color: {theme.rgba(theme.ACCENT, "22")};
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


    def mark_updated(self):
        """Show a gold badge on the card to signal that new data was auto-fetched."""
        self.update_badge.adjustSize()
        self.update_badge.move(self.width() - self.update_badge.width() - 16, 16)
        self.update_badge.show()
        self.update_badge.raise_()
