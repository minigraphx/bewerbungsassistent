"""The app inside the Store package (#344, G6): the alias for the browsers, the link from the package, updates by the Store."""
import json
import pathlib
import sys
import threading
from http import HTTPStatus

import pytest

import msix_package
import native_messaging
import routes_app
import settings
import start
import updates
from signed_update import server

STORE_NOTE = "Updates kommen über den Microsoft Store."
LOCAL = r"C:\Users\Muster\AppData\Local"
ALIAS = rf"{LOCAL}\Microsoft\WindowsApps\bewerbungsbegleiter.exe"


def never(*args, **kwargs):
    pytest.fail("must not be called")


def body(answer) -> dict:
    return json.loads(answer.inhalt)


# Detection


def test_outside_windows_there_is_no_package_and_nothing_is_asked():
    assert msix_package.running_packaged("darwin", status=never) is False
    assert msix_package.running_packaged("linux", status=never) is False


def test_windows_without_a_package_identity_is_not_packaged():
    assert msix_package.running_packaged("win32", status=lambda: msix_package.APPMODEL_ERROR_NO_PACKAGE) is False


@pytest.mark.parametrize("code", [0, msix_package.ERROR_INSUFFICIENT_BUFFER])
def test_windows_with_a_package_identity_is_packaged(code):
    assert msix_package.running_packaged("win32", status=lambda: code) is True


@pytest.mark.parametrize("problem", [OSError("no kernel32"), AttributeError("no such function")])
def test_a_failed_question_counts_as_no_package(problem):
    def failing():
        raise problem

    assert msix_package.running_packaged("win32", status=failing) is False


def test_the_alias_lives_in_the_windows_apps_folder_of_the_person():
    assert str(msix_package.alias_path({"LOCALAPPDATA": LOCAL})) == ALIAS


# Native messaging host and link


@pytest.fixture
def packed_windows(monkeypatch):
    monkeypatch.setattr(start.sys, "frozen", True, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", LOCAL)
    monkeypatch.delenv("APPIMAGE", raising=False)


def test_in_the_package_the_host_manifest_points_to_the_alias(monkeypatch, tmp_path, packed_windows):
    monkeypatch.setattr(start.msix_package, "running_packaged", lambda: True)
    paths = settings.Paths(tmp_path / "app")

    native_messaging.register(paths, start._host_executable(paths), platform="win32", set_registry=lambda key, value: None)

    written = json.loads((paths.app_dir / native_messaging.WINDOWS_MANIFEST).read_text(encoding="utf-8"))
    assert written["path"] == ALIAS


def test_outside_the_package_the_host_is_the_program_itself(monkeypatch, tmp_path, packed_windows):
    monkeypatch.setattr(start.msix_package, "running_packaged", lambda: False)

    assert start._host_executable(settings.Paths(tmp_path / "app")) == pathlib.Path(sys.executable)


def test_in_the_package_the_app_writes_no_key_for_its_link(monkeypatch, packed_windows):
    monkeypatch.setattr(start.msix_package, "running_packaged", lambda: True)
    monkeypatch.setattr(start.urlscheme, "register_windows", never)

    start.register_link("win32")


def test_outside_the_package_the_app_registers_its_link(monkeypatch, packed_windows):
    registered = []
    monkeypatch.setattr(start.msix_package, "running_packaged", lambda: False)
    monkeypatch.setattr(start.urlscheme, "register_windows", registered.append)

    start.register_link("win32")

    assert registered == [sys.executable]


# Updates


def store_routes(tmp_path, store=True):
    stopped, installed = threading.Event(), []
    controls = routes_app.Controls(stop=stopped.set, automatic=True, platform="win32", store=store,
                                   fetch=server("9.2.0", {"win32": b"MZ" + b"x" * 100}), run_installer=installed.append,
                                   run_installer_after_quit=installed.append, paths=settings.Paths(tmp_path))
    get, post = routes_app.make_routes(controls)
    return get, post, installed


@pytest.fixture
def no_update_check(monkeypatch):
    monkeypatch.setattr(updates, "latest", never)


def test_in_the_package_the_version_offers_no_update_and_says_store(tmp_path, no_update_check):
    get, _, _ = store_routes(tmp_path)

    assert body(get["/api/app/version"](None, {}, None)) == {"version": routes_app.VERSION, "update": None, "store": True}


def test_in_the_package_installing_is_refused(tmp_path, no_update_check):
    _, post, installed = store_routes(tmp_path)

    answer = post["/api/app/aktualisieren"](None, {}, {})

    assert answer.status == HTTPStatus.CONFLICT
    assert body(answer) == {"fehler": STORE_NOTE}
    assert installed == []


def test_in_the_package_quitting_installs_nothing(tmp_path, monkeypatch, no_update_check):
    monkeypatch.setattr(routes_app, "QUIT_DELAY_SECONDS", 0.01)
    _, post, installed = store_routes(tmp_path)

    assert body(post["/api/app/beenden"](None, {}, {})) == {"ok": True}
    assert installed == []


def test_in_the_package_the_switch_for_pre_releases_is_not_there(tmp_path, no_update_check):
    get, post, _ = store_routes(tmp_path)

    assert get["/api/app/vorabversionen"](None, {}, None).status == HTTPStatus.NOT_FOUND
    assert post["/api/app/vorabversionen"](None, {}, {"an": True}).status == HTTPStatus.NOT_FOUND
    assert settings.beta_updates(settings.Paths(tmp_path)) is False


def test_outside_the_package_the_update_is_offered_as_before(tmp_path):
    get, _, _ = store_routes(tmp_path, store=False)

    data = body(get["/api/app/version"](None, {}, None))

    assert data["update"]["version"] == "9.2.0" and "store" not in data
    assert body(get["/api/app/vorabversionen"](None, {}, None)) == {"an": False}


def test_controls_ask_the_detection_by_default(monkeypatch, no_update_check):
    monkeypatch.setattr(routes_app.msix_package, "running_packaged", lambda: True)

    assert routes_app.Controls(stop=lambda: None).store is True
