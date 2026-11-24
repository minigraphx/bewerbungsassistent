"""Lebenslauf erstellen, its preview, the documents step and the cuts in French and English (#428, G10).

With the preview on and French or English as the app language, the routes behind „Lebenslauf erstellen“, its live
preview, the AI's suggestions and the cuts of one application answer in it. With the preview off it all stays German,
byte for byte. Data stays German inside French and English: the stations of Meine Angaben, their firms and the names of
a version. What the scripts say at run time is tested in tests/cv_builder_languages.test.cjs. All data is invented.
"""
import json

import pytest

import cut_choice
import cuts
import cv_creation
import cv_design
import routes_cv_suggestions
import sprachen_pruefen
import translation_catalog
import ui_texts
from ai import cv_suggestions
from ai.errors import AiError
from register import Register
from sample_folder import BRIEF_ID
from test_app import get, post, server  # noqa: F401  (server is a fixture)
from test_today_languages import no_preview, preview, store_language  # noqa: F401  (fixtures)

NBSP = chr(0xA0)
ROUTE = "/api/lebenslauf/erstellen"
SCRIPT_FILES = ("seiten/lebenslauf-erstellen-logik.js", "seiten/lebenslauf-erstellen.js",
                "seiten/lebenslauf-vorschau-logik.js", "seiten/lebenslauf-vorschau.js", "seiten/lebenslauf-anpassen.js",
                "seiten/unterlagen-wahl.js", "seiten/unterlagen-ergebnis.js", "seiten/unterlagen-schritt.js",
                "seiten/kuerzen-logik.js", "seiten/kuerzen.js", "seiten/bewerbung.html")
# The routes of „Lebenslauf erstellen“, its preview and suggestions, of the cuts and of the thumbnails, with the
# modules behind them.
MODULE_FILES = ("routes_cv_creation.py", "cv_creation.py", "created_look.py", "cv_design.py", "routes_cv_preview.py",
                "cv_preview.py", "pdf_thumbnail.py", "routes_cv_suggestions.py", "ai/cv_suggestions.py",
                "routes_cuts.py", "cut_choice.py", "cv_cuts.py")
TEXT_SETS = ("lebenslauf.ki-aus", "lebenslauf.ki-ohne-inserat", "lebenslauf.ki-bereit", "lebenslauf.ki-schaetzen",
             "lebenslauf.ki-gespeichert", "lebenslauf.ki-angewendet", "lebenslauf.ki-laeuft", "lebenslauf.ki-holen",
             "lebenslauf.ki-neu", "lebenslauf.ki-nochmals", "lebenslauf.ki-einschalten", "lebenslauf.ki-zum-stellentext",
             "lebenslauf.vorschau-geaendert", "lebenslauf.foto-fehlt", "lebenslauf.foto-einspaltig",
             "lebenslauf.zeichen-ohne", "lebenslauf.zeichen-logo", "lebenslauf.logo-fehlt", "lebenslauf.farbe-passend",
             "lebenslauf.farbe-passend-zeile")
# An invented CV: one station with three points, one running until today with two, and interests to leave out.
CV = {
    "work": [
        {"position": "Planerin", "name": "Muster AG", "startDate": "2015-01", "endDate": "2018-06",
         "highlights": ["Pläne gezeichnet", "Baustellen begleitet", "Kosten geschätzt"]},
        {"position": "Zeichnerin", "name": "Probe GmbH", "startDate": "2019-03", "highlights": ["Modelle", "Details"]},
    ],
    "interests": [{"name": "Lesen"}],
}


def catalog() -> translation_catalog.Catalog:
    return translation_catalog.load(translation_catalog.CATALOG_DIR)


def said(message, language: str) -> str:
    return str(message) if language == "de" else message.in_language(catalog(), language)


def form(s) -> dict:
    status, _, body = get(s, ROUTE, id=BRIEF_ID)
    assert status == 200, body
    return json.loads(body)


def section(answer: dict, name: str) -> dict:
    return next(part for part in answer["abschnitte"] if part["abschnitt"] == name)


def choice(answer: dict, **changes) -> dict:
    return {"id": BRIEF_ID, "stand": answer["stand"], "stationen": {"work": [0]}, "berufsbezeichnung": "Planerin",
            "kurzprofil": "Plant gern.", "design": "zweispaltig", "bezeichnung": "Planung, Muster AG", **changes}


def refused(s, path: str, body) -> dict:
    status, answer = post(s, path, body)
    assert status == 400, answer
    return answer


# The files of this step


def test_the_scripts_and_the_modules_of_the_cv_builder_are_finished():
    finished = {str(path.relative_to(sprachen_pruefen.BASE)) for path in sprachen_pruefen.FERTIG
                if path.is_relative_to(sprachen_pruefen.BASE)}

    assert set(SCRIPT_FILES) | set(MODULE_FILES) <= finished


def test_the_scripts_and_the_modules_of_the_cv_builder_have_no_gap():
    files = [sprachen_pruefen.BASE / name for name in (*SCRIPT_FILES, *MODULE_FILES)]

    assert [str(gap) for gap in sprachen_pruefen.gaps(files, catalog())] == []


def test_the_text_sets_the_cv_builder_picks_at_run_time_are_in_the_catalog():
    missing = [(key, language, form_) for key in TEXT_SETS for language in ("fr", "en")
               for form_ in (("sie", "du") if language == "fr" else ("sie",))
               if not catalog().form(key, language, form_)]

    assert missing == []


def test_french_says_tu_where_the_set_says_du():
    assert catalog().form("lebenslauf.foto-fehlt", "fr", "du") == (
        f"Pas encore de photo. Tu ajoutes des photos sous «{NBSP}CV et fichiers{NBSP}».")
    assert catalog().form("lebenslauf.zeichen-logo", "fr", "du") == "Ton logo"
    assert catalog().form("lebenslauf.zeichen-logo", "fr", "sie") == "Votre logo"


# The form of „Lebenslauf erstellen“: section names and „heute“ in the app language, the stations as they are


def test_the_form_names_its_sections_in_french_and_keeps_the_stations(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "fr")

    answer = form(server)

    work = section(answer, "work")
    assert work["titel"] == "Expérience professionnelle"
    assert section(answer, "education")["titel"] == "Formation et formation continue"
    assert [station["titel"] for station in work["stationen"]] == ["Software-Entwicklerin", "Junior-Entwicklerin"]
    assert [station["zusatz"] for station in work["stationen"]] == ["Beispiel AG", "Muster GmbH"]
    assert [station["zeit"] for station in work["stationen"]] == ["03.2019 – aujourd'hui", "2015 – 2019"]


def test_the_form_names_its_sections_in_english(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "en")

    answer = form(server)

    assert section(answer, "work")["titel"] == "Work experience"
    assert section(answer, "work")["stationen"][0]["zeit"] == "03.2019 – today"


def test_the_form_stays_german_with_the_preview_off(server, no_preview):  # noqa: F811
    store_language(server.kontext.daten, "fr")

    answer = form(server)

    assert section(answer, "work")["titel"] == "Berufserfahrung"
    assert section(answer, "work")["stationen"][0]["zeit"] == "03.2019 – heute"


# Refusals of the routes


def test_saving_is_refused_in_french_and_english(server, preview):  # noqa: F811
    daten = server.kontext.daten
    store_language(daten, "fr")
    answer = form(server)

    assert refused(server, ROUTE, choice(answer, stand="alt"))["fehler"] == (
        f"Mes informations ont changé entre-temps. Merci de rouvrir «{NBSP}Créer le CV{NBSP}».")
    assert refused(server, ROUTE, choice(answer, stationen={"work": []}))["fehler"] == (
        "Merci de choisir au moins une étape du parcours.")
    assert refused(server, ROUTE, choice(answer, design="dossier-siegel"))["fehler"] == (
        "Merci de choisir Deux colonnes ou Une colonne.")
    assert refused(server, ROUTE, choice(answer, berufsbezeichnung="x" * 200))["fehler"] == (
        "Le titre professionnel est trop long, 120 caractères au maximum.")
    store_language(daten, "en")
    assert refused(server, ROUTE, choice(answer, kurzprofil=5))["fehler"] == "The profile summary must be text."
    assert refused(server, ROUTE, choice(answer, bezeichnung="x" * 200))["fehler"] == (
        "The name of the version is too long, at most 120 characters.")


def test_saving_is_refused_in_german_with_the_preview_off(server, no_preview):  # noqa: F811
    store_language(server.kontext.daten, "fr")
    answer = form(server)

    assert refused(server, ROUTE, choice(answer, design="dossier-siegel"))["fehler"] == (
        "Bitte Zweispaltig oder Einspaltig wählen.")
    assert refused(server, ROUTE, choice(answer, berufsbezeichnung="x" * 200))["fehler"] == (
        "Die Berufsbezeichnung ist zu lang, höchstens 120 Zeichen.")


def test_a_cv_saved_for_a_dossier_says_so_in_french(server, preview):  # noqa: F811
    daten = server.kontext.daten
    register = Register(daten)
    register.speichere({**register.hole(BRIEF_ID), "unterlagen": "dossier"})
    store_language(daten, "fr")

    status, answer = post(server, ROUTE, choice(form(server)))

    assert status == 200, answer
    assert answer["gebaut"] is False
    assert answer["hinweis"] == f"Enregistré. Le dossier sera recréé avec ce CV via «{NBSP}Créer les documents{NBSP}»."
    assert answer["variante"]["beschreibung"] == "Planung, Muster AG"


def test_the_preview_keeps_its_next_step_and_says_why_in_english(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "en")

    answer = refused(server, f"{ROUTE}/vorschau", choice(form(server), stand="alt"))

    assert answer == {"fehler": "My details have changed in the meantime. Please open “Create CV” again.",
                      "aktion": "neu-oeffnen"}


def test_a_page_of_the_preview_is_refused_in_french(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "fr")

    status, _, body = get(server, f"{ROUTE}/vorschau/seite", id=BRIEF_ID, schluessel="k1", seite="eins")
    gone_status, _, gone = get(server, f"{ROUTE}/vorschau/seite", id=BRIEF_ID, schluessel="k1", seite="1")

    assert status == 400 and json.loads(body)["fehler"] == "La page doit être un nombre."
    assert gone_status == 404 and json.loads(gone)["fehler"] == "Cet aperçu n'existe plus. Merci de recharger la page."


def test_a_suggestion_without_an_ad_is_refused_in_english(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "en")

    answer = refused(server, f"{ROUTE}/vorschlag", {"id": BRIEF_ID, "stand": form(server)["stand"]})

    assert answer["fehler"] == "For AI suggestions, save the job ad text first."


def test_the_cuts_are_refused_in_french_and_stay_german_without_the_preview(server, preview, monkeypatch):  # noqa: F811
    store_language(server.kontext.daten, "fr")

    assert refused(server, "/api/kuerzungen", {"id": BRIEF_ID, "weglassen": []})["fehler"] == (
        "Merci de cocher au moins une coupe ou d'autoriser trois pages.")
    assert refused(server, "/api/kuerzungen", [])["fehler"] == "id attendu"
    monkeypatch.delenv(ui_texts.PREVIEW_ENV)
    assert refused(server, "/api/kuerzungen", {"id": BRIEF_ID, "weglassen": []})["fehler"] == cut_choice.NONE_CHOSEN


# What the app writes itself: the cuts, the recommendations and a failed suggestion


@pytest.mark.parametrize("language", ["de", "fr", "en"])
def test_the_cuts_name_points_and_sections_in_the_app_language_and_the_station_as_it_is(language):
    shown = [said(cut_choice.cut_text(cut), language) for cut in cuts.options(CV)]

    assert shown == {
        "de": ["2 Stichpunkte bei «Planerin, Muster AG» (2015–2018)", "1 Stichpunkt bei «Zeichnerin, Probe GmbH» (2019–heute)",
               "Abschnitt «Interessen»"],
        "fr": [f"2 points de «{NBSP}Planerin, Muster AG{NBSP}» (2015–2018)",
               f"1 point de «{NBSP}Zeichnerin, Probe GmbH{NBSP}» (2019–aujourd'hui)",
               f"Section «{NBSP}Centres d'intérêt{NBSP}»"],
        "en": ["2 bullet points from “Planerin, Muster AG” (2015–2018)",
               "1 bullet point from “Zeichnerin, Probe GmbH” (2019–today)", "Section “Interests”"],
    }[language]


def test_the_german_cut_text_is_the_one_lebenslauf_writes():
    cv = {**CV, "projects": [{"name": "Kurs", "group": "more"}], "volunteer": [{"organization": "Verein"}],
          "awards": [{"title": "Preis"}], "work": [{"position": "Ohne Jahr", "highlights": ["a", "b"]}]}

    offered = cuts.options(cv)

    assert [str(cut_choice.cut_text(cut)) for cut in offered] == [cut.text for cut in offered]
    assert {key: str(name) for key, name in cut_choice.SECTION_NAMES.items()} == cuts.SECTION_NAMES


def test_the_offer_and_the_left_out_name_their_cuts_with_t(monkeypatch, tmp_path):
    monkeypatch.setattr(cut_choice.unterlagen, "cuts_apply", lambda daten, entry: True)
    monkeypatch.setattr(cut_choice.unterlagen, "tailored_cv", lambda daten, entry, with_cuts=True: CV)
    entry = {"id": "muster-ag-planerin"}

    offer = cut_choice.offer(tmp_path, entry, 2)
    cut_choice.write(tmp_path, entry["id"], cuts.chosen(cuts.options(CV)[:1], {}))
    state = cut_choice.state(tmp_path, entry)

    assert said(offer["optionen"][2]["text"], "en") == "Section “Interests”"
    assert said(state["weggelassen"][0]["text"], "en") == "2 bullet points from “Planerin, Muster AG” (2015–2018)"


def _stations() -> dict:
    station = cv_suggestions.Station(ref=("work", 0), title="Planerin", organization="Muster AG", time="2015 – 2018",
                                     section_title="Berufserfahrung", texts=())
    other = cv_suggestions.Station(ref=("work", 1), title="Zeichnerin", organization="", time="", section_title="",
                                   texts=())
    return {station.ref: station, other.ref: other}


@pytest.mark.parametrize("language", ["de", "fr", "en"])
def test_a_recommendation_is_named_in_the_app_language_with_the_stations_as_they_are(language):
    both = cv_suggestions.Recommendation(leave_out=(("work", 0),), move_up=(("work", 1),), summary=None, reason="")
    summary = cv_suggestions.Recommendation(leave_out=(("work", 0), ("work", 1)), move_up=(), summary="Kurz.",
                                            reason="")

    shown = [said(routes_cv_suggestions.what(r, _stations(), "Lang. Und lang."), language) for r in (both, summary)]

    assert shown == {
        "de": ["«Planerin, Muster AG» weglassen, «Zeichnerin» nach vorne",
               "«Planerin, Muster AG» und «Zeichnerin» weglassen, Kurzprofil gekürzt"],
        "fr": [f"«{NBSP}Planerin, Muster AG{NBSP}»{NBSP}: omettre, «{NBSP}Zeichnerin{NBSP}»{NBSP}: placer en tête",
               f"«{NBSP}Planerin, Muster AG{NBSP}» et «{NBSP}Zeichnerin{NBSP}»{NBSP}: omettre, Profil en bref raccourci"],
        "en": ["“Planerin, Muster AG”: leave out, “Zeichnerin”: move to the front",
               "“Planerin, Muster AG” and “Zeichnerin”: leave out, Profile summary shortened"],
    }[language]


def test_a_failed_suggestion_says_why_in_the_app_language():
    failed = routes_cv_suggestions._failed(AiError("Die KI antwortet nicht."))

    message = failed.args[0]
    assert str(message) == "Kein Vorschlag der KI. Die KI antwortet nicht. Nichts berechnet. Die Auswahl bleibt, wie sie ist."
    assert said(message, "en") == (
        "No suggestion from the AI. Die KI antwortet nicht. Nothing charged. The selection stays as it is.")


def test_the_design_names_are_shared_with_the_page():
    assert [said(cv_design.NAMES[name], "fr") for name in ("zweispaltig", "einspaltig")] == ["Deux colonnes", "Une colonne"]
    assert str(cv_design.UNKNOWN) == "Bitte Zweispaltig oder Einspaltig wählen."


def test_a_station_without_a_title_is_named_by_its_number():
    [row] = cv_creation._station_rows([{}], [0])

    assert str(row["titel"]) == "Eintrag 1"
    assert said(row["titel"], "en") == "Entry 1"
