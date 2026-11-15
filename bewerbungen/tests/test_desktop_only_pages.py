"""Pages whose routes only the desktop part registers (#308): started as app.py, they say so instead of loading empty."""
import re
import threading

import pytest

import app
import server as server_modul
from test_app import anfrage, get

ANGABEN_NOTE = "Meine Angaben gibt es nur in der installierten App."
SETUP_NOTE = "Die Einrichtung gibt es nur in der installierten App."
FULL_APP_START = "desktop/start.py"


def _running(folder, build, extra_routes=({}, {})):
    s = app.erstelle_server(folder, build=build, extra_routes=extra_routes)
    threading.Thread(target=s.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
    return s


@pytest.fixture
def plain(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    folder = tmp_path / "daten"
    folder.mkdir()
    s = _running(folder, tmp_path / "build")
    yield s
    s.shutdown()
    s.server_close()


@pytest.fixture
def with_desktop_part(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    folder = tmp_path / "daten"
    folder.mkdir()
    s = _running(folder, tmp_path / "build", ({"/api/angaben/stand": lambda k, parameter, body: {}}, {}))
    yield s
    s.shutdown()
    s.server_close()


def test_plain_interface_has_no_routes_for_meine_angaben(plain):
    status, _, body, _ = anfrage(plain, "GET", f"/api/angaben/stand?t={plain.token}")

    assert status == 404 and "Nicht gefunden" in body.decode("utf-8")


def test_meine_angaben_says_it_works_only_in_the_app_and_how_to_start_it(plain):
    status, _, body = get(plain, "/angaben")
    html = body.decode("utf-8")

    assert status == 200
    assert ANGABEN_NOTE in html
    assert FULL_APP_START in html
    assert "/api/angaben/" not in html  # no form that would save into routes that are not there


def test_meine_angaben_keeps_its_form_where_the_desktop_part_registers_the_routes(with_desktop_part):
    status, _, body = get(with_desktop_part, "/angaben")
    html = body.decode("utf-8")

    assert status == 200
    assert "/api/angaben/stand" in html
    assert ANGABEN_NOTE not in html


def test_meine_angaben_follows_routes_registered_after_the_server_is_built(plain):
    plain.routen_get["/api/angaben/stand"] = lambda k, parameter, body: {}

    html = get(plain, "/angaben")[2].decode("utf-8")

    assert "/api/angaben/stand" in html and ANGABEN_NOTE not in html


def test_the_note_keeps_the_menu_with_meine_angaben_marked(plain):
    html = get(plain, "/angaben")[2].decode("utf-8")
    nav = re.search(r"<nav[ >].*?</nav>", html, re.S).group(0)

    assert 'href="/angaben" data-target="angaben"' in nav
    assert '<script src="/sidebar.js">' in html


def test_einrichtung_says_it_works_only_in_the_app_when_its_routes_are_missing(plain):
    assert anfrage(plain, "GET", f"/api/app/einrichtung?t={plain.token}")[0] == 404
    html = get(plain, "/einrichtung")[2].decode("utf-8")
    script = (server_modul.SEITEN / "einrichtung.js").read_text(encoding="utf-8")

    assert f'id="nur-installiert" class="notice notice--warning" role="status" hidden>{SETUP_NOTE}' in html
    assert re.search(r'holen\("/api/app/einrichtung"\);\s*\} catch \{\s*info = null;\s*\$\("nur-installiert"\)\.hidden = false;',
                     script)
