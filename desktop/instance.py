"""Only one app at a time: a second start opens the running one (and hands over an invitation code).

The running app writes its port and token to the app folder (readable only by the person). A second
start checks that this app still answers before it uses it; otherwise it starts a new one.
"""
import dataclasses
import json
import os
import urllib.error
import urllib.request

from settings import Paths

TIMEOUT_SECONDS = 3


@dataclasses.dataclass(frozen=True)
class Running:
    port: int
    token: str = dataclasses.field(repr=False)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/"


def write(paths: Paths, port: int, token: str) -> None:
    paths.app_dir.mkdir(parents=True, exist_ok=True)
    data = json.dumps({"port": port, "token": token, "pid": os.getpid()})
    fd = os.open(paths.instance, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(data)


def remove(paths: Paths) -> None:
    try:
        paths.instance.unlink()
    except OSError:
        pass


def _read(paths: Paths) -> Running | None:
    try:
        data = json.loads(paths.instance.read_text(encoding="utf-8"))
        return Running(int(data["port"]), str(data["token"]))
    except (OSError, ValueError, KeyError, TypeError):
        return None


def find(paths: Paths) -> Running | None:
    """The running app, if it answers with the stored token."""
    running = _read(paths)
    if running is None:
        return None
    request = urllib.request.Request(f"{running.url}api/bewerbungen?t={running.token}")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310 (local)
            return running if response.status == 200 else None
    except (urllib.error.URLError, OSError, ValueError):
        return None


def ask_to_quit(running: Running) -> None:
    """Ask the running app to quit; if it does not answer, there is nothing more to do."""
    request = urllib.request.Request(f"{running.url}api/app/beenden", data=b"{}",
                                     headers={"Content-Type": "application/json", "X-Token": running.token},
                                     method="POST")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS):  # noqa: S310 (local)
            pass
    except (urllib.error.URLError, OSError):
        pass


def forward_code(running: Running, code: str) -> str | None:
    """Let the running app redeem an invitation; the German error message, or None if it worked."""
    request = urllib.request.Request(f"{running.url}api/ki/einladung", data=json.dumps({"code": code}).encode(),
                                     headers={"Content-Type": "application/json", "X-Token": running.token},
                                     method="POST")
    try:
        with urllib.request.urlopen(request, timeout=60):  # noqa: S310 (local)
            return None
    except urllib.error.HTTPError as error:
        try:
            return json.loads(error.read()).get("fehler") or "Einladung nicht eingelöst."
        except (ValueError, AttributeError):
            return "Einladung nicht eingelöst."
    except (urllib.error.URLError, OSError):
        return "Die App antwortet nicht."
