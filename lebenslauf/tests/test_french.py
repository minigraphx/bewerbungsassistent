"""CV, cover letter and dossier in French as well as German and English (#98, G12).

Every PDF is built from invented data: the example CV, the sample letter and the sample dossier file. A content field
written only as {de, en} shows its German in a French build.
"""
import datetime

import pytest
import yaml
from pypdf import PdfReader

import anschreiben
import build
import dossier_data
from cv_samples import beispiel, lang
from dossier_samples import build_dossier, example_letter, flat, pdftotext

LANGUAGES = ("de", "en", "fr")
NBSP = "\N{NO-BREAK SPACE}"

# What each build prints for the example data, per language
CV_LABELS = {
    "de": ("BERUFSERFAHRUNG", "SPRACHEN", "März 2019 – heute"),
    "en": ("EXPERIENCE", "LANGUAGES", "March 2019 – present"),
    "fr": ("EXPÉRIENCE PROFESSIONNELLE", "LANGUES", "mars 2019 – aujourd’hui"),
}
PLACE_AND_DATE = {"de": "Lausanne, 1. Dezember 2026", "en": "Lausanne, 1 December 2026",
                  "fr": "Lausanne, le 1er décembre 2026"}
DOSSIER_LABELS = {
    "dossier-siegel": {
        "de": ("Bewerbung als", "Kurz vorgestellt", "Berufserfahrung", "März 2019 – heute"),
        "en": ("Application as", "A short introduction", "Experience", "March 2019 – present"),
        "fr": ("Candidature au poste de", "En bref", "Expérience professionnelle", "mars 2019 – aujourd’hui"),
    },
    "dossier-raster": {
        "de": ("Stelle", "Unternehmen", "Inhalt", "Anschreiben, Lebenslauf", "Kontakt", "Auf einen Blick"),
        "en": ("Position", "Company", "Contents", "Cover letter, Curriculum vitae", "Contact", "At a glance"),
        "fr": ("Poste", "Entreprise", "Sommaire", "Lettre de motivation, Curriculum vitae", "Contact",
               "En un coup d’œil"),
    },
    "dossier-register": {
        "de": ("Teil", "Seite", "Beilagen", "Pensum 80–100 %", "Zeitraum", "Dauer", "Auf Anfrage.", "Juni 2015"),
        "en": ("Part", "Page", "Attachments", "Workload 80–100 %", "Period", "Duration", "On request.", "June 2015"),
        "fr": ("Partie", "Page", "Annexes", "Taux d’occupation 80–100 %", "Période", "Durée", "Sur demande.",
               "juin 2015"),
    },
}
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


def test_a_french_letter_without_place_has_the_date_alone():
    letter = {**example_letter(), "sprache": "fr", "ort": None, "datum": "2026-11-23"}
    assert anschreiben.bereite_vor(letter, beispiel(), datetime.date(2026, 11, 23))["ort_datum"] == "23 novembre 2026"


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
