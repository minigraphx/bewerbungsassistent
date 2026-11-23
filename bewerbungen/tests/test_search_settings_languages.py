"""Suche einstellen, part A, in French and English (#424, G10, docs/design/sprachen.md).

With the preview on and French or English as the app language, the page Suche einstellen comes with its headings,
labels, hints and buttons in that language, and the routes behind its cards answer in it: the terms, the region and
workload, the time window, the portals, the offers and the place notices. With the preview off all stays German, byte
for byte. The grammar of the search profile stays German in every language: Keywords, «Nur …», «(nur mit …)»,
«(ganzes Wort)», «Nischen (ohne Ort suchen)», portals, cantons and places. What the scripts of part A say at run time is
tested in tests/search_settings_languages.test.cjs; the cards of part B follow with #425. All data is invented.
"""
import threading

import pytest

import app
import jobscout24_regions
import place_notices
import search_plan
import server as server_module
import sprachen_pruefen
import translation_catalog
from test_today_languages import connect, no_preview, preview, request, store_language  # noqa: F401  (fixtures)

PAGE = "/suche-einstellen"
NBSP = chr(0xA0)
PROFILE = """# Suchprofil

## Region
- Kantone (job-room): AG
- Orte (jobs.ch): Aarau, Baden
- PLZ (jobscout24): 5000

## Keywords
- Kernliste: Kursplaner, Berufsbildner (nur mit Informatik, ICT)
- Nischen (ohne Ort suchen): Lernatelier
- Nur job-room: Datenpfleger
- Nur beispielportal.ch: Lernbegleiter

## Titelfilter
- Ausschluss: Praktikum
"""
# Headings, labels, hints and buttons as the server sends them; a text set in its Sie form.
SETTINGS_FR = ("<title>Régler la recherche</title>", "› Régler la recherche", "Voici comment l'app cherche aujourd'hui.",
               f"Quelles offres vous correspondent{NBSP}?", f"Que cherches-tu{NBSP}?",
               "Places d'apprentissage et stages d'orientation", "Recherches en double", ">Ajouter<",
               "Lieux propres à chaque portail", "les substituts comme {{NAME}}",
               f"Pour les deux listes, un terme correspond aussi au début ou à la fin d'un mot{NBSP}: ",
               f"Qu'est-ce qui est envoyé à l'IA{NBSP}?", "Voir le texte", "Région et taux d'activité", ">Région<",
               ">Niches<", ">Taux d'activité<", ">Domicile<", ">Cantons<", "Lieux pour jobs.ch, un par ligne",
               f"Aucune choisie{NBSP}: jobscout24 cherche aux NPA ci-dessous.", "Rayon autour du domicile", ">Enregistrer<",
               "Ce qu'a retiré le filtre de titre", "Pas maintenant", f"Où cherchez-vous{NBSP}?", ">Portails<",
               "Rechercher sur d'autres sites", f"Exemple{NBSP}:", ">Période<", "Annonces de moins de", "État des portails",
               ">Filtre de titre<", f"écrivez «{NBSP}(ganzes Wort){NBSP}» après", f"«{NBSP}Sales (ganzes Wort){NBSP}»",
               "Évaluer automatiquement les nouveaux résultats après la recherche", "Chercher dans l'onglet visible",
               "Texte envoyé à l'IA", "{{NAME}}", ">Rechercher maintenant<")
SETTINGS_EN = ("<title>Set up search</title>", "› Set up search", "This is how the app searches today.",
               "Which jobs suit you?", "What are you looking for?", "Apprenticeships and trial apprenticeships",
               "Searched twice", ">Places per portal<", ">Add<", "What goes to the AI?", "View the text", "Region and workload", ">Workload<",
               ">Place of residence<", "Places for jobs.ch, one per line",
               "None chosen: jobscout24 searches at the postcodes below.", ">Save<", "What the title filter filtered out",
               "Not now", "Where do you search?", ">Portals<", "Search other sites", "Example:", ">Time window<",
               "Ads from the last", "Status of the portals", ">Title filter<", "write “(ganzes Wort)” after it",
               "Rate new results automatically after the search", "Search in the visible tab", "Text sent to the AI",
               ">Search now<")
SETTINGS_DE = ("So sucht die App heute", "Was suchst du?", "Doppelt gesucht", ">Aufnehmen<", "Was geht an die KI?",
               "Text ansehen", "Region und Pensum", ">Wohnort<", ">Kantone<", "Orte für jobs.ch", "Umkreis um den Wohnort",
               ">Speichern<", "Was der Titelfilter aussortiert hat", "Nicht jetzt", "Wo suchen Sie?",
               "Weitere Seiten durchsuchen", "Inserate der letzten", "Stand der Portale", ">Titelfilter<", ">Ablauf<",
               "Im sichtbaren Tab suchen", "Text an die KI", ">Jetzt suchen<")
PAGE_FILES = ("seiten/suche-einstellen.html", "seiten/suche-einstellen.js", "seiten/suchliste-logik.js", "seiten/suchliste.js",
              "seiten/portal-wahl.js", "seiten/zeitfenster.js", "seiten/suche-rahmen-logik.js", "seiten/suche-rahmen.js",
              "seiten/orte-hinweise.js", "seiten/beruf-vorschlag.js")
# The modules behind /api/beruf/*, /api/suche/angebot, /einstellungen, /liste, /orte-hinweise*, /rahmen and
# /zeitfenster; routes_search.py and routes_frame.py are finished already (#416, #422).
ROUTE_FILES = ("routes_career.py", "ai/career.py", "search_terms.py", "routes_window.py", "routes_place_notices.py",
               "place_notices.py", "search_frame.py", "portal_places.py", "search_plan.py", "routes_frame.py")


@pytest.fixture
def started(tmp_path):
    """The app on a data folder with an invented job search profile."""
    folder = tmp_path / "daten"
    folder.mkdir()
    (folder / search_plan.PROFILE).write_text(PROFILE, encoding="utf-8")
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


def settings_page(server) -> str:
    """The page as the server sends it in German: its token filled in and the links the server hides taken out."""
    html = (server_module.SEITEN / app.SEITEN[PAGE]).read_text(encoding="utf-8").replace("__TOKEN__", server.token)
    for link in server.hidden_links:
        html = html.replace(link, "")
    return html


def refused(server, path: str, body: dict) -> str:
    status, answer = request(server, "POST", path, body)
    assert status == 400, answer
    return answer["fehler"]


def profile_of(folder) -> str:
    return (folder / search_plan.PROFILE).read_text(encoding="utf-8")


# The page


def test_the_search_settings_page_shows_its_headings_labels_and_buttons_in_french(started, preview):
    server, folder = started
    store_language(folder, "fr")

    status, body = page(server)

    assert status == 200
    assert '<html lang="fr">' in body
    assert [text for text in SETTINGS_FR if text not in body] == []
    assert [text for text in SETTINGS_DE if text in body] == []


def test_the_search_settings_page_shows_its_headings_labels_and_buttons_in_english(started, preview):
    server, folder = started
    store_language(folder, "en")

    status, body = page(server)

    assert status == 200
    assert [text for text in SETTINGS_EN if text not in body] == []
    assert [text for text in SETTINGS_DE if text in body] == []


def test_the_search_settings_page_stays_german_byte_for_byte_with_the_preview_off(started, no_preview):
    server, folder = started
    store_language(folder, "fr")

    status, body = page(server)

    assert (status, body) == (200, settings_page(server))
    assert [text for text in SETTINGS_DE if text not in body] == []


def test_the_page_its_scripts_and_its_route_modules_are_finished():
    finished = {str(path.relative_to(sprachen_pruefen.BASE)) for path in sprachen_pruefen.FERTIG
                if path.is_relative_to(sprachen_pruefen.BASE)}

    assert set(PAGE_FILES) | set(ROUTE_FILES) <= finished


def test_the_page_its_scripts_and_its_route_modules_have_no_gap():
    catalog = translation_catalog.load(translation_catalog.CATALOG_DIR)
    files = [sprachen_pruefen.BASE / name for name in (*PAGE_FILES, *ROUTE_FILES)]

    assert [str(gap) for gap in sprachen_pruefen.gaps(files, catalog)] == []


# The terms: adding, removing, Rückgängig, the order and the suggestions of the AI (without calling it)


def test_adding_and_removing_terms_is_refused_in_french(started, preview):
    server, folder = started
    store_language(folder, "fr")

    assert refused(server, "/api/beruf/aufnehmen", {"beruf": " "}) == "Merci de saisir un mot-clé."
    assert refused(server, "/api/beruf/aufnehmen", {"beruf": "Kursplaner"}) == f"«{NBSP}Kursplaner{NBSP}» est déjà recherché."
    assert refused(server, "/api/beruf/aufnehmen", {"beruf": "Kurs (nur mit"}) == "Cela ne convient pas comme mot-clé."
    assert refused(server, "/api/beruf/entfernen", {}) == f"Quelle entrée faut-il retirer{NBSP}?"
    assert refused(server, "/api/beruf/rueckgaengig", {"beruf": "Kursplaner", "vorher": "x"}) == (
        "Il n'est plus possible d'annuler ici. Merci d'ajouter à nouveau le terme.")
    assert refused(server, "/api/beruf/reihenfolge", {"berufe": "Kursplaner"}) == (
        "Cet ordre n'est pas possible. Merci de recharger la page.")
    assert refused(server, "/api/beruf/vorschlag", {}) == (
        f"Merci d'écrire quelque chose aux deux{NBSP}: intérêts et compétences.")
    assert refused(server, "/api/beruf/vorschlag", {"interessen": 5}) == "Intérêts et points forts attendus."
    assert refused(server, "/api/beruf/vorschlag", {"interessen": "x" * 1001}) == (
        "Merci de ne pas dépasser 1000 caractères par champ.")


def test_adding_and_removing_terms_is_refused_in_english(started, preview):
    server, folder = started
    store_language(folder, "en")

    assert refused(server, "/api/beruf/aufnehmen", {"beruf": " "}) == "Please enter a search term."
    assert refused(server, "/api/beruf/aufnehmen", {"beruf": "Kursplaner"}) == "“Kursplaner” is already being searched."
    assert refused(server, "/api/beruf/aufnehmen", {"beruf": "Kurs (nur mit"}) == "That does not work as a search term."
    assert refused(server, "/api/beruf/entfernen", {}) == "Which entry should go?"
    assert refused(server, "/api/beruf/rueckgaengig", {"beruf": "Kursplaner", "vorher": "x"}) == (
        "Undo is no longer possible here. Please add the term again.")
    assert refused(server, "/api/beruf/reihenfolge", {"berufe": "Kursplaner"}) == (
        "This order does not work. Please reload the page.")
    assert refused(server, "/api/beruf/vorschlag", {}) == "Please write something for both: interests and abilities."
    assert refused(server, "/api/beruf/vorschlag", {"interessen": "x" * 1001}) == (
        "Please use at most 1000 characters per field.")


def test_a_term_that_is_too_long_names_its_start_in_the_app_language(started, preview):
    server, folder = started
    store_language(folder, "fr")
    french = refused(server, "/api/beruf/aufnehmen", {"beruf": "Kursleiterin " * 30})
    store_language(folder, "en")
    english = refused(server, "/api/beruf/aufnehmen", {"beruf": "Kursleiterin " * 30})

    # the route names the first 20 characters of the term
    assert french.startswith(f"«{NBSP}Kursleiterin Kurslei…{NBSP}» est trop long{NBSP}: ")
    assert french.endswith(" caractères au plus.")
    assert english.startswith("“Kursleiterin Kurslei…” is too long: at most ")


# The region card, the time window, the portals and the offers


def test_the_region_card_refuses_in_french_with_the_names_of_its_fields(started, preview):
    server, folder = started
    store_language(folder, "fr")

    assert refused(server, "/api/suche/rahmen", {}) == "Rien à modifier."
    assert refused(server, "/api/suche/rahmen", {"umkreis_km": 10}) == (
        "Le rayon n'existe que dans la recherche de places d'apprentissage.")
    assert refused(server, "/api/suche/rahmen", {"kantone": ["XX"]}) == f"Canton inconnu{NBSP}: XX."
    assert refused(server, "/api/suche/rahmen", {"pensum": " "}) == "Merci d'indiquer le taux d'activité."
    assert refused(server, "/api/suche/rahmen", {"titel_positiv": "Kurs"}) == (
        f"Titres qui correspondent{NBSP}: merci d'envoyer une liste.")
    assert refused(server, "/api/suche/rahmen", {"plz": ["12"]}) == (
        f"«{NBSP}12{NBSP}» n'est pas un NPA{NBSP}: merci d'indiquer quatre chiffres.")
    assert refused(server, "/api/suche/rahmen", {"orte": "Aarau"}) == f"Lieux pour jobs.ch{NBSP}: merci d'envoyer une liste."
    assert refused(server, "/api/suche/rahmen", {"orte": [f"Ort{n}" for n in range(7)]}) == (
        f"Lieux pour jobs.ch{NBSP}: 6 entrées au plus.")


def test_the_region_card_refuses_in_english(started, preview):
    server, folder = started
    store_language(folder, "en")

    assert refused(server, "/api/suche/rahmen", {}) == "Nothing to change."
    assert refused(server, "/api/suche/rahmen", {"kantone": ["XX"]}) == "Unknown canton: XX."
    assert refused(server, "/api/suche/rahmen", {"pensum": " "}) == "Please give the workload."
    assert refused(server, "/api/suche/rahmen", {"regionen": ["nirgendwo"]}) == "Unknown region for ictjobs: nirgendwo."
    assert refused(server, "/api/suche/rahmen", {"wunsch": "x"}) == "Unknown field: wunsch."


def test_the_time_window_portals_and_offers_refuse_in_french_and_english(started, preview):
    server, folder = started
    every_portal = {"portale_aus": list(search_plan.PORTALS)}

    store_language(folder, "fr")
    assert refused(server, "/api/suche/zeitfenster", {"tage": 0}) == "1 à 60 jours sont possibles."
    assert refused(server, "/api/suche/einstellungen", every_portal) == (
        "Au moins un portail doit rester choisi, sinon la recherche ne trouve rien.")
    assert refused(server, "/api/suche/einstellungen", {"portale_aus": ["nirgends"]}) == (
        "Ce choix de portails n'est pas possible.")
    assert refused(server, "/api/suche/angebot", {"wahl": "x"}) == (
        "Merci de choisir places d'apprentissage, stages d'orientation ou les deux.")
    assert refused(server, "/api/suche/angebot", {"wahl": "beides"}) == (
        "Les stages d'orientation n'existent que dans la recherche de places d'apprentissage.")
    store_language(folder, "en")
    assert refused(server, "/api/suche/zeitfenster", {"tage": 0}) == "1 to 60 days are allowed."
    assert refused(server, "/api/suche/einstellungen", every_portal) == (
        "At least one portal must stay chosen, or the search finds nothing.")
    assert refused(server, "/api/suche/angebot", {"wahl": "beides"}) == "Trial apprenticeships exist only in the apprenticeship search."


def test_the_portals_say_what_they_search_in_the_app_language(started, preview):
    server, folder = started

    store_language(folder, "fr")
    french = {portal["name"]: portal["hinweis"] for portal in request(server, "GET", "/api/suche/liste")[1]["portale_wahl"]}
    store_language(folder, "en")
    english = {portal["name"]: portal["hinweis"] for portal in request(server, "GET", "/api/suche/liste")[1]["portale_wahl"]}

    assert french == {"job-room": "Offres des ORP, tous les métiers", "jobs.ch": "tous les métiers",
                      "jobscout24": "tous les métiers", "ictjobs": "informatique seulement"}
    assert english == {"job-room": "Jobs of the RAV, all occupations", "jobs.ch": "all occupations",
                       "jobscout24": "all occupations", "ictjobs": "IT only"}


# The place notices of the region card


def test_the_place_notices_speak_french_with_places_and_cantons_as_they_are(started, preview):
    server, folder = started
    store_language(folder, "fr")

    [notice] = request(server, "GET", "/api/suche/orte-hinweise")[1]["orte"]
    removed = request(server, "POST", "/api/suche/orte-hinweise/entfernen", {"ort": "Baden"})[1]
    back = request(server, "POST", "/api/suche/orte-hinweise/rueckgaengig", {"ort": "Baden", "vorher": removed["rueckgaengig"]})
    kept = request(server, "POST", "/api/suche/orte-hinweise/behalten", {"ort": "Baden"})

    assert notice["text"].startswith("Aarau et Baden se trouvent dans le même canton, Aargau. ")
    assert notice["text"].endswith(" recherches par série de recherches.")
    assert (notice["ort"], notice["knopf"], notice["behalten"]) == ("Baden", "Retirer Baden", "Conserver")
    assert removed["text"].startswith("Baden retiré. jobs.ch cherche toujours dans tout le canton (Aargau), ")
    assert back == (200, {"text": "Baden est de nouveau parmi les lieux pour jobs.ch."})
    assert kept == (200, {"text": "Baden reste parmi les lieux pour jobs.ch."})
    assert refused(server, "/api/suche/orte-hinweise/entfernen", {}) == (
        "Cette remarque ne vaut plus. La page montre maintenant ce qui figure dans le profil de recherche.")
    assert refused(server, "/api/suche/orte-hinweise/rueckgaengig", {"ort": "Baden"}) == "Il n'est plus possible d'annuler cela."


def test_a_place_that_costs_one_search_says_so_in_the_singular(started, preview):
    catalog = translation_catalog.load(translation_catalog.CATALOG_DIR)
    one = PROFILE.replace("Kursplaner, Berufsbildner (nur mit Informatik, ICT)", "Kursplaner").replace(
        "- Nischen (ohne Ort suchen): Lernatelier\n- Nur job-room: Datenpfleger\n- Nur beispielportal.ch: Lernbegleiter\n", "")

    [notice] = place_notices.notices(one, None, [], [])["orte"]
    removal = place_notices.removal(one, "Baden", None, [])

    assert notice["text"].endswith("Baden kostet 1 Suche pro Suchlauf.")
    assert notice["text"].in_language(catalog, "fr").endswith("Baden coûte 1 recherche par série de recherches.")
    assert notice["text"].in_language(catalog, "en").endswith("Baden costs 1 search per search run.")
    assert removal.done.in_language(catalog, "en") == (
        "Baden removed. jobs.ch keeps searching the whole canton of Aargau, and the next search run saves 1 search.")


def test_the_place_notices_say_postcodes_and_regions_in_english(started, preview):
    catalog = translation_catalog.load(translation_catalog.CATALOG_DIR)
    several = PROFILE.replace("- PLZ (jobscout24): 5000", "- PLZ (jobscout24): 5000, 5400")

    found = place_notices.notices(several, None, [], [])["plz"]

    assert found["text"].in_language(catalog, "en") == (
        "jobscout24 searches at 2 postcodes, each with a 20 km radius; nearby postcodes often find the same jobs. "
        "With a region, jobscout24 searches once per term.")
    assert found["knopf"].in_language(catalog, "fr") == "Choisir des régions"


# The grammar of the search profile stays German in every language


def test_the_grammar_of_the_profile_stays_german_in_french_and_english(started, preview):
    server, folder = started
    region = next(iter(jobscout24_regions.NAMES.values()))

    store_language(folder, "fr")
    assert request(server, "POST", "/api/suche/einstellungen", {"portale_aus": ["job-room"]})[0] == 200
    assert request(server, "POST", "/api/beruf/aufnehmen", {"beruf": "Datenanalyst (nur mit SQL)"})[0] == 200
    assert request(server, "POST", "/api/suche/rahmen", {"titel_ausschluss": ["Praktikum", "Sales (ganzes Wort)"],
                                                         "regionen_jobscout24": [region]})[0] == 200
    listed = request(server, "GET", "/api/suche/liste")[1]
    frame = request(server, "GET", "/api/suche/rahmen")[1]
    store_language(folder, "en")
    english = request(server, "GET", "/api/suche/liste")[1]["portal_hinweise"]

    profile = profile_of(folder)
    assert "- Kernliste: Kursplaner, Berufsbildner (nur mit Informatik, ICT), Datenanalyst (nur mit SQL)\n" in profile
    assert "- Nischen (ohne Ort suchen): Lernatelier\n- Nur job-room: Datenpfleger\n" in profile
    assert "- Ausschluss: Praktikum, Sales (ganzes Wort)\n" in profile
    assert listed["portal_hinweise"] == [
        f"La ligne «{NBSP}Nur beispielportal.ch: …{NBSP}» nomme un portail que l'app ne connaît pas. "
        "Elle cherche donc ses termes sur tous les portails.",
        f"«{NBSP}Datenpfleger{NBSP}» n'est recherché que sur job-room, et job-room est désactivé. "
        "Le terme ne figure donc dans aucune recherche."]
    assert english == ["The line “Nur beispielportal.ch: …” names a portal the app does not know. "
                       "So it searches its terms on all portals.",
                       "“Datenpfleger” is searched only on job-room, and job-room is switched off. So the term runs in no search."]
    assert {"begriff": "Berufsbildner", "woerter": ["Informatik", "ICT"]} in listed["begriff_pflicht"]
    assert frame["werte"]["titel_ausschluss"] == ["Praktikum", "Sales (ganzes Wort)"]
    assert {"portal": "jobscout24", "vorsatz": "Régions", "orte": [region]} in frame["orte_pro_portal"]
    assert {"portal": "jobs.ch", "orte": ["Aarau", "Baden"]} in frame["orte_pro_portal"]


def test_the_refusals_and_hints_stay_german_with_the_preview_off(started, no_preview):
    server, folder = started
    store_language(folder, "fr")

    assert refused(server, "/api/suche/rahmen", {}) == "Nichts zu ändern."
    assert refused(server, "/api/beruf/aufnehmen", {"beruf": "Kursplaner"}) == "„Kursplaner“ wird schon gesucht."
    assert refused(server, "/api/suche/zeitfenster", {"tage": 0}) == "Erlaubt sind 1 bis 60 Tage."
    assert refused(server, "/api/suche/rahmen", {"orte": [f"Ort{n}" for n in range(7)]}) == (
        "Orte für jobs.ch: höchstens 6 Einträge.")
    [notice] = request(server, "GET", "/api/suche/orte-hinweise")[1]["orte"]
    assert notice["text"].startswith("Aarau und Baden liegen beide im Kanton Aargau.")


# The wording of the UI/UX rulings on #416 to #423 that this page reuses, and the names the brief fixes.
REVIEWED = {
    "Jetzt suchen": ("Rechercher maintenant", "Search now"),
    "Zeitfenster": ("Période", "Time window"),
    "Rückgängig": ("Annuler", "Undo"),
    "Aufnehmen": ("Ajouter", "Add"),
    "Behalten": ("Conserver", "Keep"),
    "Titelfilter": ("Filtre de titre", "Title filter"),
    "Stellen": ("Offres", "Jobs"),
    "1 Suche": ("1 recherche", "1 search"),
}


@pytest.mark.parametrize("german", REVIEWED)
def test_the_reviewed_wording_is_in_the_catalog(german):
    catalog = translation_catalog.load(translation_catalog.CATALOG_DIR)

    assert (catalog.text(german, "fr"), catalog.text(german, "en")) == REVIEWED[german]
