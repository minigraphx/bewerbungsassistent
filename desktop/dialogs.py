"""Native dialogs to choose a folder or a file (MIN-342).

The browser cannot hand a local path to the app, and the einstieg file can be far larger than a request
may be. So the app opens the system's own dialog: PowerShell with Windows Forms on Windows, AppleScript on
macOS. The start folder goes in through an environment variable, never into the script text.
"""
import os
import pathlib
import subprocess
from typing import Callable

START_VARIABLE = "BEWERBUNGSASSISTENT_START"
TIMEOUT_SECONDS = 600
CANCELLED_MAC = "-128"
TYPE_PATH = "Bitte den Pfad selbst eintragen."

WINDOWS = {
    "ordner": """
Add-Type -AssemblyName System.Windows.Forms
$owner = New-Object System.Windows.Forms.Form -Property @{TopMost = $true; ShowInTaskbar = $false}
$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
$dialog.Description = 'Ordner für die Bewerbungsdaten wählen'
$dialog.ShowNewFolderButton = $true
$dialog.SelectedPath = $env:BEWERBUNGSASSISTENT_START
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
if ($dialog.ShowDialog($owner) -eq 'OK') { $dialog.SelectedPath }
""",
    "datei": """
Add-Type -AssemblyName System.Windows.Forms
$owner = New-Object System.Windows.Forms.Form -Property @{TopMost = $true; ShowInTaskbar = $false}
$dialog = New-Object System.Windows.Forms.OpenFileDialog
$dialog.Title = 'Datei aus der Einstiegsvorlage wählen'
$dialog.Filter = 'Einstiegsvorlage (*.zip;*.json)|*.zip;*.json'
$dialog.InitialDirectory = $env:BEWERBUNGSASSISTENT_START
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
if ($dialog.ShowDialog($owner) -eq 'OK') { $dialog.FileName }
""",
}
MAC = {
    "ordner": 'POSIX path of (choose folder with prompt "Ordner für die Bewerbungsdaten wählen" '
              'default location (POSIX file (system attribute "BEWERBUNGSASSISTENT_START")))',
    "datei": 'POSIX path of (choose file with prompt "Datei aus der Einstiegsvorlage wählen" '
             'of type {"public.zip-archive", "public.json"} '
             'default location (POSIX file (system attribute "BEWERBUNGSASSISTENT_START")))',
}

Run = Callable[..., subprocess.CompletedProcess]


def _command(kind: str, platform: str) -> list[str]:
    if kind not in WINDOWS:
        raise ValueError(f"Unbekannte Auswahl: {kind}")
    if platform == "win32":
        return ["powershell", "-NoProfile", "-NonInteractive", "-STA", "-Command", WINDOWS[kind]]
    if platform == "darwin":
        return ["osascript", "-e", MAC[kind]]
    raise ValueError(f"Auf diesem System gibt es keinen Auswahldialog. {TYPE_PATH}")


def choose(kind: str, start: pathlib.Path, platform: str, run: Run = subprocess.run) -> pathlib.Path | None:
    """The chosen folder or file; None when the person cancels."""
    command = _command(kind, platform)
    try:
        result = run(command, capture_output=True, text=True, encoding="utf-8", timeout=TIMEOUT_SECONDS,
                     env={**os.environ, START_VARIABLE: str(start)})
    except (OSError, UnicodeDecodeError, subprocess.TimeoutExpired) as error:
        raise ValueError(f"Der Auswahldialog liess sich nicht öffnen. {TYPE_PATH}") from error
    if result.returncode != 0:
        if CANCELLED_MAC in (result.stderr or ""):
            return None
        raise ValueError(f"Der Auswahldialog liess sich nicht öffnen. {TYPE_PATH}")
    chosen = (result.stdout or "").lstrip("\ufeff").strip()
    return pathlib.Path(chosen) if chosen else None
