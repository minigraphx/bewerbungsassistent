"""Native dialogs to choose a folder or a file (MIN-342).

The browser cannot hand a local path to the app, and the einstieg file can be far larger than a request
may be. So the app opens the system's own dialog: PowerShell with Windows Forms on Windows, AppleScript on
macOS, zenity or kdialog on Linux (#73). The start folder goes in through an environment variable, never into
the script text; on Linux there is no script, it is a plain argument.
"""
import os
import pathlib
import shutil
import subprocess
from typing import Callable

from ordner import reveal  # noqa: F401  (the setup pages use it from here)

START_VARIABLE = "BEWERBUNGSBEGLEITER_START"
TIMEOUT_SECONDS = 600
CANCELLED_MAC = "-128"
CANCELLED_LINUX = 1  # zenity and kdialog end with 1 and print nothing when the person cancels
TYPE_PATH = "Bitte den Pfad selbst eintragen."

WINDOWS = {
    "ordner": """
Add-Type -AssemblyName System.Windows.Forms
$owner = New-Object System.Windows.Forms.Form -Property @{TopMost = $true; ShowInTaskbar = $false}
$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
$dialog.Description = 'Ordner für die Bewerbungsdaten wählen'
$dialog.ShowNewFolderButton = $true
$dialog.SelectedPath = $env:BEWERBUNGSBEGLEITER_START
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
if ($dialog.ShowDialog($owner) -eq 'OK') { $dialog.SelectedPath }
""",
    "datei": """
Add-Type -AssemblyName System.Windows.Forms
$owner = New-Object System.Windows.Forms.Form -Property @{TopMost = $true; ShowInTaskbar = $false}
$dialog = New-Object System.Windows.Forms.OpenFileDialog
$dialog.Title = 'Einstiegsdatei wählen'
$dialog.Filter = 'Einstiegsdatei (*.zip;*.json)|*.zip;*.json'
$dialog.InitialDirectory = $env:BEWERBUNGSBEGLEITER_START
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
if ($dialog.ShowDialog($owner) -eq 'OK') { $dialog.FileName }
""",
}
MAC = {
    "ordner": 'POSIX path of (choose folder with prompt "Ordner für die Bewerbungsdaten wählen" '
              'default location (POSIX file (system attribute "BEWERBUNGSBEGLEITER_START")))',
    "datei": 'POSIX path of (choose file with prompt "Einstiegsdatei wählen" '
             'of type {"public.zip-archive", "public.json"} '
             'default location (POSIX file (system attribute "BEWERBUNGSBEGLEITER_START")))',
}

TITLES = {"ordner": "Ordner für die Bewerbungsdaten wählen", "datei": "Einstiegsdatei wählen"}

Run = Callable[..., subprocess.CompletedProcess]
Which = Callable[[str], str | None]


def _linux_command(kind: str, start: pathlib.Path, which: Which) -> list[str]:
    title = TITLES[kind]
    if which("zenity"):
        if kind == "ordner":
            return ["zenity", "--file-selection", "--directory", f"--title={title}", f"--filename={start}/"]
        return ["zenity", "--file-selection", f"--title={title}", "--file-filter=Einstiegsdatei | *.zip *.json",
                f"--filename={start}/"]
    if which("kdialog"):
        if kind == "ordner":
            return ["kdialog", "--title", title, "--getexistingdirectory", str(start)]
        return ["kdialog", "--title", title, "--getopenfilename", str(start), "*.zip *.json|Einstiegsdatei"]
    raise ValueError(f"Für den Auswahldialog fehlt zenity oder kdialog. {TYPE_PATH}")


def _command(kind: str, start: pathlib.Path, platform: str, which: Which) -> list[str]:
    if kind not in WINDOWS:
        raise ValueError(f"Unbekannte Auswahl: {kind}")
    if platform == "win32":
        return ["powershell", "-NoProfile", "-NonInteractive", "-STA", "-Command", WINDOWS[kind]]
    if platform == "darwin":
        return ["osascript", "-e", MAC[kind]]
    if platform.startswith("linux"):
        return _linux_command(kind, start, which)
    raise ValueError(f"Auf diesem System gibt es keinen Auswahldialog. {TYPE_PATH}")


def _cancelled(result: subprocess.CompletedProcess, platform: str) -> bool:
    if platform.startswith("linux"):
        return result.returncode == CANCELLED_LINUX and not (result.stdout or "").strip()
    return CANCELLED_MAC in (result.stderr or "")


def choose(kind: str, start: pathlib.Path, platform: str, run: Run = subprocess.run,
           which: Which = shutil.which) -> pathlib.Path | None:
    """The chosen folder or file; None when the person cancels."""
    command = _command(kind, start, platform, which)
    try:
        result = run(command, capture_output=True, text=True, encoding="utf-8", timeout=TIMEOUT_SECONDS,
                     env={**os.environ, START_VARIABLE: str(start)})
    except (OSError, UnicodeDecodeError, subprocess.TimeoutExpired) as error:
        raise ValueError(f"Der Auswahldialog liess sich nicht öffnen. {TYPE_PATH}") from error
    if result.returncode != 0:
        if _cancelled(result, platform):
            return None
        raise ValueError(f"Der Auswahldialog liess sich nicht öffnen. {TYPE_PATH}")
    chosen = (result.stdout or "").lstrip("\ufeff").strip()
    return pathlib.Path(chosen) if chosen else None


BROWSERS = {
    "chrome": ("Google Chrome", "chrome", "chrome://extensions"),
    "edge": ("Microsoft Edge", "msedge", "edge://extensions"),
}
LINUX_COMMANDS = {  # Chromium counts for Chrome: same extensions page, same add-on
    "chrome": ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"),
    "edge": ("microsoft-edge", "microsoft-edge-stable"),
}


STORE_PAGES = {
    "chrome": "https://chromewebstore.google.com/detail/bewerbungsbegleiter/nopiegcdnjpkekgfakgglegkeifpmopo",
    "edge": "https://microsoftedge.microsoft.com/addons/detail/mcbcijjbklfeffbollnemgkgnabnmfmp",
}


def open_extensions_page(browser: str, platform: str, run: Run = subprocess.run, which: Which = shutil.which) -> None:
    """Open the extensions page; a web page may not link to it, the system may (MIN-366)."""
    if browser not in BROWSERS:
        raise ValueError("Unbekannter Browser.")
    _open_in_browser(browser, BROWSERS[browser][2], platform, run, which)


def open_store_page(browser: str, platform: str, run: Run = subprocess.run, which: Which = shutil.which) -> None:
    """Open the store entry in that browser: a store only installs into its own browser (#75, #87)."""
    if browser not in STORE_PAGES:
        raise ValueError("Unbekannter Browser.")
    _open_in_browser(browser, STORE_PAGES[browser], platform, run, which)


def _browser_command(browser: str, page: str, platform: str, which: Which) -> list[str]:
    name, windows_command, _ = BROWSERS[browser]
    if platform == "darwin":
        return ["open", "-a", name, page]
    if platform == "win32":
        return ["cmd", "/c", "start", "", windows_command, page]
    found = next((command for command in LINUX_COMMANDS[browser] if which(command)), None) if platform.startswith("linux") else None
    if found is None:
        raise ValueError(f"Bitte {name} selbst öffnen und {page} in die Adresszeile eingeben.")
    return [found, page]


def _open_in_browser(browser: str, page: str, platform: str, run: Run, which: Which) -> None:
    name = BROWSERS[browser][0]
    command = _browser_command(browser, page, platform, which)
    try:
        done = run(command, capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError(f"{name} liess sich nicht öffnen.") from error
    if done.returncode != 0:
        raise ValueError(f"{name} wurde nicht gefunden. Ist der Browser installiert?")
