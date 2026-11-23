"""The page Einstellungen in French and English (#417, G10, docs/design/sprachen.md).

With the preview on and French as the app language, the page comes with its headings and labels in French, and the
routes it calls answer their errors in the app language. With the preview off it all stays German, byte for byte. The
real catalog in bewerbungen/sprachen/ is used, so these tests also prove its entries.
"""
import http.client
import json
import pathlib
import threading
import types

import pytest

import app
import language_settings
import page_limit
import routes_language_settings
import routes_page_limit
import routes_preferences
import server as server_module
import ui_texts

PAGE = "/einstellungen"
NBSP = chr(0xA0)
# Headings, legends and labels of the page; text nodes keep the apostrophe as it is.
SETTINGS_FR = ("<title>Paramètres</title>", "<h1>Paramètres</h1>", "IA, budget et langue", "Accès à l'IA",
               "Claude avec un abonnement personnel", "Clé API personnelle", "Consentement", "Budget IA",
               "Langue de l'app", "Je postule en", "Navigateur de l'app", "L'app s'ouvre dans",
               "Poste, apprentissage, ORP", "Données et sauvegarde", "Longueur du CV", "Préversions", "Avancé",
               "À propos de l'app", f"À savoir d'abord{NBSP}:")
SETTINGS_DE = ("<h1>Einstellungen</h1>", "KI, Budget und Sprache", "Zugang zur KI", "Eigener API-Schlüssel",
               "Länge des Lebenslaufs", "Vorabversionen")


def store_language(folder: pathlib.Path, language: str) -> None:
    (folder / "sprachen.yaml").write_text(f"app: {language}\n", encoding="utf-8")


@pytest.fixture
def folder(tmp_path):
    data = tmp_path / "daten"
    data.mkdir()
    return data


@pytest.fixture
def preview(monkeypatch):
    monkeypatch.setenv(ui_texts.PREVIEW_ENV, "1")


@pytest.fixture
def serve(folder):
    """The pages of the app without the desktop part, and the routes the page Einstellungen calls."""
    modules = (routes_language_settings, routes_page_limit, routes_preferences)
    s = server_module.Server(types.SimpleNamespace(daten=folder),
                             {path: route for module in modules for path, route in module.GET.items()},
                             {path: route for module in modules for path, route in module.POST.items()},
                             app.SEITEN, stand_ins=app.DESKTOP_PAGES)
    thread = threading.Thread(target=s.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    yield s
    s.shutdown()
    s.server_close()


def connect(s) -> tuple[http.client.HTTPConnection, dict]:
    port = s.server_address[1]
    return http.client.HTTPConnection("127.0.0.1", port, timeout=30), {"Host": f"127.0.0.1:{port}"}


def page(s, path: str) -> tuple[int, str]:
    connection, headers = connect(s)
    connection.request("GET", f"/?t={s.token}", headers=headers)
    cookie = connection.getresponse()
    cookie.read()
    connection.request("GET", path, headers={**headers, "Cookie": cookie.getheader("Set-Cookie").split(";", 1)[0]})
    answer = connection.getresponse()
    body = answer.read().decode("utf-8")
    connection.close()
    return answer.status, body


def post(s, path: str, body: dict) -> tuple[int, dict]:
    connection, headers = connect(s)
    connection.request("POST", path, body=json.dumps(body),
                       headers={**headers, "X-Token": s.token, "Content-Type": "application/json"})
    answer = connection.getresponse()
    data = json.loads(answer.read())
    connection.close()
    return answer.status, data


def settings_page(s) -> str:
    return (server_module.SEITEN / app.SEITEN[PAGE]).read_text(encoding="utf-8").replace("__TOKEN__", s.token)


def test_the_settings_page_shows_its_headings_and_labels_in_french(serve, folder, preview):
    store_language(folder, "fr")

    status, body = page(serve, PAGE)

    assert status == 200
    assert '<html lang="fr">' in body
    assert [text for text in SETTINGS_FR if text not in body] == []
    assert [text for text in SETTINGS_DE if text in body] == []


def test_the_settings_page_stays_german_byte_for_byte_with_the_preview_off(serve, folder, monkeypatch):
    monkeypatch.delenv(ui_texts.PREVIEW_ENV, raising=False)
    store_language(folder, "fr")

    status, body = page(serve, PAGE)

    assert (status, body) == (200, settings_page(serve))
    assert [text for text in SETTINGS_DE if text not in body] == []


def test_the_language_route_answers_its_error_in_french(serve, folder, preview):
    store_language(folder, "fr")

    assert post(serve, routes_language_settings.PATH, {}) == (
        400, {"fehler": "Merci d'indiquer la langue de l'app ou les langues de candidature."})


def test_the_language_route_answers_its_error_in_english(serve, folder, preview):
    store_language(folder, "en")

    assert post(serve, routes_language_settings.PATH, {}) == (
        400, {"fehler": "Please give the app language or the application languages."})


def test_the_page_limit_route_answers_its_error_in_french(serve, folder, preview):
    store_language(folder, "fr")

    assert post(serve, routes_page_limit.PATH, {page_limit.KEY: 5}) == (
        400, {"fehler": f"Merci de choisir{NBSP}: deux ou trois pages pour le CV."})


def test_the_routes_of_the_page_stay_german_with_the_preview_off(serve, folder, monkeypatch):
    monkeypatch.delenv(ui_texts.PREVIEW_ENV, raising=False)
    store_language(folder, "fr")

    assert post(serve, routes_language_settings.PATH, {}) == (400, {"fehler": language_settings.BAD_VALUES})
    assert post(serve, routes_page_limit.PATH, {page_limit.KEY: 5}) == (400, {"fehler": page_limit.BAD_PAGES})
