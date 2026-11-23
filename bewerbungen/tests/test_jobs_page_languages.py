"""The page Stellen in French and English (#422, G10, docs/design/sprachen.md).

With the preview on and French or English as the app language, the page Stellen comes with its headings, tabs and
buttons in that language, and the routes it calls answer in it: the reasons a search cannot start, the hints about the
search profile with the field they lead to, the search window and the refusals of rating, saving and excluding. With the
preview off all stays German, byte for byte. What the scripts say at run time is tested in
tests/jobs_page_languages.test.cjs. Search terms, companies and job titles are data and stay as they are.
"""
import threading

import pytest

import app
import search_plan
import search_stages
import server as server_module
import sprachen_pruefen
import translation_catalog
import ui_texts
from test_search_stages import profile as long_profile
from test_today_languages import connect, no_preview, preview, request, store_language  # noqa: F401  (fixtures)

PAGE = "/treffer"
NBSP = chr(0xA0)
# Searched all over Switzerland: no canton, place or postal code, so the page hints at the cantons.
PROFILE = "# Suchprofil\n\n## Keywords\n- Kernliste: Datenanalyst\n"
HIT = {"portal": "jobs.ch", "portal_id": "abc-1", "stelle": "Datenanalyst", "firma": "Muster AG", "ort": "Bern",
       "pensum": "80 %", "link": "https://www.jobs.ch/de/stellenangebote/detail/abc-1/", "alter_tage": 2,
       "text": "SQL, Python."}
WITHOUT_TEXT = {**HIT, "portal_id": "abc-2", "stelle": "Datenanalystin", "link": "https://www.jobs.ch/de/stellenangebote/detail/abc-2/",
                "text": ""}
# Title, button, tabs, filters, the bulk line and the dialogs, as the server sends them.
JOBS_FR = ("<title>Offres</title>", "Rechercher maintenant", "L'extension manque", "Nouvelles", "Dans Candidatures",
           "Écartées", "Tout évaluer", "Liste des résultats", "Par note de l'IA", "Par date", "Ordre",
           f"Plusieurs à la fois{NBSP}:", "À partir de la note", "Évaluer maintenant", "Mettre de côté", "Arrêter",
           "Faire vérifier les mots-clés", "Masquer", "Afficher tous les résultats", "Modifier la période",
           "L'IA évalue les résultats", "Liste des résultats")
JOBS_EN = ("<title>Jobs</title>", "Search now", "The extension is missing", ">New <", "In Applications", "Discarded",
           "Rate all", "Results list", "By AI grade", "By date", "Order", "Several at once:", "From grade", "Rate now",
           ">Save<", ">Stop<", "Have the search terms checked", "Show all results", "Change the time window",
           "The AI is rating results")
JOBS_DE = ("Jetzt suchen", "Die Erweiterung fehlt", ">Neu <", "In Bewerbungen <", "Alle prüfen", "Trefferliste",
           "Nach Note der KI", "Jetzt prüfen", ">Merken<", "Mehrere auf einmal:", "Anhalten", "Zeitfenster ändern")
PAGE_FILES = ("seiten/treffer.html", "seiten/suchlauf-logik.js", "seiten/treffer-firma.js", "seiten/suchbegriffe-start.js",
              "seiten/haken-ausschluss-logik.js", "seiten/haken-ausschluss.js", "seiten/treffer-wieder.js",
              "seiten/treffer.js", "seiten/merken-ab-note-logik.js", "seiten/merken-ab-note.js")
# The modules behind the routes the page calls that serve mainly this page, and what they word for it.
ROUTE_FILES = ("routes_search.py", "routes_rate_all.py", "rate_all.py", "routes_adopt_by_grade.py",
               "routes_adopt_exclusion.py", "excluded_companies.py", "search_window.py", "search_stages.py",
               "amount_text.py")


@pytest.fixture
def started(tmp_path):
    """The app on a data folder with a search profile and two invented hits, one without its ad text."""
    folder = tmp_path / "daten"
    folder.mkdir()
    (folder / search_plan.PROFILE).write_text(PROFILE, encoding="utf-8")
    server = app.erstelle_server(folder, tmp_path / "build")
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    assert request(server, "POST", "/api/suche/treffer", {"treffer": [HIT, WITHOUT_TEXT]})[0] == 200
    yield server, folder
    server.shutdown()
    server.server_close()


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


def jobs_page(server) -> str:
    """The page as the server sends it in German: its token filled in and the links the server hides taken out."""
    html = (server_module.SEITEN / app.SEITEN[PAGE]).read_text(encoding="utf-8").replace("__TOKEN__", server.token)
    for link in server.hidden_links:
        html = html.replace(link, "")
    return html


def hit_ids(server) -> dict[str, str]:
    return {hit["stelle"]: hit["id"] for hit in request(server, "GET", "/api/suche/liste")[1]["treffer"]}


# The page


def test_the_jobs_page_shows_its_headings_tabs_and_buttons_in_french(started, preview):
    server, folder = started
    store_language(folder, "fr")

    status, body = page(server)

    assert status == 200
    assert '<html lang="fr">' in body
    assert [text for text in JOBS_FR if text not in body] == []
    assert [text for text in JOBS_DE if text in body] == []


def test_the_jobs_page_shows_its_headings_tabs_and_buttons_in_english(started, preview):
    server, folder = started
    store_language(folder, "en")

    status, body = page(server)

    assert status == 200
    assert [text for text in JOBS_EN if text not in body] == []
    assert [text for text in JOBS_DE if text in body] == []


def test_the_jobs_page_stays_german_byte_for_byte_with_the_preview_off(started, no_preview):
    server, folder = started
    store_language(folder, "fr")

    status, body = page(server)

    assert (status, body) == (200, jobs_page(server))
    assert [text for text in JOBS_DE if text not in body] == []


def test_the_page_its_scripts_and_its_route_modules_are_finished():
    finished = {str(path.relative_to(sprachen_pruefen.BASE)) for path in sprachen_pruefen.FERTIG
                if path.is_relative_to(sprachen_pruefen.BASE)}

    assert set(PAGE_FILES) | set(ROUTE_FILES) <= finished


def test_the_page_its_scripts_and_its_route_modules_have_no_gap():
    catalog = translation_catalog.load(translation_catalog.CATALOG_DIR)
    files = [sprachen_pruefen.BASE / name for name in (*PAGE_FILES, *ROUTE_FILES)]

    assert [str(gap) for gap in sprachen_pruefen.gaps(files, catalog)] == []


# The list and what it says about the search


def test_the_hint_about_the_profile_comes_in_the_app_language_and_still_leads_to_its_field(started, preview):
    server, folder = started

    store_language(folder, "fr")
    french = request(server, "GET", "/api/suche/liste")[1]
    store_language(folder, "en")
    english = request(server, "GET", "/api/suche/liste")[1]

    assert french["hinweise"] == ["Recherche dans toute la Suisse, les offres proches du domicile en premier. "
                                  f"Pour limiter{NBSP}: choisir des cantons."]
    assert english["hinweise"] == ["Searching all of Switzerland, jobs near the home first. To narrow it down: choose cantons."]
    assert french["hinweis_felder"] == english["hinweis_felder"] == [search_plan.FIELD_CANTONS]


def test_the_search_window_comes_in_the_app_language(started, preview):
    server, folder = started

    store_language(folder, "fr")
    french = request(server, "GET", "/api/suche/liste")[1]["zeitraum"]["zeile"]
    store_language(folder, "en")
    english = request(server, "GET", "/api/suche/liste")[1]["zeitraum"]["zeile"]

    assert french == "La première recherche prend les annonces des 21 derniers jours."
    assert english == "The first search takes ads from the last 21 days."


def test_why_a_search_cannot_start_comes_in_the_app_language(started, preview):
    server, folder = started
    (folder / search_plan.PROFILE).unlink()
    store_language(folder, "en")

    answer = request(server, "GET", "/api/suche/liste")[1]

    assert answer["sperrgrund"] == "Complete My details first."
    assert answer["hinweise"] == []


def test_the_announcement_of_a_long_run_comes_in_the_app_language():
    plan = search_plan.chosen(search_plan.parse(long_profile()), ["job-room", "jobscout24", "ictjobs"]).as_dict()
    text = search_stages.size(plan)["text"]

    assert ui_texts.uebersetze(text, "fr") == (
        f"Cette recherche dure environ 23{NBSP}minutes{NBSP}: 193 recherches en 7 étapes, avec à chaque fois une minute "
        "de pause entre elles. De nombreuses nouvelles annonces la rallongent.")
    assert ui_texts.uebersetze(text, "en") == (
        f"This search takes about 23{NBSP}minutes: 193 searches in 7 stages, with a pause of one minute between them. "
        "Many new ads make it longer.")


def test_the_list_says_all_this_in_german_with_the_preview_off(started, no_preview):
    server, folder = started
    store_language(folder, "fr")

    answer = request(server, "GET", "/api/suche/liste")[1]

    assert answer["hinweise"] == [search_plan.NATIONWIDE_NOTE]
    assert answer["hinweis_felder"] == [search_plan.FIELD_CANTONS]
    assert answer["zeitraum"]["zeile"] == "Die erste Suche nimmt Inserate der letzten 21 Tage."


# The refusals of the routes


def test_rating_a_hit_without_its_ad_is_refused_in_french_and_english(started, preview):
    server, folder = started
    wanted = hit_ids(server)["Datenanalystin"]

    store_language(folder, "fr")
    assert request(server, "POST", f"/api/suche/bewerten?id={wanted}", {}) == (400, {"fehler": (
        "Le texte de l'annonce manque pour ce résultat. Merci d'ouvrir l'annonce et de saisir l'offre manuellement.")})
    store_language(folder, "en")
    assert request(server, "POST", f"/api/suche/bewerten?id={wanted}", {}) == (400, {"fehler": (
        "The ad text is missing for this result. Please open the ad and add the job by hand.")})


def test_saving_a_hit_twice_is_refused_in_the_app_language(started, preview):
    server, folder = started
    wanted = hit_ids(server)["Datenanalyst"]
    assert request(server, "POST", f"/api/suche/uebernehmen?id={wanted}", {})[0] == 200

    store_language(folder, "fr")
    assert request(server, "POST", f"/api/suche/uebernehmen?id={wanted}", {}) == (
        400, {"fehler": "Ce résultat est déjà dans vos candidatures."})
    store_language(folder, "en")
    assert request(server, "POST", f"/api/suche/verwerfen?id={wanted}", {}) == (
        400, {"fehler": "This result is already in your applications."})


def test_a_grade_out_of_the_list_and_an_unknown_place_are_refused_in_the_app_language(started, preview):
    server, folder = started

    store_language(folder, "fr")
    assert request(server, "GET", "/api/suche/ab-note?note=7") == (
        400, {"fehler": "La note doit être comprise entre 1 et 6, par demi-points."})
    store_language(folder, "en")
    assert request(server, "POST", "/api/suche/haken-ausschluss/rueckgaengig", {"art": "irgendwo", "wert": "Verkauf"}) == (
        400, {"fehler": "Please choose “In the title” or “In the ad”."})


def test_the_refusals_stay_german_with_the_preview_off(started, no_preview):
    server, folder = started
    store_language(folder, "fr")
    wanted = hit_ids(server)["Datenanalystin"]

    assert request(server, "POST", f"/api/suche/bewerten?id={wanted}", {})[1]["fehler"] == (
        "Für diesen Treffer fehlt der Text des Inserats. Bitte das Inserat öffnen und die Stelle von Hand erfassen.")
    assert request(server, "GET", "/api/suche/ab-note?note=7")[1]["fehler"] == (
        "Die Note muss zwischen 1 und 6 liegen, in halben Schritten.")


# The wording of the UI/UX rulings on #416 to #421 that this page reuses.
REVIEWED = {
    "Jetzt suchen": ("Rechercher maintenant", "Search now"),
    "Neu bewerten": ("Réévaluer", "Rate again"),
    "Bewerten": ("Évaluer", "Rate"),
    "Bewerbung vorbereiten": ("Préparer la candidature", "Prepare application"),
    "Merken": ("Mettre de côté", "Save"),
    "Im Titel": ("Dans le titre", "In the title"),
    "Neu": ("Nouvelles", "New"),
    "Alle prüfen": ("Tout évaluer", "Rate all"),
    "noch keine Note": ("sans note", "unrated"),
}


@pytest.mark.parametrize("german", REVIEWED)
def test_the_reviewed_wording_is_in_the_catalog(german):
    catalog = translation_catalog.load(translation_catalog.CATALOG_DIR)

    assert (catalog.text(german, "fr"), catalog.text(german, "en")) == REVIEWED[german]
