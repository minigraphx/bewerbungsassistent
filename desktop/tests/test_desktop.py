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

    assert settings.app_dir({"APPDATA": str(tmp_path / "roaming")}, "win32", home) == tmp_path / "roaming" / "Bewerbungsassistent"
    assert settings.app_dir({}, "darwin", home) == home / "Library" / "Application Support" / "Bewerbungsassistent"
    assert settings.app_dir({}, "linux", home) == home / ".config" / "bewerbungsassistent"


def test_data_folder_is_created_once_and_remembered(paths, tmp_path):
    default = tmp_path / "Dokumente" / "Bewerbungsassistent"

    first = settings.data_dir(paths, default)
    settings.save(paths, {**settings.load(paths), "datenordner": str(tmp_path / "anders")})
    second = settings.data_dir(paths, default)

    assert first == default and default.is_dir()
    assert second == tmp_path / "anders" and second.is_dir()


def test_broken_settings_fall_back_to_defaults(paths, tmp_path):
    paths.app_dir.mkdir(parents=True)
    paths.settings.write_text("{kaputt", encoding="utf-8")

    assert settings.load(paths) == {}
    assert settings.build_defaults(tmp_path) == {}


@pytest.mark.parametrize("link, code", [
    ("bewerbungsassistent://einladung?code=ABCD-EFGH-JKLM-NPQR", "ABCD-EFGH-JKLM-NPQR"),
    ("bewerbungsassistent://einladung/?code=abcd efgh", "abcd efgh"),
    ("bewerbungsassistent://anderes?code=ABCD", None),
    ("https://einladung?code=ABCD", None),
    ("bewerbungsassistent://einladung?code=<script>", None),
    (None, None),
])
def test_invitation_links(link, code):
    assert urlscheme.invitation_code(link) == code


def test_no_registry_outside_windows():
    assert urlscheme.register_windows("x.exe") is False or urlscheme.sys.platform == "win32"


def test_second_start_finds_the_running_app(paths, tmp_path, monkeypatch):
    import app
    monkeypatch.delenv("BEWERBUNGSASSISTENT_KI_URL", raising=False)
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
        assert start.main([]) == 0 and opened == [running.url]
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
    monkeypatch.delenv("BEWERBUNGSASSISTENT_KI_URL", raising=False)

    start._use_mediation({"ki_url": "https://ki.example.ch"})

    import os
    assert os.environ["BEWERBUNGSASSISTENT_KI_URL"] == "https://ki.example.ch"


def test_selftest_builds_both_pdfs(tmp_path):
    assert selftest.run(tmp_path) == 0
    assert (tmp_path / selftest.RESULT_FILE).read_text(encoding="utf-8").startswith("ok")
