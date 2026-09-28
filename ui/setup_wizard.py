"""First-run dialog offering to import a pre-2.0 MongoDB library.

Since v2.0, Library of Yore stores everything locally (no database server
needed), so this dialog is no longer a required setup step. It only appears
when a novels collection from an old MongoDB-based install is actually found
on the machine — on a fresh install with no MongoDB at all, it never shows.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QProgressBar, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap

from config import get_asset_path
from ui import theme


class ImportWorker(QThread):
    """Background thread that runs the actual MongoDB → local-file import."""
    progress = pyqtSignal(int, int)   # imported, total
    finished = pyqtSignal(int)        # total imported
    error = pyqtSignal(str)

    def run(self):
        from database.legacy_mongo import import_legacy_library
        try:
            count = import_legacy_library(progress_cb=lambda i, t: self.progress.emit(i, t))
            self.finished.emit(count)
        except Exception as e:
            self.error.emit(str(e))


class ImportWizard(QDialog):
    """Shown when an existing pre-2.0 MongoDB library is detected."""

    def __init__(self, novel_count: int, parent=None):
        super().__init__(parent)
        self.novel_count = novel_count
        self.setWindowTitle("Library of Yore — Import Existing Library")
        self.setMinimumSize(480, 320)
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(theme.dialog_stylesheet())

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(28, 28, 28, 24)

        logo_label = QLabel()
        logo_pixmap = QPixmap(get_asset_path("logo_icon.png"))
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaled(
                72, 72, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            ))
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo_label)

        title = QLabel("Existing Library Found")
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {theme.TEXT_PRIMARY};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        info = QLabel(
            f"Library of Yore found <b>{self.novel_count} novel(s)</b> in an existing "
            "MongoDB library from a previous version. Since v2.0, your library is stored "
            "locally on this machine — no database server required."
            "<br><br>Import them now so nothing is lost? You can safely uninstall MongoDB "
            "afterward."
        )
        info.setWordWrap(True)
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 13px;")
        layout.addWidget(info)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {theme.BORDER};")
        layout.addWidget(line)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, max(self.novel_count, 1))
        self.progress.setValue(0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        btn_layout = QHBoxLayout()

        self.skip_btn = QPushButton("Skip — Start Fresh")
        self.skip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.skip_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.skip_btn)

        btn_layout.addStretch()

        self.import_btn = QPushButton("Import Now →")
        self.import_btn.setObjectName("primaryButton")
        self.import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.import_btn.setDefault(True)
        self.import_btn.clicked.connect(self._start_import)
        btn_layout.addWidget(self.import_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

    def _start_import(self):
        self.import_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.status_label.setText("Importing…")
        self.status_label.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")

        self.worker = ImportWorker()
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, imported: int, total: int):
        self.progress.setValue(imported)
        self.status_label.setText(f"Imported {imported} of {total}…")

    def _on_finished(self, count: int):
        self.status_label.setText(f"✓ Imported {count} novel(s) successfully.")
        self.status_label.setStyleSheet(f"color: {theme.SUCCESS}; font-weight: 600;")
        QMessageBox.information(
            self, "Import Complete",
            f"Imported {count} novel(s) into your new local library."
            + chr(10) + chr(10) +
            "You can now uninstall MongoDB if you like — Library of Yore no longer needs it."
        )
        self.accept()

    def _on_error(self, msg: str):
        self.status_label.setText(f"✕ Import failed: {msg}")
        self.status_label.setStyleSheet(f"color: {theme.DANGER}; font-weight: 600;")
        self.import_btn.setEnabled(True)
        self.skip_btn.setEnabled(True)
