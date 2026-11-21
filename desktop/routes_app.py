"""Routes of the desktop app: version and update, quit (MIN-342, MIN-368, MIN-382). Only present in the packaged app.

A found update is asked about first in a dialog (#32, G8). "Later" lasts until the app starts again: it lives only in
this process, so every new start asks once more.

Quitting also installs a waiting update, in the background and without opening the app again; whatever goes wrong
there, the app still ends and the update is offered again.

In the package of the Microsoft Store (#344) the Store brings updates: no check, no download, no pre-releases.
"""
import dataclasses
import logging
import pathlib
import subprocess
import sys
import tempfile
import threading
import time
from http import HTTPStatus
from typing import Callable

import msix_package
import settings
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
CHECK_ROUTE = "/api/app/updates-suchen"
BY_THE_STORE = "Updates kommen über den Microsoft Store."
CHECK_FAILED = ("Die Suche nach Updates hat nicht geklappt. Vielleicht fehlt die Internetverbindung; "
                "bitte später nochmals versuchen.")


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
    paths: settings.Paths | None = None  # where the switch for pre-releases is kept; none in the tests of other parts
    store: bool = dataclasses.field(default_factory=lambda: msix_package.running_packaged())
    _checked_at: float = 0.0
    _update: updates.Update | None = None
    _lock: threading.Lock = dataclasses.field(default_factory=threading.Lock)

    def beta(self) -> bool:
        return settings.beta_updates(self.paths) if self.paths else False

    def set_beta(self, on: bool) -> None:
        """Switch pre-releases on or off; the next question for an update asks the server again."""
        if self.paths is None:
            raise ValueError("Vorabversionen gibt es nur in der App.")
        with self._lock:
            settings.set_beta_updates(self.paths, on)
            self._checked_at = 0.0

    def update(self) -> updates.Update | None:
        if self.store:
            return None
        with self._lock:
            if time.monotonic() - self._checked_at > CHECK_EVERY_SECONDS or not self._checked_at:
                self._update = updates.newer(VERSION, updates.latest(self.fetch, self.platform, self.beta()))
                self._checked_at = time.monotonic()
            return self._update

    def check_now(self) -> updates.Update | None:
        """The button «Nach Updates suchen» (#370, G100): the server at once, and what it says also counts for the
        automatic offer and the install; UpdateError when it gave no answer, and the earlier offer stays."""
        with self._lock:
            found = updates.newer(VERSION, updates.latest_asked(self.fetch, self.platform, self.beta()))
            self._update, self._checked_at = found, time.monotonic()
            return found

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


def quit_app_now(controls: Controls) -> str | None:
    """Quit as the button does; with an update to install it ends after the install, and its version is returned."""
    found = _update_for_quit(controls)
    if found is None or not controls.installing.acquire(blocking=False):
        controls.stop_soon()
        return None
    controls.background(lambda: _install_then_stop(controls, found))
    return found.version


def _offer(controls: Controls, found: updates.Update | None) -> dict | None:
    """How the page offers a found version, the same for the start and for the button."""
    if found is None:
        return None
    automatic = controls.can_install(found)
    return {"version": found.version, "seite": found.page_url, "automatisch": automatic, "beimBeenden": automatic,
            "hinweis": controls.obstacle(found) if controls.automatic else "",
            "fragen": found.version != controls.postponed}


def make_routes(controls: Controls) -> tuple[dict, dict]:
    from server import StatusError, json_antwort

    def version(k, parameter, body):
        return json_antwort({"version": VERSION, "update": _offer(controls, controls.update())})

    def check(k, parameter, body):
        try:
            found = controls.check_now()
        except updates.UpdateError as error:
            log.warning("Suche nach Updates ohne Antwort: %s", error)
            raise StatusError(CHECK_FAILED, HTTPStatus.BAD_GATEWAY) from error
        return json_antwort({"version": VERSION, "update": _offer(controls, found), "vorabversionen": controls.beta()})

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

    def beta(k, parameter, body):
        return json_antwort({"an": controls.beta()})

    def set_beta(k, parameter, body):
        if not isinstance(body, dict) or not isinstance(body.get("an"), bool):
            raise ValueError("an erwartet (ja oder nein)")
        controls.set_beta(body["an"])
        return json_antwort({"an": controls.beta()})

    def quit_app(k, parameter, body):
        updating = quit_app_now(controls)
        return json_antwort({"ok": True, "aktualisiert": updating} if updating else {"ok": True})

    routes = ({"/api/app/version": version, "/api/app/vorabversionen": beta},
              {"/api/app/aktualisieren": install, "/api/app/spaeter": later, "/api/app/beenden": quit_app,
               "/api/app/vorabversionen": set_beta, CHECK_ROUTE: check})
    return _left_to_the_store(*routes) if controls.store else routes


def _left_to_the_store(get: dict, post: dict) -> tuple[dict, dict]:
    """The page hides the pre-releases when their route is missing, and shows the note instead of the button «Nach
    Updates suchen» when the version says store; that route is missing as well."""
    from server import json_antwort

    def version(k, parameter, body):
        return json_antwort({"version": VERSION, "update": None, "store": True})

    def refused(status: HTTPStatus):
        return lambda k, parameter, body: json_antwort({"fehler": BY_THE_STORE}, status)

    missing = refused(HTTPStatus.NOT_FOUND)
    return ({**get, "/api/app/version": version, "/api/app/vorabversionen": missing},
            {**post, "/api/app/aktualisieren": refused(HTTPStatus.CONFLICT), "/api/app/vorabversionen": missing,
             CHECK_ROUTE: missing})
