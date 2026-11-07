"""Desktop start: settings, invitation links, one running app, self-test (MIN-342)."""
import json
import pathlib
import threading

import pytest

import instance
import selftest
import settings
import start
import urlscheme


@pytest.fixture
def paths(tmp_path):
    return settings.Paths(tmp_path / "app")


def test_app_folder_per_system(tmp_path):
    home = tmp_path / "home"

    assert settings.app_dir({"APPDATA": str(tmp_path / "roaming")}, "win32", home) == tmp_path / "roaming" / "Bewerbungsbegleiter"
    assert settings.app_dir({}, "darwin", home) == home / "Library" / "Application Support" / "Bewerbungsbegleiter"
    assert settings.app_dir({}, "linux", home) == home / ".config" / "bewerbungsbegleiter"


def test_broken_settings_fall_back_to_defaults(paths, tmp_path):
    paths.app_dir.mkdir(parents=True)
    paths.settings.write_text("{kaputt", encoding="utf-8")

    assert settings.load(paths) == {}
    assert settings.build_defaults(tmp_path) == {}


@pytest.mark.parametrize("link, code", [
    ("bewerbungsbegleiter://einladung?code=ABCD-EFGH-JKLM-NPQR", "ABCD-EFGH-JKLM-NPQR"),
    ("bewerbungsbegleiter://einladung/?code=abcd efgh", "abcd efgh"),
    ("bewerbungsbegleiter://anderes?code=ABCD", None),
    ("https://einladung?code=ABCD", None),
    ("bewerbungsbegleiter://einladung?code=<script>", None),
    (None, None),
])
def test_invitation_links(link, code):
    assert urlscheme.invitation_code(link) == code


def test_no_registry_outside_windows():
    assert urlscheme.register_windows("x.exe") is False or urlscheme.sys.platform == "win32"


def test_second_start_finds_the_running_app(paths, tmp_path, monkeypatch):
    import app
    monkeypatch.delenv("BEWERBUNGSBEGLEITER_KI_URL", raising=False)
    data = tmp_path / "daten"
    data.mkdir()
    server = app.erstelle_server(data)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        assert instance.find(paths) is None
        instance.write(paths, server.server_address[1], server.token)

        running = instance.find(paths)

        assert running is not None and running.port == server.server_address[1]
        assert server.token not in repr(running)
        assert "keine KI-Vermittlung" in instance.forward_code(running, "ABCD-EFGH")
        opened = []
        monkeypatch.setattr(start.webbrowser, "open", opened.append)
        monkeypatch.setattr(start.settings, "app_dir", lambda: paths.app_dir)
        assert start.main([]) == 0 and opened == [running.entry_url]
    finally:
        server.shutdown()
        server.server_close()


def test_stale_instance_file_is_ignored(paths):
    paths.app_dir.mkdir(parents=True)
    paths.instance.write_text(json.dumps({"port": 1, "token": "x"}), encoding="utf-8")

    assert instance.find(paths) is None
    instance.remove(paths)
    assert not paths.instance.exists()


def test_mediation_address_comes_with_the_package(monkeypatch):
    monkeypatch.delenv("BEWERBUNGSBEGLEITER_KI_URL", raising=False)

    start._apply_build_defaults({"ki_url": "https://ki.example.ch"})

    import os
    assert os.environ["BEWERBUNGSBEGLEITER_KI_URL"] == "https://ki.example.ch"


def test_the_privacy_page_comes_with_the_package(monkeypatch):
    monkeypatch.delenv("BEWERBUNGSBEGLEITER_DATENSCHUTZ_URL", raising=False)

    start._apply_build_defaults({"datenschutz_url": "https://example.ch/datenschutz"})

    import os
    assert os.environ["BEWERBUNGSBEGLEITER_DATENSCHUTZ_URL"] == "https://example.ch/datenschutz"


def test_the_update_address_comes_with_the_package(monkeypatch):
    import updates
    monkeypatch.delenv(updates.URL_VARIABLE, raising=False)

    start._apply_build_defaults({"update_url": "https://updates.example.ch"})

    import os
    assert os.environ[updates.URL_VARIABLE] == "https://updates.example.ch"


def test_an_invitation_link_at_the_start_waits_for_the_consent(tmp_path, monkeypatch):
    import app
    import routes_ai
    from ai.connection import URL_VARIABLE
    monkeypatch.setenv(URL_VARIABLE, "https://ki.example.ch")
    monkeypatch.setattr(routes_ai.invitation, "redeem", lambda *args, **kwargs: pytest.fail("no consent yet"))
    kontext = app.erstelle_kontext(tmp_path)

    start._redeem(kontext, "ABCD-EFGH")

    assert kontext.cache[routes_ai.WAITING_CODE] == "ABCD-EFGH"


def test_selftest_builds_both_pdfs(tmp_path):
    assert selftest.run(tmp_path) == 0
    assert (tmp_path / selftest.RESULT_FILE).read_text(encoding="utf-8").startswith("ok")


def test_mcp_flag_goes_to_the_mcp_server_before_anything_else(monkeypatch, tmp_path):
    import mcp_server
    monkeypatch.setattr(settings, "app_dir", lambda: tmp_path)
    monkeypatch.setattr(mcp_server, "main", lambda paths: 42)
    assert start.main(["--mcp"]) == 42


def test_the_page_for_questions_is_off_until_switched_on_in_the_settings(tmp_path):
    paths = settings.Paths(tmp_path)
    assert settings.questions_page(paths) is False
    settings.save(paths, {settings.QUESTIONS_PAGE: "ja"})
    assert settings.questions_page(paths) is False
    settings.save(paths, {settings.QUESTIONS_PAGE: True})
    assert settings.questions_page(paths) is True


def test_check_after_an_update_confirms_and_ends(monkeypatch):
    confirmed = []
    monkeypatch.setattr(start.updates_macos, "confirm_started", confirmed.append)
    monkeypatch.setattr(start.updates_macos, "running_app", lambda: "die-app")
    monkeypatch.setattr(selftest, "check_modules", lambda: None)

    assert start.main(["--nach-update"]) == 0
    assert confirmed == ["die-app"]


def test_check_after_an_update_does_not_confirm_a_broken_version(monkeypatch):
    def broken():
        raise ImportError("missing")

    confirmed = []
    monkeypatch.setattr(start.updates_macos, "confirm_started", confirmed.append)
    monkeypatch.setattr(selftest, "check_modules", broken)

    assert start.main(["--nach-update"]) == 1
    assert confirmed == []


# Linux as AppImage (#73): whatever starts the app later gets the AppImage file, not the temporary mount


def test_packed_on_linux_the_extension_starts_the_appimage(monkeypatch, tmp_path):
    image = tmp_path / "Bewerbungsbegleiter-x86_64.AppImage"
    image.write_bytes(b"")
    monkeypatch.setattr(start.sys, "frozen", True, raising=False)
    monkeypatch.setenv("APPIMAGE", str(image))

    assert start._host_executable(settings.Paths(tmp_path / "app")) == image


def test_packed_on_linux_the_link_and_menu_entry_are_registered(monkeypatch, tmp_path):
    image = tmp_path / "B.AppImage"
    image.write_bytes(b"")
    calls = []
    monkeypatch.setattr(start.sys, "frozen", True, raising=False)
    monkeypatch.setenv("APPIMAGE", str(image))
    monkeypatch.setattr(start.linux_desktop, "register_quietly", lambda executable, icon: calls.append((executable, icon)))

    start.register_link("linux")

    assert calls == [(image, start.bundle_dir() / "erweiterung" / "icons" / "icon128.png")]


def test_from_source_no_link_is_registered(monkeypatch):
    monkeypatch.delattr(start.sys, "frozen", raising=False)
    monkeypatch.setattr(start.linux_desktop, "register_quietly", lambda *args: pytest.fail("must not register"))
    monkeypatch.setattr(start.urlscheme, "register_windows", lambda *args: pytest.fail("must not register"))

    start.register_link("linux")
    start.register_link("win32")
