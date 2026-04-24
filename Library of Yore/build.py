"""Build script to package Library of Yore with PyInstaller.

Usage:
    python build.py              # Build single-file .exe
    python build.py --folder     # Build folder (faster startup)
    python build.py --clean      # Clean then build

Requirements:
    pip install pyinstaller
    playwright install chromium
"""
import os
import sys
import shutil
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, "dist")
BUILD_DIR = os.path.join(BASE_DIR, "build")
SPEC_FILE = os.path.join(BASE_DIR, "LibraryOfYore.spec")


def clean():
    """Remove previous build artifacts."""
    for d in [DIST_DIR, BUILD_DIR]:
        if os.path.exists(d):
            print(f"Removing {d}...")
            shutil.rmtree(d)
    if os.path.exists(SPEC_FILE):
        os.remove(SPEC_FILE)
    print("Cleaned.")


def build():
    """Run PyInstaller to create standalone executable."""
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "LibraryOfYore",
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--icon", os.path.join(BASE_DIR, "assets", "logo.ico"),
        "--add-data", f"scrapers{os.pathsep}scrapers",
        "--add-data", f"database{os.pathsep}database",
        "--add-data", f"ui{os.pathsep}ui",
        "--add-data", f"utils{os.pathsep}utils",
        "--add-data", f"assets{os.pathsep}assets",
        "--add-data", f"config.py{os.pathsep}.",
        "--hidden-import", "scrapers.webnovel",
        "--hidden-import", "scrapers.novelfire",
        "--hidden-import", "database.connection",
        "--hidden-import", "database.models",
        "--hidden-import", "pymongo",
        "--hidden-import", "gridfs",
        "--hidden-import", "openpyxl",
        "--hidden-import", "PIL",
        "--hidden-import", "playwright",
        "--hidden-import", "requests",
        "--hidden-import", "bs4",
        "--hidden-import", "dateutil",
        os.path.join(BASE_DIR, "main.py"),
    ]

    print("Running PyInstaller...")
    print(" ".join(cmd))
    result = subprocess.run(cmd, cwd=BASE_DIR)
    if result.returncode != 0:
        print("PyInstaller failed!")
        sys.exit(1)

    out_path = os.path.join(DIST_DIR, "LibraryOfYore.exe")
    print("\nBuild complete! Output: " + out_path)


def build_folder():
    """Alternative: build as folder (faster startup, easier to debug)."""
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "LibraryOfYore",
        "--onedir",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--icon", os.path.join(BASE_DIR, "assets", "logo.ico"),
        "--add-data", f"scrapers{os.pathsep}scrapers",
        "--add-data", f"database{os.pathsep}database",
        "--add-data", f"ui{os.pathsep}ui",
        "--add-data", f"utils{os.pathsep}utils",
        "--add-data", f"assets{os.pathsep}assets",
        "--add-data", f"config.py{os.pathsep}.",
        "--hidden-import", "scrapers.webnovel",
        "--hidden-import", "scrapers.novelfire",
        "--hidden-import", "pymongo",
        "--hidden-import", "gridfs",
        "--hidden-import", "openpyxl",
        "--hidden-import", "PIL",
        "--hidden-import", "playwright",
        "--hidden-import", "requests",
        "--hidden-import", "bs4",
        "--hidden-import", "dateutil",
        os.path.join(BASE_DIR, "main.py"),
    ]
    print("Running PyInstaller (folder mode)...")
    subprocess.run(cmd, cwd=BASE_DIR)
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

    if not args.folder:
        build_folder()
    else:
        build()
