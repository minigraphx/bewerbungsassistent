"""Checks of the MSIX trial (#255): does the outside world still reach the app when it is installed as MSIX?

Runs on the CI's Windows runner after the package is installed and its app started the way a person starts it
(.github/workflows/msix-versuch.yml), from a normal process outside the package, like a browser or Claude Desktop.
Each check prints PASS or FAIL with what it saw; a FAIL is a result of the trial, not an error of this script.

  python desktop/msix/msix_check.py --family <PackageFamilyName> --install-location <folder>
"""
import argparse
import dataclasses
import json
import os
import pathlib
import re
import struct
import subprocess
import sys
import threading
import urllib.request
from typing import BinaryIO, Callable

CHECKS = ("registry", "manifest", "host", "link", "claude")
APP_NAME = "Bewerbungsbegleiter"  # as settings.APP_NAME
INSTANCE_FILE = "instanz.json"  # as settings.INSTANCE_FILE
EXECUTABLE = f"{APP_NAME}.exe"
HOST_KEYS = {"Chrome": r"HKCU\Software\Google\Chrome\NativeMessagingHosts\bewerbungsbegleiter",
             "Edge": r"HKCU\Software\Microsoft\Edge\NativeMessagingHosts\bewerbungsbegleiter"}
LINK_KEY = r"HKCU\Software\Classes\bewerbungsbegleiter\shell\open\command"
ORIGIN = "chrome-extension://ghniboofenadplgmdgddmgjaaeeogejn/"  # the developer add-on, as native_messaging
CLAUDE_CONFIG = pathlib.Path("Claude") / "claude_desktop_config.json"
SERVER_NAME = "bewerbungsbegleiter"
HOST_TIMEOUT = 60
HTTP_TIMEOUT = 30
DEFAULT_VALUE = re.compile(r"^\s*\([^)]*\)\s+REG_(?:EXPAND_)?SZ[ \t]+(?P<value>\S.*?)\s*$", re.MULTILINE)


@dataclasses.dataclass(frozen=True)
class Result:
    name: str
    passed: bool
    seen: str

    def line(self) -> str:
        return f"{'PASS' if self.passed else 'FAIL'} {self.name}: {self.seen}"


def frame(message: dict) -> bytes:
    """A message as the browser sends it: 4 bytes length, little-endian, then the JSON."""
    data = json.dumps(message).encode("utf-8")
    return struct.pack("<I", len(data)) + data


def read_framed(stream: BinaryIO) -> dict | None:
    """One framed message, or None when the stream ends before it is complete."""
    head = stream.read(4)
    if len(head) < 4:
        return None
    size = struct.unpack("<I", head)[0]
    data = stream.read(size)
    return json.loads(data.decode("utf-8")) if len(data) == size else None


def default_value(reg_output: str) -> str | None:
    """The default value in the output of `reg query <key> /ve`, whatever the language of Windows."""
    found = DEFAULT_VALUE.search(reg_output)
    return found.group("value") if found else None


def command_program(command: str) -> str:
    """The program of a shell command like `"C:\\...\\app.exe" "%1"`."""
    command = command.strip()
    if command.startswith('"'):
        return command[1:].split('"', 1)[0]
    return command.split(" ", 1)[0]


def app_places(roaming: pathlib.Path, local: pathlib.Path, family: str) -> list[pathlib.Path]:
    """The app folder as the app writes it, and where MSIX redirects writes to AppData of a packaged app."""
    return [roaming / APP_NAME, local / "Packages" / family / "LocalCache" / "Roaming" / APP_NAME]


def running_app(places: list[pathlib.Path]) -> tuple[pathlib.Path, int, str] | None:
    """(folder, port, token) of the first place holding the instance file of the running app."""
    for place in places:
        try:
            data = json.loads((place / INSTANCE_FILE).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        return place, int(data["port"]), str(data["token"])
    return None


def summary(results: list[Result]) -> str:
    return "MSIX-Versuch (#255)\n\n" + "\n".join(result.line() for result in results)


def reg_query(key: str) -> str:
    done = subprocess.run(["reg", "query", key, "/ve"], capture_output=True, text=True, errors="replace")  # noqa: S603, S607
    return done.stdout + done.stderr


def check_registry(query: Callable[[str], str]) -> tuple[Result, str | None]:
    values = {browser: default_value(query(key)) for browser, key in HOST_KEYS.items()}
    seen = "; ".join(f"{browser}: {value or 'nicht sichtbar'}" for browser, value in values.items())
    return Result("registry", all(values.values()), seen), next((v for v in values.values() if v), None)


def check_manifest(path: str | None) -> tuple[Result, pathlib.Path | None]:
    if not path:
        return Result("manifest", False, "kein Pfad, weil der Registry-Eintrag fehlt"), None
    try:
        target = pathlib.Path(json.loads(pathlib.Path(path).read_text(encoding="utf-8"))["path"])
    except (OSError, ValueError, KeyError) as error:
        return Result("manifest", False, f"{path} nicht lesbar: {error}"), None
    return Result("manifest", target.is_file(), f"{path} lesbar, path {target} "
                  f"{'existiert' if target.is_file() else 'fehlt'}"), target


def ping(executable: pathlib.Path, timeout: float = HOST_TIMEOUT) -> dict | None:
    """Start the host like a browser does and send `hallo`; its framed reply, or None."""
    process = subprocess.Popen([str(executable), ORIGIN], stdin=subprocess.PIPE, stdout=subprocess.PIPE,  # noqa: S603
                               stderr=subprocess.DEVNULL)
    reply: list[dict | None] = [None]

    def read() -> None:
        reply[0] = read_framed(process.stdout)

    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    process.stdin.write(frame({"id": 1, "art": "hallo"}))
    process.stdin.flush()
    reader.join(timeout)
    process.stdin.close()
    try:
        process.wait(10)
    except subprocess.TimeoutExpired:
        process.kill()
    return reply[0]


def check_host(target: pathlib.Path | None, packaged: pathlib.Path, send: Callable = ping) -> Result:
    executable = target or packaged
    try:
        reply = send(executable)
    except OSError as error:
        reply, problem = None, f"Start nicht möglich: {error}"
    else:
        problem = "keine Antwort"
    if not reply:
        seen = problem
    else:
        data = reply.get("daten") or {}
        seen = (f"Antwort ok={reply.get('ok')}, Version {data.get('version')}, "
                f"sieht die laufende App: {'ja' if data.get('app') else 'nein'}")
    via = "über das Manifest" if target else "direkt aus dem Paketordner, weil kein Manifest sichtbar ist"
    return Result("host", bool(target and reply and reply.get("ok")), f"{executable} {via}: {seen}")


def check_link(query: Callable[[str], str]) -> Result:
    command = default_value(query(LINK_KEY))
    if not command:
        return Result("link", False, f"{LINK_KEY} nicht sichtbar")
    program = pathlib.Path(command_program(command))
    return Result("link", program.is_file(), f"{command} ({'Programm existiert' if program.is_file() else 'Programm fehlt'})")


def post(port: int, token: str, path: str, body: dict) -> dict:
    request = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode("utf-8"), method="POST",
                                     headers={"Content-Type": "application/json", "X-Token": token})
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:  # noqa: S310 (local app)
        return json.loads(response.read())


def _holds_entry(path: pathlib.Path) -> bool:
    try:
        return SERVER_NAME in json.loads(path.read_text(encoding="utf-8-sig")).get("mcpServers", {})
    except (OSError, ValueError, AttributeError):
        return False


def check_claude(roaming: pathlib.Path, local: pathlib.Path, family: str, send: Callable = post) -> Result:
    found = running_app(app_places(roaming, local, family))
    if found is None:
        return Result("claude", False, "laufende App nicht gefunden (keine instanz.json)")
    folder, port, token = found
    try:
        send(port, token, "/api/claude/zugang", {"an": True, "bestaetigt": True})
        said = send(port, token, "/api/claude/desktop", {"eintragen": True}).get("desktop_datei")
    except (OSError, ValueError) as error:
        return Result("claude", False, f"App in {folder}, Eintragen fehlgeschlagen: {error}")
    real = roaming / CLAUDE_CONFIG
    redirected = local / "Packages" / family / "LocalCache" / "Roaming" / CLAUDE_CONFIG
    where = [f"{place} {'mit' if _holds_entry(place) else 'ohne'} Eintrag" for place in (real, redirected)]
    return Result("claude", _holds_entry(real), f"App-Ordner {folder}; App meldet {said}; " + "; ".join(where))


def keep_open(roaming: pathlib.Path, local: pathlib.Path, family: str, send: Callable = post) -> None:
    """Report a page as open: without one, the app quits a minute after its start (presence.GRACE_SECONDS)."""
    found = running_app(app_places(roaming, local, family))
    if found is None:
        return
    try:
        send(found[1], found[2], "/api/app/da", {"seite": "msix-versuch"})
    except (OSError, ValueError) as error:
        print(f"App nicht erreicht: {error}", file=sys.stderr)


def run(family: str, install_location: pathlib.Path, environ: dict) -> list[Result]:
    roaming, local = pathlib.Path(environ["APPDATA"]), pathlib.Path(environ["LOCALAPPDATA"])
    keep_open(roaming, local, family)
    registry, manifest_path = check_registry(reg_query)
    manifest, target = check_manifest(manifest_path)
    host = check_host(target, install_location / EXECUTABLE)
    return [registry, manifest, host, check_link(reg_query), check_claude(roaming, local, family)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Checks of the MSIX trial (#255)")
    ap.add_argument("--family", required=True, help="PackageFamilyName of the installed package")
    ap.add_argument("--install-location", required=True, type=pathlib.Path)
    args = ap.parse_args(argv)
    text = summary(run(args.family, args.install_location, dict(os.environ)))
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
            handle.write("```\n" + text + "\n```\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
