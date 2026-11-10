"""Design "Register" (G16, G39) on the dossier foundation, following docs/design/dossier.md, design C.

All data is invented: the example CV, the sample cover letter and dossier files written here.
"""
import datetime

import pytest
from pypdf import PdfReader

import dossier
import dossier_data
from dossier_samples import assert_in_order, build_dossier, example_cv, flat, page_texts, pdftotext

THEME = "dossier-register"
TODAY = datetime.date(2026, 11, 10)


@pytest.fixture
def make(tmp_path):
    """Builds all three PDFs of the design Register from invented inputs in tmp_path."""
    counter = iter(range(100))

    def _make(*options: str, cv: dict | None = None, dossier_file: dict | None = None):
        return build_dossier(tmp_path / f"run{next(counter)}", "--theme", THEME, *options, cv=cv,
                             dossier_file=dossier_file)

    return _make


@pytest.fixture(scope="module")
def example(tmp_path_factory):
    return build_dossier(tmp_path_factory.mktemp("register") / "example", "--theme", THEME)


def with_references() -> dict:
    cv = example_cv()
    cv["references"] = [{"name": "Petra Muster, Teamleiterin Beispiel AG", "reference": "079 111 11 11"}]
    return cv


# Duration


@pytest.mark.parametrize("entry, expected", [
    ({"startDate": "2019-03"}, "7 J. 9 M."),
    ({"startDate": 2015, "endDate": 2019}, "5 J."),
    ({"startDate": "2026-09", "endDate": "2026-11"}, "3 M."),
    ({"position": "ohne Datum"}, None),
])
def test_duration_from_the_dates_up_to_today(entry, expected):
    assert dossier_data.duration(entry, TODAY, "de") == expected


# The built files


def test_entry_point_builds_dossier_and_single_files(example):
    for pdf in (example.dossier, example.cv, example.letter):
        assert pdf.read_bytes().startswith(b"%PDF")


def test_cover_is_the_table_of_contents(example):
    pages = page_texts(example.dossier)
    cover = pages[0]

    assert_in_order(cover, ["Erika Beispiel", "Bewerbung", "Data Engineer", "Beispiel AG", "Inhalt",
                            "Anschreiben", "Lebenslauf", "Beilagen", "Arbeitszeugnis Beispiel AG",
                            "Diplom Bachelor Informatik"])
    letter_page = next(i for i, p in enumerate(pages) if "Sehr geehrte Frau Meier" in p) + 1
    assert f"Anschreiben Bewerbung als Data Engineer {letter_page}" in flat(cover)


def test_page_sequence_with_attachments(example):
    pages = page_texts(example.dossier)

    assert "Sehr geehrte Frau Meier" in pages[1]
    assert "Berufserfahrung" in flat(" ".join(pages[2:-1]))
    assert_in_order(pages[-1], ["Beilagen", "1", "Arbeitszeugnis Beispiel AG", "2", "Diplom Bachelor Informatik",
                                "Juni 2015"])


def test_cover_reads_name_and_contact(example):
    assert_in_order(page_texts(example.dossier)[0], ["Erika Beispiel", "Musterweg 1", "3000 Bern", "079 000 00 00",
                                                     "erika@example.ch"])


def test_tab_labels_are_not_read_as_text(example):
    pages = [flat(p) for p in page_texts(example.dossier)]
    letter, cv_pages, attachments = pages[1], pages[2:-1], pages[-1]

    assert dossier.query(example, "<dossier-tab>", part="dossier") != []
    assert not any(label in letter for label in ("Lebenslauf", "Beilagen", "Referenzen"))
    for page in cv_pages:
        assert not any(label in page for label in ("Anschreiben", "Beilagen"))
    assert not any(label in attachments for label in ("Anschreiben", "Lebenslauf"))


def test_single_files_carry_no_tab_labels(example):
    assert dossier.query(example, "<dossier-tab>", part="cv") == []
    assert dossier.query(example, "<dossier-tab>", part="letter") == []


def test_tab_labels_are_pdf_artifacts(example):
    content = b"".join(page.get_contents().get_data() for page in PdfReader(example.dossier).pages)

    assert b"/Artifact" in content


def test_letter_box_with_position_workload_and_company(example):
    letter = pdftotext(example.letter)

    assert_in_order(letter, ["Erika Beispiel", "Data Engineer", "80–100 %", "Beispiel AG", "Sehr geehrte Frau Meier",
                             "Freundliche Grüsse"])
    assert "Berufserfahrung" not in letter and "Inhalt" not in letter


def test_cv_tables_read_period_duration_and_station(example):
    text = pdftotext(example.cv)

    assert_in_order(text, ["Erika Beispiel", "Berufserfahrung", "März 2019 – heute", "J.", "Software-Entwicklerin",
                           "Beispiel AG", "Entwicklung einer Plattform", "2015 – 2019", "5 J.", "Junior-Entwicklerin",
                           "Muster GmbH", "Wartung von Webshops"])
    assert "Sehr geehrte" not in text and "Beilagen" not in text


def test_cv_section_titles_are_headings(example):
    titles = [entry.title for entry in PdfReader(example.cv).outline if not isinstance(entry, list)]

    assert {"Profil", "Berufserfahrung", "Fähigkeiten", "Sprachen", "Interessen"} <= set(titles)


def test_interests_are_a_word_list_without_icons(example):
    assert dossier.query(example, "<dossier-icon>") == []
    assert "Wandern, Fotografie" in flat(pdftotext(example.cv))


def test_language_levels_are_words(example):
    text = flat(pdftotext(example.cv))

    assert "C2 · Muttersprache" in text and "C1 · Fliessend" in text


def test_without_references_the_cv_says_on_request(example):
    assert "Auf Anfrage." in flat(pdftotext(example.cv))


def test_references_get_their_own_page(make):
    result = make(cv=with_references())
    pages = page_texts(result.dossier)

    assert_in_order(pages[-1], ["Referenzen", "Petra Muster, Teamleiterin Beispiel AG", "079 111 11 11"])
    assert "Auf Anfrage." not in flat(" ".join(pages))
    assert "Referenzen" in flat(pages[0])


def test_optional_pages_without_content_are_dropped(make):
    bare = make(dossier_file={})
    pages = page_texts(bare.dossier)

    assert "Arbeitszeugnis" not in flat(" ".join(pages))
    assert "Beilagen" not in flat(" ".join(pages))
    assert "Sehr geehrte Frau Meier" in pages[1]
    assert "Auf Anfrage." in flat(pages[-1])


def test_no_level_anywhere_draws_no_badge(make):
    cv = example_cv()
    for language in cv["languages"]:
        language.pop("x-level", None)

    assert dossier.query(make(cv=cv), "<dossier-level>") == []


def test_partial_levels_say_without_level_and_never_invent(make):
    cv = example_cv()
    for language in cv["languages"]:
        language.pop("x-level", None)
    cv["skills"][0]["keywords"] = ["Python", {"name": "SQL", "level": 5}]
    result = make(cv=cv)

    assert dossier.query(result, "<dossier-level>") == [{"level": None}, {"level": 5}]
    assert_in_order(pdftotext(result.cv), ["Python", "ohne Angabe", "SQL", "sehr gut"])
