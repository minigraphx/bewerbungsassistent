"""The page Firmen in French and English (#423, G10, docs/design/sprachen.md).

With the preview on and French or English as the app language, the page Firmen comes with its headings, filters,
table heads and dialogs in that language, and the routes it calls answer in it: a link that is not a kununu page, a
company that was not among the choices, a reading of the extension that does not fit and a missing field. With the
preview off all stays German, byte for byte. What firmen.js says at run time is tested in
tests/companies_page_languages.test.cjs. Company names are data and stay as they are; all companies are invented.
"""
import threading

import pytest

import app
import excluded_companies
import search_plan
import server as server_module
import sprachen_pruefen
import translation_catalog
from test_today_languages import connect, no_preview, preview, request, store_language  # noqa: F401  (fixtures)

PAGE = "/firmen"
NBSP = chr(0xA0)
PROFILE = "# Suchprofil\n\n## Keywords\n- Kernliste: Datenanalyst\n"
HIT = {"portal": "jobs.ch", "portal_id": "abc-1", "stelle": "Datenanalyst", "firma": "Muster AG", "ort": "Bern",
       "pensum": "80 %", "link": "https://www.jobs.ch/de/stellenangebote/detail/abc-1/", "alter_tage": 2,
       "text": "SQL, Python."}
KEY = excluded_companies.key_of("Muster AG")
# Title, filters, the search field, the help, the table heads, the source line and both dialogs, as the server sends them.
COMPANIES_FR = ("<title>Entreprises</title>", '<h1 id="titel" data-text="nav.stellen">Offres</h1>',
                'aria-label="Afficher les entreprises"', "Avec de nouveaux résultats", "Avec candidature", "À clarifier",
                'placeholder="Chercher une entreprise"', f"Comment lire kununu{NBSP}?", "Résultats et candidatures",
                ">Vérification<", ">Actions<",
                f"Avis{NBSP}: kununu, état au jour indiqué. Ils proviennent du personnel, pas de l'app.",
                "Sur kununu, le personnel actuel et ancien évalue son entreprise", "Lien vers l'entreprise sur kununu",
                ">Associer<", "Valeur et nombre tels qu'indiqués sur kununu.", "Valeur de 1 à 5", "Nombre d'avis",
                ">Ajouter<", ">Annuler<", "Aucune entreprise ne correspond à cette recherche.")
COMPANIES_EN = ("<title>Companies</title>", '<h1 id="titel" data-text="nav.stellen">Jobs</h1>', 'aria-label="Show companies"',
                "With new results", "With application", "To clarify", 'placeholder="Search for a company"',
                "How do I read kununu?", "Results and applications", ">Checked<", ">Actions<",
                "Reviews: kununu, as of the date shown.", "Link to the company on kununu", ">Assign<",
                "Value and number as shown on kununu.", "Value from 1 to 5", "Number of reviews", ">Add<", ">Cancel<",
                "No company matches this search.")
COMPANIES_DE = ("Mit neuen Treffern", "Zu klären", "Firma suchen", "Wie lese ich kununu?", "Treffer und Bewerbungen",
                ">Geprüft<", ">Zuordnen<", "Wert von 1 bis 5", "Anzahl Bewertungen", ">Eintragen<", ">Abbrechen<",
                "Keine Firma passt zu dieser Suche.")
PAGE_FILES = ("seiten/firmen.html", "seiten/firmen.js", "seiten/stellen-reiter.js")
# The modules behind the routes of the page; /api/suche/liste for the tab counts is in routes_search.py (#422).
ROUTE_FILES = ("routes_companies.py", "companies.py")


@pytest.fixture
def started(tmp_path):
    """The app on a data folder with a search profile and one invented hit, so one company has a row."""
    folder = tmp_path / "daten"
    folder.mkdir()
    (folder / search_plan.PROFILE).write_text(PROFILE, encoding="utf-8")
    server = app.erstelle_server(folder, tmp_path / "build")
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    assert request(server, "POST", "/api/suche/treffer", {"treffer": [HIT]})[0] == 200
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


def companies_page(server) -> str:
    """The page as the server sends it in German: its token filled in and the links the server hides taken out."""
    html = (server_module.SEITEN / app.SEITEN[PAGE]).read_text(encoding="utf-8").replace("__TOKEN__", server.token)
    for link in server.hidden_links:
        html = html.replace(link, "")
    return html


# The page


def test_the_companies_page_shows_its_headings_filters_and_dialogs_in_french(started, preview):
    server, folder = started
    store_language(folder, "fr")

    status, body = page(server)

    assert status == 200
    assert '<html lang="fr">' in body
    assert [text for text in COMPANIES_FR if text not in body] == []
    assert [text for text in COMPANIES_DE if text in body] == []


def test_the_companies_page_shows_its_headings_filters_and_dialogs_in_english(started, preview):
    server, folder = started
    store_language(folder, "en")

    status, body = page(server)

    assert status == 200
    assert [text for text in COMPANIES_EN if text not in body] == []
    assert [text for text in COMPANIES_DE if text in body] == []


def test_the_companies_page_stays_german_byte_for_byte_with_the_preview_off(started, no_preview):
    server, folder = started
    store_language(folder, "fr")

    status, body = page(server)

    assert (status, body) == (200, companies_page(server))
    assert [text for text in COMPANIES_DE if text not in body] == []


def test_the_page_its_scripts_and_its_route_modules_are_finished():
    finished = {str(path.relative_to(sprachen_pruefen.BASE)) for path in sprachen_pruefen.FERTIG
                if path.is_relative_to(sprachen_pruefen.BASE)}

    assert set(PAGE_FILES) | set(ROUTE_FILES) <= finished


def test_the_page_its_scripts_and_its_route_modules_have_no_gap():
    catalog = translation_catalog.load(translation_catalog.CATALOG_DIR)
    files = [sprachen_pruefen.BASE / name for name in (*PAGE_FILES, *ROUTE_FILES)]

    assert [str(gap) for gap in sprachen_pruefen.gaps(files, catalog)] == []


# The refusals of the routes, with the company name as it is


def test_a_link_that_is_no_kununu_page_is_refused_in_french_and_english(started, preview):
    server, folder = started
    path = f"/api/firmen/zuordnen?firma={KEY}"

    store_language(folder, "fr")
    assert request(server, "POST", path, {"link": "https://example.org/muster"}) == (
        400, {"fehler": "Ce n'est pas un lien vers une entreprise sur kununu."})
    store_language(folder, "en")
    assert request(server, "POST", path, {"link": "https://example.org/muster"}) == (
        400, {"fehler": "That is not a link to a company on kununu."})


def test_a_company_that_was_not_among_the_choices_is_refused_in_the_app_language(started, preview):
    server, folder = started
    path = f"/api/firmen/waehlen?firma={KEY}"

    store_language(folder, "fr")
    assert request(server, "POST", path, {"link": "https://www.kununu.com/ch/muster-ag"}) == (
        400, {"fehler": "Cette entreprise ne faisait pas partie du choix. Merci de recharger la page."})
    store_language(folder, "en")
    assert request(server, "POST", path, {"link": "https://www.kununu.com/ch/muster-ag"}) == (
        400, {"fehler": "This company was not one of the choices. Please reload the page."})


def test_a_reading_that_does_not_fit_and_a_missing_field_are_refused_in_the_app_language(started, preview):
    server, folder = started

    store_language(folder, "fr")
    assert request(server, "POST", "/api/firmen/kununu", {"firma": KEY, "zustand": "irgendwas"}) == (
        400, {"fehler": "Ce que l'extension a lu sur kununu n'est pas utilisable."})
    assert request(server, "POST", "/api/firmen/wieder-zeigen", {}) == (400, {"fehler": f"Il manque{NBSP}: schluessel"})
    store_language(folder, "en")
    assert request(server, "POST", "/api/firmen/kununu", {"zustand": "gefunden"}) == (400, {"fehler": "Missing: firma"})
    assert request(server, "POST", "/api/firmen/kununu", {"firma": KEY, "zustand": "irgendwas"}) == (
        400, {"fehler": "What the extension read on kununu is not usable."})


def test_the_refusals_stay_german_with_the_preview_off(started, no_preview):
    server, folder = started
    store_language(folder, "fr")

    assert request(server, "POST", f"/api/firmen/zuordnen?firma={KEY}", {"link": "https://example.org/muster"}) == (
        400, {"fehler": "Das ist kein Link zu einer Firma bei kununu."})
    assert request(server, "POST", "/api/firmen/wieder-zeigen", {}) == (400, {"fehler": "Es fehlt: schluessel"})
    assert request(server, "POST", "/api/firmen/kununu", {"zustand": "gefunden"}) == (400, {"fehler": "Es fehlt: firma"})


def test_the_listing_keeps_the_company_name_as_data(started, preview):
    server, folder = started
    store_language(folder, "fr")

    rows = request(server, "GET", "/api/firmen")[1]["firmen"]

    assert [(row["schluessel"], row["name"], row["ort"]) for row in rows] == [(KEY, "Muster AG", "Bern")]


# The wording of the UI/UX rulings on #416 to #422 that this page reuses.
REVIEWED = {
    "Prüfen": ("Vérifier", "Check"),
    "Jetzt prüfen": ("Vérifier maintenant", "Check now"),
    "Eintragen": ("Ajouter", "Add"),
    "Abbrechen": ("Annuler", "Cancel"),
    "Neu": ("Nouvelles", "New"),
    "In Bewerbungen": ("Dans Candidatures", "In Applications"),
    "Verworfen": ("Écartées", "Discarded"),
    # the UI/UX ruling on #423
    "Mit neuen Treffern": ("Avec de nouveaux résultats", "With new results"),
    "Geprüft": ("Vérification", "Checked"),
    "Selbst zuordnen": ("Associer à la main", "Assign by hand"),
    "Bewertungen: kununu, Stand am angegebenen Tag. Sie stammen von Mitarbeitenden, nicht von der App.": (
        f"Avis{NBSP}: kununu, état au jour indiqué. Ils proviennent du personnel, pas de l'app.",
        "Reviews: kununu, as of the date shown. They come from employees, not from the app."),
    "Was die Erweiterung bei kununu gelesen hat, passt nicht.": (
        "Ce que l'extension a lu sur kununu n'est pas utilisable.", "What the extension read on kununu is not usable."),
    "Mehrere Lehrbetriebe bei kununu.": ("Plusieurs entreprises formatrices sur kununu.", "Several host companies on kununu."),
}


@pytest.mark.parametrize("german", REVIEWED)
def test_the_reviewed_wording_is_in_the_catalog(german):
    catalog = translation_catalog.load(translation_catalog.CATALOG_DIR)

    assert (catalog.text(german, "fr"), catalog.text(german, "en")) == REVIEWED[german]
