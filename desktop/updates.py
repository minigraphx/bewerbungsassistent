"""Updates of the desktop app from our update server (MIN-342, MIN-368, MIN-403).

Publishing a release puts the packages on the server, then `latest.json`: version and SHA-256 sums, signed with Ed25519
(.github/workflows/update-ausrollen.yml). The server is shared with other websites, so it is not trusted: the app only
believes a valid signature, and the sums come from that signed file. Package addresses are built from our own address.
On Windows the installer then runs silently over the installed version and starts the app again; on macOS
`updates_macos.py` takes over. Data folder, settings and the access in the keychain stay untouched.
"""
import base64
import dataclasses
import hashlib
import http.client
import json
import logging
import os
import pathlib
import queue
import re
import ssl
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from typing import Callable

import truststore
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

import update_key

log = logging.getLogger("bewerbungsbegleiter")

URL_VARIABLE = "BEWERBUNGSBEGLEITER_UPDATE_URL"
ANNOUNCEMENT = "latest.json"
BETA_ANNOUNCEMENT = "beta.json"  # pre-releases and releases, signed with the same key (#212)
RELEASES_PAGE = "https://github.com/minigraphx/bewerbungsassistent/releases"  # only ever opened by the person
INSTALLER = re.compile(r"^Bewerbungsbegleiter-Setup-(\d+\.\d+\.\d+)\.exe$")
MAC_ZIP = re.compile(r"^Bewerbungsbegleiter-(\d+\.\d+\.\d+)-macOS\.zip$")
APPIMAGE = re.compile(r"^Bewerbungsbegleiter-(\d+\.\d+\.\d+)-x86_64\.AppImage$")
PACKAGES = {"win32": INSTALLER, "darwin": MAC_ZIP, "linux": APPIMAGE}
LOADED_BY_HAND = ("linux",)  # no self-update: the person opens the package itself, from our server
VERSION = re.compile(r"^\d+\.\d+\.\d+$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
MAX_NOTES = 2000
TIMEOUT_SECONDS = 10
DOWNLOAD_TIMEOUT_SECONDS = 300
ANNOUNCEMENT_DEADLINE_SECONDS = 20
DOWNLOAD_DEADLINE_SECONDS = 1800
MAX_INSTALLER_BYTES = 400 * 1024 * 1024
SMALL_FILE_BYTES = 1024 * 1024
SILENT = ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"]
NO_START = "/NOSTART"  # see ShouldStart in installer.iss

Fetch = Callable[[str, int], bytes]


class UpdateError(Exception):
    """German message for the interface."""


@dataclasses.dataclass(frozen=True)
class Update:
    version: str
    page_url: str
    installer_url: str | None
    sha256: str | None
    notes: str = ""


def parse_version(text: str) -> tuple[int, ...]:
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", (text or "").strip())
    return tuple(int(part) for part in match.groups()) if match else (0, 0, 0)


def _read_url(url: str, limit: int, timeout: int) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Bewerbungsbegleiter"})
    context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)  # the packed app has no CA file of its own
    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:  # noqa: S310 (https only)
        data = response.read(limit + 1)
    if len(data) > limit:
        raise UpdateError("Die Datei ist grösser als erwartet; Update abgebrochen.")
    return data


def _fetch(url: str, limit: int) -> bytes:
    """The file at url within a deadline: the socket timeout only limits each read, and the server is not trusted."""
    small = limit <= SMALL_FILE_BYTES
    deadline = ANNOUNCEMENT_DEADLINE_SECONDS if small else DOWNLOAD_DEADLINE_SECONDS
    outcome: queue.SimpleQueue = queue.SimpleQueue()

    def read() -> None:
        try:
            outcome.put((_read_url(url, limit, TIMEOUT_SECONDS if small else DOWNLOAD_TIMEOUT_SECONDS), None))
        except Exception as error:  # noqa: BLE001 (raised again in the caller's thread)
            outcome.put((None, error))

    threading.Thread(target=read, name="update-laden", daemon=True).start()  # a stuck request must not block quitting
    try:
        data, error = outcome.get(timeout=deadline)
    except queue.Empty:
        raise TimeoutError(f"no answer within {deadline} s") from None
    if error:
        raise error
    return data


def _server_address() -> str | None:
    address = os.environ.get(URL_VARIABLE, "").strip().rstrip("/")
    return address if address.startswith("https://") else None


def verified_payload(raw: bytes, public_key: str) -> dict:
    """The announcement inside `raw`; ValueError unless the signature is valid and the content an object."""
    try:
        envelope = json.loads(raw)
        payload = base64.b64decode(envelope["payload"], validate=True)
        signature = base64.b64decode(envelope["signature"], validate=True)
        Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key, validate=True)).verify(signature, payload)
        announced = json.loads(payload)
    except (KeyError, TypeError, RecursionError, InvalidSignature) as error:
        raise ValueError(f"announcement refused: {type(error).__name__}") from error
    if not isinstance(announced, dict):
        raise ValueError("announcement refused: no object")
    return announced


def _package(announced: dict, platform: str, version: str, address: str) -> tuple[str | None, str | None]:
    """Address and sum of the package for this system; nothing unless both look exactly as expected."""
    pattern = PACKAGES.get(platform)
    packages = announced.get("packages")
    entry = packages.get(platform) if isinstance(packages, dict) else None
    if not pattern or not isinstance(entry, dict):
        return None, None
    name, digest = str(entry.get("file") or ""), str(entry.get("sha256") or "")
    found = pattern.match(name)
    if not found or found.group(1) != version or not SHA256.match(digest):
        return None, None
    return f"{address}/{version}/{name}", digest


def _announced(fetch: Fetch, address: str, name: str, platform: str) -> Update | None:
    """The update one announcement offers; None when it is missing, unsigned or meaningless."""
    try:
        announced = verified_payload(fetch(f"{address}/{name}", SMALL_FILE_BYTES), update_key.PUBLIC_KEY)
    except (urllib.error.URLError, http.client.HTTPException, OSError):
        return None
    except (ValueError, UpdateError) as error:
        log.warning("Update-Ankündigung %s abgelehnt: %s", name, error)
        return None
    version = str(announced.get("version") or "")
    if not VERSION.match(version):
        log.warning("Update-Ankündigung %s ohne gültige Version", name)
        return None
    package_url, digest = _package(announced, platform, version, address)
    page_url = package_url if platform in LOADED_BY_HAND and package_url else RELEASES_PAGE
    return Update(version=version, page_url=page_url, installer_url=package_url, sha256=digest,
                  notes=str(announced.get("notes") or "")[:MAX_NOTES])


def latest(fetch: Fetch = _fetch, platform: str = sys.platform, beta: bool = False) -> Update | None:
    """The newest announced version; pre-releases only for whoever switched them on (#212, G47)."""
    address = _server_address()
    if not address:
        return None
    names = (ANNOUNCEMENT, BETA_ANNOUNCEMENT) if beta else (ANNOUNCEMENT,)
    found = [update for update in (_announced(fetch, address, name, platform) for name in names) if update]
    return max(found, key=lambda update: parse_version(update.version), default=None)


def newer(current: str, update: Update | None) -> Update | None:
    return update if update and parse_version(update.version) > parse_version(current) else None


def download(update: Update, target_dir: pathlib.Path, fetch: Fetch = _fetch) -> pathlib.Path:
    """The verified installer in target_dir; UpdateError if anything does not match."""
    if not update.installer_url or not update.sha256:
        raise UpdateError("Für diese Version gibt es keinen Installer; bitte von der Release-Seite laden.")
    name = update.installer_url.rsplit("/", 1)[-1]
    try:
        data = fetch(update.installer_url, MAX_INSTALLER_BYTES)
    except (urllib.error.URLError, http.client.HTTPException, OSError) as error:
        raise UpdateError("Die neue Version liess sich nicht laden. Ist der Rechner online?") from error
    if hashlib.sha256(data).hexdigest() != update.sha256:
        raise UpdateError("Die Prüfsumme stimmt nicht; der Download ist beschädigt. Update abgebrochen.")
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / name
    path.write_bytes(data)
    return path


def _start_installer(path: pathlib.Path, options: list[str], popen) -> None:
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    popen([str(path), *options], creationflags=flags, close_fds=True)


def run_installer(path: pathlib.Path, popen=subprocess.Popen) -> None:
    """Start the installer detached; it closes this app, replaces it and starts the new version."""
    _start_installer(path, SILENT, popen)


def run_installer_after_quit(path: pathlib.Path, popen=subprocess.Popen) -> None:
    """The same when the person is quitting (MIN-382): the new version waits for the next start."""
    _start_installer(path, [*SILENT, NO_START], popen)
