; Windows-Installer des Bewerbungsassistenten (MIN-342), gebaut in der CI mit Inno Setup:
;   ISCC.exe /DAppVersion=0.1.0 desktop\installer.iss   (nach pyinstaller, aus dem Repo-Ordner)
; Installation pro Benutzer ohne Administratorrechte. Ein neuer Installer über eine bestehende Version
; ist das Update (auch still mit /VERYSILENT); Datenordner, Einstellungen und Schlüsselbund bleiben.
#define AppName "Bewerbungsassistent"
#define AppExe "Bewerbungsassistent.exe"
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6B0C9E7A-3F2D-4C1B-9E55-8A1D2F4B7C30}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Bewerbungsassistent
DefaultDirName={localappdata}\Programs\{#AppName}
DisableProgramGroupPage=yes
DisableDirPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist-installer
OutputBaseFilename=Bewerbungsassistent-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=force
RestartApplications=no
UninstallDisplayIcon={app}\{#AppExe}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "de"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Verknüpfung auf dem Desktop anlegen"; Flags: unchecked

[InstallDelete]
; Dateien der alten Version entfernen, damit nichts Veraltetes liegen bleibt
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\dist\{#AppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
; Einladungslink bewerbungsassistent://einladung?code=… öffnet die App
Root: HKCU; Subkey: "Software\Classes\bewerbungsassistent"; ValueType: string; ValueName: ""; ValueData: "URL:Bewerbungsassistent"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\bewerbungsassistent"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\bewerbungsassistent\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""

[Run]
; Läuft auch beim stillen Update, damit die neue Version gleich wieder offen ist (ausser mit /NOSTART, für die CI)
Filename: "{app}\{#AppExe}"; Description: "Bewerbungsassistent starten"; Flags: nowait postinstall; Check: ShouldStart

[Code]
function ShouldStart(): Boolean;
begin
  Result := Pos('/NOSTART', UpperCase(GetCmdTail())) = 0;
end;
