"""Updates of the desktop app from GitHub Releases of the public repo (MIN-342).

A release `v1.2.3` carries `Bewerbungsassistent-Setup-1.2.3.exe` and `SHA256SUMS.txt`. The app checks the
latest release, and on Windows downloads the installer, verifies its SHA-256 sum and runs it silently over
the installed version; the installer starts the app again. Data folder, settings and the access in the
keychain stay untouched. On macOS the app links to the release page.
"""
import dataclasses
import hashlib
import json
import pathlib
import re
import subprocess
import urllib.error
import urllib.request
from typing import Callable

REPO = "minigraphx/bewerbungsassistent"
LATEST_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
DOWNLOAD_PREFIX = f"https://github.com/{REPO}/releases/download/"
INSTALLER = re.compile(r"^Bewerbungsassistent-Setup-(\d+\.\d+\.\d+)\.exe$")
CHECKSUMS = "SHA256SUMS.txt"
TIMEOUT_SECONDS = 10
DOWNLOAD_TIMEOUT_SECONDS = 300
MAX_INSTALLER_BYTES = 400 * 1024 * 1024
SMALL_FILE_BYTES = 1024 * 1024
SILENT = ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"]

Fetch = Callable[[str, int], bytes]


class UpdateError(Exception):
    """German message for the interface."""


@dataclasses.dataclass(frozen=True)
class Update:
    version: str
    page_url: str
    installer_url: str | None
    checksums_url: str | None
    notes: str = ""


def parse_version(text: str) -> tuple[int, ...]:
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", (text or "").strip())
    return tuple(int(part) for part in match.groups()) if match else (0, 0, 0)


def _fetch(url: str, limit: int) -> bytes:
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                                   "User-Agent": "Bewerbungsassistent"})
    timeout = DOWNLOAD_TIMEOUT_SECONDS if limit > SMALL_FILE_BYTES else TIMEOUT_SECONDS
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 (https only)
        data = response.read(limit + 1)
    if len(data) > limit:
        raise UpdateError("Die Datei ist grösser als erwartet; Update abgebrochen.")
    return data


def latest(fetch: Fetch = _fetch) -> Update | None:
    try:
        release = json.loads(fetch(LATEST_URL, SMALL_FILE_BYTES))
    except (urllib.error.URLError, OSError, ValueError):
        return None
    if not isinstance(release, dict) or release.get("draft") or release.get("prerelease"):
        return None
    assets = {a.get("name"): a.get("browser_download_url") for a in release.get("assets") or [] if isinstance(a, dict)}
    version = str(release.get("tag_name") or "").lstrip("v")
    installer = next((url for name, url in assets.items() if name and INSTALLER.match(name)
                      and INSTALLER.match(name).group(1) == version), None)
    safe = [url for url in (installer, assets.get(CHECKSUMS)) if url and str(url).startswith(DOWNLOAD_PREFIX)]
    return Update(version=version, page_url=str(release.get("html_url") or f"https://github.com/{REPO}/releases"),
                  installer_url=installer if installer in safe else None,
                  checksums_url=assets.get(CHECKSUMS) if assets.get(CHECKSUMS) in safe else None,
                  notes=str(release.get("body") or "")[:2000])


def newer(current: str, update: Update | None) -> Update | None:
    return update if update and parse_version(update.version) > parse_version(current) else None


def download(update: Update, target_dir: pathlib.Path, fetch: Fetch = _fetch) -> pathlib.Path:
    """The verified installer in target_dir; UpdateError if anything does not match."""
    if not update.installer_url or not update.checksums_url:
        raise UpdateError("Für diese Version gibt es keinen Installer; bitte von der Release-Seite laden.")
    name = update.installer_url.rsplit("/", 1)[-1]
    try:
        sums = fetch(update.checksums_url, 64 * 1024).decode("utf-8")
        expected = next((line.split()[0].lower() for line in sums.splitlines()
                         if len(line.split()) == 2 and line.split()[1].lstrip("*") == name), None)
        if not expected:
            raise UpdateError("Die Prüfsumme des Installers fehlt; Update abgebrochen.")
        data = fetch(update.installer_url, MAX_INSTALLER_BYTES)
    except (urllib.error.URLError, OSError, UnicodeDecodeError) as error:
        raise UpdateError("Die neue Version liess sich nicht laden. Ist der Rechner online?") from error
    if hashlib.sha256(data).hexdigest() != expected:
        raise UpdateError("Die Prüfsumme stimmt nicht; der Download ist beschädigt. Update abgebrochen.")
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / name
    path.write_bytes(data)
    return path


def run_installer(path: pathlib.Path, popen=subprocess.Popen) -> None:
    """Start the installer detached; it closes this app, replaces it and starts the new version."""
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    popen([str(path), *SILENT], creationflags=flags, close_fds=True)
