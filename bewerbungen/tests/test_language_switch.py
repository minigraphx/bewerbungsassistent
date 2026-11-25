"""The language switch beside the card (#435, G10): the route tells the page whether the translation is on, and the
switch's names and its trilingual label stay out of the translation and its gate.
"""
import json
import pathlib

import language_sources
import sprachen_pruefen
import translation_catalog
import ui_texts
from test_app import get, post, server  # noqa: F401  (server is a fixture)

SEITEN = pathlib.Path(__file__).resolve().parents[1] / "seiten"
SWITCH_FILES = (SEITEN / "sprache-logik.js", SEITEN / "sprachwahl.js")
LABEL = "Sprache · Langue · Language"
NAMES = ("Français", "English")


def test_the_route_says_the_translation_is_off_until_434(server, monkeypatch):  # noqa: F811
    monkeypatch.delenv(ui_texts.PREVIEW_ENV, raising=False)
    status, _, body = get(server, "/api/sprachen")
    assert status == 200 and json.loads(body)["uebersetzung"] is False
    status, answer = post(server, "/api/sprachen", {"app": "fr"})
    assert status == 200 and answer["app"] == "fr" and answer["uebersetzung"] is False


def test_the_route_says_the_translation_is_on_with_the_preview(server, monkeypatch):  # noqa: F811
    monkeypatch.setenv(ui_texts.PREVIEW_ENV, "1")
    status, answer = post(server, "/api/sprachen", {"app": "en"})
    assert status == 200 and answer["uebersetzung"] is True


def test_the_switch_is_in_the_gate_with_no_gap():
    assert set(SWITCH_FILES) <= set(sprachen_pruefen.FERTIG)
    catalog = translation_catalog.load(translation_catalog.CATALOG_DIR)
    assert [str(gap) for gap in sprachen_pruefen.gaps(SWITCH_FILES, catalog)] == []


def test_the_label_and_the_names_are_no_ui_text():
    texts = {item.text for item in language_sources.items(SWITCH_FILES)}
    assert LABEL not in texts and not set(NAMES) & texts
    catalog = translation_catalog.load(translation_catalog.CATALOG_DIR)
    assert LABEL not in catalog.entries
    assert not set(NAMES) & set(catalog.entries)


def test_the_note_on_a_folder_with_its_own_language_is_in_french_and_english():
    catalog = translation_catalog.load(translation_catalog.CATALOG_DIR)
    entry = catalog.entries["In diesem Ordner war schon eine Sprache der App gespeichert: {sprache}. Sie gilt jetzt."]
    # The wording of the UI/UX review (#435); French keeps its no-break space before the colon.
    assert entry["fr"] == ("Une langue de l'app était déjà enregistrée dans ce dossier\N{NO-BREAK SPACE}: {sprache}. "
                           "Elle s'applique maintenant.")
    assert entry["en"] == "An app language was already saved in this folder: {sprache}. It now applies."
