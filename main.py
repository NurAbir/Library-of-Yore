"""Entry point for LibraryOfYore desktop application."""
import sys
import os
import traceback

# Ensure bundled resources are found when running from PyInstaller
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.environ.setdefault("LIBRARYOFYORE_BASE", BASE_DIR)

# Crash log path — written next to the exe so it's easy to find
CRASH_LOG = os.path.join(BASE_DIR, "crash_log.txt")

# Name of the local socket used to keep only one copy of the app running.
SINGLE_INSTANCE_NAME = "LibraryOfYore-single-instance"


def _acquire_single_instance():
    """Return (server, is_primary).

    A second launch does not open a second window (two windows would share the
    same library file and fight over the extension API's port). Instead it
    asks the copy that is already running to show its window and then exits.
    ``server`` is the QLocalServer the primary copy must keep alive; it is
    None when QtNetwork is unavailable or the socket couldn't be created.
    """
    try:
        from PyQt6.QtNetwork import QLocalServer, QLocalSocket
    except ImportError:
        return None, True

    probe = QLocalSocket()
    probe.connectToServer(SINGLE_INSTANCE_NAME)
    if probe.waitForConnected(300):
        probe.write(b"show")
        probe.flush()
        probe.waitForBytesWritten(300)
        probe.disconnectFromServer()
        return None, False

    # Remove a stale socket left behind by a crash, then claim the name.
    QLocalServer.removeServer(SINGLE_INSTANCE_NAME)
    server = QLocalServer()
    if not server.listen(SINGLE_INSTANCE_NAME):
        return None, True
    return server, True


def _wire_show_handler(server, window):
    """Make a second launch bring the existing window back to the front."""
    def on_new_connection():
        while server.hasPendingConnections():
            connection = server.nextPendingConnection()
            if connection:
                connection.disconnected.connect(connection.deleteLater)
                connection.readAll()
        window._show_window()

    server.newConnection.connect(on_new_connection)


def main():
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont
    from ui.main_window import MainWindow

    # Enable high-DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    from config import APP_VERSION

    app = QApplication(sys.argv)
    app.setApplicationName("Library of Yore")
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("LibraryOfYore")
    # The app lives in the tray, so closing the last window must not end the
    # process. Quitting is explicit: File -> Exit, the tray's Quit item, or a
    # window close when no tray is available.
    app.setQuitOnLastWindowClosed(False)

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    server, primary = _acquire_single_instance()
    if not primary:
        return 0  # already running; the primary copy was asked to show itself

    start_minimized = any(arg in ("--startup", "--minimized") for arg in sys.argv[1:])
    window = MainWindow(start_minimized=start_minimized)
    if server:
        _wire_show_handler(server, window)

    if start_minimized and window.tray_available:
        window.hide()          # start quietly in the tray at Windows login
    else:
        window.showMaximized()

    print(f"Library of Yore v{APP_VERSION} started successfully.")
    return app.exec()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        error_text = traceback.format_exc()
        # Write crash log next to the exe
        try:
            with open(CRASH_LOG, "w", encoding="utf-8") as f:
                f.write("Library of Yore — Crash Report\n")
                f.write("=" * 50 + "\n\n")
                f.write(error_text)
        except Exception:
            pass
        # Also try to show a message box if Qt is available
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            _app = QApplication.instance() or QApplication(sys.argv)
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Library of Yore — Startup Error")
            msg.setText("The application failed to start.")
            msg.setDetailedText(error_text)
            msg.exec()
        except Exception:
            pass
        sys.exit(1)
