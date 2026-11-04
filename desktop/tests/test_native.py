"""Native Messaging and the developer add-on (MIN-339): protocol, forwarding, registration, extension folder."""
import io
import json
import os
import struct
import subprocess
import sys

import pytest

import extension
import instance
import native_host
import native_messaging
import settings
import start

RUNNING = instance.Running(port=4321, token="geheim")


def framed(*messages) -> io.BytesIO:
    data = b"".join(struct.pack("<I", len(b)) + b for b in (json.dumps(m).encode() for m in messages))
    return io.BytesIO(data)


def replies(stream: io.BytesIO) -> list[dict]:
    data, found = stream.getvalue(), []
    while data:
        size = struct.unpack("<I", data[:4])[0]
        found.append(json.loads(data[4:4 + size]))
        data = data[4 + size:]
    return found


@pytest.fixture
def paths(tmp_path):
    return settings.Paths(tmp_path / "app")


# Protocol


@pytest.mark.parametrize("argv, expected", [
    (["chrome-extension://abc/"], True),
    (["chrome-extension://abc/", "--parent-window=0"], True),
    (["bewerbungsassistent://einladung?code=x"], False),
    ([], False),
])
def test_started_by_the_browser_is_recognised(argv, expected):
    assert native_host.invoked(argv) is expected


def test_message_round_trip():
    out = io.BytesIO()
    native_host.write_message(out, {"id": 1, "text": "Grüsse"})
    out.seek(0)
    assert native_host.read_message(out) == {"id": 1, "text": "Grüsse"}
    assert native_host.read_message(out) is None


def test_oversized_message_is_refused():
    with pytest.raises(ValueError):
        native_host.read_message(io.BytesIO(struct.pack("<I", native_host.MAX_IN + 1)))


def test_oversized_reply_becomes_an_error():
    out = io.BytesIO()
    native_host.write_message(out, {"id": 7, "daten": "x" * native_host.MAX_OUT})
    assert replies(out) == [{"id": 7, "ok": False, "fehler": "Antwort zu gross"}]


class Trickle(io.RawIOBase):
    """A pipe that hands out at most a few bytes per read and accepts a few per write, like a real one under load."""

    def __init__(self, data: bytes = b"", chunk: int = 3) -> None:
        self.data, self.chunk, self.written = data, chunk, b""

    def readable(self) -> bool:
        return True

    def writable(self) -> bool:
        return True

    def read(self, size: int = -1) -> bytes:
        part, self.data = self.data[:min(size, self.chunk)], self.data[min(size, self.chunk):]
        return part

    def write(self, data) -> int:
        self.written += bytes(data[:self.chunk])
        return min(len(data), self.chunk)


def test_large_message_arrives_in_pieces():
    message = {"id": 1, "daten": {"text": "Inserat " * 20000}}
    assert native_host.read_message(Trickle(framed(message).getvalue())) == message


def test_large_reply_is_written_completely():
    out = Trickle()
    native_host.write_message(out, {"id": 1, "daten": "x" * 5000})
    assert replies(io.BytesIO(out.written)) == [{"id": 1, "daten": "x" * 5000}]


# Host


def test_hello_reports_version_and_running_app(paths):
    host = native_host.Host(paths, find=lambda p: RUNNING)
    out = io.BytesIO()
    assert host.serve(framed({"id": 1, "art": "hallo"}), out) == 0
    [reply] = replies(out)
    assert reply["ok"] and reply["daten"]["app"] == RUNNING.url


def test_allowed_request_is_forwarded(paths):
    sent = []
    host = native_host.Host(paths, find=lambda p: RUNNING, send=lambda *a: sent.append(a) or {"neu": 1})
    out = io.BytesIO()
    host.serve(framed({"id": 2, "art": "anfrage", "methode": "POST", "pfad": "/api/suche/treffer",
                       "daten": {"treffer": []}}), out)
    assert replies(out) == [{"id": 2, "ok": True, "daten": {"neu": 1}}]
    assert sent == [(RUNNING, "POST", "/api/suche/treffer", {"treffer": []})]


@pytest.mark.parametrize("method, path", [("GET", "/api/bewerbungen"), ("POST", "/api/app/beenden"),
                                          ("GET", "/api/suche/treffer")])
def test_other_routes_are_refused(paths, method, path):
    host = native_host.Host(paths, find=lambda p: RUNNING, send=lambda *a: pytest.fail("forwarded"))
    out = io.BytesIO()
    host.serve(framed({"id": 3, "art": "anfrage", "methode": method, "pfad": path}), out)
    assert replies(out)[0]["ok"] is False


def test_app_is_started_when_it_does_not_run(paths):
    found = iter([None, None, RUNNING])
    started = []
    host = native_host.Host(paths, find=lambda p: next(found), start=lambda: started.append(True),
                            send=lambda *a: {"plan": {}}, sleep=lambda s: None)
    out = io.BytesIO()
    host.serve(framed({"id": 4, "art": "anfrage", "methode": "GET", "pfad": "/api/suche/plan"}), out)
    assert started == [True]
    assert replies(out)[0]["ok"] is True


def test_second_host_waits_for_the_app_another_host_is_starting(paths):
    paths.app_dir.mkdir(parents=True)
    (paths.app_dir / native_host.START_LOCK).write_text("")
    found = iter([None, None, RUNNING])
    host = native_host.Host(paths, find=lambda p: next(found), start=lambda: pytest.fail("started twice"),
                            send=lambda *a: {"plan": {}}, sleep=lambda s: None)
    out = io.BytesIO()
    host.serve(framed({"id": 4, "art": "anfrage", "methode": "GET", "pfad": "/api/suche/plan"}), out)
    assert replies(out)[0]["ok"] is True


def test_stale_start_lock_does_not_block(paths):
    paths.app_dir.mkdir(parents=True)
    lock = paths.app_dir / native_host.START_LOCK
    lock.write_text("")
    os.utime(lock, (0, 0))
    found = iter([None, RUNNING])
    started = []
    host = native_host.Host(paths, find=lambda p: next(found), start=lambda: started.append(True),
                            send=lambda *a: {}, sleep=lambda s: None)
    host.serve(framed({"id": 4, "art": "anfrage", "methode": "GET", "pfad": "/api/suche/plan"}), io.BytesIO())
    assert started == [True]
    assert not lock.exists()


def test_app_that_does_not_start_gives_a_clear_error(paths):
    host = native_host.Host(paths, find=lambda p: None, start=lambda: None, sleep=lambda s: None, timeout=2)
    out = io.BytesIO()
    host.serve(framed({"id": 5, "art": "anfrage", "methode": "GET", "pfad": "/api/suche/plan"}), out)
    assert replies(out)[0]["fehler"] == native_host.NOT_RUNNING


@pytest.mark.parametrize("message", [
    {"id": 8, "art": "anfrage", "methode": ["GET"], "pfad": "/api/suche/plan"},
    {"id": 8, "art": "anfrage", "methode": "GET", "pfad": "/api/suche/plan", "daten": ["kein", "objekt"]},
])
def test_malformed_request_gets_an_error_reply(paths, message):
    host = native_host.Host(paths, find=lambda p: RUNNING, send=native_host.call)
    out = io.BytesIO()
    assert host.serve(framed(message), out) == 0
    assert replies(out)[0]["ok"] is False


def test_unexpected_failure_still_answers(paths):
    def broken(*args):
        raise RuntimeError("kaputt")
    host = native_host.Host(paths, find=lambda p: RUNNING, send=broken)
    out = io.BytesIO()
    host.serve(framed({"id": 9, "art": "anfrage", "methode": "GET", "pfad": "/api/suche/plan"}), out)
    assert replies(out)[0] == {"id": 9, "ok": False, "fehler": native_host.UNEXPECTED}


def test_error_of_the_app_reaches_the_extension(paths):
    def refuse(*args):
        raise ValueError("Es gibt noch kein Suchprofil.")
    host = native_host.Host(paths, find=lambda p: RUNNING, send=refuse)
    out = io.BytesIO()
    host.serve(framed({"id": 6, "art": "anfrage", "methode": "GET", "pfad": "/api/suche/plan"}), out)
    assert replies(out)[0] == {"id": 6, "ok": False, "fehler": "Es gibt noch kein Suchprofil."}


def test_launch_detaches_without_inheriting_the_pipes(monkeypatch):
    calls = []
    monkeypatch.setattr(subprocess, "Popen", lambda command, **options: calls.append((command, options)))
    native_host.launch(["app", "--kein-browser"], platform="darwin")
    command, options = calls[0]
    assert options["start_new_session"] is True
    assert options["stdin"] == options["stdout"] == subprocess.DEVNULL


def test_main_runs_the_host_when_the_browser_starts_the_app(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "app_dir", lambda: tmp_path / "app")
    monkeypatch.setattr(native_host, "main", lambda paths: 42)
    assert start.main(["chrome-extension://ghniboofenadplgmdgddmgjaaeeogejn/"]) == 42


def test_real_forwarding_to_a_running_app(tmp_path):
    """call() against a tiny local server, as the host talks to the app."""
    import http.server
    import threading

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            ok = self.headers["X-Token"] == "geheim"
            self.send_response(200 if ok else 403)
            self.end_headers()
            self.wfile.write(json.dumps({"echo": json.loads(body)} if ok else {"fehler": "Ungültiges Token"}).encode())

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        running = instance.Running(server.server_address[1], "geheim")
        assert native_host.call(running, "POST", "/api/suche/treffer", {"a": 1}) == {"echo": {"a": 1}}
        with pytest.raises(ValueError, match="Ungültiges Token"):
            native_host.call(instance.Running(server.server_address[1], "falsch"), "POST", "/x", {})
    finally:
        server.shutdown()


# Registration


def test_manifest_allows_only_our_extension(tmp_path):
    data = native_messaging.manifest(tmp_path / "app")
    assert data["name"] == native_messaging.HOST_NAME
    assert data["allowed_origins"] == ["chrome-extension://ghniboofenadplgmdgddmgjaaeeogejn/"]
    assert data["type"] == "stdio"


def test_extension_key_gives_the_registered_id():
    """The ID follows from the public key in the manifest; both must stay in step."""
    import base64
    import hashlib
    manifest = json.loads((extension.source(start.bundle_dir(), frozen=False) / "manifest.json").read_text("utf-8"))
    digest = hashlib.sha256(base64.b64decode(manifest["key"])).hexdigest()[:32]
    assert "".join(chr(ord("a") + int(c, 16)) for c in digest) in native_messaging.EXTENSION_IDS


def test_macos_registers_for_installed_browsers_only(paths, tmp_path):
    home = tmp_path / "home"
    (home / "Library" / "Application Support" / "Google" / "Chrome").mkdir(parents=True)
    where = native_messaging.register(paths, tmp_path / "Bewerbungsassistent", platform="darwin", home=home)
    target = home / "Library" / "Application Support" / "Google" / "Chrome" / "NativeMessagingHosts" / "bewerbungsassistent.json"
    assert where == [str(target.parent)]
    assert json.loads(target.read_text(encoding="utf-8"))["path"] == str(tmp_path / "Bewerbungsassistent")


def test_one_unwritable_browser_folder_does_not_stop_the_others(paths, tmp_path):
    home = tmp_path / "home"
    support = home / "Library" / "Application Support"
    (support / "Google" / "Chrome").mkdir(parents=True)
    (support / "Microsoft Edge").mkdir(parents=True)
    (support / "Google" / "Chrome" / "NativeMessagingHosts").write_text("eine Datei statt eines Ordners")
    where = native_messaging.register(paths, tmp_path / "Bewerbungsassistent", platform="darwin", home=home)
    assert where == [str(support / "Microsoft Edge" / "NativeMessagingHosts")]


def test_windows_registers_in_the_registry(paths, tmp_path):
    keys = {}
    native_messaging.register(paths, tmp_path / "app.exe", platform="win32", set_registry=keys.__setitem__)
    manifest_file = paths.app_dir / native_messaging.WINDOWS_MANIFEST
    assert set(keys) == set(native_messaging.WINDOWS_KEYS)
    assert set(keys.values()) == {str(manifest_file)}
    assert manifest_file.is_file()


def test_launcher_from_source_sets_the_module_path(paths, tmp_path):
    source = tmp_path / "repo" / "desktop"
    script = native_messaging.launcher(paths, "darwin", source, tmp_path / "python")
    text = script.read_text(encoding="utf-8")
    assert "PYTHONPATH=" in text and str(tmp_path / "repo" / "onboarding") in text
    assert str(source / "start.py") in text
    assert script.stat().st_mode & 0o100
    bat = native_messaging.launcher(paths, "win32", source, tmp_path / "python.exe")
    assert bat.suffix == ".bat" and "%*" in bat.read_text(encoding="utf-8")


# Extension folder


def test_frozen_app_copies_the_extension_and_keeps_it_while_the_version_is_the_same(paths, tmp_path):
    origin = tmp_path / "bundle" / "erweiterung"
    origin.mkdir(parents=True)
    (origin / "manifest.json").write_text('{"version": "0.1.0"}', encoding="utf-8")
    target = extension.install(paths, origin, frozen=True)
    assert target == paths.app_dir / "erweiterung" and extension.version(target) == "0.1.0"
    (target / "eigene.txt").write_text("x", encoding="utf-8")
    extension.install(paths, origin, frozen=True)
    assert (target / "eigene.txt").exists()
    (origin / "manifest.json").write_text('{"version": "0.2.0"}', encoding="utf-8")
    extension.install(paths, origin, frozen=True)
    assert extension.version(target) == "0.2.0" and not (target / "eigene.txt").exists()


def test_from_source_the_repo_folder_is_used(paths, tmp_path):
    origin = tmp_path / "erweiterung"
    assert extension.install(paths, origin, frozen=False) == origin


def test_extension_in_the_repo_has_a_version():
    assert extension.version(extension.source(start.bundle_dir(), frozen=False))


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX streams")
def test_streams_are_binary():
    incoming, outgoing = native_host.streams()
    assert "b" in incoming.mode and "b" in outgoing.mode


# Setup page: extension step


def setup_routes(paths, tmp_path, shown):
    import routes_setup
    folder = tmp_path / "erweiterung"
    folder.mkdir(exist_ok=True)
    (folder / "manifest.json").write_text('{"version": "0.1.0"}', encoding="utf-8")
    state = routes_setup.Setup(paths=paths, switch=lambda folder: None, suggestion=tmp_path / "Dokumente",
                               extension_dir=folder, reveal=shown.append)
    return folder, routes_setup.make_routes(state)


def test_setup_overview_names_the_extension_folder(paths, tmp_path):
    import types
    folder, (get_routes, _) = setup_routes(paths, tmp_path, [])
    answer = get_routes["/api/app/einrichtung"](types.SimpleNamespace(daten=tmp_path), {}, None)
    assert json.loads(answer.inhalt)["erweiterung"] == {"ordner": str(folder), "version": "0.1.0"}


def test_extension_folder_can_be_shown(paths, tmp_path):
    shown = []
    folder, (_, post_routes) = setup_routes(paths, tmp_path, shown)
    post_routes["/api/app/ordner-zeigen"](None, {}, {"art": "erweiterung"})
    assert shown == [folder]
    with pytest.raises(ValueError):
        post_routes["/api/app/ordner-zeigen"](None, {}, {"art": "/etc"})


def test_reveal_opens_finder_or_explorer(tmp_path):
    import dialogs
    calls = []
    dialogs.reveal(tmp_path, "darwin", run=lambda command, **options: calls.append(command))
    dialogs.reveal(tmp_path, "win32", run=lambda command, **options: calls.append(command))
    assert calls == [["open", str(tmp_path)], ["explorer", str(tmp_path)]]
    with pytest.raises(ValueError):
        dialogs.reveal(tmp_path / "fehlt", "darwin")


def test_the_extension_reaches_the_routes_for_the_open_page():
    assert ("POST", "/api/seite/pruefen") in native_host.ALLOWED and ("POST", "/api/seite/speichern") in native_host.ALLOWED


def test_the_extension_reaches_the_routes_for_applying_but_not_the_choice():
    for route in (("POST", "/api/bewerben/start"), ("GET", "/api/bewerben/daten"), ("GET", "/api/bewerben/datei"),
                  ("POST", "/api/bewerben/stand"), ("POST", "/api/bewerben/felder"), ("POST", "/api/bewerben/abgeschickt")):
        assert route in native_host.ALLOWED
    assert ("GET", "/api/bewerbungen") not in native_host.ALLOWED


def test_extension_reaches_what_it_needs_for_the_rav_and_not_the_rest():
    for route in (("POST", "/api/rav/start"), ("GET", "/api/rav/angaben"), ("POST", "/api/rav/eingetragen")):
        assert route in native_host.ALLOWED
    assert ("GET", "/api/rav/auswahl") not in native_host.ALLOWED
    assert ("POST", "/api/rav/zuruecksetzen") not in native_host.ALLOWED
