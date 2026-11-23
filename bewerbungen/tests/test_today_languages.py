"""The page Heute in French and English (#419, G10, docs/design/sprachen.md).

With the preview on and French or English as the app language, the start page comes with its headings and labels in
that language, and the routes it calls answer in it: a missing application, a stage change that finds nothing, why an
ad text is missing, and why a Job-Room entry is refused. With the preview off it all stays German, byte for byte. The
real catalog in bewerbungen/sprachen/ is used, so these tests also prove its entries.
"""
import datetime
import http.client
import json
import pathlib
import threading

import pytest

import app
import rav
import server as server_module
import sprachen_pruefen
import ui_texts

PAGE = "/"
NBSP = chr(0xA0)
REGISTER = """\
- id: muster-ag-planer
  firma: Muster AG
  stelle: Planer:in
  status: Gemerkt
  eingetragen_am: '2026-11-01'
  link: https://www.linkedin.com/jobs/view/123
"""
# Headings, card titles, empty states and buttons of the page as text nodes.
TODAY_FR = ("<title>Aujourd'hui</title>", "<h1>Bienvenue</h1>", "Au programme aujourd'hui", "<h2 id=\"danach-titel\">Ensuite</h2>",
            "Rendez-vous et délais", "Aucun rendez-vous ces prochains jours.", f"Pour l'ORP{NBSP}:", "Bon à savoir",
            "Rien ne part automatiquement.", "Ouvrir le guide illustré (en allemand)", "Prochaine étape",
            "Saisir mes informations", "Mises de côté", "Envoyées", "Terminées", "Terminer le tri", "Écarter", "Postuler",
            "Ouvrir quand même", "Votre chemin vers la première candidature")
TODAY_EN = ("<title>Today</title>", "<h1>Welcome</h1>", "What's on today", "Dates and deadlines",
            "No dates in the next few days.", "For the RAV:", "Good to know", "Nothing goes out automatically.",
            "Open the illustrated guide (in German)", "Next step", "Enter my details", "Saved", "Applied", "Closed",
            "End review", "Discard", "Apply", "Open anyway", "Your path to your first application")
TODAY_DE = ("<h1>Willkommen</h1>", "Das steht heute an", "Termine und Fristen", "Gut zu wissen", "Durchgang beenden",
            "Keine Termine in den nächsten Tagen.", "Trotzdem öffnen")
PAGE_FILES = ("seiten/uebersicht.html", "seiten/heute-logic.js", "seiten/pass.js", "seiten/uebersicht.js")


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
    """The app on a data folder with one invented saved job whose ad text is missing."""
    folder = tmp_path / "daten"
    folder.mkdir()
    (folder / "bewerbungen.yaml").write_text(REGISTER, encoding="utf-8")
    server = app.erstelle_server(folder, tmp_path / "build")
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    yield server, folder
    server.shutdown()
    server.server_close()


def connect(server) -> tuple[http.client.HTTPConnection, dict]:
    port = server.server_address[1]
    return http.client.HTTPConnection("127.0.0.1", port, timeout=30), {"Host": f"127.0.0.1:{port}"}


def page(server) -> tuple[int, str]:
    connection, headers = connect(server)
    connection.request("GET", f"/?t={server.token}", headers=headers)
    cookie = connection.getresponse()
    cookie.read()
    connection.request("GET", PAGE, headers={**headers, "Cookie": cookie.getheader("Set-Cookie").split(";", 1)[0]})
    answer = connection.getresponse()
    body = answer.read().decode("utf-8")
    connection.close()
    return answer.status, body


def request(server, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    connection, headers = connect(server)
    if method == "GET":
        separator = "&" if "?" in path else "?"
        connection.request("GET", f"{path}{separator}t={server.token}", headers=headers)
    else:
        connection.request("POST", path, body=json.dumps(body),
                           headers={**headers, "X-Token": server.token, "Content-Type": "application/json"})
    answer = connection.getresponse()
    data = json.loads(answer.read())
    connection.close()
    return answer.status, data


def today_page(server) -> str:
    """The page as the server sends it in German: its token filled in and the links the server hides taken out."""
    html = (server_module.SEITEN / app.SEITEN[PAGE]).read_text(encoding="utf-8").replace("__TOKEN__", server.token)
    for link in server.hidden_links:
        html = html.replace(link, "")
    return html


# The page


def test_the_start_page_shows_its_headings_and_labels_in_french(started, preview):
    server, folder = started
    store_language(folder, "fr")

    status, body = page(server)

    assert status == 200
    assert '<html lang="fr">' in body
    assert [text for text in TODAY_FR if text not in body] == []
    assert [text for text in TODAY_DE if text in body] == []


def test_the_start_page_shows_its_headings_and_labels_in_english(started, preview):
    server, folder = started
    store_language(folder, "en")

    status, body = page(server)

    assert status == 200
    assert [text for text in TODAY_EN if text not in body] == []
    assert [text for text in TODAY_DE if text in body] == []


def test_the_start_page_stays_german_byte_for_byte_with_the_preview_off(started, no_preview):
    server, folder = started
    store_language(folder, "fr")

    status, body = page(server)

    assert (status, body) == (200, today_page(server))
    assert [text for text in TODAY_DE if text not in body] == []


def test_the_page_and_its_own_scripts_and_routes_are_finished():
    finished = {str(path.relative_to(sprachen_pruefen.BASE)) for path in sprachen_pruefen.FERTIG
                if path.is_relative_to(sprachen_pruefen.BASE)}

    assert set(PAGE_FILES) | {"rav.py", "routes_rav.py", "missing_ads.py"} <= finished


# The routes it calls


def test_a_job_the_pass_cannot_find_is_named_in_french_and_english(started, preview):
    server, folder = started
    store_language(folder, "fr")
    assert request(server, "GET", "/api/bewerbung?id=weg") == (404, {"fehler": "Candidature 'weg' introuvable"})

    store_language(folder, "en")
    assert request(server, "GET", "/api/bewerbung?id=weg") == (404, {"fehler": "Application 'weg' not found"})


def test_a_stage_change_for_a_job_gone_meanwhile_is_refused_in_french(started, preview):
    server, folder = started
    store_language(folder, "fr")

    assert request(server, "POST", "/api/bewerbungen/stand", {"ids": ["weg"], "status": "Verworfen"}) == (
        400, {"fehler": f"Ces candidatures n'existent pas{NBSP}: weg. Rien n'a été modifié."})


def test_why_the_ad_text_is_missing_comes_in_the_app_language(started, preview):
    server, folder = started
    store_language(folder, "fr")
    status, answer = request(server, "GET", "/api/bewerbung?id=muster-ag-planer")
    assert (status, answer["text_fehlt"]) == (200, {
        "grund": "linkedin.com ne fait pas partie des portails qui permettent le chargement automatique.",
        "weg": f"Ouvrir l'annonce et l'enregistrer avec l'extension, ou coller le texte sous «{NBSP}Texte de l'annonce{NBSP}»."})

    store_language(folder, "en")
    assert request(server, "GET", "/api/bewerbung?id=muster-ag-planer")[1]["text_fehlt"]["grund"] == (
        "linkedin.com is not one of the portals that allow automatic loading.")


def test_a_job_room_entry_before_applying_is_refused_in_french(started, preview):
    server, folder = started
    store_language(folder, "fr")

    status, answer = request(server, "POST", "/api/rav/start", {"ids": ["muster-ag-planer"]})

    assert (status, answer["abgelehnt"][0]["grund"]) == (200, "Candidature pas encore envoyée.")


def test_the_routes_of_the_page_stay_german_with_the_preview_off(started, no_preview):
    server, folder = started
    store_language(folder, "fr")

    assert request(server, "GET", "/api/bewerbung?id=weg") == (404, {"fehler": "Bewerbung 'weg' nicht gefunden"})
    assert request(server, "POST", "/api/bewerbungen/stand", {"ids": ["weg"], "status": "Verworfen"}) == (
        400, {"fehler": "Diese Bewerbungen gibt es nicht: weg. Es wurde nichts geändert."})
    assert request(server, "GET", "/api/bewerbung?id=muster-ag-planer")[1]["text_fehlt"]["grund"] == (
        "linkedin.com ist keines der Portale, die automatisches Laden erlauben.")
    assert request(server, "POST", "/api/rav/start", {"ids": ["muster-ag-planer"]})[1]["abgelehnt"][0]["grund"] == (
        "Noch nicht beworben.")


def test_the_job_room_reminder_names_its_month_so_the_page_can_word_it():
    entries = [{"id": "a", "firma": "A", "stelle": "B", "status": "Beworben", "beworben_am": "2026-12-03"},
               {"id": "b", "firma": "C", "stelle": "D", "status": "Beworben", "beworben_am": "2026-11-03",
                "rav_eingetragen_am": "2026-11-04"}]

    found = rav.reminder(entries, datetime.date(2027, 1, 2))

    assert (found["monat"], found["monat_iso"]) == ("Dezember 2026", "2026-12")
