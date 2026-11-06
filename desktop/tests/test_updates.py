"""Updates from the update server: signed announcement, verified package, silent install (MIN-342, MIN-403)."""
import base64
import json
import shutil
import subprocess
import threading

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

import routes_app
import signed_update
import updates
from signed_update import BASE, announcement, envelope, server

INSTALLER = b"MZ" + b"x" * 5000
INSTALLER_NAME = "Bewerbungsbegleiter-Setup-9.2.0.exe"


def release(version="9.2.0", installer=INSTALLER):
    return server(version, {"win32": installer})


@pytest.mark.parametrize("text, expected", [("v1.2.3", (1, 2, 3)), ("0.10.0", (0, 10, 0)), ("kaputt", (0, 0, 0))])
def test_versions(text, expected):
    assert updates.parse_version(text) == expected


def test_newer_release_is_found_and_older_ignored():
    found = updates.latest(release(), "win32")

    assert updates.newer("0.1.0", found).version == "9.2.0"
    assert updates.newer("9.2.0", found) is None and updates.newer("9.10.0", found) is None


def test_offline_is_no_update():
    assert updates.latest(lambda url, limit: (_ for _ in ()).throw(OSError("offline"))) is None


def test_without_an_address_nothing_is_asked(monkeypatch):
    monkeypatch.delenv(updates.URL_VARIABLE)

    assert updates.latest(lambda url, limit: pytest.fail("must not ask anyone"), "win32") is None


def test_only_https_is_asked(monkeypatch):
    monkeypatch.setenv(updates.URL_VARIABLE, "http://updates.example.ch")

    assert updates.latest(lambda url, limit: pytest.fail("must not ask over http"), "win32") is None


def test_the_address_may_end_with_a_slash(monkeypatch):
    monkeypatch.setenv(updates.URL_VARIABLE, BASE + "/")

    assert updates.latest(release(), "win32").version == "9.2.0"


def test_a_wrong_signature_is_no_update():
    other_key = Ed25519PrivateKey.generate()
    forged = envelope(announcement("9.2.0", {"win32": INSTALLER}), other_key)

    assert updates.latest(server(raw=forged), "win32") is None


def test_a_changed_announcement_is_no_update():
    good = json.loads(envelope(announcement("9.2.0", {"win32": INSTALLER})))
    changed = announcement("9.3.0", {"win32": INSTALLER})

    forged = json.dumps({"payload": base64.b64encode(changed).decode(), "signature": good["signature"]}).encode()

    assert updates.latest(server(raw=forged), "win32") is None


@pytest.mark.parametrize("raw", [b"", b"<html>Wartung</html>", b"[]", b'{"payload": "x"}',
                                 b'{"payload": "$$$", "signature": "$$$"}', b"\xff\xfe"])
def test_a_broken_announcement_is_no_update(raw):
    assert updates.latest(server(raw=raw), "win32") is None


def test_an_endlessly_nested_announcement_is_no_update():
    assert updates.latest(server(raw=b"[" * 200_000), "win32") is None


def test_a_too_large_announcement_is_no_update():
    def too_large(url, limit):
        raise updates.UpdateError("Die Datei ist grösser als erwartet; Update abgebrochen.")

    assert updates.latest(too_large, "win32") is None


def test_a_server_that_only_drips_cannot_hold_the_app(monkeypatch):
    """The timeout of a socket only limits each read, so the whole request needs a deadline of its own."""
    release_it = threading.Event()
    monkeypatch.setattr(updates, "_read_url", lambda url, limit, timeout: release_it.wait(30))
    monkeypatch.setattr(updates, "ANNOUNCEMENT_DEADLINE_SECONDS", 0.05)

    try:
        assert updates.latest(updates._fetch, "win32") is None
    finally:
        release_it.set()


def test_a_download_has_a_deadline_too(monkeypatch, tmp_path):
    release_it = threading.Event()
    monkeypatch.setattr(updates, "_read_url", lambda url, limit, timeout: release_it.wait(30))
    monkeypatch.setattr(updates, "DOWNLOAD_DEADLINE_SECONDS", 0.05)
    found = updates.latest(release(), "win32")

    try:
        with pytest.raises(updates.UpdateError, match="nicht laden"):
            updates.download(found, tmp_path)
    finally:
        release_it.set()


def test_errors_of_the_request_reach_the_caller(monkeypatch):
    def refused(url, limit, timeout):
        raise OSError("refused")
    monkeypatch.setattr(updates, "_read_url", refused)

    with pytest.raises(OSError, match="refused"):
        updates._fetch(f"{BASE}/latest.json", 100)


def test_a_failed_check_is_not_repeated_on_every_page():
    calls = []

    def offline(url, limit):
        calls.append(url)
        raise OSError("offline")
    controls = routes_app.Controls(stop=lambda: None, automatic=True, platform="win32", fetch=offline)

    assert controls.update() is None and controls.update() is None
    assert len(calls) == 1


def test_without_a_key_in_the_app_nothing_is_trusted(monkeypatch):
    monkeypatch.setattr(updates.update_key, "PUBLIC_KEY", "")

    assert updates.latest(release(), "win32") is None


@pytest.mark.parametrize("payload", [b"[]", b"{}", b'{"version": "kaputt", "packages": {}}', b"nicht json"])
def test_a_signed_but_meaningless_announcement_is_no_update(payload):
    assert updates.latest(server(raw=envelope(payload)), "win32") is None


@pytest.mark.parametrize("entry", [
    {"file": "../../evil.exe", "sha256": "a" * 64},
    {"file": "Bewerbungsbegleiter-Setup-1.0.0.exe", "sha256": "a" * 64},
    {"file": "Bewerbungsbegleiter-Setup-9.2.0.exe", "sha256": "kurz"},
    {"file": "Bewerbungsbegleiter-Setup-9.2.0.exe"},
    "nicht-einmal-ein-objekt",
])
def test_packages_must_look_right_even_when_signed(entry):
    payload = json.dumps({"version": "9.2.0", "packages": {"win32": entry}}).encode()

    found = updates.latest(server(raw=envelope(payload)), "win32")

    assert found.installer_url is None and found.sha256 is None


def test_the_package_address_is_built_from_our_address_only():
    found = updates.latest(release(), "win32")

    assert found.installer_url == f"{BASE}/9.2.0/{INSTALLER_NAME}"


def test_the_shipped_public_key_is_a_real_key():
    assert Ed25519PublicKey.from_public_bytes(base64.b64decode(signed_update.SHIPPED_KEY, validate=True))


def test_a_signature_made_with_openssl_is_accepted(tmp_path, monkeypatch):
    """The commands of update-ausrollen.yml, so the workflow and the app cannot drift apart."""
    openssl = shutil.which("openssl")
    key, payload, signature = tmp_path / "key.pem", tmp_path / "payload.json", tmp_path / "payload.sig"
    if not openssl or subprocess.run([openssl, "genpkey", "-algorithm", "ed25519", "-out", key], capture_output=True).returncode:
        pytest.skip("needs an openssl with ed25519")
    payload.write_bytes(announcement("9.2.0", {"win32": INSTALLER}))
    signed = subprocess.run([openssl, "pkeyutl", "-sign", "-inkey", key, "-rawin", "-in", payload, "-out", signature], capture_output=True)
    if signed.returncode:
        pytest.skip("needs an openssl with -rawin")
    der = subprocess.run([openssl, "pkey", "-in", key, "-pubout", "-outform", "DER"], capture_output=True, check=True).stdout
    monkeypatch.setattr(updates.update_key, "PUBLIC_KEY", base64.b64encode(der[-32:]).decode())
    raw = json.dumps({"payload": base64.b64encode(payload.read_bytes()).decode(),
                      "signature": base64.b64encode(signature.read_bytes()).decode()}).encode()

    assert updates.latest(server(raw=raw), "win32").version == "9.2.0"


def test_download_verifies_the_checksum(tmp_path):
    path = updates.download(updates.latest(release(), "win32"), tmp_path, release())

    assert path.read_bytes() == INSTALLER and path.name == INSTALLER_NAME


def test_tampered_installer_is_refused(tmp_path):
    good = release()
    found = updates.latest(good, "win32")

    def tampered(url, limit):
        return b"MZ evil" if url.endswith(".exe") else good(url, limit)

    with pytest.raises(updates.UpdateError, match="Prüfsumme"):
        updates.download(found, tmp_path, tampered)
    assert not any(tmp_path.iterdir())


def test_a_package_missing_from_the_announcement_is_refused(tmp_path):
    found = updates.latest(server(raw=envelope(json.dumps({"version": "9.2.0", "packages": {}}).encode())), "win32")

    with pytest.raises(updates.UpdateError, match="keinen Installer"):
        updates.download(found, tmp_path, release())


def test_a_package_not_on_the_server_yet_is_a_load_error(tmp_path):
    found = updates.latest(release(), "win32")

    def missing(url, limit):
        raise OSError("not found")

    with pytest.raises(updates.UpdateError, match="nicht laden"):
        updates.download(found, tmp_path, missing)
    assert not any(tmp_path.iterdir())


def test_installer_runs_silently(tmp_path):
    calls = []

    updates.run_installer(tmp_path / "setup.exe", popen=lambda args, **kw: calls.append(args))

    assert calls[0][1:] == ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"]


def routes(automatic=True, fetch=None):
    stopped, installed = threading.Event(), []
    controls = routes_app.Controls(stop=stopped.set, automatic=automatic, platform="win32", fetch=fetch or release(),
                                   run_installer=installed.append)
    get, post = routes_app.make_routes(controls)
    return get, post, stopped, installed


def body(answer):
    return json.loads(answer.inhalt)


def test_version_route_tells_about_the_update():
    get, _, _, _ = routes()

    data = body(get["/api/app/version"](None, {}, None))

    assert data["version"] == routes_app.VERSION and data["update"]["version"] == "9.2.0"
    assert data["update"]["automatisch"] is True


def test_update_route_installs_and_quits():
    _, post, stopped, installed = routes()

    data = body(post["/api/app/aktualisieren"](None, {}, {}))

    assert data["ok"] and installed[0].name == INSTALLER_NAME
    assert stopped.wait(3)


def test_without_automatic_update_the_page_is_named():
    _, post, _, installed = routes(automatic=False)

    with pytest.raises(ValueError, match="https://github.com"):
        post["/api/app/aktualisieren"](None, {}, {})
    assert installed == []


def test_quit():
    _, post, stopped, _ = routes()

    post["/api/app/beenden"](None, {}, {})

    assert stopped.wait(3)


def quitting(fetch=None, automatic=True, installer=None):
    stopped, installed = threading.Event(), []

    def finish_now(work):
        work()

    def install(path):
        if installer:
            installer(path)
        installed.append(path)

    controls = routes_app.Controls(stop=stopped.set, automatic=automatic, platform="win32", fetch=fetch or release(),
                                   run_installer_after_quit=install, background=finish_now)
    return routes_app.make_routes(controls)[1], stopped, installed, controls


def test_quit_installs_a_waiting_update_and_still_stops():
    post, stopped, installed, _ = quitting()

    data = body(post["/api/app/beenden"](None, {}, {}))

    assert data == {"ok": True, "aktualisiert": "9.2.0"}
    assert installed[0].name == INSTALLER_NAME
    assert stopped.wait(3)


def test_quit_without_an_update_only_stops():
    post, stopped, installed, _ = quitting(fetch=release(version="0.0.1"))

    assert body(post["/api/app/beenden"](None, {}, {})) == {"ok": True}
    assert installed == [] and stopped.wait(3)


def test_quit_does_not_install_where_the_app_cannot_update_itself():
    post, stopped, installed, _ = quitting(automatic=False)

    assert body(post["/api/app/beenden"](None, {}, {})) == {"ok": True}
    assert installed == [] and stopped.wait(3)


def test_quit_stops_even_when_the_download_fails():
    good = release()

    def broken(url, limit):
        if url.endswith(".exe"):
            raise OSError("offline")
        return good(url, limit)

    post, stopped, installed, _ = quitting(fetch=broken)

    assert body(post["/api/app/beenden"](None, {}, {}))["aktualisiert"] == "9.2.0"
    assert installed == [] and stopped.wait(3)


def test_quit_stops_even_when_the_installer_cannot_start():
    def cannot_start(path):
        raise OSError("blocked")

    post, stopped, installed, _ = quitting(installer=cannot_start)

    post["/api/app/beenden"](None, {}, {})

    assert installed == [] and stopped.wait(3)


def test_quit_stops_even_when_the_check_for_updates_breaks():
    def broken(url, limit):
        raise RuntimeError("unexpected")

    post, stopped, installed, _ = quitting(fetch=broken)

    assert body(post["/api/app/beenden"](None, {}, {})) == {"ok": True}
    assert installed == [] and stopped.wait(3)


def test_quit_while_an_update_runs_starts_no_second_one():
    post, stopped, installed, controls = quitting()
    controls.installing.acquire()

    assert body(post["/api/app/beenden"](None, {}, {})) == {"ok": True}
    assert installed == [] and stopped.wait(3)


def test_quit_works_in_the_real_background_thread():
    stopped, installed = threading.Event(), []
    controls = routes_app.Controls(stop=stopped.set, automatic=True, platform="win32", fetch=release(),
                                   run_installer_after_quit=installed.append)

    routes_app.make_routes(controls)[1]["/api/app/beenden"](None, {}, {})

    assert stopped.wait(5) and installed


def test_installer_after_quit_does_not_start_the_app_again(tmp_path):
    calls = []

    updates.run_installer_after_quit(tmp_path / "setup.exe", popen=lambda args, **kw: calls.append(args))

    assert calls[0][1:] == ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/NOSTART"]


def test_version_route_says_the_update_comes_with_quitting():
    get, _, _, _ = routes()

    assert body(get["/api/app/version"](None, {}, None))["update"]["beimBeenden"] is True


def test_version_route_promises_nothing_without_automatic_update():
    get, _, _, _ = routes(automatic=False)

    assert body(get["/api/app/version"](None, {}, None))["update"]["beimBeenden"] is False


def test_https_uses_the_certificates_of_the_system(monkeypatch):
    """The packed app has no CA file of its own (macOS build): the system's trust store must verify."""
    import io

    import truststore

    seen = {}

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def urlopen(request, timeout, context=None):
        seen["context"] = context
        return Response(b"{}")
    monkeypatch.setattr(updates.urllib.request, "urlopen", urlopen)

    updates._fetch(f"{BASE}/latest.json", 100)

    assert isinstance(seen["context"], truststore.SSLContext)
