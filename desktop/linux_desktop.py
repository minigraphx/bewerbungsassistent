"""The app on Linux as AppImage (#73, G5): a stable path to start, a menu entry and the invitation link.

An AppImage runs from a temporary mount that is gone after it ends, so everything that starts the app later
(browser for the extension, invitation link, Claude Desktop) gets the AppImage file itself from $APPIMAGE.
There is no installer: on every start the app writes its menu entry with the scheme
`bewerbungsbegleiter://` for the current user, the same way Windows registers it in HKCU.
"""
import logging
import os
import pathlib
import shutil
import subprocess
from typing import Callable

import urlscheme

log = logging.getLogger("bewerbungsbegleiter")

DESKTOP_FILE = "bewerbungsbegleiter.desktop"
ICON_NAME = "bewerbungsbegleiter"
SCHEME_TYPE = f"x-scheme-handler/{urlscheme.SCHEME}"
TOOL_TIMEOUT_SECONDS = 20

Run = Callable[..., subprocess.CompletedProcess]


def launch_path(executable: pathlib.Path, environ: dict) -> pathlib.Path:
    """The AppImage file when running from one, else the program itself."""
    image = environ.get("APPIMAGE") or ""
    return pathlib.Path(image) if image and pathlib.Path(image).is_file() else executable


def _exec_argument(path: pathlib.Path) -> str:
    """One quoted argument as the desktop entry spec wants it, then escaped once more as a string value."""
    quoted = "".join("\\" + char if char in '"`$\\' else char for char in str(path))
    return ('"' + quoted + '"').replace("\\", "\\\\").replace("%", "%%")


def desktop_entry(executable: pathlib.Path) -> str:
    lines = ["[Desktop Entry]", "Type=Application", "Name=Bewerbungsbegleiter",
             "Comment=Bewerbungen vorbereiten, prüfen und festhalten",
             f"Exec={_exec_argument(executable)} %u", f"Icon={ICON_NAME}", "Terminal=false",
             "Categories=Office;", f"MimeType={SCHEME_TYPE};"]
    return "\n".join(lines) + "\n"


def _data_home(environ: dict, home: pathlib.Path) -> pathlib.Path:
    return pathlib.Path(environ.get("XDG_DATA_HOME") or home / ".local" / "share")


def _tool(command: list[str], run: Run) -> bool:
    try:
        return run(command, capture_output=True, timeout=TOOL_TIMEOUT_SECONDS).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def register(executable: pathlib.Path, icon: pathlib.Path | None, environ: dict, home: pathlib.Path,
             run: Run = subprocess.run) -> bool:
    """Write menu entry and icon, then claim the scheme; False if the link will not reach the app."""
    share = _data_home(environ, home)
    applications = share / "applications"
    applications.mkdir(parents=True, exist_ok=True)
    (applications / DESKTOP_FILE).write_text(desktop_entry(executable), encoding="utf-8")
    if icon is not None and icon.is_file():
        icons = share / "icons" / "hicolor" / "128x128" / "apps"
        icons.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(icon, icons / f"{ICON_NAME}.png")
    _tool(["update-desktop-database", str(applications)], run)  # optional: only speeds up the lookup
    return _tool(["xdg-mime", "default", DESKTOP_FILE, SCHEME_TYPE], run)


def register_quietly(executable: pathlib.Path, icon: pathlib.Path | None) -> None:
    """At start: the app runs without the entry too, the log says why the link does not work."""
    try:
        if not register(executable, icon, dict(os.environ), pathlib.Path.home()):
            log.warning("Einladungslink nicht angemeldet: xdg-mime fehlt oder lehnt ab")
    except OSError as error:
        log.warning("Menüeintrag nicht geschrieben: %s", error)
