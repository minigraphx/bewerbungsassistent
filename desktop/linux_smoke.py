"""Does the AppImage work on a fresh Linux? python desktop/linux_smoke.py <AppImage>; run by the CI on Ubuntu (#73).

Start in an empty home folder, then check what only the packed app can show: the menu entry claims the
invitation link, the browser finds the AppImage for the extension and reaches the running app through it,
and a link reaches the running app. Nothing is sent anywhere but to this computer.
"""
import json
import os
import pathlib
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request

ORIGIN = "chrome-extension://ghniboofenadplgmdgddmgjaaeeogejn/"
LINK = "bewerbungsbegleiter://einladung?code=TEST-1234"
START_SECONDS = 60
TIMEOUT_SECONDS = 60


def environment(home: pathlib.Path) -> dict:
    env = {key: value for key, value in os.environ.items() if not key.startswith("XDG_")}
    return {**env, "HOME": str(home), "BROWSER": "true",  # no browser in the CI: "opening" one does nothing
            "PYTHON_KEYRING_BACKEND": "keyring.backends.null.Keyring"}


def wait_for_instance(app_dir: pathlib.Path) -> dict:
    deadline = time.monotonic() + START_SECONDS
    while time.monotonic() < deadline:
        try:
            return json.loads((app_dir / "instanz.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            time.sleep(0.5)
    raise AssertionError("Die App hat nicht gestartet.")


def native_hello(program: str, env: dict) -> dict:
    data = json.dumps({"id": 1, "art": "hallo"}).encode()
    done = subprocess.run([program, ORIGIN], input=struct.pack("<I", len(data)) + data, capture_output=True,
                          env=env, timeout=TIMEOUT_SECONDS, check=False)
    if len(done.stdout) < 4:
        raise AssertionError(f"Native Messaging antwortet nicht: {done.stderr[-500:]!r}")
    size = struct.unpack("<I", done.stdout[:4])[0]
    return json.loads(done.stdout[4:4 + size])


def check_menu_entry(home: pathlib.Path, image: pathlib.Path, env: dict) -> None:
    entry = (home / ".local" / "share" / "applications" / "bewerbungsbegleiter.desktop").read_text(encoding="utf-8")
    assert f'Exec="{image}" %u' in entry, entry
    handler = subprocess.run(["xdg-mime", "query", "default", "x-scheme-handler/bewerbungsbegleiter"],
                             capture_output=True, text=True, env=env, timeout=TIMEOUT_SECONDS, check=False)
    assert handler.stdout.strip() == "bewerbungsbegleiter.desktop", handler


def check_extension(home: pathlib.Path, image: pathlib.Path, env: dict) -> None:
    manifest = json.loads((home / ".config" / "google-chrome" / "NativeMessagingHosts" / "bewerbungsbegleiter.json")
                          .read_text(encoding="utf-8"))
    assert manifest["path"] == str(image), manifest
    answer = native_hello(manifest["path"], env)
    assert answer.get("ok") and answer["daten"]["app"], answer


def check_link(home: pathlib.Path, image: pathlib.Path, env: dict) -> None:
    done = subprocess.run([str(image), LINK], capture_output=True, env=env, timeout=TIMEOUT_SECONDS, check=False)
    log = (home / ".config" / "bewerbungsbegleiter" / "protokoll.txt").read_text(encoding="utf-8")
    assert done.returncode == 0 and "Die App antwortet nicht" not in log, log[-1000:]


def stop(running: dict) -> None:
    request = urllib.request.Request(f"http://127.0.0.1:{running['port']}/api/app/beenden", data=b"{}", method="POST",
                                     headers={"Content-Type": "application/json", "X-Token": running["token"]})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS):  # noqa: S310 (this computer)
        pass


def main(argv: list[str]) -> int:
    image = pathlib.Path(argv[1]).resolve()
    with tempfile.TemporaryDirectory() as folder:
        home = pathlib.Path(folder)
        (home / ".config" / "google-chrome").mkdir(parents=True)  # as if Chrome had run once
        env = environment(home)
        app = subprocess.Popen([str(image), "--kein-browser"], env=env)  # noqa: S603
        try:
            running = wait_for_instance(home / ".config" / "bewerbungsbegleiter")
            for check in (check_menu_entry, check_extension, check_link):
                check(home, image, env)
                print(f"ok: {check.__name__}")
            stop(running)
            app.wait(TIMEOUT_SECONDS)
        except (AssertionError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
            print(f"Fehler: {error}")
            app.kill()
            return 1
    print("Das AppImage läuft.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
