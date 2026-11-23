"""The shared frame of every page in French and English (#416, G10, docs/design/sprachen.md).

With the preview on and French as the app language, the page shown in place of Meine Angaben comes with its navigation
in French, and the routes of the frame answer their errors in French. With the preview off it all stays German, byte
for byte. The real catalog in bewerbungen/sprachen/ is used, so these tests also prove its entries.
"""
import http.client
import json
import pathlib
import threading
import types

import pytest

import app
import routes_ai
import routes_frame
import server as server_module
import ui_texts
from ai import budget

PAGE = "/angaben"
# Text nodes keep the apostrophe as it is; attributes such as aria-label escape quotes.
NAVIGATION_FR = ('aria-label="Navigation principale"', "Aujourd'hui", "Candidatures", "Mes documents", "Mes informations",
                 "CV et fichiers", "Aide", "Paramètres")
PAGE_FR = ("La page Mes informations n'existe que dans l'app installée.", "modifier comme texte")
NBSP = chr(0xA0)


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
    """The pages of the app without the desktop part, so /angaben shows nur-in-der-app.html, and the frame's routes."""
    s = server_module.Server(types.SimpleNamespace(daten=folder), {**routes_frame.GET, **routes_ai.GET},
                             {**routes_frame.POST, **routes_ai.POST}, app.SEITEN, stand_ins=app.DESKTOP_PAGES)
    thread = threading.Thread(target=s.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    yield s
    s.shutdown()
    s.server_close()


def connect(s) -> tuple[http.client.HTTPConnection, dict]:
    port = s.server_address[1]
    return http.client.HTTPConnection("127.0.0.1", port, timeout=30), {"Host": f"127.0.0.1:{port}"}


def page(s, path: str, session: bool = True) -> tuple[int, str]:
    connection, headers = connect(s)
    if session:
        connection.request("GET", f"/?t={s.token}", headers=headers)
        cookie = connection.getresponse()
        cookie.read()
        headers = {**headers, "Cookie": cookie.getheader("Set-Cookie").split(";", 1)[0]}
    connection.request("GET", path, headers=headers)
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


def desktop_only_page(s) -> str:
    return (server_module.SEITEN / app.DESKTOP_ONLY_PAGE).read_text(encoding="utf-8").replace("__TOKEN__", s.token)


def test_the_desktop_only_page_and_its_navigation_come_in_french(serve, folder, preview):
    store_language(folder, "fr")

    status, body = page(serve, PAGE)

    assert status == 200
    assert '<html lang="fr">' in body
    assert '<script src="/uebersetzung.js?sprache=fr"></script>' in body
    assert [text for text in (*NAVIGATION_FR, *PAGE_FR) if text not in body] == []
    assert "Hauptnavigation" not in body and "Einstellungen" not in body


def test_the_desktop_only_page_stays_german_byte_for_byte_with_the_preview_off(serve, folder, monkeypatch):
    monkeypatch.delenv(ui_texts.PREVIEW_ENV, raising=False)
    store_language(folder, "fr")

    assert page(serve, PAGE) == (200, desktop_only_page(serve))


def test_the_locked_page_comes_in_french(serve, folder, preview):
    store_language(folder, "fr")

    status, body = page(serve, PAGE, session=False)

    assert status == 403
    assert '<html lang="fr">' in body and "Cette page ne s'ouvre que depuis l'app." in body


def test_the_locked_page_stays_german_with_the_preview_off(serve, folder, monkeypatch):
    monkeypatch.delenv(ui_texts.PREVIEW_ENV, raising=False)
    store_language(folder, "fr")

    assert page(serve, PAGE, session=False) == (403, server_module.PAGE_LOCKED)


def test_a_route_of_the_search_frame_answers_its_error_in_french(serve, folder, preview):
    store_language(folder, "fr")

    assert post(serve, "/api/suche/rahmen", {"pensum": "80"}) == (
        400, {"fehler": "Terminer d'abord Mes informations."})


def test_the_used_up_budget_names_its_renewal_day_in_the_app_language():
    first = budget.used_up_message({"monat": "2026-11", "erneuert_am": "2026-12-01"})
    second = budget.used_up_message({"monat": "2026-03", "erneuert_am": "2026-04-02"})

    assert ui_texts.uebersetze(first, "fr") == (f"Le budget IA pour novembre est épuisé. L'IA fonctionne à nouveau dès le "
                                                f"1er{NBSP}décembre{NBSP}; tout le reste continue de fonctionner.")
    assert ui_texts.uebersetze(second, "en") == (f"The AI budget for March is used up. The AI works again from "
                                                 f"2{NBSP}April; everything else keeps working.")
    assert first == (f"Das KI-Budget für November ist aufgebraucht. Die KI geht wieder ab 1.{NBSP}Dezember; "
                     "alles andere funktioniert weiterhin.")


def test_a_route_of_the_ai_answers_its_error_in_english(serve, folder, preview):
    store_language(folder, "en")

    assert post(serve, "/api/ki/einwilligung", {"zustimmung": False}) == (
        400, {"fehler": "Please read the text and confirm it first."})


def test_the_routes_of_the_frame_stay_german_with_the_preview_off(serve, folder, monkeypatch):
    monkeypatch.delenv(ui_texts.PREVIEW_ENV, raising=False)
    store_language(folder, "fr")

    assert post(serve, "/api/suche/rahmen", {"pensum": "80"}) == (400, {"fehler": routes_frame.NO_PROFILE})
    assert post(serve, "/api/ki/einwilligung", {"zustimmung": False}) == (400, {"fehler": routes_ai.NO_TICK})
