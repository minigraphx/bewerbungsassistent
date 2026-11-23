"""The page Bewerbungen and the status names in French and English (#420, G10, docs/design/sprachen.md).

With the preview on and French or English as the app language, the list of applications comes with its headings,
views, filters and buttons in that language, and the routes it calls answer in it. With the preview off it all stays
German, byte for byte. Every stage the register stores has a name in fr and en, while the stored value stays German.
The real catalog in bewerbungen/sprachen/ is used, so these tests also prove its entries.
"""
import re
import threading

import pytest

import app
import language_sources
import register
import server as server_module
import sprachen_pruefen
import translation_catalog
from test_today_languages import connect, no_preview, preview, request, store_language  # noqa: F401  (fixtures)

PAGE = "/bewerbungen"
NBSP = chr(0xA0)
REGISTER = """\
- id: muster-ag-planer
  firma: Muster AG
  stelle: Planer:in
  status: Bewerben
  eingetragen_am: '2026-11-01'
  link: https://www.example.org/stelle/1
  versand:
    datum: '2026-11-02'
"""
# Title, views, the search, column heads, the bulk bar, the dialog to enter a job and the pass, as the server sends them.
APPLICATIONS_FR = ("<title>Candidatures</title>", '<h1 id="titel">Candidatures</h1>', "Mises de côté", "Envoyées",
                   "Terminées", "Toutes", "Rechercher", "Saisir une offre manuellement",
                   "Aucune candidature ne correspond à cette recherche.", "Tout sélectionner dans cette vue", "Statut",
                   "Échéance", "Ajoutée", "Écarter les cochées", "Cocher d'abord des candidatures.", "Autre statut…",
                   "Définir le statut", "Créer", "Annuler", "Terminer le tri", "Postuler")
APPLICATIONS_EN = ("<title>Applications</title>", '<h1 id="titel">Applications</h1>', "Saved", "Applied", "Closed",
                   "All", "Search", "Add a job by hand", "No application matches this search.",
                   "Select all in this view", "Status", "Due", "Added", "Discard ticked", "Tick applications first.",
                   "Other status…", "Set status", "Create", "Cancel", "End review", "Apply")
APPLICATIONS_DE = ("Angehakte verwerfen", "Zuerst Bewerbungen anhaken.", "Bis wann", "Erfasst", "Stand setzen",
                   "Anderer Stand …", ">Anlegen<", ">Gemerkt<", ">Bewerben<", ">Suchen<")
PAGE_FILES = ("seiten/bewerbungen.html", "seiten/bewerbungen-logic.js", "seiten/wieder-logik.js", "seiten/bewerbungen.js")
ROUTE_FILES = ("routen_bewerbungen.py", "register.py", "routes_apply.py", "routes_rav.py")
STATUS_SETS = re.compile(r"const STATUS_SETS = \{(.*?)\};", re.S)
STATUS_SET = re.compile(r'"?([^\s",:{}]+)"?:\s*"(status\.[\w-]+)"')


@pytest.fixture
def started(tmp_path):
    """The app on a data folder with one invented application that went out already."""
    folder = tmp_path / "daten"
    folder.mkdir()
    (folder / "bewerbungen.yaml").write_text(REGISTER, encoding="utf-8")
    server = app.erstelle_server(folder, tmp_path / "build")
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
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


def applications_page(server) -> str:
    """The page as the server sends it in German: its token filled in and the links the server hides taken out."""
    html = (server_module.SEITEN / app.SEITEN[PAGE]).read_text(encoding="utf-8").replace("__TOKEN__", server.token)
    for link in server.hidden_links:
        html = html.replace(link, "")
    return html


def status_sets() -> dict[str, str]:
    """The stored stage -> its text set, as texte.js names them in STATUS_SETS."""
    block = STATUS_SETS.search(language_sources.TEXTE_JS.read_text(encoding="utf-8"))
    assert block, "texte.js has no STATUS_SETS"
    return dict(STATUS_SET.findall(block[1]))


# The page


def test_the_applications_page_shows_its_headings_and_filters_in_french(started, preview):
    server, folder = started
    store_language(folder, "fr")

    status, body = page(server)

    assert status == 200
    assert '<html lang="fr">' in body
    assert [text for text in APPLICATIONS_FR if text not in body] == []
    assert [text for text in APPLICATIONS_DE if text in body] == []


def test_the_applications_page_shows_its_headings_and_filters_in_english(started, preview):
    server, folder = started
    store_language(folder, "en")

    status, body = page(server)

    assert status == 200
    assert [text for text in APPLICATIONS_EN if text not in body] == []
    assert [text for text in APPLICATIONS_DE if text in body] == []


def test_the_applications_page_stays_german_byte_for_byte_with_the_preview_off(started, no_preview):
    server, folder = started
    store_language(folder, "fr")

    status, body = page(server)

    assert (status, body) == (200, applications_page(server))
    assert [text for text in APPLICATIONS_DE if text not in body] == []


def test_the_page_its_scripts_and_its_route_modules_are_finished():
    finished = {str(path.relative_to(sprachen_pruefen.BASE)) for path in sprachen_pruefen.FERTIG
                if path.is_relative_to(sprachen_pruefen.BASE)}

    assert set(PAGE_FILES) | set(ROUTE_FILES) <= finished


# The routes it calls


def test_a_job_entered_without_a_company_is_refused_in_french_and_english(started, preview):
    server, folder = started
    store_language(folder, "fr")
    assert request(server, "POST", "/api/bewerbung/neu", {"firma": " ", "stelle": "Planer:in"}) == (
        400, {"fehler": "Indiquer l'entreprise et le poste"})

    store_language(folder, "en")
    assert request(server, "POST", "/api/bewerbung/neu", {"firma": " ", "stelle": "Planer:in"}) == (
        400, {"fehler": "Enter the company and the job"})


def test_why_an_application_cannot_be_opened_comes_in_the_app_language(started, preview):
    server, folder = started
    store_language(folder, "en")

    status, answer = request(server, "GET", "/api/bewerben/auswahl")

    assert (status, answer["bewerbungen"]) == (200, [{"id": "muster-ag-planer", "grund": "Already sent"}])


def test_the_routes_of_the_page_stay_german_with_the_preview_off(started, no_preview):
    server, folder = started
    store_language(folder, "fr")

    assert request(server, "POST", "/api/bewerbung/neu", {"firma": " ", "stelle": "Planer:in"}) == (
        400, {"fehler": "firma und stelle angeben"})
    assert request(server, "GET", "/api/bewerben/auswahl")[1]["bewerbungen"][0]["grund"] == "Schon versendet"


def test_the_stored_stages_stay_german_in_every_language(started, preview):
    server, folder = started
    store_language(folder, "fr")

    status, answer = request(server, "GET", "/api/bewerbungen")

    assert status == 200
    assert answer["status"] == list(register.STATUS)
    assert answer["bewerbungen"][0]["status"] == "Bewerben"


# The status names


def test_every_stored_stage_has_a_text_set_in_texte_js():
    sets = status_sets()
    known = language_sources.text_sets()

    assert [stage for stage in register.STATUS if stage not in sets] == []
    assert [key for key in sets.values() if key not in known] == []


def test_every_stored_stage_has_a_name_in_french_and_english():
    catalog = translation_catalog.load(translation_catalog.CATALOG_DIR)
    sets = status_sets()

    missing = [(stage, language) for stage in register.STATUS for language in ("fr", "en")
               if not catalog.form(sets.get(stage, ""), language, "sie")]

    assert missing == []
    assert catalog.form(sets["Absage"], "fr", "du")
