; Inno Setup script for LibraryOfYore
; Requires Inno Setup 6.x: https://jrsoftware.org/isdl.php

#define MyAppName     "Library of Yore"
#define MyAppVersion  "1.3.0"
#define MyAppPublisher "LibraryOfYore"
#define MyAppExeName  "LibraryOfYore.exe"
#define MyDistDir     "dist\LibraryOfYore"
#define MyExePath     MyDistDir + "\" + MyAppExeName

; Hard-fail at compile time with a clear message if the build hasn't been run yet.
; Run build_release.bat (or python build.py --folder) before compiling this script.
#if !FileExists(MyExePath)
  #error "dist\LibraryOfYore\LibraryOfYore.exe not found. Run build_release.bat first, then compile this script."
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
Source: "{#MyDistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

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
