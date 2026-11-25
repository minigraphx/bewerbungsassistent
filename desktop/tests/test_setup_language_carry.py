"""The app language chosen on the first start goes along into the data folder (#435, G10, Andy 25.11.2026).

Before a data folder is chosen the app runs on a placeholder folder, so a choice in the switch on Einrichtung lands
there. Choosing the folder, or a folder that comes back (a USB stick), carries it into that folder when the folder has
no app language of its own; a folder with its own keeps it, and the answer says so for the page's note.
"""
import json
import threading
import types
import urllib.error
import urllib.request

import pytest
import yaml

import app
import language_settings
import routes_setup
import settings
import setup


@pytest.fixture
def started(tmp_path):
    """The app on its placeholder folder, as on the first start, switching folders as the desktop app does."""
    paths = settings.Paths(tmp_path / "app")
    placeholder = setup.placeholder_dir(paths)
    server = app.erstelle_server(placeholder)

    def switch(folder):
        server.kontext = app.erstelle_kontext(folder)
        return server.kontext

    state = routes_setup.Setup(paths=paths, switch=switch, suggestion=tmp_path / "Dokumente" / "Bewerbungsbegleiter",
                               downloads=tmp_path / "Downloads")
    get_routes, post_routes = routes_setup.make_routes(state)
    server.routen_get.update(get_routes)
    server.routen_post.update(post_routes)
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
    yield server, paths
    server.shutdown()
    server.server_close()


def call(server, path, body=None):
    url = f"{server.url.rstrip('/')}{path}"
    if body is None:
        request = urllib.request.Request(f"{url}?t={server.token}")
    else:
        request = urllib.request.Request(url, json.dumps(body).encode(), method="POST",
                                         headers={"Content-Type": "application/json", "X-Token": server.token})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def stored(folder) -> dict:
    path = folder / language_settings.FILE
    return yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else {}


def data_folder_with(folder, languages: str):
    """An existing data folder of the app (its search profile marks it as one) with its own sprachen.yaml."""
    folder.mkdir(parents=True)
    (folder / "suchprofil.md").write_text("# Suchprofil\n", encoding="utf-8")
    (folder / language_settings.FILE).write_text(languages, encoding="utf-8")
    return folder


def choose_on_first_start(server, language: str) -> None:
    status, answer = call(server, "/api/sprachen", {"app": language})
    assert status == 200 and answer["app"] == language


def test_a_language_chosen_on_the_first_start_goes_into_a_new_folder_with_drafts(started, tmp_path):
    server, _ = started
    choose_on_first_start(server, "fr")
    folder = tmp_path / "Bewerbungsbegleiter"

    status, answer = call(server, "/api/app/datenordner", {"pfad": str(folder)})

    assert status == 200 and answer["eingerichtet"] is True
    assert answer["sprache"] == {"ergebnis": "uebernommen", "app": "fr"}
    assert stored(folder) == {"app": "fr"}
    assert language_settings.app_language(server.kontext.daten) == "fr"
    assert server.kontext.ablage.liste(folder / language_settings.FILE), "written with a draft like every change"


def test_a_folder_with_its_own_app_language_keeps_it_and_the_answer_says_so(started, tmp_path):
    server, _ = started
    folder = data_folder_with(tmp_path / "Bewerbungsbegleiter", "app: de\nbewerbung: [de, en]\n")
    choose_on_first_start(server, "en")

    status, answer = call(server, "/api/app/datenordner", {"pfad": str(folder)})

    assert status == 200 and answer["sprache"] == {"ergebnis": "eigene", "app": "de"}
    assert stored(folder) == {"app": "de", "bewerbung": ["de", "en"]}


def test_the_same_language_in_both_needs_no_note(started, tmp_path):
    server, _ = started
    folder = data_folder_with(tmp_path / "Bewerbungsbegleiter", "app: fr\n")
    choose_on_first_start(server, "fr")

    assert call(server, "/api/app/datenordner", {"pfad": str(folder)})[1]["sprache"] is None


def test_without_a_choice_on_the_first_start_nothing_is_written(started, tmp_path):
    server, _ = started
    folder = tmp_path / "Bewerbungsbegleiter"

    status, answer = call(server, "/api/app/datenordner", {"pfad": str(folder)})

    assert status == 200 and answer["sprache"] is None
    assert not (folder / language_settings.FILE).exists()


def test_changing_from_one_data_folder_to_another_carries_nothing(started, tmp_path):
    server, _ = started
    choose_on_first_start(server, "fr")
    first = tmp_path / "erster"
    call(server, "/api/app/datenordner", {"pfad": str(first)})
    assert stored(first) == {"app": "fr"}
    second = tmp_path / "zweiter"

    status, answer = call(server, "/api/app/datenordner", {"pfad": str(second)})

    assert status == 200 and answer["sprache"] is None
    assert not (second / language_settings.FILE).exists()


def test_a_folder_that_comes_back_takes_the_language_chosen_meanwhile(started, tmp_path):
    server, paths = started
    folder = tmp_path / "usb-stick" / "daten"
    settings.remember_data_dir(paths, folder)
    choose_on_first_start(server, "en")  # the stick is not plugged in: the app runs on the placeholder
    folder.mkdir(parents=True)

    status, answer = call(server, "/api/app/einrichtung")

    assert status == 200 and answer["gewechselt"] is True
    assert answer["sprache"] == {"ergebnis": "uebernommen", "app": "en"}
    assert stored(folder) == {"app": "en"}


def test_a_folder_that_comes_back_keeps_its_own_language(started, tmp_path):
    server, paths = started
    folder = tmp_path / "usb-stick" / "daten"
    settings.remember_data_dir(paths, folder)
    choose_on_first_start(server, "en")
    folder.mkdir(parents=True)
    (folder / language_settings.FILE).write_text("app: fr\n", encoding="utf-8")

    status, answer = call(server, "/api/app/einrichtung")

    assert status == 200 and answer["sprache"] == {"ergebnis": "eigene", "app": "fr"}
    assert stored(folder) == {"app": "fr"}


def test_the_desktop_app_switch_hands_back_the_new_state(tmp_path):
    import start
    old = app.erstelle_kontext(setup.placeholder_dir(settings.Paths(tmp_path / "app")))
    holder = {"server": types.SimpleNamespace(kontext=old)}
    folder = tmp_path / "daten"
    folder.mkdir()

    new = start.folder_switch(holder)(folder)

    assert new.daten == folder.resolve() and holder["server"].kontext is new
