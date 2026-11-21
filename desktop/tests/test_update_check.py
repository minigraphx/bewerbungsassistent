"""The button «Nach Updates suchen» under «Über die App» (#370, G100): the person asks the update server at once.

It reuses the signed announcements of the automatic check; announcements here are invented and signed with the test
key of signed_update, so no test reaches the real update server.
"""
import json
import threading
from http import HTTPStatus

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import routes_app
import settings
import updates
from server import StatusError
from signed_update import BASE, PACKAGE_NAMES, announcement, envelope

ROUTE = "/api/app/updates-suchen"
INSTALLER = b"MZ" + b"x" * 500
APPIMAGE = b"\x7fELF" + b"x" * 500


class Server:
    """A fake update server whose announcements can change while the app runs; it counts what the app asked."""

    def __init__(self, stable: str | None = routes_app.VERSION, beta: str | None = None):
        self.files: dict[str, bytes] = {}
        self.asked: list[str] = []
        self.publish("latest.json", stable)
        self.publish("beta.json", beta)

    def publish(self, name: str, version: str | None, packages: dict[str, bytes] | None = None) -> None:
        self.files.pop(f"{BASE}/{name}", None)
        if not version:
            return
        packages = {"win32": INSTALLER, "linux": APPIMAGE} if packages is None else packages
        self.files[f"{BASE}/{name}"] = envelope(announcement(version, packages))
        for platform, data in packages.items():
            self.files[f"{BASE}/{version}/{PACKAGE_NAMES[platform].format(version)}"] = data

    def fetch(self, url: str, limit: int) -> bytes:
        self.asked.append(url)
        if url not in self.files:
            raise OSError("not found")
        return self.files[url]


def routes(tmp_path, server: Server, platform: str = "win32", store: bool = False, installed: list | None = None):
    controls = routes_app.Controls(stop=threading.Event().set, automatic=platform in routes_app.SELF_UPDATING,
                                   platform=platform, fetch=server.fetch, store=store,
                                   run_installer=(installed if installed is not None else []).append,
                                   paths=settings.Paths(tmp_path))
    return routes_app.make_routes(controls)


def body(answer) -> dict:
    return json.loads(answer.inhalt)


def check(post) -> dict:
    return body(post[ROUTE](None, {}, {}))


def test_up_to_date_names_the_running_version(tmp_path):
    _, post = routes(tmp_path, Server())

    assert check(post) == {"version": routes_app.VERSION, "update": None, "vorabversionen": False}


def test_the_check_asks_the_server_again_at_once_and_offers_what_it_found(tmp_path):
    server = Server()
    get, post = routes(tmp_path, server)
    assert body(get["/api/app/version"](None, {}, None))["update"] is None
    server.publish("latest.json", "99.0.0")
    assert body(get["/api/app/version"](None, {}, None))["update"] is None  # the automatic check waits six hours

    found = check(post)

    assert found["update"] == body(get["/api/app/version"](None, {}, None))["update"]
    assert found["update"]["version"] == "99.0.0"
    assert found["update"]["automatisch"] is True and found["update"]["seite"] == updates.RELEASES_PAGE


def test_a_found_version_can_be_installed_right_after(tmp_path):
    server, installed = Server(), []
    get, post = routes(tmp_path, server, installed=installed)
    get["/api/app/version"](None, {}, None)
    server.publish("latest.json", "99.0.0")
    check(post)

    assert body(post["/api/app/aktualisieren"](None, {}, {})) == {"ok": True, "version": "99.0.0"}
    assert len(installed) == 1


def test_with_pre_releases_on_the_check_includes_them_and_says_so(tmp_path):
    _, post = routes(tmp_path, Server(beta="99.1.0"))
    settings.set_beta_updates(settings.Paths(tmp_path), True)

    found = check(post)

    assert found["vorabversionen"] is True
    assert found["update"]["version"] == "99.1.0"


def test_without_pre_releases_the_beta_announcement_is_not_asked(tmp_path):
    server = Server(beta="99.1.0")
    _, post = routes(tmp_path, server)

    assert check(post)["update"] is None
    assert f"{BASE}/beta.json" not in server.asked


def test_a_missing_beta_announcement_is_no_failure(tmp_path):
    _, post = routes(tmp_path, Server(stable="99.0.0", beta=None))
    settings.set_beta_updates(settings.Paths(tmp_path), True)

    assert check(post)["update"]["version"] == "99.0.0"


def test_under_linux_the_new_version_is_offered_as_a_download(tmp_path):
    _, post = routes(tmp_path, Server(stable="99.0.0"), platform="linux")

    offered = check(post)["update"]

    assert offered["automatisch"] is False
    assert offered["seite"] == f"{BASE}/99.0.0/{PACKAGE_NAMES['linux'].format('99.0.0')}"


def failure(post) -> StatusError:
    with pytest.raises(StatusError) as raised:
        post[ROUTE](None, {}, {})
    return raised.value


def test_an_unreachable_server_is_a_failed_check(tmp_path):
    server = Server()
    server.files.clear()
    _, post = routes(tmp_path, server)

    error = failure(post)

    assert error.status == HTTPStatus.BAD_GATEWAY
    assert str(error) == routes_app.CHECK_FAILED


def test_a_check_that_runs_out_of_time_failed(tmp_path):
    server = Server()

    def too_slow(url: str, limit: int) -> bytes:
        raise TimeoutError("no answer within 20 s")
    server.fetch = too_slow
    _, post = routes(tmp_path, server)

    assert failure(post).status == HTTPStatus.BAD_GATEWAY


def test_a_wrong_signature_is_a_failed_check_and_offers_nothing(tmp_path):
    server = Server()
    server.files[f"{BASE}/latest.json"] = envelope(announcement("99.0.0", {"win32": INSTALLER}),
                                                  Ed25519PrivateKey.generate())
    get, post = routes(tmp_path, server)

    failure(post)

    assert body(get["/api/app/version"](None, {}, None))["update"] is None


def test_without_an_update_address_the_check_failed(tmp_path, monkeypatch):
    monkeypatch.delenv(updates.URL_VARIABLE)
    _, post = routes(tmp_path, Server(stable="99.0.0"))

    failure(post)


def test_the_automatic_check_still_says_nothing_when_the_server_is_away(tmp_path):
    server = Server()
    server.files.clear()
    get, _ = routes(tmp_path, server)

    assert body(get["/api/app/version"](None, {}, None))["update"] is None


def test_in_the_store_package_the_check_is_not_there(tmp_path):
    server = Server(stable="99.0.0")
    _, post = routes(tmp_path, server, store=True)

    answer = post[ROUTE](None, {}, {})

    assert answer.status == HTTPStatus.NOT_FOUND
    assert body(answer) == {"fehler": routes_app.BY_THE_STORE}
    assert server.asked == []
