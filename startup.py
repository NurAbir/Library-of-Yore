"""Start Library of Yore automatically when the user signs in to Windows.

The app asks once, on the first normal launch, whether it may add itself to
the current user's startup items. The switch is the per-user Windows Run key:

    HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run

That key needs no administrator rights, applies only to the signed-in user,
and is removed cleanly when the feature is turned off. The app is started with
``--startup`` so it opens hidden in the system tray instead of popping a
window in the user's face at login.

Everything here is a no-op on non-Windows machines (the app itself only ships
for Windows) so tests and development on other platforms stay unaffected.
"""
import os
import sys

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "LibraryOfYore"
STARTUP_ARG = "--startup"


def is_supported() -> bool:
    """True on Windows, where the per-user Run key exists."""
    return sys.platform == "win32"


def _main_script() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py"))


def launch_command() -> str:
    """The exact command Windows should run at sign-in.

    A packaged build points at the exe. Running from source points at
    main.py through pythonw.exe when it is available, so no console window
    flashes at login.
    """
    if getattr(sys, "frozen", False):
        return f'"{os.path.abspath(sys.executable)}" {STARTUP_ARG}'
    exe = os.path.abspath(sys.executable)
    pythonw = os.path.join(os.path.dirname(exe), "pythonw.exe")
    runner = pythonw if os.path.exists(pythonw) else exe
    return f'"{runner}" "{_main_script()}" {STARTUP_ARG}'


def _open_run_key(access):
    import winreg
    return winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, access)


def is_enabled() -> bool:
    """True if a startup value for this app exists in the user's Run key."""
    if not is_supported():
        return False
    import winreg
    try:
        with _open_run_key(winreg.KEY_READ) as key:
            value, _kind = winreg.QueryValueEx(key, VALUE_NAME)
        return bool(value)
    except (OSError, ImportError):
        return False


def enable() -> bool:
    """Add or refresh the startup entry. Returns True on success."""
    if not is_supported():
        return False
    try:
        import winreg
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, launch_command())
        return True
    except (OSError, ImportError):
        return False


def disable() -> bool:
    """Remove the startup entry. Returns True if it is gone afterwards."""
    if not is_supported():
        return False
    try:
        import winreg
        with _open_run_key(winreg.KEY_SET_VALUE) as key:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass  # already absent — that is the desired end state
        return True
    except (OSError, ImportError):
        return False


def set_enabled(enabled: bool) -> bool:
    """Turn the startup entry on or off. Returns True if the request worked."""
    return enable() if enabled else disable()
