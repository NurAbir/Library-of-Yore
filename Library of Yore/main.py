"""Entry point for LibraryOfYore desktop application."""
import sys
import os

# Ensure bundled resources are found when running from PyInstaller
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.environ.setdefault("LIBRARYOFYORE_BASE", BASE_DIR)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ui.main_window import MainWindow


def main():
    # Enable high-DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Library of Yore")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("LibraryOfYore")

    # Global font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()

    print("Library of Yore v1.0.0 started successfully.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
