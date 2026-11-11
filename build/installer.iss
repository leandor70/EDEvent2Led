; ============================================================
; Inno Setup script for ED:Event2Led
;
; Prerequisites:
;   - Inno Setup 6.x  (https://jrsoftware.org/isinfo.php)
;   - PyInstaller build already run:  dist\EDEvent2Led\
;   - Icon file at:                   build\icon.ico
;
; Usage:
;   iscc build\installer.iss
;
; Output:
;   dist\EDEvent2Led-Setup-x.y.z.exe
; ============================================================

#define AppName      "ED:Event2Led"
#define AppVersion   "1.2.4"
#define AppPublisher "ED:Event2Led Project"
#define AppURL       "https://github.com/your-repo/EDEvent2Led"
#define AppExeName   "EDEvent2Led.exe"
#define DistDir      "..\dist\EDEvent2Led"

[Setup]
AppId={{A3F2B1C0-4D5E-6F70-8190-A2B3C4D5E6F7}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
; Installer will NOT require admin rights if user installs to local AppData
PrivilegesRequiredOverridesAllowed=dialog
LicenseFile=..\LICENSE.txt
OutputDir=..\dist
OutputBaseFilename=EDEvent2Led-Setup-{#AppVersion}
SetupIconFile=icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; Minimum Windows 10
MinVersion=10.0
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main application bundle (PyInstaller output)
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}";       Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; Offer to launch after install
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up log files and cache generated at runtime, but NOT config/ (user data)
Type: filesandordirs; Name: "{app}\log"
Type: filesandordirs; Name: "{app}\__pycache__"

[Code]
// ── Prerequisites check ──────────────────────────────────────────────────
// Warn if OpenRGB does not appear to be installed.
// (We check for the OpenRGB executable in common install locations.)
function OpenRGBFound(): Boolean;
begin
  Result := FileExists(ExpandConstant('{pf}\OpenRGB\OpenRGB.exe'))
         or FileExists(ExpandConstant('{pf32}\OpenRGB\OpenRGB.exe'))
         or FileExists(ExpandConstant('{localappdata}\OpenRGB\OpenRGB.exe'));
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  if not OpenRGBFound() then
  begin
    if MsgBox(
      'OpenRGB does not appear to be installed.' + #13#10 +
      'ED:Event2Led requires OpenRGB to control RGB hardware.' + #13#10#13#10 +
      'Download OpenRGB from: https://openrgb.org/' + #13#10#13#10 +
      'Continue installation anyway?',
      mbConfirmation, MB_YESNO) = IDNO then
      Result := False;
  end;
end;
