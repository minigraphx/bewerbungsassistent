"""The browser the app opens in (G99, #369): the default browser, Google Chrome or Microsoft Edge, as far as installed.

The extension runs only in Chrome and Edge, so a person whose default is another browser can have the app open in
one of them. Whatever goes wrong with the chosen browser, the app opens in the default browser instead and the
address carries the notice for the first page: never zero windows.

On Windows the program comes from the App Paths of the registry and gets the address directly; `cmd /c start` would
cut the address at its "&". A browser that is still running after a short grace counts as started: the first
instance of Chrome or Edge keeps running, a second one hands the address over and ends.
"""
import dataclasses
import logging
import pathlib
import shutil
import subprocess
import sys
import webbrowser
from typing import Callable

from dialogs import BROWSERS, LINUX_COMMANDS
from settings import BROWSER_CHOICES, DEFAULT_BROWSER

log = logging.getLogger("bewerbungsbegleiter")

FALLBACK_PARAMETER = "browser-fehlt"  # read by the first page (seiten/app.js) for its notice
GRACE_SECONDS = 2.0
APP_PATHS = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
WINDOWS_PROGRAMS = {"chrome": "chrome.exe", "edge": "msedge.exe"}
MAC_APPLICATIONS = pathlib.Path("/Applications")
PAGE_PLATFORMS = {"win32": "windows", "darwin": "macos"}

Launch = Callable[[list[str]], int | None]


def windows_app_path(program: str, registry=None) -> str | None:
    """Where Windows finds `program` (as `start` would), for this user first; None when it is not registered."""
    if registry is None:
        return None
    for root in (registry.HKEY_CURRENT_USER, registry.HKEY_LOCAL_MACHINE):
        try:
            found = registry.QueryValue(root, rf"{APP_PATHS}\{program}")
        except OSError:
            continue
        if found:
            return found.strip('"')
    return None


def _registry():
    try:
        import winreg
        return winreg
    except ImportError:
        return None


def launch(command: list[str], popen: Callable[..., subprocess.Popen] = subprocess.Popen) -> int | None:
    """Start the browser without waiting for it; its exit code when it ended within the grace, otherwise None."""
    detached = {} if sys.platform == "win32" else {"start_new_session": True}  # the browser outlives the app
    process = popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **detached)
    try:
        return process.wait(timeout=GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        return None


@dataclasses.dataclass(frozen=True)
class System:
    """What this computer offers; the tests give stand-ins, so no test starts a real browser."""
    platform: str = sys.platform
    home: pathlib.Path = dataclasses.field(default_factory=pathlib.Path.home)
    which: Callable[[str], str | None] = shutil.which
    exists: Callable[[pathlib.Path], bool] = pathlib.Path.exists
    app_path: Callable[[str], str | None] = lambda program: windows_app_path(program, _registry())
    launch: Launch = launch
    open_default: Callable[[str], bool] = lambda address: webbrowser.open(address)


def current_system() -> System:
    return System()


def page_platform(platform: str) -> str:
    """The system as the settings page names it; on Linux the label for Chrome includes Chromium."""
    return PAGE_PLATFORMS.get(platform, "linux" if platform.startswith("linux") else "andere")


def command(browser: str, address: str, system: System) -> list[str] | None:
    """How to open `address` in `browser` here; None when this computer does not have it."""
    if browser not in WINDOWS_PROGRAMS:
        return None
    if system.platform == "darwin":
        name = BROWSERS[browser][0]
        bundles = (MAC_APPLICATIONS / f"{name}.app", system.home / "Applications" / f"{name}.app")
        return ["open", "-a", name, address] if any(system.exists(bundle) for bundle in bundles) else None
    if system.platform == "win32":
        program = system.app_path(WINDOWS_PROGRAMS[browser])
        return [program, address] if program else None
    if system.platform.startswith("linux"):
        found = next((path for path in map(system.which, LINUX_COMMANDS[browser]) if path), None)
        return [found, address] if found else None
    return None


def installed(system: System) -> dict[str, bool]:
    """Which choices this computer can follow; the default browser always."""
    return {choice: choice == DEFAULT_BROWSER or command(choice, "", system) is not None for choice in BROWSER_CHOICES}


def with_notice(address: str, browser: str) -> str:
    separator = "&" if "?" in address else "?"
    return f"{address}{separator}{FALLBACK_PARAMETER}={browser}"


def _started(browser: str, address: str, system: System) -> bool:
    found = command(browser, address, system)
    if found is None:
        log.warning("Browser für die App nicht gefunden: %s", browser)
        return False
    try:
        exit_code = system.launch(found)
    except (OSError, subprocess.SubprocessError) as error:
        log.warning("Browser für die App liess sich nicht starten (%s): %s", browser, error)
        return False
    if exit_code not in (None, 0):
        log.warning("Browser für die App endete mit %s: %s", exit_code, browser)
        return False
    return True


def open_app(choice: str, address: str, system: System) -> str | None:
    """Open the app in the chosen browser; the browser that failed when the default browser had to step in."""
    if choice == DEFAULT_BROWSER or choice not in BROWSER_CHOICES:
        _open_default(address, system)
        return None
    if _started(choice, address, system):
        return None
    _open_default(with_notice(address, choice), system)
    return choice


def _open_default(address: str, system: System) -> None:
    if not system.open_default(address):
        log.error("Kein Browser liess sich öffnen; die App läuft trotzdem und öffnet sich beim nächsten Doppelklick.")
