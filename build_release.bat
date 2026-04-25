@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ==========================================
echo    Library of Yore - Release Builder
echo ==========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ and add to PATH.
    pause
    exit /b 1
)

REM Check PyInstaller
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PyInstaller not installed. Run: pip install pyinstaller
    pause
    exit /b 1
)

REM Check Inno Setup
set INNO="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %INNO% (
    set INNO="C:\Program Files\Inno Setup 6\ISCC.exe"
    if not exist %INNO% (
        echo [WARNING] Inno Setup not found at default location.
        echo [WARNING] Skipping installer creation.
        echo [WARNING] Download from: https://jrsoftware.org/isdl.php
        set SKIP_INNO=1
    )
)

echo [1/4] Cleaning old builds...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist *.spec del /q *.spec

echo [2/4] Building executable (folder mode - more stable)...
python -m PyInstaller ^
    --name LibraryOfYore ^
    --onedir ^
    --windowed ^
    --noconfirm ^
    --clean ^
    --icon assets\logo.ico ^
    --add-data "scrapers;scrapers" ^
    --add-data "database;database" ^
    --add-data "ui;ui" ^
    --add-data "utils;utils" ^
    --add-data "assets;assets" ^
    --add-data "config.py;." ^
    --hidden-import scrapers.novelfire --hidden-import scrapers.wuxiaworld --hidden-import scrapers.freewebnovel --hidden-import scrapers.novelupdates ^
    --hidden-import database.connection ^
    --hidden-import database.models ^
    --hidden-import pymongo ^
    --hidden-import gridfs ^
    --hidden-import openpyxl ^
    --hidden-import PIL ^
    --hidden-import playwright ^
    --hidden-import requests ^
    --hidden-import bs4 ^
    --hidden-import dateutil ^
    main.py

if errorlevel 1 (
    echo [ERROR] PyInstaller build failed!
    pause
    exit /b 1
)

echo [3/4] Build complete!
echo    Location: dist\LibraryOfYore
echo    Run: dist\LibraryOfYore\LibraryOfYore.exe

if defined SKIP_INNO (
    echo.
    echo [4/4] Skipping installer (Inno Setup not found)
    goto :done
)

echo [4/4] Creating installer with Inno Setup...
if not exist installer mkdir installer
%INNO% installer.iss

if errorlevel 1 (
    echo [WARNING] Installer creation failed, but build is ready.
    goto :done
)

echo.
echo ==========================================
echo    SUCCESS!
echo ==========================================
echo.
echo Portable:  dist\LibraryOfYore
echo Installer: installer\LibraryOfYore_Setup.exe
echo.

:done
pause
