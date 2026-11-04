"""Routes of the desktop app: version and update, quit (MIN-342, MIN-368). Only present in the packaged app."""
import dataclasses
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

CHECK_EVERY_SECONDS = 6 * 3600
QUIT_DELAY_SECONDS = 1.0
SELF_UPDATING = ("win32", "darwin")
FROZEN = getattr(sys, "frozen", False)
FAILED_BEFORE = "Das Update auf Version {version} liess sich nicht starten, die bisherige Version läuft weiter. Bitte die neue Version von Hand laden."
UPDATE_RUNNING = "Das Update läuft schon."


def _own_app() -> pathlib.Path | None:
    return updates_macos.running_app() if FROZEN and sys.platform == "darwin" else None


@dataclasses.dataclass
class Controls:
    stop: Callable[[], None]
    automatic: bool = FROZEN and sys.platform in SELF_UPDATING
    platform: str = sys.platform
    fetch: updates.Fetch = updates._fetch
    run_installer: Callable[[pathlib.Path], None] = updates.run_installer
    app: pathlib.Path | None = dataclasses.field(default_factory=_own_app)
    failed_note: pathlib.Path | None = None
    run_tool: updates_macos.Run = subprocess.run
    start_swap: Callable[..., None] = updates_macos.start_swap
    installing: threading.Lock = dataclasses.field(default_factory=threading.Lock)
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


def _install_windows(controls: Controls, found: updates.Update) -> None:
    folder = pathlib.Path(tempfile.mkdtemp(prefix="bewerbungsassistent-"))
    controls.run_installer(updates.download(found, folder, controls.fetch))


def _install_macos(controls: Controls, found: updates.Update) -> None:
    staging = updates_macos.prepare(found, controls.app, controls.fetch, controls.run_tool)
    try:
        controls.start_swap(controls.app, staging, controls.failed_note, found.version)
    except OSError as error:
        updates_macos.discard(staging)
        raise updates.UpdateError("Das Update liess sich nicht starten.") from error


def make_routes(controls: Controls) -> tuple[dict, dict]:
    from server import json_antwort

    def version(k, parameter, body):
        found = controls.update()
        if found is None:
            return json_antwort({"version": VERSION, "update": None})
        obstacle = controls.obstacle(found) if controls.automatic else ""
        automatic = controls.automatic and bool(found.installer_url) and not obstacle
        return json_antwort({"version": VERSION, "update": {"version": found.version, "seite": found.page_url,
                                                            "automatisch": automatic, "hinweis": obstacle}})

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

    def quit_app(k, parameter, body):
        controls.stop_soon()
        return json_antwort({"ok": True})

    return {"/api/app/version": version}, {"/api/app/aktualisieren": install, "/api/app/beenden": quit_app}
