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

COMMON_HIDDEN_IMPORTS = [
    "scrapers.novelfire",
    "scrapers.wuxiaworld",
    "scrapers.freewebnovel",
    "scrapers.novelupdates",
    "database.connection",
    "database.models",
    "pymongo",
    "gridfs",
    "openpyxl",
    "PIL",
    "playwright",
    "requests",
    "bs4",
    "dateutil",
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
    cmd.append(os.path.join(BASE_DIR, "main.py"))
    return cmd


def build():
    """Run PyInstaller to create standalone single-file executable."""
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
