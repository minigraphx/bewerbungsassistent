"""CV, cover letter and dossier in French as well as German and English (#98, G12).

Every PDF is built from invented data: the example CV, the sample letter and the sample dossier file. A content field
written only as {de, en} shows its German in a French build.
"""
import datetime
import json
import pathlib

import pytest
import typst
import yaml
from pypdf import PdfReader

import anschreiben
import build
import dossier_data
from typst_root import typst_root
from cv_samples import beispiel, lang
from dossier_samples import build_dossier, example_letter, flat, pdftotext

LANGUAGES = ("de", "en", "fr")
NBSP = "\N{NO-BREAK SPACE}"

# What each build prints for the example data, per language
CV_LABELS = {
    "de": ("BERUFSERFAHRUNG", "SPRACHEN", "März 2019 – heute"),
    "en": ("EXPERIENCE", "LANGUAGES", "March 2019 – present"),
    # Upper case keeps the accents
    "fr": ("EXPÉRIENCE PROFESSIONNELLE", "LANGUES", "mars 2019 – aujourd’hui", "COMPÉTENCES",
           "CENTRES D’INTÉRÊT", "FORMATION ET PERFECTIONNEMENT"),
}
PLACE_AND_DATE = {"de": "Lausanne, 1. Dezember 2026", "en": "Lausanne, 1 December 2026",
                  "fr": "Lausanne, le 1er décembre 2026"}
DOSSIER_LABELS = {
    "dossier-siegel": {
        "de": ("Bewerbung als", "Kurz vorgestellt", "Berufserfahrung", "März 2019 – heute"),
        "en": ("Application as", "A short introduction", "Experience", "March 2019 – present"),
        "fr": ("Poste visé", "En bref", "Expérience professionnelle", "mars 2019 – aujourd’hui",
               "Formation et perfectionnement"),
    },
    "dossier-raster": {
        "de": ("Stelle", "Unternehmen", "Inhalt", "Anschreiben, Lebenslauf", "Kontakt", "Auf einen Blick",
               "Bewerbung als Data Engineer"),
        "en": ("Position", "Company", "Contents", "Cover letter, Curriculum vitae", "Contact", "At a glance",
               "Application as Data Engineer"),
        "fr": ("Poste", "Entreprise", "Sommaire", "Lettre de motivation, Curriculum vitae", "Contact", "Aperçu",
               "Candidature au poste de Data Engineer"),
    },
    "dossier-register": {
        "de": ("Teil", "Seite", "Beilagen", "Pensum 80–100 %", "Zeitraum", "Dauer", "Station", "Auf Anfrage.",
               "Juni 2015", "Bewerbung als Data Engineer"),
        "en": ("Part", "Page", "Attachments", "Workload 80–100 %", "Period", "Duration", "Position", "On request.",
               "June 2015", "Application as Data Engineer"),
        "fr": ("Partie", "Page", "Annexes", "Taux d’occupation 80–100 %", "Période", "Durée", "Fonction",
               "Sur demande.", "juin 2015", "Candidature au poste de Data Engineer"),
    },
}
# The level words of the design Register, 1 to 6; each stays on one line
REGISTER_LEVELS = {
    "de": ("Einstieg", "Grundlagen", "solide", "gut", "sehr gut", "Expertise"),
    "en": ("Entry", "Basics", "Solid", "Good", "Very good", "Expert"),
    "fr": ("Initiation", "Notions", "Bases solides", "Bonne maîtrise", "Très bonne maîtrise", "Expertise"),
}
SUPERSCRIPT_FIRST = "1er"
# Labels a French dossier must not print; the example letter itself is German, so "Bewerbung als" is in its text
GERMAN_ONLY = ("Berufserfahrung", "Kurz vorgestellt", "Auf einen Blick", "Beilagen", "Zeitraum", "heute")


@pytest.fixture
def build_cv(tmp_path):
    def _build(cv: dict, *options: str) -> str:
        folder = tmp_path / "cv"
        folder.mkdir(exist_ok=True)
        data = folder / "cv.yaml"
        data.write_text(yaml.safe_dump(cv, allow_unicode=True), encoding="utf-8")
        out = folder / "cv.pdf"
        build.main([str(data), "--build-dir", str(folder / "build"), "-o", str(out), *options])
        return "".join(page.extract_text() for page in PdfReader(out).pages)

    return _build


@pytest.fixture
def build_letter(tmp_path):
    def _build(letter: dict) -> str:
        path = tmp_path / "brief.yaml"
        data = {**letter, "lebenslauf": str(build.ROOT / "data" / "beispiel.yaml")}
        path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        out = tmp_path / "brief.pdf"
        anschreiben.main([str(path), "--build-dir", str(tmp_path / "build"), "-o", str(out)])
        return PdfReader(out).pages[0].extract_text()

    return _build


# Dates and the place and date line


@pytest.mark.parametrize("day, expected", [(datetime.date(2026, 11, 23), "23 novembre 2026"),
                                           (datetime.date(2026, 12, 1), "1er décembre 2026"),
                                           (datetime.date(2027, 8, 1), "1er août 2027"),
                                           (datetime.date(2027, 2, 2), "2 février 2027")])
def test_the_letter_writes_the_date_in_french(day, expected):
    assert anschreiben.formatiere_datum(day, "fr") == expected


def test_german_and_english_dates_stay_as_they_were():
    assert anschreiben.formatiere_datum(datetime.date(2026, 12, 1), "de") == "1. Dezember 2026"
    assert anschreiben.formatiere_datum(datetime.date(2026, 12, 1), "en") == "1 December 2026"


@pytest.mark.parametrize("language", LANGUAGES)
def test_the_place_and_date_line_in_each_language(language):
    letter = {**example_letter(), "sprache": language, "ort": "Lausanne", "datum": "2026-12-01"}
    prepared = anschreiben.bereite_vor(letter, beispiel(), datetime.date(2026, 11, 23))
    assert prepared["ort_datum"] == PLACE_AND_DATE[language]


@pytest.mark.parametrize("language, expected", [("de", "23. November 2026"), ("en", "23 November 2026"),
                                                ("fr", "Le 23 novembre 2026")])
def test_a_letter_without_place_has_the_date_alone(language, expected):
    letter = {**example_letter(), "sprache": language, "ort": None, "datum": "2026-11-23"}
    assert anschreiben.bereite_vor(letter, beispiel(), datetime.date(2026, 11, 23))["ort_datum"] == expected


# The position in the heading of the letter


@pytest.mark.parametrize("position, line", [
    ("Informaticienne", "Candidature au poste d’Informaticienne"),
    ("Économiste", "Candidature au poste d’Économiste"),
    ("horloger", "Candidature au poste d’horloger"),
    ("Logisticien", "Candidature au poste de Logisticien"),
    ("Data Engineer", "Candidature au poste de Data Engineer"),
])
def test_the_french_line_elides_de_before_a_vowel_or_h(position, line):
    assert dossier_data.letter_heading({"stelle": position}, "fr")["line"] == line


def test_the_french_intro_above_the_position_is_its_own_phrase():
    assert dossier_data.letter_heading({"stelle": "Logisticien"}, "fr")["intro"] == "Poste visé"


@pytest.mark.parametrize("language, intro", [("de", "Bewerbung als"), ("en", "Application as")])
def test_german_and_english_headings_stay_as_they_were(language, intro):
    heading = dossier_data.letter_heading({"stelle": "Informatikerin"}, language)
    assert heading["intro"] == intro and heading["line"] == f"{intro} Informatikerin"


def test_a_letter_in_another_language_is_refused():
    with pytest.raises(ValueError, match="sprache"):
        anschreiben.pruefe_brief({**example_letter(), "sprache": "it"})


# Multilingual content


def test_french_content_is_chosen_where_it_is_written():
    data = {"summary": {"de": "Hallo", "en": "Hello", "fr": "Bonjour"}, "work": [{"highlights": [{"de": "eins", "fr": "un"}]}]}
    assert build.waehle_sprache(data, "fr") == {"summary": "Bonjour", "work": [{"highlights": ["un"]}]}


def test_a_field_without_french_falls_back_to_german_per_field():
    data = {"summary": {"de": "Hallo", "en": "Hello"}, "label": {"de": "Entwicklerin", "en": "Developer", "fr": "Développeuse"}}
    assert build.waehle_sprache(data, "fr") == {"summary": "Hallo", "label": "Développeuse"}


def test_english_keeps_its_choice_with_french_in_the_field():
    data = {"summary": {"de": "Hallo", "en": "Hello", "fr": "Bonjour"}, "label": {"de": "Entwicklerin", "fr": "Développeuse"}}
    assert build.waehle_sprache(data, "en") == {"summary": "Hello", "label": "Entwicklerin"}
    assert build.waehle_sprache(data, "de") == {"summary": "Hallo", "label": "Entwicklerin"}


# Durations of the design Register


@pytest.mark.parametrize("entry, expected", [
    ({"startDate": "2019-03"}, f"7{NBSP}ans 9{NBSP}mois"),
    ({"startDate": "2025-12"}, f"1{NBSP}an"),
    ({"startDate": "2026-06"}, f"6{NBSP}mois"),
])
def test_durations_in_french(entry, expected):
    assert dossier_data.duration(entry, datetime.date(2026, 11, 23), "fr") == expected


# PDFs in each language


@pytest.mark.parametrize("theme", ["zweispaltig", "einspaltig"])
@pytest.mark.parametrize("language", LANGUAGES)
def test_the_cv_prints_its_labels_and_dates_in_the_language(build_cv, theme, language):
    text = build_cv(beispiel(), "--lang", language, "--theme", theme)
    for label in CV_LABELS[language]:
        assert label in text
    if language == "fr":
        assert not any(german in text for german in ("BERUFSERFAHRUNG", "SPRACHEN", "heute", "März"))


@pytest.mark.parametrize("theme, lines", [
    ("zweispaltig", (f"Projets sur{NBSP}: https://github.com/example", f"Web{NBSP}: Vue.js")),
    ("einspaltig", (f"Web{NBSP}: Vue.js",)),
])
def test_a_french_cv_keeps_a_no_break_space_before_the_colon(build_cv, theme, lines):
    text = build_cv(beispiel(), "--lang", "fr", "--theme", theme)
    for line in lines:
        assert line in text


def test_a_german_cv_keeps_its_colon(build_cv):
    text = build_cv(beispiel(), "--lang", "de")
    assert "Projekte auf: https://github.com/example" in text and "Web: Vue.js" in text


def test_the_continued_heading_is_french(build_cv):
    text = build_cv(lang(beispiel()), "--lang", "fr")
    assert "EXPÉRIENCE PROFESSIONNELLE (SUITE)" in text


def test_a_french_cv_shows_german_where_french_is_missing(build_cv):
    cv = beispiel()
    cv["basics"]["summary"] = {"de": "Deutsches Profil.", "en": "English profile."}
    cv["work"][0]["highlights"][0] = {"de": "Deutscher Stichpunkt", "en": "English point", "fr": "Point en français"}
    text = build_cv(cv, "--lang", "fr")
    assert "Deutsches Profil." in text and "English profile." not in text
    assert "Point en français" in text and "Deutscher Stichpunkt" not in text


@pytest.mark.parametrize("language", LANGUAGES)
def test_the_letter_prints_place_and_date_in_its_language(build_letter, language):
    letter = {**example_letter(), "sprache": language, "ort": "Lausanne", "datum": "2026-12-01"}
    assert PLACE_AND_DATE[language] in flat(build_letter(letter))


@pytest.mark.parametrize("theme", sorted(DOSSIER_LABELS))
@pytest.mark.parametrize("language", LANGUAGES)
def test_the_dossier_prints_its_labels_in_the_language(tmp_path, theme, language):
    letter = {**example_letter(), "sprache": language}
    result = build_dossier(tmp_path / "dossier", "--theme", theme, "--lang", language, letter=letter)
    text = flat(pdftotext(result.dossier))
    for label in DOSSIER_LABELS[theme][language]:
        assert label in text, f"{label!r} missing in {theme} ({language})"
    if language == "fr":
        assert not [german for german in GERMAN_ONLY if german in text]
    for single in (result.cv, result.letter):
        assert PdfReader(single).pages


# The first of the month in superscript, the levels of Register, and the language of each PDF


def superscripts(entry: pathlib.Path, root: pathlib.Path, inputs: dict) -> list[str]:
    """The text of every superscript the document sets for the first of a month."""
    found = typst.query(str(entry), "<first-of-month>", root=str(root), font_paths=[str(build.ROOT / "fonts")],
                        sys_inputs=inputs)
    return [element["body"]["text"] for element in json.loads(found) if element["func"] == "super"]


def letter_superscripts(tmp_path: pathlib.Path, letter: dict) -> list[str]:
    path = tmp_path / "brief.yaml"
    path.write_text(yaml.safe_dump({**letter, "lebenslauf": str(build.ROOT / "data" / "beispiel.yaml")},
                                   allow_unicode=True), encoding="utf-8")
    folder = tmp_path / "build"
    anschreiben.main([str(path), "--build-dir", str(folder), "-o", str(tmp_path / "brief.pdf")])
    root = typst_root(folder, [build.ROOT / "themes"])
    entry = root.locate(build.ROOT / "themes" / "zweispaltig" / "anschreiben-main.typ")
    return superscripts(entry, root.path, {"data": root.typst_path(folder / "anschreiben.json")})


@pytest.mark.parametrize("place", ["Lausanne", None])
def test_the_french_letter_sets_the_first_of_the_month_in_superscript(tmp_path, place):
    letter = {**example_letter(), "sprache": "fr", "ort": place, "datum": "2026-12-01"}
    assert letter_superscripts(tmp_path, letter) == ["er"]


@pytest.mark.parametrize("language, day", [("fr", "2026-12-02"), ("de", "2026-12-01"), ("en", "2026-12-01")])
def test_other_dates_have_no_superscript(tmp_path, language, day):
    letter = {**example_letter(), "sprache": language, "ort": "Lausanne", "datum": day}
    assert letter_superscripts(tmp_path, letter) == []


def test_the_french_dossier_sets_the_first_of_the_month_in_superscript(tmp_path):
    letter = {**example_letter(), "sprache": "fr", "ort": "Lausanne", "datum": "2026-12-01"}
    result = build_dossier(tmp_path / "dossier", "--theme", "dossier-raster", "--lang", "fr", letter=letter)
    found = superscripts(result.root.locate(result.entries["dossier"]), result.root.path, result.inputs["dossier"])
    # The place line on the cover and in the letter
    assert found == ["er", "er"]
    assert "Lausanne, le 1er décembre 2026" in flat(pdftotext(result.letter))


@pytest.mark.parametrize("language", LANGUAGES)
def test_each_level_word_of_register_stays_on_one_line(tmp_path, language):
    cv = beispiel()
    cv["skills"][0]["keywords"] = [{"name": f"Outil {level}", "level": level} for level in range(1, 7)]
    result = build_dossier(tmp_path / "dossier", "--theme", "dossier-register", "--lang", language, cv=cv,
                           letter={**example_letter(), "sprache": language})
    text = pdftotext(result.cv)
    for word in REGISTER_LEVELS[language]:
        assert word in text, f"{word!r} missing or broken in {language}"


@pytest.mark.parametrize("theme", ["zweispaltig", "einspaltig"])
@pytest.mark.parametrize("language", LANGUAGES)
def test_the_cv_and_the_letter_carry_their_language(tmp_path, build_cv, build_letter, theme, language):
    build_cv(beispiel(), "--lang", language, "--theme", theme)
    build_letter({**example_letter(), "sprache": language})
    for pdf in (tmp_path / "cv" / "cv.pdf", tmp_path / "brief.pdf"):
        assert PdfReader(pdf).trailer["/Root"]["/Lang"] == language


@pytest.mark.parametrize("theme", sorted(DOSSIER_LABELS))
def test_every_french_dossier_file_carries_its_language(tmp_path, theme):
    result = build_dossier(tmp_path / "dossier", "--theme", theme, "--lang", "fr",
                           letter={**example_letter(), "sprache": "fr"})
    for pdf in (result.dossier, result.cv, result.letter):
        assert PdfReader(pdf).trailer["/Root"]["/Lang"] == "fr"
