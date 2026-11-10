"""Design "Raster" (G16, G39) on the dossier foundation, following docs/design/dossier.md, design B.

All data is invented: the example CV, the sample cover letter and dossier files written here.
"""
import datetime

import pytest
from pypdf import PdfReader

import dossier
import dossier_data
from dossier_samples import assert_in_order, build_dossier, example_cv, flat, page_texts, pdftotext

THEME = "dossier-raster"
TODAY = datetime.date(2026, 11, 10)


@pytest.fixture
def make(tmp_path):
    """Builds all three PDFs of the design Raster from invented inputs in tmp_path."""
    counter = iter(range(100))

    def _make(*options: str, cv: dict | None = None, dossier_file: dict | None = None):
        return build_dossier(tmp_path / f"run{next(counter)}", "--theme", THEME, *options, cv=cv,
                             dossier_file=dossier_file)

    return _make


@pytest.fixture(scope="module")
def example(tmp_path_factory):
    return build_dossier(tmp_path_factory.mktemp("raster") / "example", "--theme", THEME)


# Timeline axis


def test_timeline_bars_follow_the_duration_and_keep_the_cv_numbers():
    work = [{"startDate": "2019-03", "endDate": None}, {"startDate": 2015, "endDate": 2019}]

    axis = dossier_data.timeline(work, TODAY)

    assert axis["earlier"] is False
    assert [bar["number"] for bar in axis["bars"]] == [1, 2]
    current, past = axis["bars"]
    assert current["current"] is True and past["current"] is False
    assert past["from"] == 0 and current["to"] == 1
    assert past["to"] > current["from"]
    assert {past["lane"], current["lane"]} == {0, 1}
    assert axis["lanes"] == 2
    assert [tick["year"] for tick in axis["ticks"]][0] == 2015 and axis["ticks"][-1]["year"] == 2026


def test_timeline_collects_stations_older_than_fifteen_years_as_earlier():
    work = [{"startDate": "2020-01"}, {"startDate": 1995, "endDate": 2000}, {"startDate": 2005, "endDate": 2016}]

    axis = dossier_data.timeline(work, TODAY)

    assert axis["earlier"] is True
    assert [bar["number"] for bar in axis["bars"]] == [1, 3]
    assert min(bar["from"] for bar in axis["bars"]) == 0


def test_timeline_without_dates_is_empty():
    assert dossier_data.timeline([{"position": "Ohne Datum"}], TODAY) == {
        "bars": [], "ticks": [], "lanes": 0, "earlier": False}


# The built files


def test_entry_point_builds_dossier_and_single_files(example):
    for pdf in (example.dossier, example.cv, example.letter):
        assert pdf.read_bytes().startswith(b"%PDF")
    assert example.theme == THEME


def test_page_sequence_with_glance_and_back_page(example):
    pages = page_texts(example.dossier)

    assert "Auf einen Blick" in pages[1] and "Jahre Praxis" in pages[1]
    assert "Sehr geehrte Frau Meier" in pages[2]
    assert "Berufserfahrung" in flat(" ".join(pages[3:-1]))
    assert "Danke für Ihre Zeit" in pages[-1]


def test_cover_reads_name_application_and_contact_in_order(example):
    cover = page_texts(example.dossier)[0]

    assert_in_order(cover, ["Erika Beispiel", "Software-Entwicklerin – Web und Daten", "Data Engineer",
                            "Beispiel AG", "Musterweg 1", "3000 Bern", "079 000 00 00", "erika@example.ch"])


def test_letter_head_is_the_band_with_the_company(example):
    letter = pdftotext(example.letter)

    assert_in_order(letter, ["Beispiel AG", "Bewerbung als", "Data Engineer", "Erika Beispiel",
                             "Sehr geehrte Frau Meier", "Freundliche Grüsse"])
    assert "Berufserfahrung" not in letter and "Auf einen Blick" not in letter


def test_cv_reads_number_and_period_before_each_station(example):
    text = pdftotext(example.cv)

    assert_in_order(text, ["Erika Beispiel", "Berufserfahrung", "1", "März 2019 – heute", "Software-Entwicklerin",
                           "Beispiel AG", "Entwicklung einer Plattform", "2", "2015 – 2019", "Junior-Entwicklerin",
                           "Muster GmbH", "Wartung von Webshops"])
    assert "Auf einen Blick" not in text and "Sehr geehrte" not in text


def test_cv_section_titles_are_headings(example):
    titles = [entry.title for entry in PdfReader(example.cv).outline if not isinstance(entry, list)]

    assert {"Profil", "Berufserfahrung", "Fähigkeiten", "Sprachen", "Interessen"} <= set(titles)


def test_optional_pages_without_content_are_dropped(make):
    bare = make(dossier_file={})
    pages = page_texts(bare.dossier)

    assert "Auf einen Blick" not in flat(" ".join(pages))
    assert "Danke" not in pages[-1]
    assert "Sehr geehrte Frau Meier" in pages[1]


def test_glance_page_needs_figures_and_back_page_needs_thanks(make):
    only_thanks = make(dossier_file={"dank": "Danke für Ihre Zeit.", "gruss": "Guten Tag."})
    pages = page_texts(only_thanks.dossier)

    assert "Auf einen Blick" not in flat(" ".join(pages))
    assert "Danke für Ihre Zeit" in pages[-1]


def test_timeline_axis_is_drawn_and_can_be_switched_off(make):
    with_axis = make()
    without_axis = make("--ohne-zeitachse")

    assert dossier.query(with_axis, "<dossier-axis>") == [{"bars": 2}]
    assert dossier.query(without_axis, "<dossier-axis>") == []
    assert_in_order(pdftotext(without_axis.cv), ["Berufserfahrung", "1", "März 2019 – heute", "Software-Entwicklerin"])


def test_no_level_anywhere_draws_no_grade_bar(make):
    cv = example_cv()
    for language in cv["languages"]:
        language.pop("x-level", None)

    assert dossier.query(make(cv=cv), "<dossier-level>") == []


def test_partial_levels_draw_dashed_fields_and_never_invent(make):
    cv = example_cv()
    for language in cv["languages"]:
        language.pop("x-level", None)
    cv["skills"][0]["keywords"] = ["Python", {"name": "SQL", "level": "B2"}]

    assert dossier.query(make(cv=cv), "<dossier-level>") == [{"level": None}, {"level": 4}]


def test_all_levels_drawn_as_given(make):
    assert dossier.query(make(), "<dossier-level>") == [{"level": 6}, {"level": 5}]


def test_interest_icons_with_the_word(make):
    result = make()

    assert dossier.query(result, "<dossier-icon>") == [{"icon": "mountain"}, {"icon": "camera"}]
    assert_in_order(pdftotext(result.cv), ["Interessen", "Wandern", "Fotografie"])
