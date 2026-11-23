"""Suche einstellen, part B, and Suchbegriffe prüfen in French and English (#425, G10, docs/design/sprachen.md).

With the preview on and French or English as the app language, the page Suchbegriffe prüfen comes with its headings and
buttons in that language, and the routes behind both pages answer in it: the yield, the pairs searched twice, further
sites, the word from dismissed hits, the exclusions of the AI and the proposal of the AI on the terms. With the preview
off all stays German, byte for byte. The grammar of the search profile and what the person typed stay German in every
language. What the scripts say at run time is tested in tests/search_terms_languages.test.cjs. All data is invented;
nothing goes to the AI.
"""
import threading

import pytest

import app
import own_sites
import routes_ai
import routes_terms
import search_plan
import server as server_module
import sprachen_pruefen
import term_changes
import term_pairs
import translation_catalog
from ai import connection
from ai.errors import BAD_ANSWER, AnswerError
from test_today_languages import connect, no_preview, preview, request, store_language  # noqa: F401  (fixtures)
from ui_message import T, listing

PAGE = "/suchbegriffe"
NBSP = chr(0xA0)
STALE_ACTION = "vorschlag-veraltet"
PROFILE = """# Suchprofil

## Region
- Kantone (job-room): AG
- Orte (jobs.ch): Aarau
- PLZ (jobscout24): 5000

## Keywords
- Kernliste: Kursleiter, Lernbegleiter, Kursleiter Informatik
- Nischen (ohne Ort suchen): Kursleiter, Lernatelier
- Nur job-room: Datenpfleger

## Titelfilter
- Ausschluss: Praktikum
"""
TERMS_FR = ("<title>Vérifier les mots-clés</title>", "Retour aux résultats", ">Vérifier les mots-clés<",
            "Modifications à appliquer", "Propositions de l'IA", "Termes actuels",
            "Voici comment l'app cherchera ensuite", f"Qu'est-ce qui doit changer{NBSP}?",
            f"Par exemple{NBSP}: garder «{NBSP}Trainer{NBSP}», je donne aussi des cours pour adultes.", ">Proposer à nouveau<",
            ">Annuler<", ">Écarter<")
TERMS_EN = ("<title>Checking search terms</title>", "Back to the results", "Changes to apply", "AI proposals", "Current terms",
            "How the app searches afterwards", "What should be different?",
            "For example: keep “Trainer”, I also teach courses for adults.", ">Suggest again<", ">Cancel<", ">Discard<")
TERMS_DE = ("Zurück zu den Treffern", "Änderungen zum Übernehmen", "Vorschläge der KI", "Bisherige Begriffe",
            "So sucht die App danach", "Was soll anders sein?", "«Trainer» behalten", ">Neu vorschlagen<", ">Abbrechen<",
            ">Verwerfen<")
# Every script the two pages load, their HTML and the modules behind their fetches (#424 finished part A).
TERMS_PAGE = ("seiten/suchbegriffe.html", "seiten/texte.js", "seiten/meldungen.js", "seiten/dot-line.js", "seiten/app.js",
              "seiten/uebersicht-logik.js", "seiten/sidebar-logic.js", "seiten/sidebar.js", "seiten/einwilligung.js",
              "seiten/treffer-logik.js", "seiten/suchbegriffe-logik.js", "seiten/suchbegriffe-schalter.js",
              "seiten/suchbegriffe-gezaehlt.js", "seiten/suchbegriffe.js")
PART_B = ("seiten/suche-ertrag-logik.js", "seiten/suche-ertrag.js", "seiten/doppelt-gesucht.js", "seiten/weitere-seiten.js",
          "seiten/verworfen-woerter.js", "seiten/ki-ausschluesse-logik.js", "seiten/ki-ausschluesse.js",
          "seiten/titelfilter-logik.js", "seiten/titelfilter-beispiele.js")
ROUTE_FILES = ("search_yield.py", "routes_search_yield.py", "title_examples.py", "routes_terms.py", "term_evidence.py",
               "term_changes.py", "term_moves.py", "ai/term_review.py", "term_pairs.py", "term_pair_texts.py",
               "routes_term_pairs.py", "own_sites.py", "routes_sites.py", "ai/site_list.py", "dismissed_words.py",
               "routes_dismissed_words.py", "routes_ai_exclusions.py", "ai/exclusion_reasons.py", "rating_exclusion.py")


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


@pytest.fixture
def without_key(monkeypatch):
    """No own API key, and none is read from this computer."""
    for module in (connection, own_sites, routes_ai):
        monkeypatch.setattr(module, "own_key", lambda: None)


@pytest.fixture
def with_key(monkeypatch):
    for module in (connection, own_sites, routes_ai):
        monkeypatch.setattr(module, "own_key", lambda: "sk-ant-erfunden")


@pytest.fixture
def catalog():
    return translation_catalog.load(translation_catalog.CATALOG_DIR)


def page(server) -> tuple[int, str]:
    connection_, headers = connect(server)
    connection_.request("GET", f"/?t={server.token}", headers=headers)
    cookie = connection_.getresponse()
    cookie.read()
    connection_.request("GET", PAGE, headers={**headers, "Cookie": cookie.getheader("Set-Cookie").split(";", 1)[0]})
    answer = connection_.getresponse()
    body = answer.read().decode("utf-8")
    connection_.close()
    return answer.status, body


def terms_page(server) -> str:
    """The page as the server sends it in German: its token filled in and the links the server hides taken out."""
    html = (server_module.SEITEN / app.SEITEN[PAGE]).read_text(encoding="utf-8").replace("__TOKEN__", server.token)
    for link in server.hidden_links:
        html = html.replace(link, "")
    return html


def refused(server, path: str, body: dict) -> dict:
    status, answer = request(server, "POST", path, body)
    assert status == 400, answer
    return answer


def said(value, catalog, language: str):
    return value.in_language(catalog, language) if isinstance(value, T) else value


# The page


def test_the_terms_page_shows_its_headings_and_buttons_in_french(started, preview):
    server, folder = started
    store_language(folder, "fr")

    status, body = page(server)

    assert status == 200
    assert '<html lang="fr">' in body
    assert [text for text in TERMS_FR if text not in body] == []
    assert [text for text in TERMS_DE if text in body] == []


def test_the_terms_page_shows_its_headings_and_buttons_in_english(started, preview):
    server, folder = started
    store_language(folder, "en")

    status, body = page(server)

    assert status == 200
    assert [text for text in TERMS_EN if text not in body] == []
    assert [text for text in TERMS_DE if text in body] == []


def test_the_terms_page_stays_german_byte_for_byte_with_the_preview_off(started, no_preview):
    server, folder = started
    store_language(folder, "fr")

    status, body = page(server)

    assert (status, body) == (200, terms_page(server))
    assert [text for text in TERMS_DE if text not in body] == []


def test_every_script_of_both_pages_and_their_route_modules_are_finished():
    finished = {str(path.relative_to(sprachen_pruefen.BASE)) for path in sprachen_pruefen.FERTIG
                if path.is_relative_to(sprachen_pruefen.BASE)}
    settings = (sprachen_pruefen.BASE / "seiten/suche-einstellen.html").read_text(encoding="utf-8")
    loaded = {f"seiten/{name}" for name in __import__("re").findall(r'<script src="/([\w.-]+\.js)"', settings)}

    assert loaded - finished == set()
    assert set(TERMS_PAGE) | set(PART_B) | set(ROUTE_FILES) <= finished


def test_both_pages_their_scripts_and_their_route_modules_have_no_gap(catalog):
    files = [sprachen_pruefen.BASE / name for name in (*TERMS_PAGE, *PART_B, *ROUTE_FILES)]

    assert [str(gap) for gap in sprachen_pruefen.gaps(files, catalog)] == []


# Suchbegriffe prüfen: the routes, without the AI


def test_the_term_routes_refuse_in_french_and_english(started, preview):
    server, folder = started

    store_language(folder, "fr")
    assert refused(server, "/api/suchbegriffe/endstand", {"vorschlag": "weg"})["fehler"] == (
        "Cette proposition n'est plus valable. Merci d'en demander une nouvelle.")
    assert refused(server, "/api/suchbegriffe/rueckgaengig", {})["fehler"] == (
        f"Impossible d'annuler{NBSP}: le profil de recherche a changé depuis. L'état précédent se trouve sous Brouillons et versions.")
    assert refused(server, "/api/suchbegriffe/vorschlag", {"hinweis": "x" * 1001})["fehler"] == (
        "Merci de ne pas dépasser 1000 caractères.")
    store_language(folder, "en")
    assert refused(server, "/api/suchbegriffe/uebernehmen", {"vorschlag": "weg"})["fehler"] == (
        "This proposal is no longer valid. Please ask for a new one.")
    assert refused(server, "/api/suchbegriffe/vorschlag", {"hinweis": "x" * 1001})["fehler"] == "Please use at most 1000 characters."


def test_a_stale_proposal_names_its_action_and_says_so_in_the_app_language(started, preview):
    server, folder = started
    server.kontext.cache[routes_terms.CACHE_KEY] = ({"id": "v1", "stand": "0" * 64, "changes": (), "round": 1, "spent": 0},)
    store_language(folder, "fr")

    shown = request(server, "POST", "/api/suchbegriffe/endstand", {"vorschlag": "v1", "danach": {}})[1]
    taken = refused(server, "/api/suchbegriffe/uebernehmen", {"vorschlag": "v1", "danach": {}})

    stale = ("Proposition dépassée. Les mots-clés ont changé depuis la proposition. Merci d'en demander une nouvelle.")
    assert shown == {"veraltet": True, "meldung": stale}
    assert (taken["fehler"], taken["aktion"]) == (stale, STALE_ACTION)


def test_a_failed_proposal_says_what_it_cost_in_the_app_language(started, preview, monkeypatch):
    server, folder = started

    def failing(*args, **kwargs):
        raise AnswerError(BAD_ANSWER, cost_usd=0.03)

    monkeypatch.setattr(routes_ai, "ai_gateway", failing)
    monkeypatch.setattr(routes_terms, "currency_now", lambda: "CHF")  # as with the mediation, without reaching it
    store_language(folder, "fr")
    french = refused(server, "/api/suchbegriffe/vorschlag", {})["fehler"]
    store_language(folder, "en")
    english = refused(server, "/api/suchbegriffe/vorschlag", {})["fehler"]

    assert french.startswith("Aucune proposition. La réponse de l'IA")
    assert f" Facturé{NBSP}: CHF{NBSP}0.03. Le profil de recherche n'a pas changé." in french
    assert english.startswith("No proposal. The AI's answer")
    assert english.endswith(f" Charged: CHF{NBSP}0.03. The search profile has not changed.")


def test_a_job_search_only_check_says_so_for_an_apprenticeship(started, preview):
    server, folder = started
    (folder / search_plan.PROFILE).write_text(PROFILE + f"\n{search_plan.APPRENTICESHIP_MARK}\n", encoding="utf-8")
    store_language(folder, "en")

    assert refused(server, "/api/suchbegriffe/vorschlag", {})["fehler"] == (
        "Checking search terms is only available for the job search for now.")


def test_the_cards_of_a_proposal_speak_the_app_language_with_the_terms_as_they_are(catalog):
    add = term_changes.Change(term_changes.KEYWORDS, (), ("Datenanalyst",), "")
    replace = term_changes.Change(term_changes.POSITIVE, ("Engineer",), ("Backend", "Frontend"), "")
    two = term_changes.Change(term_changes.EXCLUDE, (), ("Verkauf", "Sales (ganzes Wort)"), "")
    drop = term_changes.Change(term_changes.KEYWORDS, ("Kursleiter", "Lernbegleiter", "Lernatelier"), (), "")
    sentences = [term_changes.sentence(change) for change in (add, replace, two, drop)]

    assert sentences == ["Suchbegriff «Datenanalyst» aufnehmen", "«Engineer» ersetzen durch Backend und Frontend",
                         "«Verkauf» und «Sales (ganzes Wort)» ausschliessen", "„Kursleiter“, „Lernbegleiter“ und „Lernatelier“ entfernen"]
    assert [said(s, catalog, "fr") for s in sentences] == [
        f"Ajouter le mot-clé «{NBSP}Datenanalyst{NBSP}»", f"Remplacer «{NBSP}Engineer{NBSP}» par Backend et Frontend",
        f"Exclure «{NBSP}Verkauf{NBSP}» et «{NBSP}Sales (ganzes Wort){NBSP}»",
        f"Retirer «{NBSP}Kursleiter{NBSP}», «{NBSP}Lernbegleiter{NBSP}» et «{NBSP}Lernatelier{NBSP}»"]
    assert [said(s, catalog, "en") for s in sentences] == [
        "Add the search term “Datenanalyst”", "Replace “Engineer” with Backend and Frontend",
        "Exclude “Verkauf” and “Sales (ganzes Wort)”", "Remove “Kursleiter”, “Lernbegleiter” and “Lernatelier”"]
    assert said(term_changes.AREA_NAMES[term_changes.EXCLUDE], catalog, "fr") == "Le titre n'en contient aucun"


def test_the_moves_of_a_proposal_speak_the_app_language(catalog):
    niche = term_changes.Change(term_changes.KEYWORDS, (), (), "", "niche", moved="Lernatelier")
    limit = term_changes.Change(term_changes.KEYWORDS, (), (), "", "portals", moved="Datenpfleger", portals=("job-room", "jobs.ch"))

    assert [said(term_changes.sentence(c), catalog, "fr") for c in (niche, limit)] == [
        f"Déplacer «{NBSP}Lernatelier{NBSP}» vers les niches (chercher sans lieu)",
        f"Ne chercher «{NBSP}Datenpfleger{NBSP}» que sur job-room, jobs.ch"]
    assert [said(term_changes.sentence(c), catalog, "en") for c in (niche, limit)] == [
        "Move “Lernatelier” to the niches (search without a place)", "Search “Datenpfleger” only on job-room, jobs.ch"]


def test_the_limits_of_a_choice_take_the_singular_for_one_and_name_the_area(catalog):
    before = term_changes.Terms(("Python",), ("Web",) * 0, ())
    one = term_changes.limits(before, term_changes.Terms(("Python",), (), ()), 1, moves=1)
    many = term_changes.limits(before, term_changes.Terms(("Python", "Daten"), tuple(f"W{n}" for n in range(32)), ()), 3)
    none = term_changes.limits(before, term_changes.Terms((), (), ()), 1)

    assert one["teile"] == ["Danach: 1 von 15 Suchbegriffen", "bis 1 Suche pro Portal"]
    assert [said(part, catalog, "fr") for part in one["teile"]] == [f"Ensuite{NBSP}: 1 mot-clé sur 15", "jusqu'à 1 recherche par portail"]
    assert [said(part, catalog, "en") for part in many["teile"]] == ["After: 2 of 15 search terms", "up to 6 searches per portal"]
    assert said(many["gesperrt"], catalog, "fr") == (
        f"Avec cette sélection, «{NBSP}Le titre contient l'un d'eux{NBSP}» aurait 32 termes, 30 au plus sont possibles. "
        "Merci d'en désactiver encore 2 à cet endroit.")
    assert said(none["gesperrt"], catalog, "en") == (
        "Then no search term would be left in the search. Please switch at least one on.")


# Doppelt gesucht


def test_the_pairs_searched_twice_speak_french_with_the_lines_of_the_profile_as_they_are(catalog):
    duplicate, overlap = term_pairs.pairs(PROFILE, None, ["ictjobs"], (), [])

    assert said(duplicate["text"], catalog, "fr").startswith(
        f"«{NBSP}Kursleiter{NBSP}» figure deux fois{NBSP}: dans la liste principale et parmi les niches. Pour les niches, "
        "l'app cherche sans lieu, donc aussi tout ce que trouve la liste principale. Dans la liste principale, il coûte ")
    assert [said(o["knopf"], catalog, "fr") for o in duplicate["optionen"]] == ["Retirer de la liste principale", "Retirer des niches"]
    assert [said(o["name"], catalog, "en") for o in duplicate["optionen"]] == [
        "Remove from the core list: “Kursleiter”", "Remove from the niches: “Kursleiter”"]
    assert said(overlap["text"], catalog, "en").startswith(
        "“Kursleiter Informatik” is fully contained in “Kursleiter”: the search for “Kursleiter” mostly finds these jobs already. "
        "“Kursleiter Informatik” costs ")
    assert said(duplicate["behalten"], catalog, "fr") == "Conserver les deux"
    assert said(overlap["behalten_name"], catalog, "en") == "Keep both: “Kursleiter Informatik” and “Kursleiter”"


def test_removing_from_a_pair_says_what_the_run_saves_in_french_and_english(catalog):
    [duplicate, _] = term_pairs.pairs(PROFILE, None, ["ictjobs"], (), [])
    removal = term_pairs.removal(PROFILE, duplicate["id"], duplicate["optionen"][1]["seite"], None, ["ictjobs"])

    assert said(removal.done, catalog, "fr").startswith(
        f"«{NBSP}Kursleiter{NBSP}» retiré des niches. La prochaine série de recherches économise ")
    assert said(removal.done, catalog, "en").startswith("“Kursleiter” removed from the niches. The next search run saves ")
    assert said(removal.back, catalog, "fr") == f"«{NBSP}Kursleiter{NBSP}» figure de nouveau parmi les niches."
    assert said(removal.back, catalog, "en") == "“Kursleiter” is back among the niches."


def test_a_limited_line_keeps_its_german_label_in_french(catalog):
    text = PROFILE.replace("- Nur job-room: Datenpfleger", "- Nur job-room: Lernbegleiter")
    found = [pair for pair in term_pairs.pairs(text, None, ["ictjobs"], (), []) if "Lernbegleiter" in pair["text"]]

    assert found, "the term in the core list and in the «Nur» line is a pair"
    french = said(found[0]["text"], catalog, "fr")
    assert f"dans la ligne «{NBSP}Nur job-room{NBSP}»" in french
    assert "Nur job-room" in said(found[0]["optionen"][1]["knopf"], catalog, "en")


def test_the_pair_routes_refuse_in_the_app_language(started, preview):
    server, folder = started
    store_language(folder, "fr")

    assert refused(server, "/api/suche/doppelt/entfernen", {"paar": "weg", "seite": "a"})["fehler"] == (
        "Cela a changé entre-temps. La liste a été rechargée.")
    store_language(folder, "en")
    pairs = request(server, "GET", "/api/suche/doppelt")[1]["paare"]
    assert pairs[0]["behalten"] == "Keep both"
    kept = request(server, "POST", "/api/suche/doppelt/behalten", {"paar": pairs[0]["id"]})[1]
    assert kept == {"text": "Both stay. The app will not ask about this pair again."}


# Further sites, dismissed words and the exclusions of the AI


def test_further_sites_refuse_in_french_without_and_with_a_key(started, preview, monkeypatch):
    server, folder = started
    store_language(folder, "fr")
    for module in (connection, own_sites, routes_ai):
        monkeypatch.setattr(module, "own_key", lambda: None)
    assert refused(server, "/api/suche/weitere-seiten", {"seiten": []})["fehler"] == (
        "D'autres sites ne sont possibles qu'avec une clé API personnelle.")

    for module in (connection, own_sites, routes_ai):
        monkeypatch.setattr(module, "own_key", lambda: "sk-ant-erfunden")
    assert refused(server, "/api/suche/weitere-seiten", {"seiten": ["http://beispiel.ch"]})["fehler"] == (
        f"«{NBSP}http://beispiel.ch{NBSP}» ne fonctionne pas{NBSP}: "
        "l'adresse doit commencer par https:// et ne doit contenir ni identifiants ni port.")
    assert refused(server, "/api/suche/weitere-seiten", {"seiten": ["https://www.jobs.ch/x"]})["fehler"] == (
        f"«{NBSP}https://www.jobs.ch/x{NBSP}» ne fonctionne pas{NBSP}: l'app parcourt déjà ce site.")
    assert refused(server, "/api/suche/weitere-seiten", {"seiten": [f"https://s{n}.ch" for n in range(6)]})["fehler"] == (
        "5 autres sites au plus sont possibles.")
    assert refused(server, "/api/suche/weitere-seiten", {"seiten": ["https://a.ch/x", "https://a.ch/y"]})["fehler"] == (
        "Un site figure deux fois dans la liste. Une seule adresse par site.")
    assert refused(server, "/api/suche/seite-lesen", {"text": "x", "portal": "a.ch"})["fehler"] == (
        "Ce site ne figure pas dans la liste des autres sites.")


def test_further_sites_name_the_placeholders_in_english(started, preview, with_key):
    server, folder = started
    store_language(folder, "en")

    assert refused(server, "/api/suche/weitere-seiten", {"seiten": ["https://a.ch/{x}"]})["fehler"] == (
        "“https://a.ch/{x}” does not work: Only the placeholders {begriff} and {ort} are allowed.")
    assert refused(server, "/api/suche/weitere-seiten", {"seiten": ["https://localhost/x"]})["fehler"] == (
        "“https://localhost/x” does not work: That is not a public page.")


def test_a_word_from_dismissed_hits_that_is_gone_says_so_in_french(started, preview):
    server, folder = started
    store_language(folder, "fr")

    assert refused(server, "/api/suche/verworfen-woerter/ausschliessen", {"wort": "Aussendienst"})["fehler"] == (
        "Cette proposition n'est plus valable. La page montre maintenant l'état actuel.")


def test_the_exclusions_of_the_ai_refuse_in_the_app_language(started, preview, without_key):
    server, folder = started

    store_language(folder, "fr")
    assert refused(server, "/api/suche/ki-ausschluesse/vorschlag", {})["fehler"] == (
        "L'IA ne propose des exclusions qu'à partir de 3 offres écartées.")
    assert refused(server, "/api/suche/ki-ausschluesse/uebernehmen", {"vorschlag": "weg", "nummer": 0})["fehler"] == (
        "Cette proposition n'existe plus. Merci d'en demander une nouvelle.")
    store_language(folder, "en")
    assert refused(server, "/api/suche/ki-ausschluesse/vorschlag", {})["fehler"] == (
        "The AI only suggests exclusions from 3 discarded jobs on.")


def test_a_proposed_exclusion_names_its_place_and_category_in_the_app_language(catalog):
    import routes_ai_exclusions
    from ai import exclusion_reasons
    proposal = exclusion_reasons.Proposal("branche", "ausschluss", "Detailhandel", "Zwei Stellen.", ("a", "b"))
    hits = {"a": {"stelle": "Verkauf"}, "b": {"stelle": "Kasse"}}

    shown = routes_ai_exclusions._view(0, proposal, hits)

    assert (shown["ort"], shown["kategorie"], shown["wert"]) == ("Im Inserat", "Branche", "Detailhandel")
    assert (said(shown["ort"], catalog, "fr"), said(shown["kategorie"], catalog, "fr")) == ("Dans l'annonce", "Secteur")
    assert [said(exclusion_reasons.CATEGORIES[key], catalog, "en") for key in exclusion_reasons.CATEGORIES] == [
        "Word in the title", "Workload", "Industry", "Place of work", "Other"]


# What stays German, and German itself


def test_the_grammar_of_the_profile_stays_german_after_a_pair_is_removed_in_french(started, preview):
    server, folder = started
    store_language(folder, "fr")
    pairs = request(server, "GET", "/api/suche/doppelt")[1]["paare"]

    status, answer = request(server, "POST", "/api/suche/doppelt/entfernen",
                             {"paar": pairs[0]["id"], "seite": pairs[0]["optionen"][1]["seite"]})

    assert status == 200 and answer["text"].startswith(f"«{NBSP}Kursleiter{NBSP}» retiré des niches.")
    profile = (folder / search_plan.PROFILE).read_text(encoding="utf-8")
    assert "- Kernliste: Kursleiter, Lernbegleiter, Kursleiter Informatik\n- Nischen (ohne Ort suchen): Lernatelier\n" in profile
    assert "- Nur job-room: Datenpfleger\n" in profile and "- Ausschluss: Praktikum\n" in profile


def test_the_refusals_stay_german_with_the_preview_off(started, no_preview):
    server, folder = started
    store_language(folder, "fr")

    assert refused(server, "/api/suchbegriffe/endstand", {"vorschlag": "weg"})["fehler"] == (
        "Dieser Vorschlag gilt nicht mehr. Bitte neu vorschlagen lassen.")
    assert refused(server, "/api/suche/doppelt/entfernen", {"paar": "weg", "seite": "a"})["fehler"] == (
        "Das hat sich inzwischen geändert. Die Liste ist neu geladen.")
    assert request(server, "GET", "/api/suche/doppelt")[1]["paare"][0]["text"].startswith(
        "„Kursleiter“ steht zweimal: in der Kernliste und bei den Nischen.")


def test_a_list_is_joined_in_the_app_language_with_each_part_in_it(catalog):
    joined = listing([T("„{begriff}“", begriff="A"), T("„{begriff}“", begriff="B"), T("„{begriff}“", begriff="C")])

    assert joined == "„A“, „B“ und „C“"
    assert said(joined, catalog, "en") == "“A”, “B” and “C”"
    assert listing(["job-room"]) == "job-room"


# The wording the brief and the UI/UX rulings fix
REVIEWED = {
    "Suchbegriffe": ("Mots-clés", "Search terms"),
    "Rückgängig": ("Annuler", "Undo"),
    "ohne Ertrag": ("improductif", "unproductive"),
    "Jetzt suchen": ("Rechercher maintenant", "Search now"),
    "1 Suchlauf": ("1 série de recherches", "1 search run"),
    "Übernehmen": ("Appliquer", "Apply"),
    "Kein Titelfilter": ("Aucun filtre de titre", "No title filter"),
}


@pytest.mark.parametrize("german", REVIEWED)
def test_the_reviewed_wording_is_in_the_catalog(german, catalog):
    assert (catalog.text(german, "fr"), catalog.text(german, "en")) == REVIEWED[german]
