"""First-time MongoDB setup wizard."""
import webbrowser
import subprocess
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QMessageBox, QProgressBar, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap

from database.connection import test_connection
from config import save_config, DEFAULT_MONGO_URI, get_asset_path


class ConnectionTester(QThread):
    """Background thread to test MongoDB connection."""
    result = pyqtSignal(bool, str)

    def __init__(self, uri):
        super().__init__()
        self.uri = uri

    def run(self):
        ok, msg = test_connection(self.uri)
        self.result.emit(ok, msg)


class SetupWizard(QDialog):
    """Shown on first launch if MongoDB is not detected."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Library of Yore - First Time Setup")
        self.setMinimumSize(500, 350)
        self._build_ui()
        self._test_connection()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        # Logo
        logo_label = QLabel()
        logo_path = get_asset_path("logo.png")
        logo_pixmap = QPixmap(logo_path)
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo_label)

        title = QLabel("Welcome to Library of Yore")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        info = QLabel(
            "Library of Yore needs <b>MongoDB Community Server</b> to store your library. "
            "If you haven't installed it yet, download it from the official site."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #444;")
        layout.addWidget(line)

        # MongoDB URI input
        uri_layout = QHBoxLayout()
        uri_layout.addWidget(QLabel("MongoDB URI:"))
        self.uri_input = QLineEdit(DEFAULT_MONGO_URI)
        self.uri_input.setPlaceholderText("mongodb://localhost:27017")
        uri_layout.addWidget(self.uri_input)
        layout.addLayout(uri_layout)

        # Status
        self.status_label = QLabel("Testing connection...")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # Indeterminate
        layout.addWidget(self.progress)

        # Buttons
        btn_layout = QHBoxLayout()

        self.download_btn = QPushButton(" Download MongoDB")
        self.download_btn.setToolTip("Open MongoDB download page in browser")
        self.download_btn.clicked.connect(self._open_download_page)
        btn_layout.addWidget(self.download_btn)

        self.start_svc_btn = QPushButton(" Start MongoDB Service")
        self.start_svc_btn.setToolTip("Try to start MongoDB Windows service")
        self.start_svc_btn.clicked.connect(self._start_service)
        btn_layout.addWidget(self.start_svc_btn)

        btn_layout.addStretch()

        self.retry_btn = QPushButton(" Retry Connection")
        self.retry_btn.setDefault(True)
        self.retry_btn.clicked.connect(self._test_connection)
        btn_layout.addWidget(self.retry_btn)

        self.continue_btn = QPushButton("Continue →")
        self.continue_btn.setEnabled(False)
        self.continue_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.continue_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

        # Footer note
        note = QLabel(
            "<i>Tip: After installing MongoDB, make sure the service is running. "
            "You can change this later in Settings.</i>"
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(note)

    def _test_connection(self):
        self.status_label.setText("Testing connection...")
        self.status_label.setStyleSheet("color: #aaa;")
        self.progress.setRange(0, 0)
        self.continue_btn.setEnabled(False)
        self.retry_btn.setEnabled(False)

        uri = self.uri_input.text().strip()
        self.tester = ConnectionTester(uri)
        self.tester.result.connect(self._on_test_result)
        self.tester.start()

    def _on_test_result(self, ok: bool, msg: str):
        self.progress.setRange(0, 1)
        self.progress.setValue(1 if ok else 0)
        self.retry_btn.setEnabled(True)

        if ok:
            self.status_label.setText(f" {msg}")
            self.status_label.setStyleSheet("color: #d4af37; font-weight: bold;")
            self.continue_btn.setEnabled(True)
            self.continue_btn.setDefault(True)
            save_config({"mongo_uri": self.uri_input.text().strip()})
        else:
            self.status_label.setText(f" {msg}")
            self.status_label.setStyleSheet("color: #f44336;")
            self.continue_btn.setEnabled(False)

    def _open_download_page(self):
        webbrowser.open("https://www.mongodb.com/try/download/community")

    def _start_service(self):
        """Attempt to start MongoDB Windows service."""
        try:
            result = subprocess.run(
                ["net", "start", "MongoDB"],
                capture_output=True, text=True, shell=True
            )
            if result.returncode == 0:
                QMessageBox.information(self, "Service Started", "MongoDB service started successfully.")
                self._test_connection()
            else:
                err_msg = "Could not start MongoDB service." + chr(10) + chr(10)
                err_msg += result.stderr + chr(10) + chr(10)
                err_msg += "Make sure MongoDB is installed and the service name is 'MongoDB'."
                QMessageBox.warning(self, "Service Error", err_msg)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start service: {e}")
