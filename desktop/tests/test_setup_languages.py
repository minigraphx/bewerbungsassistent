"""The page Einrichtung in French and English (#418, G10, docs/design/sprachen.md).

With the preview on and French or English as the app language, the page comes with its headings and labels in that
language, the routes it calls answer in it, and the system's folder dialog is titled in it. With the preview off it all
stays German, byte for byte. The real catalog in bewerbungen/sprachen/ is used, so these tests also prove its entries.
"""
import http.client
import json
import pathlib
import subprocess
import threading

import pytest

import app
import dialogs
import routes_preferences
import routes_setup
import server as server_module
import settings
import setup
import ui_texts

PAGE = "/einrichtung"
NBSP = chr(0xA0)
# Headings, legends, labels and buttons of the page as text nodes.
SETUP_FR = ("<title>Configuration</title>", "<h1>Configuration</h1>", f"Que faut-il chercher{NBSP}?", "Un poste",
            "Une place d'apprentissage", f"Inscription à l'ORP{NBSP}?", "Informations depuis un fichier",
            "Charger l'extension de navigateur", "Presque terminé", "Saisir mes informations", "Passer",
            "Configurer plus tard", f"Ça ne marche pas{NBSP}?")
SETUP_EN = ("<title>Setup</title>", "<h1>Setup</h1>", "What are you looking for?", "A job", "An apprenticeship",
            "Registered with the RAV?", "Details from a file", "Load the browser extension", "Almost done")
SETUP_DE = ("<h1>Einrichtung</h1>", "Was wird gesucht?", "Eine Lehrstelle", "Beim RAV gemeldet?",
            "Angaben aus einer Datei", "Browser-Erweiterung laden", "Fast fertig", "Klappt es nicht?")


class Runner:
    def __init__(self, stdout=""):
        self.calls = []
        self.stdout = stdout

    def __call__(self, command, **options):
        self.calls.append((command, options))
        return subprocess.CompletedProcess(command, 0, self.stdout, "")


def store_language(folder: pathlib.Path, language: str) -> None:
    (folder / "sprachen.yaml").write_text(f"app: {language}\n", encoding="utf-8")


@pytest.fixture
def preview(monkeypatch):
    monkeypatch.setenv(ui_texts.PREVIEW_ENV, "1")


@pytest.fixture
def no_preview(monkeypatch):
    monkeypatch.delenv(ui_texts.PREVIEW_ENV, raising=False)


@pytest.fixture
def started(tmp_path):
    """The app on its placeholder folder, as on the first start, with the routes the page Einrichtung calls."""
    paths = settings.Paths(tmp_path / "app")
    placeholder = setup.placeholder_dir(paths)
    server = app.erstelle_server(placeholder)
    asked = []

    def choose(kind, start, language):
        asked.append((kind, language))
        return None

    state = routes_setup.Setup(paths=paths, switch=lambda folder: None, suggestion=tmp_path / "Dokumente" / "Bewerbung",
                               choose=choose, downloads=tmp_path / "Downloads")
    get_routes, post_routes = routes_setup.make_routes(state)
    server.routen_get.update({**get_routes, **routes_preferences.GET})
    server.routen_post.update({**post_routes, **routes_preferences.POST})
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    yield server, placeholder, paths, asked
    server.shutdown()
    server.server_close()


def connect(server) -> tuple[http.client.HTTPConnection, dict]:
    port = server.server_address[1]
    return http.client.HTTPConnection("127.0.0.1", port, timeout=30), {"Host": f"127.0.0.1:{port}"}


def page(server, path: str) -> tuple[int, str]:
    connection, headers = connect(server)
    connection.request("GET", f"/?t={server.token}", headers=headers)
    cookie = connection.getresponse()
    cookie.read()
    connection.request("GET", path, headers={**headers, "Cookie": cookie.getheader("Set-Cookie").split(";", 1)[0]})
    answer = connection.getresponse()
    body = answer.read().decode("utf-8")
    connection.close()
    return answer.status, body


def post(server, path: str, body: dict) -> tuple[int, dict]:
    connection, headers = connect(server)
    connection.request("POST", path, body=json.dumps(body),
                       headers={**headers, "X-Token": server.token, "Content-Type": "application/json"})
    answer = connection.getresponse()
    data = json.loads(answer.read())
    connection.close()
    return answer.status, data


def setup_page(server) -> str:
    """The page as the server sends it in German: its token filled in and the links the server hides taken out."""
    html = (server_module.SEITEN / app.SEITEN[PAGE]).read_text(encoding="utf-8").replace("__TOKEN__", server.token)
    for link in server.hidden_links:
        html = html.replace(link, "")
    return html


# The page


def test_the_setup_page_shows_its_headings_and_labels_in_french(started, preview):
    server, folder, _, _ = started
    store_language(folder, "fr")

    status, body = page(server, PAGE)

    assert status == 200
    assert '<html lang="fr">' in body
    assert [text for text in SETUP_FR if text not in body] == []
    assert [text for text in SETUP_DE if text in body] == []


def test_the_setup_page_shows_its_headings_and_labels_in_english(started, preview):
    server, folder, _, _ = started
    store_language(folder, "en")

    status, body = page(server, PAGE)

    assert status == 200
    assert [text for text in SETUP_EN if text not in body] == []
    assert [text for text in SETUP_DE if text in body] == []


def test_the_setup_page_stays_german_byte_for_byte_with_the_preview_off(started, no_preview):
    server, folder, _, _ = started
    store_language(folder, "fr")

    status, body = page(server, PAGE)

    assert (status, body) == (200, setup_page(server))
    assert [text for text in SETUP_DE if text not in body] == []


# The routes it calls


def test_the_folder_check_answers_its_error_in_french(started, preview):
    server, folder, _, _ = started
    store_language(folder, "fr")

    assert post(server, "/api/app/ordner-pruefen", {"pfad": "Bewerbung"}) == (
        400, {"fehler": f"Merci d'indiquer le chemin complet du dossier, p.{NBSP}ex. C:\\Users\\…\\Documents\\Candidature."})


def test_the_folder_check_answers_its_error_in_english(started, preview):
    server, folder, _, _ = started
    store_language(folder, "en")

    assert post(server, "/api/app/ordner-pruefen", {"pfad": "Bewerbung"}) == (
        400, {"fehler": "Please give the full path of the folder, e.g. C:\\Users\\…\\Documents\\Applications."})


def test_the_folder_check_says_what_happens_to_the_folder_in_french(started, preview, tmp_path):
    server, folder, _, _ = started
    store_language(folder, "fr")

    status, answer = post(server, "/api/app/ordner-pruefen", {"pfad": str(tmp_path / "Neu")})

    assert (status, answer["zustand"], answer["text"]) == (200, "neu", "Le dossier sera créé.")


def test_a_missing_data_folder_is_named_in_french(started, preview, tmp_path):
    server, folder, paths, _ = started
    store_language(folder, "fr")
    gone = tmp_path / "Weg"
    settings.remember_data_dir(paths, gone)

    status, answer = post(server, "/api/app/einstieg", {"pfad": str(tmp_path / "einstieg.json")})

    assert (status, answer) == (400, {"fehler": f"Le dossier de données {gone} est introuvable."})


def test_the_routes_of_the_page_stay_german_with_the_preview_off(started, no_preview, tmp_path):
    server, folder, paths, _ = started
    store_language(folder, "fr")
    gone = tmp_path / "Weg"

    assert post(server, "/api/app/ordner-pruefen", {"pfad": "Bewerbung"}) == (
        400, {"fehler": "Bitte den vollständigen Pfad des Ordners angeben, z.B. C:\\Users\\…\\Documents\\Bewerbung."})
    assert post(server, "/api/app/ordner-pruefen", {"pfad": str(tmp_path / "Neu")})[1]["text"] == "Der Ordner wird neu angelegt."
    settings.remember_data_dir(paths, gone)
    assert post(server, "/api/app/einstieg", {"pfad": "x"}) == (400, {"fehler": f"Der Datenordner {gone} wurde nicht gefunden."})


# The system's folder dialog


def test_the_choice_route_hands_the_app_language_to_the_dialog(started, preview):
    server, folder, _, asked = started
    store_language(folder, "fr")

    assert post(server, "/api/app/waehlen", {"art": "ordner"}) == (200, {"pfad": None})
    assert asked == [("ordner", "fr")]


def test_the_folder_dialog_is_titled_in_the_app_language_on_every_system(tmp_path):
    linux, windows, mac = Runner(), Runner(), Runner()

    dialogs.choose("ordner", tmp_path, platform="linux", run=linux, which=lambda name: "/usr/bin/kdialog" if name == "kdialog" else None,
                   language="fr")
    dialogs.choose("datei", tmp_path, platform="win32", run=windows, language="en")
    dialogs.choose("ordner", tmp_path, platform="darwin", run=mac, language="fr")

    assert linux.calls[0][0][:3] == ["kdialog", "--title", "Choisir le dossier des données de candidature"]
    assert "$dialog.Title = 'Choose the starting file'" in windows.calls[0][0][-1]
    assert "'Starting file (*.zip;*.json)|*.zip;*.json'" in windows.calls[0][0][-1]
    assert 'choose folder with prompt "Choisir le dossier des données de candidature"' in mac.calls[0][0][-1]


def test_the_dialog_scripts_stay_german_without_a_language(tmp_path):
    windows, mac = Runner(), Runner()

    dialogs.choose("ordner", tmp_path, platform="win32", run=windows)
    dialogs.choose("datei", tmp_path, platform="darwin", run=mac)

    assert windows.calls[0][0][-1] == dialogs.WINDOWS["ordner"]
    assert mac.calls[0][0][-1] == dialogs.MAC["datei"]
    assert "$dialog.Description = 'Ordner für die Bewerbungsdaten wählen'" in dialogs.WINDOWS["ordner"]
    assert 'choose file with prompt "Einstiegsdatei wählen"' in dialogs.MAC["datei"]


def test_a_failed_dialog_says_so_in_the_app_language(tmp_path, preview):
    with pytest.raises(ValueError) as failed:
        dialogs.choose("ordner", tmp_path, platform="plan9", run=Runner(), language="fr")

    assert ui_texts.uebersetze(failed.value.args[0], "fr") == (
        "Ce système n'a pas de fenêtre de sélection. Merci de saisir le chemin à la main.")
    assert str(failed.value) == "Auf diesem System gibt es keinen Auswahldialog. Bitte den Pfad selbst eintragen."
