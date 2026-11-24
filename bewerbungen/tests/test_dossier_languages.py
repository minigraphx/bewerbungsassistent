"""The letter editor, greeting and thanks, the mark of the dossier and the dialog in French and English (#429, G10).

With the preview on and French or English as the app language, the routes behind the letter editor, „Dossier
gestalten“, the own letter, the drafts and the backup answer in it, and the page Bewerbung is finished: every script
it loads and every route module behind those scripts is in FERTIG without a gap. With the preview off it all stays
German, byte for byte. Data stays as it is: the letter, initials, colours as #rrggbb, file names. What the scripts say
at run time is tested in tests/dossier_languages.test.cjs. All data is invented.
"""
import base64
import inspect
import json
import pathlib
import re
import zipfile

import pytest

import backup
import created_look
import dossier_texts
import inhalte
import letter_edit
import logo_file
import mark_settings
import own_files
import sprachen_pruefen
import translation_catalog
import ui_texts
from ai import tasks
from ai.errors import AiError
from sample_folder import BRIEF_ID
from test_app import get, post, server  # noqa: F401  (server is a fixture)
from test_mark_settings import png
from test_today_languages import no_preview, preview, store_language  # noqa: F401  (fixtures)

NBSP = chr(0xA0)
PAGE = "seiten/bewerbung.html"
LETTER_ROUTE = "/api/bewerbung/anschreiben"
MARK_ROUTE = "/api/dossier/zeichen"
SCRIPT_FILES = ("seiten/finding-row.js", "seiten/letter-editor-logik.js", "seiten/letter-editor.js",
                "seiten/dossier-texte.js", "seiten/zeichen-logik.js", "seiten/zeichen.js",
                "seiten/dossier-dialog-logik.js", "seiten/dossier-dialog.js")
# The routes of the letter editor, of greeting and thanks, of the mark and the logo, of the own letter, of the drafts
# and of the backup, with the modules behind them.
MODULE_FILES = ("routes_letter_edit.py", "letter_edit.py", "inhalte.py", "routes_dossier.py", "dossier_texts.py",
                "ai/tasks.py", "routes_mark.py", "mark_settings.py", "logo_file.py", "routes_own_files.py",
                "own_files.py", "routen_ablage.py", "draft_groups.py", "routes_backup.py", "backup.py")
TEXT_SETS = ("anschreiben.editor-intro", "anschreiben.editor-freigabe", "anschreiben.gespeichert",
             "anschreiben.nicht-erreichbar", "anschreiben.geaendert", "dossier.logo-statt-initialen")
API_ROUTE = re.compile(r"/api/[a-z0-9/_-]*[a-z0-9]")


def catalog() -> translation_catalog.Catalog:
    return translation_catalog.load(translation_catalog.CATALOG_DIR)


def said(message, language: str) -> str:
    return str(message) if language == "de" else message.in_language(catalog(), language)


def finished() -> set[pathlib.Path]:
    return {path.resolve() for path in sprachen_pruefen.FERTIG}


def page_scripts() -> list[pathlib.Path]:
    html = (sprachen_pruefen.BASE / PAGE).read_text(encoding="utf-8")
    return [sprachen_pruefen.BASE / "seiten" / name for name in re.findall(r'<script src="/([^"?]+\.js)"', html)]


def letter_body(s, **changes) -> dict:
    _, _, body = get(s, "/api/bewerbung", id=BRIEF_ID)
    letter = json.loads(body)["anschreiben_text"]
    return {"betreff": letter["betreff"], "anrede": letter["anrede"], "absaetze": letter["absaetze"],
            "gruss": letter["gruss"], "fingerabdruck": letter["fingerabdruck"], **changes}


def refused(s, path: str, body, status: int = 400, **parameter) -> str:
    code, answer = post(s, path, body, **parameter)
    assert code == status, answer
    return answer["fehler"]


# The files of this step and the page Bewerbung as a whole


def test_the_scripts_and_the_modules_of_the_letter_editor_and_the_dossier_are_finished():
    names = {str(path.relative_to(sprachen_pruefen.BASE)) for path in sprachen_pruefen.FERTIG
             if path.is_relative_to(sprachen_pruefen.BASE)}

    assert set(SCRIPT_FILES) | set(MODULE_FILES) <= names


def test_the_scripts_and_the_modules_of_the_letter_editor_and_the_dossier_have_no_gap():
    files = [sprachen_pruefen.BASE / name for name in (*SCRIPT_FILES, *MODULE_FILES)]

    assert [str(gap) for gap in sprachen_pruefen.gaps(files, catalog())] == []


def test_every_script_the_page_bewerbung_loads_is_finished():
    scripts = page_scripts()

    assert len(scripts) > 30, scripts
    assert [str(path.name) for path in scripts if path.resolve() not in finished()] == []


def test_every_route_module_behind_the_page_bewerbung_is_finished(server):  # noqa: F811
    asked = {route for path in page_scripts() for route in API_ROUTE.findall(path.read_text(encoding="utf-8"))}
    handlers = [table[route] for route in sorted(asked) for table in (server.routen_get, server.routen_post)
                if route in table]
    modules = {pathlib.Path(inspect.getsourcefile(handler)).resolve() for handler in handlers}

    assert len(modules) > 10, modules
    assert sorted(path.name for path in modules if path not in finished()) == []


def test_the_page_bewerbung_has_no_gap():
    files = [sprachen_pruefen.BASE / PAGE, *page_scripts()]

    assert [str(gap) for gap in sprachen_pruefen.gaps(files, catalog())] == []


def test_the_text_sets_of_the_editor_and_the_logo_are_in_the_catalog():
    missing = [(key, language, form_) for key in TEXT_SETS for language in ("fr", "en")
               for form_ in (("sie", "du") if language == "fr" else ("sie",))
               if not catalog().form(key, language, form_)]

    assert missing == []


def test_french_says_tu_where_the_set_says_du():
    assert catalog().form("anschreiben.gespeichert", "fr", "du") == (
        "Enregistré. Recrée les documents pour que le PDF et la vérification montrent le nouveau texte.")
    assert catalog().form("dossier.logo-statt-initialen", "fr", "du") == "Ton logo à la place des initiales"
    assert catalog().form("dossier.logo-statt-initialen", "fr", "sie") == "Votre logo à la place des initiales"


def test_the_mark_names_match_the_message_of_lebenslauf_erstellen():
    assert catalog().text("Verschränkt", "en") == "Intertwined"
    assert catalog().text("Verschränkt", "fr") == "Entrelacé"
    assert catalog().text(created_look.NEEDS_TWO, "en") == "“Intertwined” only works with exactly two initials."
    assert catalog().text(created_look.NEEDS_TWO, "fr") == (
        f"«{NBSP}Entrelacé{NBSP}» ne fonctionne qu'avec exactement deux initiales.")


# The letter editor


def test_the_letter_editor_is_refused_in_french_and_english(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "fr")

    assert refused(server, LETTER_ROUTE, letter_body(server, absaetze=[" ", ""]), id=BRIEF_ID) == (
        "La lettre de motivation doit contenir au moins un paragraphe avec du texte.")
    assert refused(server, LETTER_ROUTE, letter_body(server, betreff="x" * 301), id=BRIEF_ID) == (
        "L'objet dépasse 300 caractères")
    assert refused(server, LETTER_ROUTE, letter_body(server, absaetze=["a"] * 41), id=BRIEF_ID) == (
        "40 paragraphes au maximum")
    store_language(server.kontext.daten, "en")
    assert refused(server, LETTER_ROUTE, letter_body(server, gruss=5), id=BRIEF_ID) == "The closing must be text"
    assert refused(server, LETTER_ROUTE, letter_body(server, anrede="x" * 301), id=BRIEF_ID) == (
        "The salutation has more than 300 characters")
    assert refused(server, LETTER_ROUTE, [], id=BRIEF_ID) == (
        "Expected: betreff, anrede, absaetze, gruss and fingerabdruck")
    assert refused(server, LETTER_ROUTE, letter_body(server, fingerabdruck="alt"), 409, id=BRIEF_ID) == (
        "The cover letter has changed in the meantime.")


def test_the_letter_editor_is_refused_in_german_with_the_preview_off(server, no_preview):  # noqa: F811
    store_language(server.kontext.daten, "fr")

    assert refused(server, LETTER_ROUTE, letter_body(server, betreff="x" * 301), id=BRIEF_ID) == (
        "Betreff hat mehr als 300 Zeichen")
    assert refused(server, LETTER_ROUTE, letter_body(server, absaetze=[" "]), id=BRIEF_ID) == letter_edit.NO_PARAGRAPH
    assert refused(server, LETTER_ROUTE, letter_body(server, fingerabdruck="alt"), 409, id=BRIEF_ID) == (
        "Das Anschreiben hat sich inzwischen geändert.")


@pytest.mark.parametrize("language", ["de", "fr", "en"])
def test_a_letter_that_is_no_yaml_mapping_is_named_in_the_app_language(language):
    with pytest.raises(ValueError) as refusal:
        letter_edit.unchanged("- eine Liste\n", letter_edit.LetterEdit("", "", ("a",), "", "f"))

    assert said(refusal.value.args[0], language) == {
        "de": "Das Anschreiben muss eine YAML-Zuordnung sein",
        "fr": "La lettre de motivation doit être un mappage YAML",
        "en": "The cover letter must be a YAML mapping",
    }[language]


@pytest.mark.parametrize("language", ["de", "fr", "en"])
def test_a_file_that_may_not_be_edited_is_named_in_the_app_language(language, tmp_path):
    with pytest.raises(ValueError) as refusal:
        inhalte.pruefe_datei(tmp_path, "geheim.txt")

    assert said(refusal.value.args[0], language) == {
        "de": "Datei 'geheim.txt' ist nicht bearbeitbar",
        "fr": "Le fichier 'geheim.txt' n'est pas modifiable",
        "en": "File 'geheim.txt' cannot be edited",
    }[language]


# Greeting and thanks


def test_greeting_and_thanks_are_refused_in_french_and_stay_german_without_the_preview(server, preview, monkeypatch):  # noqa: F811
    store_language(server.kontext.daten, "fr")
    too_long = {"gruss": "x" * (dossier_texts.MAX_CHARS + 1), "dank": ""}

    assert refused(server, "/api/dossier/texte", too_long, id=BRIEF_ID) == (
        "L'accueil et les remerciements comptent chacun 2000 caractères au maximum.")
    store_language(server.kontext.daten, "en")
    assert refused(server, "/api/dossier/texte", {"gruss": 5}, id=BRIEF_ID) == "Welcome and thanks must be text."
    monkeypatch.delenv(ui_texts.PREVIEW_ENV)
    assert refused(server, "/api/dossier/texte", too_long, id=BRIEF_ID) == (
        "Begrüssung und Dank haben je höchstens 2000 Zeichen.")


def test_an_unreadable_dossier_file_is_named_in_english(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "en")
    file = dossier_texts.path(server.kontext.daten, BRIEF_ID)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text("- keine Zuordnung\n", encoding="utf-8")

    status, _, body = get(server, "/api/dossier/texte", id=BRIEF_ID)

    assert status == 400
    assert json.loads(body)["fehler"] == "dossier.yaml cannot be read. Please get an earlier version under “Drafts”."


# The mark and the logo


def test_the_mark_is_saved_and_refused_in_french(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "fr")

    status, answer = post(server, MARK_ROUTE, {"zeichen": "ring"})
    assert status == 200 and answer["meldung"] == (
        f"Emblème enregistré. «{NBSP}Créer et vérifier les documents{NBSP}» crée le dossier avec le nouvel emblème.")
    assert refused(server, MARK_ROUTE, {"initialen": "E1"}) == f"Initiales{NBSP}: 1 à 3 lettres."
    post(server, MARK_ROUTE, {"initialen": "EKB"})
    assert refused(server, MARK_ROUTE, {"zeichen": "verschraenkt"}) == "Seulement avec deux lettres"
    assert refused(server, MARK_ROUTE, {"zeichen": "stern"}) == (
        f"Emblème inconnu{NBSP}: 'stern'. Autorisés{NBSP}: passend, ring, block, verschraenkt, linie, punkt, logo")
    assert refused(server, MARK_ROUTE, {"zeichen": "logo"}) == "Choisir d'abord un logo."
    assert refused(server, MARK_ROUTE, {"akzent": "rot"}) == "Merci de saisir une couleur comme #38495d."
    assert refused(server, MARK_ROUTE, []) == "Emblème, initiales ou couleur d'accent attendus"
    status, answer = post(server, "/api/dossier/zeichen-zuruecksetzen", {})
    assert answer["meldung"] == (
        f"L'emblème et la couleur sont de nouveau sur «{NBSP}Assortie au design{NBSP}».")


def test_a_colour_that_reads_badly_is_refused_in_english_with_the_suggestion(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "en")

    assert refused(server, MARK_ROUTE, {"akzent": "#e0b84a"}) == (
        "Too light: ring, lines and dots would hardly show on the paper. This colour is not saved. Suggestion: #927119.")
    status, answer = post(server, MARK_ROUTE, {"akzent": "#1d5c6b"})
    assert status == 200 and answer["akzent"] == "#1d5c6b"
    assert answer["meldung"] == "Accent colour saved. “Create and check documents” creates the dossier in the new colour."


def test_the_mark_stays_german_with_the_preview_off(server, no_preview):  # noqa: F811
    store_language(server.kontext.daten, "fr")

    assert refused(server, MARK_ROUTE, {"akzent": "#e0b84a"}) == (
        "Zu hell: Ring, Linien und Punkte wären auf dem Papier kaum zu sehen. Gespeichert wird diese Farbe nicht. "
        "Vorschlag #927119.")
    assert refused(server, MARK_ROUTE, {"zeichen": "stern"}) == (
        "Unbekanntes Zeichen: 'stern'. Erlaubt: passend, ring, block, verschraenkt, linie, punkt, logo")
    status, answer = post(server, MARK_ROUTE, {"initialen": "EB"})
    assert answer["meldung"] == mark_settings.SAVED["initialen"]


def test_a_logo_is_saved_removed_and_refused_in_english(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "en")
    upload = lambda data: post(server, "/api/dossier/logo", {"daten": base64.b64encode(data).decode()})  # noqa: E731

    status, answer = upload(png(300, 60))
    assert status == 200 and answer["meldung"] == "Logo saved. “Create and check documents” creates the dossier with the logo."
    assert answer["logo"]["hinweise"][:2] == [
        "Very wide: on the cover page the logo is only about 7 mm high. A more compact mark works better.",
        "The image has only 300 × 60 pixels and will print blurred. Better at least 1000 pixels wide."]
    status, answer = post(server, "/api/dossier/logo-entfernen", {})
    assert answer["meldung"] == "Logo removed. The dossier shows the initials again."
    assert upload(b"GIF89a....")[1]["fehler"] == "This file is not a PNG, JPG or SVG image."
    assert upload(b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>')[1]["fehler"] == (
        "This SVG contains a script. Please save the logo as PNG and choose it again.")


@pytest.mark.parametrize("language", ["de", "fr", "en"])
def test_the_hints_on_a_logo_are_said_in_the_app_language(language, tmp_path):
    white = logo_file.inspect("png", png(1200, 600, background=(255, 255, 255, 255)), tmp_path)["hinweise"]
    high = logo_file.inspect("png", png(400, 900), tmp_path)["hinweise"]

    assert [said(hint, language) for hint in (*white, high[0])] == {
        "de": [logo_file.WHITE_BACKGROUND, logo_file.VERY_HIGH],
        "fr": [f"Le logo a un fond blanc. Sur le papier, cela se remarque à peine{NBSP}; dans Trame, il figure de "
               "toute façon sur une surface blanche.",
               f"Très haut{NBSP}: sur la page de garde, le logo devient étroit et paraît petit. Une version en largeur "
               "convient mieux."],
        "en": ["The logo has a white background. On paper this hardly shows; in Grid it sits on a white area anyway.",
               "Very tall: on the cover page the logo becomes narrow and looks small. A landscape version fits better."],
    }[language]


def test_the_german_logo_refusals_are_the_ones_lebenslauf_writes():
    import svg_check

    assert [str(logo_file.SVG_PROBLEMS[problem]) for problem in (svg_check.SCRIPT, svg_check.REMOTE,
                                                                 svg_check.UNCHECKABLE)] == [
        svg_check.SCRIPT, svg_check.REMOTE, svg_check.UNCHECKABLE]


# The own letter, the drafts, the backup and the AI


def test_an_own_letter_that_is_no_pdf_is_refused_in_french(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "fr")
    letter = {"id": BRIEF_ID, "name": "brief.docx", "daten": base64.b64encode(b"PK..").decode()}

    assert refused(server, "/api/dateien/anschreiben", letter) == "La lettre de motivation doit être un PDF."
    assert refused(server, "/api/dateien/anschreiben", {**letter, "daten": 5}) == (
        "Le fichier n'a pas pu être lu. Merci de réessayer.")
    assert refused(server, "/api/dateien/anschreiben", "x") == "La requête a une forme inconnue."


@pytest.mark.parametrize("language", ["de", "fr", "en"])
def test_a_file_too_large_or_of_another_kind_is_named_in_the_app_language(language, monkeypatch):
    monkeypatch.setattr(own_files, "MAX_FILE_BYTES", 2_000_000)
    with pytest.raises(ValueError) as large:
        own_files.check_letter("brief.pdf", b"%PDF-" + b"0" * 2_000_000)
    with pytest.raises(ValueError) as renamed:
        own_files.check_letter("brief.pdf", b"PK..")

    assert [said(error.value.args[0], language) for error in (large, renamed)] == {
        "de": ["Die Datei ist zu gross, höchstens 2 MB.",
               "Diese Datei ist kein echtes PDF. Vielleicht wurde sie nur umbenannt."],
        "fr": ["Le fichier est trop volumineux, 2 Mo au maximum.",
               "Ce fichier n'est pas un vrai PDF. Il a peut-être seulement été renommé."],
        "en": ["The file is too large, at most 2 MB.", "This file is not a real PDF. Perhaps it was only renamed."],
    }[language]


def test_the_drafts_are_refused_in_english(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "en")

    status, _, body = get(server, "/api/entwuerfe", datei="cv.yaml", anzahl="0")

    assert status == 400
    assert json.loads(body)["fehler"] == "anzahl must be a number from 1 to 1000"


@pytest.mark.parametrize("language", ["de", "fr", "en"])
def test_a_file_the_backup_cannot_read_is_named_in_the_app_language(language, tmp_path, monkeypatch):
    def broken(*args, **kwargs):
        raise PermissionError("gesperrt")

    with zipfile.ZipFile(tmp_path / "sicherung.zip", "w") as archive:
        monkeypatch.setattr(archive, "write", broken)
        with pytest.raises(ValueError) as refusal:
            backup._pack(archive, tmp_path / "cv.yaml", "cv.yaml")

    assert said(refusal.value.args[0], language) == {
        "de": "Die Datei cv.yaml liess sich nicht lesen. Falls sie in einem Programm offen ist: dort schliessen und "
              "nochmals versuchen.",
        "fr": f"Le fichier cv.yaml n'a pas pu être lu. S'il est ouvert dans un programme{NBSP}: le fermer et réessayer.",
        "en": "The file cv.yaml could not be read. If it is open in a program: close it there and try again.",
    }[language]


@pytest.mark.parametrize("language", ["de", "fr", "en"])
def test_the_ai_names_what_is_missing_in_the_app_language(language, tmp_path):
    with pytest.raises(AiError) as missing:
        tasks.load_material(tmp_path)
    with pytest.raises(AiError) as too_long:
        tasks._ad("x" * (tasks.MAX_AD_CHARS + 1))

    assert [said(error.value.args[0], language) for error in (missing, too_long)] == {
        "de": ["Für die KI fehlt noch cv.yaml. Zuerst Meine Angaben abschliessen.",
               "Das Inserat ist zu lang (höchstens 30000 Zeichen)."],
        "fr": ["Il manque encore cv.yaml pour l'IA. Terminer d'abord Mes informations.",
               "L'annonce est trop longue (30000 caractères au maximum)."],
        "en": ["The AI still needs cv.yaml. Complete My details first.",
               "The job ad is too long (at most 30000 characters)."],
    }[language]
