"""Build script to package Library of Yore with PyInstaller.

Usage:
    python build.py              # Build single-file .exe
    python build.py --folder     # Build folder (faster startup)
    python build.py --clean      # Clean then build

Requirements:
    pip install -r requirements.txt
    playwright install chromium
"""
import os
import sys
import shutil
import subprocess
import importlib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, "dist")
BUILD_DIR = os.path.join(BASE_DIR, "build")
SPEC_FILE = os.path.join(BASE_DIR, "LibraryOfYore.spec")

COMMON_HIDDEN_IMPORTS = [
    "scrapers.novelfire",
    "scrapers.novelphoenix",
    "scrapers.wuxiaworld",
    "scrapers.freewebnovel",
    "scrapers.flamecomics",
    "utils.chapters",
    "database.connection",
    "database.models",
    "database.legacy_mongo",
    "tinydb",
    "pymongo",
    "gridfs",
    "openpyxl",
    "PIL",
    "playwright",
    "requests",
    "bs4",
    "dateutil",
]

# The subset of COMMON_HIDDEN_IMPORTS that come from pip (as opposed to
# scrapers.*/database.* which are just local source files, always present).
# --hidden-import only tells PyInstaller to *try* bundling these — if one
# isn't actually installed, PyInstaller prints a warning and keeps going,
# producing an exe that builds cleanly but crashes with ModuleNotFoundError
# the moment it's run. Checking these up front turns that into a build-time
# error instead of a runtime surprise.
PIP_HIDDEN_IMPORTS = [
    "tinydb", "pymongo", "gridfs", "openpyxl", "PIL",
    "playwright", "requests", "bs4", "dateutil",
]

# openpyxl optionally uses numpy/pandas if present, but this app never needs
# them and PyInstaller frequently bundles numpy incompletely (missing C
# extension attributes at runtime -- e.g. "module 'numpy' has no attribute
# 'short'"). Excluding them outright avoids that failure mode entirely.
COMMON_EXCLUDES = [
    "numpy",
    "pandas",
    "matplotlib",
]

COMMON_ADD_DATA = [
    f"scrapers{os.pathsep}scrapers",
    f"database{os.pathsep}database",
    f"ui{os.pathsep}ui",
    f"utils{os.pathsep}utils",
    f"assets{os.pathsep}assets",
    f"config.py{os.pathsep}.",
]


def clean():
    """Remove previous build artifacts."""
    for d in [DIST_DIR, BUILD_DIR]:
        if os.path.exists(d):
            print(f"Removing {d}...")
            shutil.rmtree(d)
    if os.path.exists(SPEC_FILE):
        os.remove(SPEC_FILE)
    print("Cleaned.")


def check_dependencies():
    """Verify every pip-installed hidden-import is actually importable in
    *this* Python environment before handing off to PyInstaller. Catches the
    "build succeeded, exe crashes with ModuleNotFoundError" failure mode at
    build time, with a clear fix, instead of at runtime with a stack trace."""
    missing = []
    for name in PIP_HIDDEN_IMPORTS:
        try:
            importlib.import_module(name)
        except ImportError:
            missing.append(name)

    if missing:
        print("ERROR: The following packages are required but not installed")
        print(f"in this Python environment ({sys.executable}):")
        for name in missing:
            print(f"  - {name}")
        print("\nInstall them, then re-run the build:")
        print("  pip install -r requirements.txt")
        sys.exit(1)


def _base_cmd(onefile=False):
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "LibraryOfYore",
        "--onefile" if onefile else "--onedir",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--icon", os.path.join(BASE_DIR, "assets", "logo.ico"),
    ]
    for data in COMMON_ADD_DATA:
        cmd += ["--add-data", data]
    for imp in COMMON_HIDDEN_IMPORTS:
        cmd += ["--hidden-import", imp]
    for exc in COMMON_EXCLUDES:
        cmd += ["--exclude-module", exc]
    cmd.append(os.path.join(BASE_DIR, "main.py"))
    return cmd


def build():
    """Run PyInstaller to create standalone single-file executable."""
    check_dependencies()
    cmd = _base_cmd(onefile=True)
    print("Running PyInstaller (single-file mode)...")
    print(" ".join(cmd))
    result = subprocess.run(cmd, cwd=BASE_DIR)
    if result.returncode != 0:
        print("PyInstaller failed!")
        sys.exit(1)
    out_path = os.path.join(DIST_DIR, "LibraryOfYore.exe")
    print("\nBuild complete! Output: " + out_path)


def build_folder():
    """Alternative: build as folder (faster startup, easier to debug)."""
    check_dependencies()
    cmd = _base_cmd(onefile=False)
    print("Running PyInstaller (folder mode)...")
    print(" ".join(cmd))
    result = subprocess.run(cmd, cwd=BASE_DIR)
    if result.returncode != 0:
        print("PyInstaller failed!")
        sys.exit(1)
    out_path = os.path.join(DIST_DIR, "LibraryOfYore")
    print("\nBuild complete! Output: " + out_path + os.sep)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build LibraryOfYore")
    parser.add_argument("--clean", action="store_true", help="Clean build dirs first")
    parser.add_argument("--folder", action="store_true", help="Build as folder instead of single file")
    args = parser.parse_args()

    if args.clean:
        clean()

    if args.folder:
        build_folder()   # --folder → folder build (was inverted before)
    else:
        build()          # default → single-file .exe
