; Windows-Installer des Bewerbungsbegleiters (MIN-342), gebaut in der CI mit Inno Setup:
;   ISCC.exe /DAppVersion=0.1.0 desktop\installer.iss   (nach pyinstaller, aus dem Repo-Ordner)
; Installation pro Benutzer ohne Administratorrechte. Ein neuer Installer über eine bestehende Version
; ist das Update (auch still mit /VERYSILENT); Datenordner, Einstellungen und Schlüsselbund bleiben.
#define AppName "Bewerbungsbegleiter"
#define AppExe "Bewerbungsbegleiter.exe"
; Der Name bis Version 0.2.10 (MIN-395)
#define OldName "Bewerbungsassistent"
#define OldScheme "bewerbungsassistent"
; Host-Namen für die Browser wie in native_messaging.py (HOST_NAME, OLD_HOST_NAME)
#define HostName "bewerbungsbegleiter"
#define OldHostName "bewerbungsassistent"
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6B0C9E7A-3F2D-4C1B-9E55-8A1D2F4B7C30}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppName}
DefaultDirName={localappdata}\Programs\{#AppName}
UsePreviousAppDir=no
DisableProgramGroupPage=yes
DisableDirPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist-installer
OutputBaseFilename=Bewerbungsbegleiter-Setup-{#AppVersion}
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
; Ordner und Verknüpfungen unter dem alten Namen
Type: filesandordirs; Name: "{localappdata}\Programs\{#OldName}"
Type: files; Name: "{autoprograms}\{#OldName}.lnk"
Type: files; Name: "{autodesktop}\{#OldName}.lnk"

[Files]
Source: "..\dist\{#AppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
; Der Link unter dem alten Namen führte in den alten Ordner
Root: HKCU; Subkey: "Software\Classes\{#OldScheme}"; ValueType: none; Flags: deletekey
; Einladungslink bewerbungsbegleiter://einladung?code=… öffnet die App
Root: HKCU; Subkey: "Software\Classes\bewerbungsbegleiter"; ValueType: string; ValueName: ""; ValueData: "URL:Bewerbungsbegleiter"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\bewerbungsbegleiter"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\bewerbungsbegleiter\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""
; Die Verbindung zur Erweiterung schreibt die App bei jedem Start (native_messaging.py). Der Installer legt
; nichts an (dontcreatekey) und löscht bei der Deinstallation nur den eigenen Schlüssel, nie den Ordner des Browsers.
Root: HKCU; Subkey: "Software\Google\Chrome\NativeMessagingHosts\{#HostName}"; ValueType: none; Flags: dontcreatekey uninsdeletekey
Root: HKCU; Subkey: "Software\Microsoft\Edge\NativeMessagingHosts\{#HostName}"; ValueType: none; Flags: dontcreatekey uninsdeletekey
Root: HKCU; Subkey: "Software\Chromium\NativeMessagingHosts\{#HostName}"; ValueType: none; Flags: dontcreatekey uninsdeletekey
Root: HKCU; Subkey: "Software\BraveSoftware\Brave-Browser\NativeMessagingHosts\{#HostName}"; ValueType: none; Flags: dontcreatekey uninsdeletekey
; Unter dem alten Namen, falls die neue Version nie gestartet wurde und ihn darum nicht entfernt hat
Root: HKCU; Subkey: "Software\Google\Chrome\NativeMessagingHosts\{#OldHostName}"; ValueType: none; Flags: dontcreatekey uninsdeletekey
Root: HKCU; Subkey: "Software\Microsoft\Edge\NativeMessagingHosts\{#OldHostName}"; ValueType: none; Flags: dontcreatekey uninsdeletekey
Root: HKCU; Subkey: "Software\Chromium\NativeMessagingHosts\{#OldHostName}"; ValueType: none; Flags: dontcreatekey uninsdeletekey
Root: HKCU; Subkey: "Software\BraveSoftware\Brave-Browser\NativeMessagingHosts\{#OldHostName}"; ValueType: none; Flags: dontcreatekey uninsdeletekey

[Run]
; Läuft auch beim stillen Update, damit die neue Version gleich wieder offen ist (ausser mit /NOSTART, für die CI)
Filename: "{app}\{#AppExe}"; Description: "{#AppName} starten"; Flags: nowait postinstall; Check: ShouldStart

[Code]
function ShouldStart(): Boolean;
begin
  Result := Pos('/NOSTART', UpperCase(GetCmdTail())) = 0;
end;
