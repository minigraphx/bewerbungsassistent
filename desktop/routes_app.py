"""Routes of the desktop app: version and update, quit (MIN-342, MIN-368, MIN-382). Only present in the packaged app.

A found update is asked about first in a dialog (#32, G8). "Later" lasts until the app starts again: it lives only in
this process, so every new start asks once more.

Quitting also installs a waiting update, in the background and without opening the app again; whatever goes wrong
there, the app still ends and the update is offered again.
"""
import dataclasses
import logging
import pathlib
import subprocess
import sys
import tempfile
import threading
import time
from typing import Callable

import updates
import updates_macos
from version import VERSION

log = logging.getLogger("bewerbungsbegleiter")

CHECK_EVERY_SECONDS = 6 * 3600
QUIT_DELAY_SECONDS = 1.0
SELF_UPDATING = ("win32", "darwin")
FROZEN = getattr(sys, "frozen", False)
FAILED_BEFORE = "Das Update auf Version {version} liess sich nicht starten, die bisherige Version läuft weiter. Bitte die neue Version von Hand laden."
UPDATE_RUNNING = "Das Update läuft schon."


def _own_app() -> pathlib.Path | None:
    return updates_macos.running_app() if FROZEN and sys.platform == "darwin" else None


def _in_background(work: Callable[[], None]) -> None:
    threading.Thread(target=work, name="update-beim-beenden").start()  # not a daemon: it must finish its work


@dataclasses.dataclass
class Controls:
    stop: Callable[[], None]
    automatic: bool = FROZEN and sys.platform in SELF_UPDATING
    platform: str = sys.platform
    fetch: updates.Fetch = updates._fetch
    run_installer: Callable[[pathlib.Path], None] = updates.run_installer
    run_installer_after_quit: Callable[[pathlib.Path], None] = updates.run_installer_after_quit
    background: Callable[[Callable[[], None]], None] = _in_background
    app: pathlib.Path | None = dataclasses.field(default_factory=_own_app)
    failed_note: pathlib.Path | None = None
    run_tool: updates_macos.Run = subprocess.run
    start_swap: Callable[..., None] = updates_macos.start_swap
    installing: threading.Lock = dataclasses.field(default_factory=threading.Lock)
    postponed: str = ""  # the version the person put off with "later" in this run
    _checked_at: float = 0.0
    _update: updates.Update | None = None
    _lock: threading.Lock = dataclasses.field(default_factory=threading.Lock)

    def update(self) -> updates.Update | None:
        with self._lock:
            if time.monotonic() - self._checked_at > CHECK_EVERY_SECONDS or not self._checked_at:
                self._update = updates.newer(VERSION, updates.latest(self.fetch, self.platform))
                self._checked_at = time.monotonic()
            return self._update

    def stop_soon(self) -> None:
        threading.Timer(QUIT_DELAY_SECONDS, self.stop).start()

    def failed_version(self) -> str:
        """The version whose start went wrong last, written by the swap; a newer one gets its own try."""
        try:
            return self.failed_note.read_text(encoding="utf-8").strip() if self.failed_note else ""
        except OSError:
            return ""

    def obstacle(self, found: updates.Update) -> str:
        """Why the update has to be done by hand although this system could do it itself; empty if nothing."""
        if self.platform != "darwin":
            return ""
        if self.failed_version() == found.version:
            return FAILED_BEFORE.format(version=found.version)
        return updates_macos.place_problem(self.app) or ""

    def can_install(self, found: updates.Update) -> bool:
        return self.automatic and bool(found.installer_url) and not self.obstacle(found)


def _install_windows(controls: Controls, found: updates.Update, after_quit: bool = False) -> None:
    folder = pathlib.Path(tempfile.mkdtemp(prefix="bewerbungsbegleiter-"))
    run = controls.run_installer_after_quit if after_quit else controls.run_installer
    run(updates.download(found, folder, controls.fetch))


def _install_macos(controls: Controls, found: updates.Update, after_quit: bool = False) -> None:
    staging = updates_macos.prepare(found, controls.app, controls.fetch, controls.run_tool)
    try:
        controls.start_swap(controls.app, staging, controls.failed_note, found.version, check_only=after_quit)
    except OSError as error:
        updates_macos.discard(staging)
        raise updates.UpdateError("Das Update liess sich nicht starten.") from error


def _update_for_quit(controls: Controls) -> updates.Update | None:
    """The update to install while quitting; quitting must work whatever the check does."""
    try:
        found = controls.update()
        return found if found and controls.can_install(found) else None
    except Exception as error:  # noqa: BLE001
        log.warning("Update beim Beenden nicht geprüft: %s", error)
        return None


def _install_then_stop(controls: Controls, found: updates.Update) -> None:
    try:
        (_install_macos if controls.platform == "darwin" else _install_windows)(controls, found, after_quit=True)
    except Exception as error:  # noqa: BLE001 (the next start offers it again)
        log.warning("Update beim Beenden nicht installiert: %s", error)
    finally:
        controls.stop_soon()


def make_routes(controls: Controls) -> tuple[dict, dict]:
    from server import json_antwort

    def version(k, parameter, body):
        found = controls.update()
        if found is None:
            return json_antwort({"version": VERSION, "update": None})
        obstacle = controls.obstacle(found) if controls.automatic else ""
        automatic = controls.can_install(found)
        return json_antwort({"version": VERSION, "update": {"version": found.version, "seite": found.page_url,
                                                            "automatisch": automatic, "beimBeenden": automatic,
                                                            "hinweis": obstacle,
                                                            "fragen": found.version != controls.postponed}})

    def install(k, parameter, body):
        found = controls.update()
        if found is None:
            raise ValueError("Es gibt keine neuere Version.")
        if not controls.automatic:
            raise ValueError(f"Bitte die neue Version hier laden: {found.page_url}")
        obstacle = controls.obstacle(found)
        if obstacle:
            raise ValueError(f"{obstacle} {found.page_url}")
        if not controls.installing.acquire(blocking=False):
            raise ValueError(UPDATE_RUNNING)
        try:
            (_install_macos if controls.platform == "darwin" else _install_windows)(controls, found)
        except updates.UpdateError as error:
            controls.installing.release()
            raise ValueError(str(error)) from error
        except Exception:
            controls.installing.release()  # otherwise every retry would say the update is still running
            raise
        controls.stop_soon()
        return json_antwort({"ok": True, "version": found.version})

    def later(k, parameter, body):
        found = controls.update()
        if found is None:
            raise ValueError("Es gibt keine neuere Version.")
        controls.postponed = found.version
        return json_antwort({"ok": True})

    def quit_app(k, parameter, body):
        found = _update_for_quit(controls)
        if found is None or not controls.installing.acquire(blocking=False):
            controls.stop_soon()
            return json_antwort({"ok": True})
        controls.background(lambda: _install_then_stop(controls, found))
        return json_antwort({"ok": True, "aktualisiert": found.version})

    return {"/api/app/version": version}, {"/api/app/aktualisieren": install, "/api/app/spaeter": later,
                                         "/api/app/beenden": quit_app}
