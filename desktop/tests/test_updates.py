"""Updates from GitHub Releases: find a newer version, verify the installer, run it (MIN-342)."""
import hashlib
import json
import threading

import pytest

import routes_app
import updates

INSTALLER = b"MZ" + b"x" * 5000
BASE = updates.DOWNLOAD_PREFIX + "v9.2.0/"


def release(version="9.2.0", installer=INSTALLER, prefix=BASE, **extra):
    sums = f"{hashlib.sha256(installer).hexdigest()}  Bewerbungsbegleiter-Setup-{version}.exe\n".encode()
    files = {
        updates.LATEST_URL: json.dumps({"tag_name": f"v{version}", "html_url": "https://github.com/x/releases/v",
                                        "body": "Neu: Updates", **extra, "assets": [
            {"name": f"Bewerbungsbegleiter-Setup-{version}.exe", "browser_download_url": prefix + f"Bewerbungsbegleiter-Setup-{version}.exe"},
            {"name": "SHA256SUMS.txt", "browser_download_url": prefix + "SHA256SUMS.txt"}]}).encode(),
        prefix + f"Bewerbungsbegleiter-Setup-{version}.exe": installer,
        prefix + "SHA256SUMS.txt": sums,
    }

    def fetch(url, limit):
        if url not in files:
            raise OSError("not found")
        return files[url]
    return fetch


@pytest.mark.parametrize("text, expected", [("v1.2.3", (1, 2, 3)), ("0.10.0", (0, 10, 0)), ("kaputt", (0, 0, 0))])
def test_versions(text, expected):
    assert updates.parse_version(text) == expected


def test_newer_release_is_found_and_older_ignored():
    found = updates.latest(release(), "win32")

    assert updates.newer("0.1.0", found).version == "9.2.0"
    assert updates.newer("9.2.0", found) is None and updates.newer("9.10.0", found) is None


def test_drafts_prereleases_and_offline_are_no_update():
    assert updates.latest(release(prerelease=True), "win32") is None
    assert updates.latest(lambda url, limit: (_ for _ in ()).throw(OSError("offline"))) is None


def test_download_verifies_the_checksum(tmp_path):
    path = updates.download(updates.latest(release(), "win32"), tmp_path, release())

    assert path.read_bytes() == INSTALLER and path.name == "Bewerbungsbegleiter-Setup-9.2.0.exe"


def test_tampered_installer_is_refused(tmp_path):
    good = release()
    found = updates.latest(good, "win32")

    def tampered(url, limit):
        return b"MZ evil" if url.endswith(".exe") else good(url, limit)

    with pytest.raises(updates.UpdateError, match="Prüfsumme"):
        updates.download(found, tmp_path, tampered)
    assert not any(tmp_path.iterdir())


def test_downloads_only_from_our_releases(tmp_path):
    found = updates.latest(release(prefix="https://evil.example/"), "win32")

    assert found.installer_url is None
    with pytest.raises(updates.UpdateError, match="keinen Installer"):
        updates.download(found, tmp_path, release())


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

    assert data["ok"] and installed[0].name == "Bewerbungsbegleiter-Setup-9.2.0.exe"
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
    assert installed[0].name == "Bewerbungsbegleiter-Setup-9.2.0.exe"
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

    updates._fetch(updates.LATEST_URL, 100)

    assert isinstance(seen["context"], truststore.SSLContext)
