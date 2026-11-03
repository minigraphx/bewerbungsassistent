"""Routes of the desktop app: version and update, quit (MIN-342). Only present in the packaged app."""
import dataclasses
import pathlib
import sys
import tempfile
import threading
import time
from typing import Callable

import updates
from version import VERSION

CHECK_EVERY_SECONDS = 6 * 3600
QUIT_DELAY_SECONDS = 1.0


@dataclasses.dataclass
class Controls:
    stop: Callable[[], None]
    automatic: bool = sys.platform == "win32" and getattr(sys, "frozen", False)
    fetch: updates.Fetch = updates._fetch
    run_installer: Callable[[pathlib.Path], None] = updates.run_installer
    _checked_at: float = 0.0
    _update: updates.Update | None = None
    _lock: threading.Lock = dataclasses.field(default_factory=threading.Lock)

    def update(self) -> updates.Update | None:
        with self._lock:
            if time.monotonic() - self._checked_at > CHECK_EVERY_SECONDS or not self._checked_at:
                self._update = updates.newer(VERSION, updates.latest(self.fetch))
                self._checked_at = time.monotonic()
            return self._update

    def stop_soon(self) -> None:
        threading.Timer(QUIT_DELAY_SECONDS, self.stop).start()


def make_routes(controls: Controls) -> tuple[dict, dict]:
    from server import json_antwort

    def version(k, parameter, body):
        found = controls.update()
        update = None if found is None else {"version": found.version, "seite": found.page_url,
                                             "automatisch": controls.automatic and bool(found.installer_url)}
        return json_antwort({"version": VERSION, "update": update})

    def install(k, parameter, body):
        found = controls.update()
        if found is None:
            raise ValueError("Es gibt keine neuere Version.")
        if not controls.automatic:
            raise ValueError(f"Bitte die neue Version hier laden: {found.page_url}")
        try:
            path = updates.download(found, pathlib.Path(tempfile.mkdtemp(prefix="bewerbungsassistent-")),
                                    controls.fetch)
        except updates.UpdateError as error:
            raise ValueError(str(error)) from error
        controls.run_installer(path)
        controls.stop_soon()
        return json_antwort({"ok": True, "version": found.version})

    def quit_app(k, parameter, body):
        controls.stop_soon()
        return json_antwort({"ok": True})

    return {"/api/app/version": version}, {"/api/app/aktualisieren": install, "/api/app/beenden": quit_app}
