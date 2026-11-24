"""The checks of lebenslauf/anschreiben.py in French and English (#453, G10).

`pruefe_brief` and the letter build refuse a letter in German, since lebenslauf runs on its own and never imports the
app. The app says those refusals in its language wherever it shows them: the letter editor, „Inhalte als Text“ and
„Unterlagen erstellen“ on the page Bewerbung, for two files as for a dossier. With the preview off, and for lebenslauf on
its own, every refusal stays German byte for byte. Field names, language codes and paths are data and stay as written.
All data is invented.
"""
import ast
import datetime
import json

import pytest
import yaml

import anschreiben
import letter_messages
import sprachen_pruefen
import translation_catalog
import unterlagen
from sample_folder import BRIEF_ID
from test_app import post, server  # noqa: F401  (server is a fixture)
from test_dossier_languages import letter_body, refused
from test_today_languages import no_preview, preview, store_language  # noqa: F401  (fixtures)

NBSP = chr(0xA0)
LETTER_ROUTE = "/api/bewerbung/anschreiben"
LETTER_FILE = sprachen_pruefen.ROOT / "lebenslauf" / "anschreiben.py"
MODULE_FILE = sprachen_pruefen.BASE / "letter_messages.py"


def catalog() -> translation_catalog.Catalog:
    return translation_catalog.load(translation_catalog.CATALOG_DIR)


def said(message, language: str) -> str:
    return str(message) if language == "de" else message.in_language(catalog(), language)


def valid_letter(**changes) -> dict:
    letter = {"empfaenger": ["Beispiel AG", "Musterweg 1", "3000 Bern"], "betreff": "Bewerbung als Data Engineer",
              "anrede": "Sehr geehrte Damen und Herren", "text": "Ein Absatz.", "gruss": "Freundliche Grüsse"}
    return {**letter, **changes}


def refusal(call) -> str:
    """The message `call` is refused with once the app has said it: the first argument of its ValueError."""
    with pytest.raises(ValueError) as refused_:
        with letter_messages.in_app_language():
            call()
    return refused_.value.args[0]


def write_letter(server, letter: dict) -> None:  # noqa: F811
    path = unterlagen.letter_source(server.kontext.daten, BRIEF_ID)
    path.write_text(yaml.safe_dump(letter, allow_unicode=True), encoding="utf-8")


# The files


def test_the_letter_module_and_its_messages_are_finished():
    finished = {path.resolve() for path in sprachen_pruefen.FERTIG}

    assert LETTER_FILE.resolve() in finished
    assert MODULE_FILE.resolve() in finished


def test_the_letter_module_and_its_messages_have_no_gap():
    assert [str(gap) for gap in sprachen_pruefen.gaps((LETTER_FILE, MODULE_FILE), catalog())] == []


def test_every_source_includes_the_letter_module_so_its_entries_are_no_orphans():
    assert LETTER_FILE in sprachen_pruefen.app_sources()


def test_lebenslauf_imports_nothing_of_the_app():
    app_modules = {path.stem for path in sprachen_pruefen.BASE.glob("*.py")}
    tree = ast.parse(LETTER_FILE.read_text(encoding="utf-8"))
    imported = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import)
                for alias in node.names}
    imported |= {node.module.split(".")[0] for node in ast.walk(tree)
                 if isinstance(node, ast.ImportFrom) and node.module}

    assert imported & app_modules == set()


# Each refusal in the three languages


@pytest.mark.parametrize("language", ["de", "fr", "en"])
def test_a_letter_that_is_no_mapping_is_named_in_the_app_language(language):
    assert said(refusal(lambda: anschreiben.pruefe_brief(["eine Liste"])), language) == {
        "de": "Das Anschreiben muss eine YAML-Zuordnung sein",
        "fr": "La lettre de motivation doit être un mappage YAML",
        "en": "The cover letter must be a YAML mapping",
    }[language]


@pytest.mark.parametrize("language", ["de", "fr", "en"])
def test_missing_fields_are_named_in_the_app_language_with_their_keys(language):
    letter = {key: value for key, value in valid_letter().items() if key not in ("anrede", "gruss")}

    assert said(refusal(lambda: anschreiben.pruefe_brief(letter)), language) == {
        "de": "Im Anschreiben fehlen: anrede, gruss",
        "fr": f"Il manque dans la lettre de motivation{NBSP}: anrede, gruss",
        "en": "Missing from the cover letter: anrede, gruss",
    }[language]


@pytest.mark.parametrize("language", ["de", "fr", "en"])
def test_a_recipient_that_is_no_list_is_named_in_the_app_language(language):
    letter = valid_letter(empfaenger="Beispiel AG")

    assert said(refusal(lambda: anschreiben.pruefe_brief(letter)), language) == {
        "de": "empfaenger muss eine Liste von Zeilen sein, z.B. [Firma AG, Strasse 1, 3000 Bern]",
        "fr": f"empfaenger doit être une liste de lignes, p.{NBSP}ex. [Firma AG, Strasse 1, 3000 Bern]",
        "en": "empfaenger must be a list of lines, e.g. [Firma AG, Strasse 1, 3000 Bern]",
    }[language]


@pytest.mark.parametrize("language", ["de", "fr", "en"])
def test_an_unknown_letter_language_is_named_in_the_app_language(language):
    letter = valid_letter(sprache="it")

    assert said(refusal(lambda: anschreiben.pruefe_brief(letter)), language) == {
        "de": "sprache muss eine von de, en, fr sein, nicht 'it'",
        "fr": "sprache doit être l'une des valeurs de, en, fr, et non 'it'",
        "en": "sprache must be one of de, en, fr, not 'it'",
    }[language]


@pytest.mark.parametrize("language", ["de", "fr", "en"])
def test_a_field_that_is_no_text_is_named_in_the_app_language(language):
    letter = valid_letter(gruss=["Freundliche", "Grüsse"])

    assert said(refusal(lambda: anschreiben.pruefe_brief(letter)), language) == {
        "de": "gruss muss Text sein",
        "fr": "gruss doit être du texte",
        "en": "gruss must be text",
    }[language]


@pytest.mark.parametrize("language", ["de", "fr", "en"])
def test_a_letter_without_sender_and_cv_is_named_in_the_app_language(language):
    call = lambda: anschreiben.bereite_vor(valid_letter(), None, datetime.date(2026, 11, 24))  # noqa: E731

    assert said(refusal(call), language) == {
        "de": "Kein absender im Anschreiben und kein Lebenslauf angegeben (lebenslauf: oder --cv)",
        "fr": "Ni absender dans la lettre de motivation, ni CV indiqué (lebenslauf: ou --cv)",
        "en": "No absender in the cover letter and no CV given (lebenslauf: or --cv)",
    }[language]


@pytest.mark.parametrize("language", ["de", "fr", "en"])
def test_a_cv_that_is_not_there_is_named_in_the_app_language(language, tmp_path):
    missing = tmp_path / "cv.yaml"

    assert said(refusal(lambda: anschreiben.lade_cv(tmp_path / "brief.yaml", {}, str(missing))), language) == {
        "de": f"Lebenslauf nicht gefunden: {missing}",
        "fr": f"CV introuvable{NBSP}: {missing}",
        "en": f"CV not found: {missing}",
    }[language]


def test_other_errors_pass_unchanged():
    with pytest.raises(KeyError, match="anders"):
        with letter_messages.in_app_language():
            raise KeyError("anders")


# The routes: the letter editor, Inhalte als Text and Unterlagen erstellen


def test_the_letter_editor_names_an_empty_field_in_french_and_english(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "fr")

    assert refused(server, LETTER_ROUTE, letter_body(server, anrede=" "), id=BRIEF_ID) == (
        f"Il manque dans la lettre de motivation{NBSP}: anrede")
    store_language(server.kontext.daten, "en")
    assert refused(server, LETTER_ROUTE, letter_body(server, gruss=""), id=BRIEF_ID) == (
        "Missing from the cover letter: gruss")


def test_the_letter_editor_names_an_empty_field_in_german_with_the_preview_off(server, no_preview):  # noqa: F811
    store_language(server.kontext.daten, "fr")

    assert refused(server, LETTER_ROUTE, letter_body(server, anrede=""), id=BRIEF_ID) == "Im Anschreiben fehlen: anrede"


def test_inhalte_als_text_names_the_letter_check_in_english(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "en")
    rel = unterlagen.letter_source(server.kontext.daten, BRIEF_ID).relative_to(server.kontext.daten).as_posix()
    text = yaml.safe_dump(valid_letter(sprache="it"), allow_unicode=True)

    assert refused(server, "/api/inhalt/pruefen", {"text": text}, datei=rel) == (
        "sprache must be one of de, en, fr, not 'it'")


def test_unterlagen_erstellen_names_the_letter_check_in_french(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "fr")
    write_letter(server, {key: value for key, value in valid_letter().items() if key != "gruss"})

    assert refused(server, "/api/unterlagen", {}, id=BRIEF_ID) == (
        f"Il manque dans la lettre de motivation{NBSP}: gruss")


def test_unterlagen_erstellen_names_the_letter_check_of_a_dossier_in_english(server, preview):  # noqa: F811
    store_language(server.kontext.daten, "en")
    register = server.kontext.register()
    register.speichere({**register.hole(BRIEF_ID), "unterlagen": "dossier"})
    write_letter(server, valid_letter(empfaenger="Beispiel AG"))

    assert refused(server, "/api/unterlagen", {}, id=BRIEF_ID) == (
        "empfaenger must be a list of lines, e.g. [Firma AG, Strasse 1, 3000 Bern]")


def test_unterlagen_erstellen_names_the_letter_check_in_german_with_the_preview_off(server, no_preview):  # noqa: F811
    store_language(server.kontext.daten, "en")
    write_letter(server, valid_letter(betreff=5))

    status, answer = post(server, "/api/unterlagen", {}, id=BRIEF_ID)

    assert status == 400
    assert json.dumps(answer, ensure_ascii=False) == '{"fehler": "betreff muss Text sein"}'
