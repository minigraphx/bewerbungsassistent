"""The app registers itself with the browsers as a Native Messaging host (MIN-339).

Then the extension reaches the app without a port and without a pairing code: the browser starts the app
with the extension's origin as argument (see `native_host.py`), and only the extensions listed here may
connect. Registered on every start, so a moved or updated app is found again.

  macOS/Linux: <browser profile folder>/NativeMessagingHosts/bewerbungsassistent.json
  Windows:     manifest in the app folder, path in HKCU\\Software\\<browser>\\NativeMessagingHosts\\…
"""
import json
import logging
import pathlib
import shlex
import sys
from typing import Callable

from settings import Paths

log = logging.getLogger("bewerbungsassistent")

HOST_NAME = "bewerbungsassistent"
# The developer add-on (key in erweiterung/manifest.json); the IDs of the stores follow with the release.
EXTENSION_IDS = ("ghniboofenadplgmdgddmgjaaeeogejn",)
MANIFEST_FILE = f"{HOST_NAME}.json"
WINDOWS_MANIFEST = "native-messaging-host.json"
LAUNCHER = "native-messaging-host"
MAC_BROWSERS = ("Google/Chrome", "Google/Chrome Beta", "Microsoft Edge", "Chromium", "BraveSoftware/Brave-Browser")
LINUX_BROWSERS = ("google-chrome", "chromium", "microsoft-edge", "BraveSoftware/Brave-Browser")
WINDOWS_KEYS = (r"Software\Google\Chrome\NativeMessagingHosts", r"Software\Microsoft\Edge\NativeMessagingHosts",
                r"Software\Chromium\NativeMessagingHosts", r"Software\BraveSoftware\Brave-Browser\NativeMessagingHosts")
SOURCE_MODULES = ("desktop", "bewerbungen", "lebenslauf", "onboarding")


def manifest(executable: pathlib.Path) -> dict:
    return {"name": HOST_NAME, "description": "Bewerbungsassistent", "path": str(executable), "type": "stdio",
            "allowed_origins": [f"chrome-extension://{extension_id}/" for extension_id in EXTENSION_IDS]}


def launcher(paths: Paths, platform: str, source_dir: pathlib.Path, python: pathlib.Path) -> pathlib.Path:
    """Running from source: a small script, since the browser starts one program without arguments."""
    repo = source_dir.parent
    modules = [str(repo / name) for name in SOURCE_MODULES]
    start = source_dir / "start.py"
    paths.app_dir.mkdir(parents=True, exist_ok=True)
    if platform == "win32":
        script = paths.app_dir / f"{LAUNCHER}.bat"
        script.write_text(f'@echo off\r\nset "PYTHONPATH={";".join(modules)}"\r\n"{python}" "{start}" %*\r\n',
                          encoding="utf-8")
        return script
    script = paths.app_dir / f"{LAUNCHER}.sh"
    script.write_text(f"#!/bin/sh\nexport PYTHONPATH={shlex.quote(':'.join(modules))}\n"
                      f"exec {shlex.quote(str(python))} {shlex.quote(str(start))} \"$@\"\n", encoding="utf-8")
    script.chmod(0o755)
    return script


def _manifest_dirs(platform: str, home: pathlib.Path) -> list[pathlib.Path]:
    """Folders of installed browsers; a browser installed later is found on the next start."""
    if platform == "darwin":
        base = home / "Library" / "Application Support"
        browsers = [base / name for name in MAC_BROWSERS]
    else:
        browsers = [home / ".config" / name for name in LINUX_BROWSERS]
    return [b / "NativeMessagingHosts" for b in browsers if b.is_dir()]


def _set_registry(key: str, value: str) -> None:
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{key}\{HOST_NAME}") as handle:
        winreg.SetValueEx(handle, "", 0, winreg.REG_SZ, value)


def register(paths: Paths, executable: pathlib.Path, platform: str = sys.platform, home: pathlib.Path | None = None,
             set_registry: Callable[[str, str], None] = _set_registry) -> list[str]:
    """Write the host manifest for every installed browser; returns where it was registered."""
    text = json.dumps(manifest(executable), indent=1)
    if platform == "win32":
        paths.app_dir.mkdir(parents=True, exist_ok=True)
        target = paths.app_dir / WINDOWS_MANIFEST
        target.write_text(text, encoding="utf-8")
        for key in WINDOWS_KEYS:
            set_registry(key, str(target))
        return list(WINDOWS_KEYS)
    written = []
    for folder in _manifest_dirs(platform, home or pathlib.Path.home()):
        try:
            folder.mkdir(exist_ok=True)
            (folder / MANIFEST_FILE).write_text(text, encoding="utf-8")
        except OSError as error:
            log.warning("Native Messaging: %s nicht angemeldet (%s)", folder, error)
            continue
        written.append(str(folder))
    return written
