"""The app as Native Messaging host (MIN-339): the browser starts it for the extension.

The browser starts the app with the extension's origin as argument and talks to it over stdin/stdout:
each message is 4 bytes length (native byte order, little-endian on all our platforms) and JSON. This
process only passes the requests on to the running app (address and token from the app folder) and starts
the app first if it does not run. It answers only a fixed list of routes; everything else is refused.

Messages:  {"id": 1, "art": "hallo"}
           {"id": 2, "art": "anfrage", "methode": "POST", "pfad": "/api/suche/treffer", "daten": {...}}
Answers:   {"id": …, "ok": true, "daten": {...}}  or  {"id": …, "ok": false, "fehler": "…"}
"""
import json
import logging
import os
import pathlib
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import BinaryIO, Callable

import instance
import version
from settings import Paths

ORIGIN_PREFIX = "chrome-extension://"
ALLOWED = {("GET", "/api/suche/plan"), ("POST", "/api/suche/sichten"), ("POST", "/api/suche/treffer"),
           ("POST", "/api/suche/abschluss")}
MAX_IN = 8 * 1024 * 1024
MAX_OUT = 1024 * 1024  # limit of the browser for messages to the extension
START_TIMEOUT = 40
REQUEST_TIMEOUT = 120
NOT_RUNNING = "Die App startet nicht. Bitte den Bewerbungsassistenten von Hand öffnen."
START_LOCK = "start-erweiterung.lock"
UNEXPECTED = "Unerwarteter Fehler in der App, Details im Protokoll."
log = logging.getLogger("bewerbungsassistent")


def invoked(argv: list[str]) -> bool:
    """Started by the browser: Chrome and Edge pass the extension's origin (on Windows also --parent-window)."""
    return any(arg.startswith(ORIGIN_PREFIX) for arg in argv)


def _read_exact(stream: BinaryIO, size: int) -> bytes:
    """Up to size bytes; a pipe hands out large messages in pieces. Shorter only at the end of the stream."""
    parts, missing = [], size
    while missing:
        part = stream.read(missing)
        if not part:
            break
        parts.append(part)
        missing -= len(part)
    return b"".join(parts)


def read_message(stream: BinaryIO) -> dict | None:
    """The next message, or None when the browser closed the connection."""
    head = _read_exact(stream, 4)
    if len(head) < 4:
        return None
    size = struct.unpack("<I", head)[0]
    if size > MAX_IN:
        raise ValueError("Nachricht zu gross")
    data = _read_exact(stream, size)
    if len(data) < size:
        return None
    message = json.loads(data.decode("utf-8"))
    if not isinstance(message, dict):
        raise ValueError("Nachricht muss ein Objekt sein")
    return message


def write_message(stream: BinaryIO, message: dict) -> None:
    data = json.dumps(message, ensure_ascii=False).encode("utf-8")
    if len(data) > MAX_OUT:
        data = json.dumps({"id": message.get("id"), "ok": False, "fehler": "Antwort zu gross"}).encode("utf-8")
    view = memoryview(struct.pack("<I", len(data)) + data)
    while view:
        written = stream.write(view)
        view = view[written if written is not None else len(view):]
    stream.flush()


def call(running: instance.Running, method: str, path: str, data) -> dict:
    """One request to the running app; its German error message becomes ValueError."""
    if method == "GET":
        query = urllib.parse.urlencode({"t": running.token, **(data or {})})
        request = urllib.request.Request(f"{running.url.rstrip('/')}{path}?{query}")
    else:
        request = urllib.request.Request(f"{running.url.rstrip('/')}{path}", method="POST",
                                         data=json.dumps(data or {}).encode("utf-8"),
                                         headers={"Content-Type": "application/json", "X-Token": running.token})
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:  # noqa: S310 (local)
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        try:
            message = json.loads(error.read()).get("fehler")
        except (ValueError, AttributeError):
            message = None
        raise ValueError(message or f"Die App antwortet mit Fehler {error.code}.") from error
    except (urllib.error.URLError, OSError) as error:
        raise ValueError("Die App antwortet nicht.") from error


def launch_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--kein-browser"]
    return [sys.executable, str(pathlib.Path(__file__).resolve().parent / "start.py"), "--kein-browser"]


def launch(command: list[str], platform: str = sys.platform) -> None:
    """Start the app on its own, detached: it keeps running when the browser ends this process."""
    options = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL,
               "close_fds": True}
    if platform != "win32":
        subprocess.Popen(command, start_new_session=True, **options)  # noqa: S603
        return
    detached = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    try:
        subprocess.Popen(command, creationflags=detached | subprocess.CREATE_BREAKAWAY_FROM_JOB, **options)  # noqa: S603
    except OSError:
        subprocess.Popen(command, creationflags=detached, **options)  # noqa: S603


class Host:
    def __init__(self, paths: Paths, find: Callable = instance.find, start: Callable[[], None] | None = None,
                 send: Callable = call, sleep: Callable[[float], None] = time.sleep,
                 timeout: float = START_TIMEOUT) -> None:
        self.paths, self.find, self.send, self.sleep, self.timeout = paths, find, send, sleep, timeout
        self.start = start or (lambda: launch(launch_command()))

    def _claim_start(self) -> bool:
        """Only one host starts the app; a second one (e.g. popup and page at once) waits for it."""
        lock = self.paths.app_dir / START_LOCK
        self.paths.app_dir.mkdir(parents=True, exist_ok=True)
        try:
            if time.time() - lock.stat().st_mtime > self.timeout:
                lock.unlink()
        except FileNotFoundError:
            pass
        try:
            os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            return True
        except FileExistsError:
            return False

    def running(self) -> instance.Running:
        found = self.find(self.paths)
        if found is not None:
            return found
        claimed = self._claim_start()
        try:
            if claimed:
                log.info("App für die Erweiterung gestartet")
                self.start()
            waited = 0.0
            while waited < self.timeout:
                self.sleep(0.5)
                waited += 0.5
                found = self.find(self.paths)
                if found is not None:
                    return found
        finally:
            if claimed:
                (self.paths.app_dir / START_LOCK).unlink(missing_ok=True)
        raise ValueError(NOT_RUNNING)

    def answer(self, message: dict) -> dict:
        kind = message.get("art")
        if kind == "hallo":
            found = self.find(self.paths)
            return {"version": version.VERSION, "app": found.url if found else None}
        if kind != "anfrage":
            raise ValueError("Unbekannte Nachricht")
        method, path, data = message.get("methode"), message.get("pfad"), message.get("daten")
        if not isinstance(method, str) or not isinstance(path, str) or not isinstance(data, (dict, type(None))):
            raise ValueError("Die Anfrage hat eine unbekannte Form.")
        if (method, path) not in ALLOWED:
            raise ValueError("Diese Anfrage ist für die Erweiterung nicht erlaubt.")
        return self.send(self.running(), method, path, data)

    def serve(self, incoming: BinaryIO, outgoing: BinaryIO) -> int:
        while True:
            try:
                message = read_message(incoming)
            except (ValueError, UnicodeDecodeError) as error:
                log.warning("Native Messaging: ungültige Nachricht (%s)", error)
                return 1
            if message is None:
                return 0
            reply_id = message.get("id")
            try:
                reply = {"id": reply_id, "ok": True, "daten": self.answer(message)}
            except ValueError as error:
                reply = {"id": reply_id, "ok": False, "fehler": str(error)}
            except Exception:  # noqa: BLE001 (the extension must get an answer, the details go to the log)
                log.exception("Native Messaging: Anfrage fehlgeschlagen")
                reply = {"id": reply_id, "ok": False, "fehler": UNEXPECTED}
            write_message(outgoing, reply)


def _std_fd(number: int) -> int:
    """File descriptor of stdin/stdout; a windowed app on Windows may need it from the handle Chrome passed."""
    try:
        os.fstat(number)
        return number
    except OSError:
        if sys.platform != "win32":
            raise
    import ctypes
    import msvcrt
    handle = ctypes.windll.kernel32.GetStdHandle(-10 if number == 0 else -11)
    return msvcrt.open_osfhandle(handle, os.O_BINARY)


def streams() -> tuple[BinaryIO, BinaryIO]:
    incoming, outgoing = _std_fd(0), _std_fd(1)
    if sys.platform == "win32":
        import msvcrt
        for fd in (incoming, outgoing):
            msvcrt.setmode(fd, os.O_BINARY)
    return open(incoming, "rb", buffering=0, closefd=False), open(outgoing, "wb", buffering=0, closefd=False)


def main(paths: Paths) -> int:
    incoming, outgoing = streams()
    return Host(paths).serve(incoming, outgoing)
