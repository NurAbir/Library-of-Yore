; Inno Setup script for LibraryOfYore
; Requires Inno Setup 6.x: https://jrsoftware.org/isdl.php

#define MyAppName     "Library of Yore"
#define MyAppVersion  "2.0.0"
#define MyAppPublisher "LibraryOfYore"
#define MyAppExeName  "LibraryOfYore.exe"

; ── Locating the build output ────────────────────────────────────────────
; By default this script looks for either build layout, in this order:
;   1. Folder build   (build_release.bat / python build.py --folder):
;        dist\LibraryOfYore\LibraryOfYore.exe  + supporting files
;   2. Onefile build   (build.bat / python build.py):
;        dist\LibraryOfYore.exe   (single file, nothing else needed)
;
; NOTE: these checks are anchored to SourcePath (the folder this .iss file
; lives in) rather than plain relative paths. Inno Setup's preprocessor
; resolves FileExists() against the compiler's *current working directory*,
; not the script's folder -- so a plain relative check here would work when
; build_release.bat calls ISCC.exe from the project root, but silently fail
; when this script is compiled on its own (e.g. via the Inno Setup IDE),
; even though the exe is right there. Using SourcePath makes it reliable
; either way.
;
; To point this at a build living somewhere else entirely, pass the folder
; that directly CONTAINS LibraryOfYore.exe on the command line, e.g.:
;   ISCC.exe installer.iss /DMyDistDir="C:\Users\User\Downloads\Documents\Library-of-Yore-main\dist"
; (that override is honored below and skips auto-detection.)

#ifndef MyDistDir
  #if FileExists(SourcePath + "dist\LibraryOfYore\" + MyAppExeName)
    #define MyDistDir SourcePath + "dist\LibraryOfYore"
    #define MyBuildMode "folder"
  #elif FileExists(SourcePath + "dist\" + MyAppExeName)
    #define MyDistDir SourcePath + "dist"
    #define MyBuildMode "onefile"
  #else
    #error "Could not find LibraryOfYore.exe under dist\LibraryOfYore\ or dist\ (looked in " + SourcePath + "dist). Run build_release.bat (or build.bat) first, then compile this script -- or pass /DMyDistDir=<folder containing LibraryOfYore.exe> to ISCC.exe manually."
  #endif
#else
  ; MyDistDir was passed in manually via /D -- assume folder mode (copy
  ; everything alongside the exe) since that's the common case for a
  ; relocated build.
  #define MyBuildMode "folder"
#endif

#define MyExePath MyDistDir + "\" + MyAppExeName

; Belt-and-braces: re-check even if MyDistDir was passed in manually via /D.
#if !FileExists(MyExePath)
  #error "LibraryOfYore.exe not found in the folder given by MyDistDir. Check the path (it must point directly at the folder containing LibraryOfYore.exe) and try again."
#endif

#define MyIconPath MyDistDir + "\assets\logo.ico"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=installer
OutputBaseFilename=LibraryOfYore_Setup
#if FileExists(MyIconPath)
SetupIconFile={#MyIconPath}
#endif
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
#if MyBuildMode == "onefile"
; Onefile build: just the single self-contained exe, nothing else to copy.
Source: "{#MyExePath}"; DestDir: "{app}"; Flags: ignoreversion
#else
; Folder build: the exe plus its _internal\ dependencies and assets\.
Source: "{#MyDistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
#endif

[Icons]
Name: "{group}\{#MyAppName}";     Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
