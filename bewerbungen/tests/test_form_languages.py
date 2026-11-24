"""Meine Angaben, the form, in French and English (#431, G10, docs/design/sprachen.md).

The texts of onboarding/form.json and the page around the form (seiten/angaben.html, built from
onboarding/src/template.html) are in the catalog and in FERTIG without a gap; the scripts show the texts of form.json
through the T of onboarding/src/words.js. Stored values stay German: the values of options, suggestions and presets,
which go into cv.yaml and the search profile. dist/einstieg.html stays German (Andy, 23.11.2026). The scripts' own
words follow with #432 and #433. What the form shows at run time is tested in onboarding/tests/form_languages.test.cjs.
All data is invented.
"""
import json
import pathlib
import re

import language_sources
import page_translation
import sprachen_pruefen
import translation_catalog

ONBOARDING = sprachen_pruefen.BASE.parent / "onboarding"
FORM = ONBOARDING / "form.json"
PAGE = sprachen_pruefen.BASE / "seiten" / "angaben.html"
FILES = (FORM, PAGE, ONBOARDING / "src" / "words.js")
NBSP = chr(0xA0)


def catalog() -> translation_catalog.Catalog:
    return translation_catalog.load(translation_catalog.CATALOG_DIR)


def form() -> dict:
    return json.loads(FORM.read_text(encoding="utf-8"))


def write_form(folder: pathlib.Path, data: dict) -> pathlib.Path:
    path = folder / "form.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def found_texts(path: pathlib.Path) -> set[str]:
    return {item.text for item in language_sources.items((path,)) if item.kind == "text"}


SAMPLE = {
    "format": "bewerbungsassistent-einstieg",
    "tracks": {"job": "Stellensuche", "apprenticeship": "Lehrstellensuche"},
    "formats": {"canton": {"pattern": "^[A-Z]{2}$", "example": "BE"},
                "url": {"pattern": "^https?://", "example": "https://www.example.org/…"},
                "date": {"pattern": "^[0-9]{4}$", "example": "2024 oder 2024-08"}},
    "documents": {"title": "Unterlagen", "fileTypes": {"document": {"labels": ["PDF", "Textdateien (.txt)"],
                                                                     "extensions": ["pdf", "txt"]}},
                  "categories": [{"id": "zeugnisse", "title": "Zeugnisse", "kindLabel": {"job": "Zeugnis"},
                                  "kindPlural": "Zeugnisse", "fileTypes": ["document"]}]},
    "cantons": [{"code": "GE", "name": "Genf"}],
    "sections": [{
        "id": "searchJob", "title": {"job": "Suche"}, "intro": {"job": "Danach sucht die App."},
        "itemTitle": "Eintrag",
        "fields": [
            {"id": "remote", "label": "Homeoffice erwünscht?", "type": "select", "options": ["ja", "nein"]},
            {"id": "postalCode", "label": "PLZ", "type": "text", "format": "postalCode"},
            {"id": "group", "label": "Gruppe", "type": "select", "options": ["main"],
             "optionLabels": {"main": "Hauptprojekte"}, "emptyLabel": "ohne Gruppe"},
            {"id": "level", "label": "Stufe", "type": "select", "options": ["A1", "C2"]},
            {"id": "radius", "label": "Umkreis", "type": "select", "options": ["10 km"]},
            {"id": "tone", "label": "Ton", "type": "choice", "options": {"job": ["Kurz und direkt"]},
             "preset": {"option": 0}},
            {"id": "workload", "label": "Pensum", "type": "text", "preset": "nach Vereinbarung",
             "placeholder": "z.B. 80 %", "hint": {"apprenticeship": "Wie viel?"}},
            {"id": "fluency", "label": "Niveau", "type": "text", "suggestions": ["Muttersprache"],
             "messages": {"format": "Bitte eine Zahl."}},
            {"id": "portals", "label": "Portale", "type": "list", "tracks": ["job"],
             "options": ["jobs.ch"], "optionLabels": {"jobs.ch": "jobs.ch (alle Berufe)"}},
        ],
    }],
}


# The files of this step


def test_form_json_the_page_and_its_t_are_in_fertig():
    finished = {path.resolve() for path in sprachen_pruefen.FERTIG}

    assert [path.name for path in FILES if path.resolve() not in finished] == []


def test_form_json_the_page_and_its_t_have_no_gap():
    assert [str(gap) for gap in sprachen_pruefen.gaps(FILES, catalog())] == []


def test_every_source_includes_form_json_and_the_scripts_of_the_form():
    sources = sprachen_pruefen.app_sources()

    assert FORM in sources
    assert {ONBOARDING / "src" / name for name in ("words.js", "dom.js", "app.js", "validate.js")} <= set(sources)


# What the scanner reads in form.json


def test_the_scanner_reads_what_the_form_shows(tmp_path):
    texts = found_texts(write_form(tmp_path, SAMPLE))

    assert {"2024 oder 2024-08", "Unterlagen", "Textdateien (.txt)", "Zeugnisse", "Zeugnis", "Genf", "Suche",
            "Danach sucht die App.", "Eintrag", "Homeoffice erwünscht?", "ja", "nein", "Gruppe", "Hauptprojekte",
            "ohne Gruppe", "Stufe", "Umkreis", "Ton", "Kurz und direkt", "Pensum", "z.B. 80 %", "Wie viel?", "Niveau",
            "Bitte eine Zahl.", "Portale", "jobs.ch (alle Berufe)", "PLZ"} <= texts


def test_the_scanner_leaves_out_stored_values_codes_names_and_what_the_form_never_shows(tmp_path):
    texts = found_texts(write_form(tmp_path, SAMPLE))

    # Suggestions and presets go into the field as they are, an option with a label stays its value, the tracks are
    # never shown; codes, levels, units, names and addresses read the same in every language.
    assert texts.isdisjoint({"Muttersprache", "nach Vereinbarung", "main", "jobs.ch", "Stellensuche",
                             "Lehrstellensuche", "BE", "GE", "A1", "C2", "10 km", "PDF",
                             "https://www.example.org/…", "bewerbungsassistent-einstieg", "searchJob", "remote",
                             "document", "zeugnisse"})


def test_a_text_of_form_json_is_named_with_its_line(tmp_path):
    path = write_form(tmp_path, SAMPLE)
    line = next(number for number, text in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
                if "Homeoffice erwünscht?" in text)

    gaps = sprachen_pruefen.gaps((path,), translation_catalog.load(tmp_path / "leer"))

    assert (line, "Homeoffice erwünscht?") in {(gap.line, gap.text) for gap in gaps}


def test_a_literal_in_the_t_of_an_onboarding_script_is_a_text_while_another_script_needs_texte_t(tmp_path, monkeypatch):
    source = '"use strict";\nzeile.textContent = T("Zeile {nummer} entfernen", { nummer });\n'
    onboarding = tmp_path / "src"
    onboarding.mkdir()
    (onboarding / "dom.js").write_text(source, encoding="utf-8")
    (tmp_path / "seite.js").write_text(source, encoding="utf-8")
    monkeypatch.setattr(language_sources, "ONBOARDING_SRC", onboarding)

    found = [(item.path.name, item.kind, item.text)
             for item in language_sources.items((onboarding / "dom.js", tmp_path / "seite.js"))]

    assert found == [("seite.js", "leftover", "Zeile {nummer} entfernen"), ("dom.js", "text", "Zeile {nummer} entfernen")]


def test_the_steps_show_the_titles_and_intros_of_form_json_through_t():
    # app.js with its own words follows with #432; the sections of form.json it shows are part of the form.
    source = (ONBOARDING / "src" / "app.js").read_text(encoding="utf-8")

    assert "T(forTrack(section.intro, track))" in source
    assert "T(forTrack(section.title, track))" in source


# The catalog: glossary, tu and vous, stored values


def test_french_says_vous_for_the_job_and_tu_for_the_apprenticeship():
    person = next(section for section in form()["sections"] if section["id"] == "person")

    job = catalog().text(person["intro"]["job"], "fr")
    apprenticeship = catalog().text(person["intro"]["apprenticeship"], "fr")

    you = re.compile(r"\b(?:vous|votre|vos)\b", re.I)
    thou = re.compile(r"\b(?:tu|ton|ta|tes|te)\b", re.I)
    assert you.search(job) and not thou.search(job)
    assert thou.search(apprenticeship) and not you.search(apprenticeship)


def test_the_glossary_holds_for_rav_efz_eba_and_ki():
    assert "ORP" in catalog().text("job-room (Stellen der RAV, alle Berufe)", "fr")
    assert "RAV" in catalog().text("job-room (Stellen der RAV, alle Berufe)", "en")
    assert {"CFC", "AFP"} <= set(re.findall(r"[A-Z]{3}", catalog().text(
        "Berufe mit EFZ oder EBA (einer pro Zeile, der wichtigste zuerst)", "fr")))
    hint = next(field["hint"] for section in form()["sections"] for field in section["fields"]
                if field["id"] == "directions")
    assert "l'IA" in catalog().text(hint, "fr") and "the AI" in catalog().text(hint, "en")


def test_the_labels_a_message_cuts_at_the_bracket_keep_the_bracket_after_a_plain_space():
    # dom.js and validate.js name a field by its label up to " (": a translation keeps that space plain.
    labels = [label for section in form()["sections"] for field in section["fields"]
              for label in (field["label"].values() if isinstance(field["label"], dict) else [field["label"]])
              if " (" in label]

    broken = [(label, language) for label in labels for language in ("fr", "en")
              if " (" not in catalog().text(label, language)]

    assert len(labels) > 30
    assert broken == []


def test_option_values_suggestions_and_presets_of_form_json_stay_german():
    fields = {(section["id"], field["id"]): field for section in form()["sections"] for field in section["fields"]}

    assert fields[("searchJob", "remote")]["options"] == ["ja", "teilweise", "nein"]
    assert fields[("style", "tone")]["options"]["job"][0] == "Sachlich und freundlich"
    assert fields[("languages", "fluency")]["suggestions"][0] == "Muttersprache"
    assert fields[("searchJob", "start")]["preset"] == "nach Vereinbarung"
    assert catalog().text("Muttersprache", "fr") is None
    assert catalog().text("nach Vereinbarung", "fr") is None


# The page around the form


def test_the_page_around_the_form_speaks_french():
    page = PAGE.read_text(encoding="utf-8")

    french = page_translation.translate(page, "fr", catalog())

    assert '<html lang="fr"' in french
    assert [text for text in ("<title>Mes informations – Bewerbungsbegleiter</title>", "<h1>Mes informations</h1>",
                              'aria-label="Étapes"', '<script src="/uebersetzung.js?sprache=fr"></script>')
            if text not in french] == []
    # The inline script keeps its own words until #432; the page around it no longer says Schritte.
    assert 'aria-label="Schritte"' not in french


def test_the_scripts_and_the_form_of_the_page_stay_as_they_are_in_french_and_english():
    # The page allows its inline script by hash, and the form definition is data: neither may change.
    page = PAGE.read_text(encoding="utf-8")
    inline = re.compile(r"<script(?: type=\"application/json\" id=\"form-definition\")?>.*?</script>", re.S)

    for language in ("fr", "en"):
        assert inline.findall(page_translation.translate(page, language, catalog())) == inline.findall(page)


def test_the_page_stays_german_byte_for_byte():
    page = PAGE.read_text(encoding="utf-8")

    assert page_translation.translate(page, "de", catalog()) == page


def test_the_file_for_sharing_loads_no_translation():
    shared = (ONBOARDING / "dist" / "einstieg.html").read_text(encoding="utf-8")

    assert not re.search(r'<script[^>]*\ssrc="/(?:uebersetzung|texte)\.js', shared)
    assert '<html lang="de-CH">' in shared


def test_french_puts_a_no_break_space_before_a_colon_and_a_question_mark():
    assert catalog().text("Homeoffice erwünscht?", "fr").endswith(NBSP + "?")
    opening = catalog().text("Einstieg: Welcher Satz passt am besten?", "fr")
    assert NBSP + ":" in opening and opening.endswith(NBSP + "?")
