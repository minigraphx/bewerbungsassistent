"""Dossier foundation and the design "Siegel" (G16, G39), following docs/design/dossier.md.

All data is invented: the example CV, the sample cover letter and dossier files written here.
"""
import copy
import json
import re
import shutil
import subprocess

import pytest
import typst
import yaml
from pypdf import PdfReader

import build
import dossier
import dossier_data

DATA = build.ROOT / "data"
THEMES = build.ROOT / "themes"
TOKENS_JSON = build.ROOT.parent / "docs" / "design" / "system" / "tokens.json"
EXAMPLE = DATA / "dossier-beispiel.yaml"


def pdftotext(pdf) -> str:
    tool = shutil.which("pdftotext")
    assert tool, "pdftotext (poppler) is needed to check the reading order"
    return subprocess.run([tool, "-enc", "UTF-8", str(pdf), "-"], capture_output=True, text=True, check=True).stdout


def page_texts(pdf) -> list[str]:
    return [p for p in pdftotext(pdf).split("\f")][: len(PdfReader(pdf).pages)]


def flat(text: str) -> str:
    return " ".join(text.split())


def assert_in_order(text: str, parts: list[str]) -> None:
    text = flat(text)
    position = 0
    for part in parts:
        found = text.find(part, position)
        assert found >= 0, f"{part!r} missing or out of order after position {position} in: {text[:600]}"
        position = found + len(part)


def example_cv() -> dict:
    return yaml.safe_load((DATA / "beispiel.yaml").read_text(encoding="utf-8"))


def example_dossier() -> dict:
    return yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))


@pytest.fixture
def make(tmp_path):
    """Writes CV, letter and dossier file to tmp_path, builds all three PDFs and returns the result."""
    counter = iter(range(100))

    def _make(cv: dict | None = None, dossier_file: dict | None = None, letter: dict | None = None):
        n = next(counter)
        folder = tmp_path / f"run{n}"
        folder.mkdir()
        cv_path = folder / "cv.yaml"
        cv_path.write_text(yaml.safe_dump(cv or example_cv(), allow_unicode=True), encoding="utf-8")
        letter_data = letter or yaml.safe_load((DATA / "anschreiben-beispiel.yaml").read_text(encoding="utf-8"))
        letter_path = folder / "brief.yaml"
        letter_path.write_text(yaml.safe_dump({**letter_data, "lebenslauf": "cv.yaml"}, allow_unicode=True),
                               encoding="utf-8")
        file_data = {**(example_dossier() if dossier_file is None else dossier_file),
                     "lebenslauf": "cv.yaml", "anschreiben": "brief.yaml"}
        file_path = folder / "dossier.yaml"
        file_path.write_text(yaml.safe_dump(file_data, allow_unicode=True), encoding="utf-8")
        return dossier.main([str(file_path), "--build-dir", str(folder / "build"), "--out-dir", str(folder / "out")])

    return _make


@pytest.fixture(scope="module")
def example(tmp_path_factory):
    folder = tmp_path_factory.mktemp("example")
    return dossier.main([str(EXAMPLE), "--build-dir", str(folder / "build"), "--out-dir", str(folder / "out")])


# Tokens


def test_tokens_take_colours_spacing_and_radii_from_the_design_system():
    source = (THEMES / "tokens.typ").read_text(encoding="utf-8")
    system = json.loads(TOKENS_JSON.read_text(encoding="utf-8"))
    colours = dict(re.findall(r'^\s*([a-z-]+): rgb\("(#[0-9a-f]{6})"\)', source, re.M))
    lengths = dict(re.findall(r"^\s*((?:space|radius)-[a-z0-9]+): (\d+)pt", source, re.M))

    for name in ("bg", "surface", "surface-subtle", "accent-subtle", "line", "line-strong", "text-strong", "text",
                 "text-muted", "accent", "on-accent"):
        token = next(t for t in system["color"]["tokens"] if t["name"] == name)
        assert colours.get(name) == token["value"]["light"], name
    for token in system["spacing"]["tokens"] + [t for t in system["radius"]["tokens"] if t["name"] != "radius-full"]:
        assert lengths.get(token["name"]) == token["value"].removesuffix("px"), token["name"]


@pytest.mark.parametrize("accent, expected", [("#38495d", "#ffffff"), ("#f0c040", "#27333f")])
def test_text_on_the_accent_follows_contrast(accent, expected):
    probe = ('#import "/themes/tokens.typ": on-accent\n'
             f'#metadata(on-accent(rgb("{accent}")).to-hex())<probe>\n').encode()

    result = json.loads(typst.query(probe, "<probe>", field="value", one=True, root=str(build.ROOT)))
    assert result == expected


# Data extensions


@pytest.mark.parametrize("value, level", [(1, 1), (6, 6), ("A1", 1), ("a2", 2), ("B1", 3), ("B2", 4), ("C1", 5),
                                          ("C2", 6), (None, None)])
def test_levels_are_one_to_six_or_cefr(value, level):
    assert dossier_data.parse_level(value, "x") == level


@pytest.mark.parametrize("value", [0, 7, 2.5, True, "D1", "gut", ""])
def test_invalid_levels_are_refused(value):
    with pytest.raises(ValueError, match="1 bis 6"):
        dossier_data.parse_level(value, "skills")


def test_no_level_in_a_group_means_no_graphic():
    groups = dossier_data.skill_groups([{"name": "Web", "keywords": ["Vue.js", "Django"]}])

    assert groups == [{"name": "Web", "graphic": False,
                       "items": [{"name": "Vue.js", "level": None}, {"name": "Django", "level": None}]}]


def test_one_level_in_a_group_shows_the_graphic_for_all_and_invents_none():
    groups = dossier_data.skill_groups([
        {"name": "Web", "keywords": [{"name": "Vue.js", "level": 5}, "Django", {"name": "REST-APIs"}]},
        {"name": "Daten", "keywords": ["pandas"]},
    ])

    assert groups[0] == {"name": "Web", "graphic": True, "items": [
        {"name": "Vue.js", "level": 5}, {"name": "Django", "level": None}, {"name": "REST-APIs", "level": None}]}
    assert groups[1]["graphic"] is False


def test_language_levels_accept_cefr_and_keep_the_fluency_text():
    group = dossier_data.language_group([
        {"language": "Deutsch", "fluency": "Muttersprache", "x-level": 6},
        {"language": "Englisch", "fluency": "Fliessend", "x-level": "C1"},
        {"language": "Französisch", "fluency": "Grundkenntnisse"},
    ])

    assert group == {"graphic": True, "items": [
        {"language": "Deutsch", "fluency": "Muttersprache", "level": 6},
        {"language": "Englisch", "fluency": "Fliessend", "level": 5},
        {"language": "Französisch", "fluency": "Grundkenntnisse", "level": None}]}


def test_monogram_from_the_name_or_x_monogramm():
    assert dossier_data.monogram({"name": "Erika Beispiel"}) == "EB"
    assert dossier_data.monogram({"name": "Erika von Beispiel"}) == "EB"
    assert dossier_data.monogram({"name": "Erika Beispiel", "x-monogramm": "EvB"}) == "EvB"


@pytest.mark.parametrize("value", ["", "ABCD", "E1", 3])
def test_invalid_monogram_is_refused(value):
    with pytest.raises(ValueError, match="x-monogramm"):
        dossier_data.monogram({"name": "Erika Beispiel", "x-monogramm": value})


def test_interest_icons_come_from_the_catalogue():
    catalogue = dossier.icon_catalogue()
    items = dossier_data.interests([{"name": "Wandern", "x-icon": "mountain"}, {"name": "Lesen"}], catalogue)

    assert items == [{"name": "Wandern", "icon": "mountain"}, {"name": "Lesen", "icon": None}]
    with pytest.raises(ValueError, match="x-icon"):
        dossier_data.interests([{"name": "Segeln", "x-icon": "sailboat-unknown"}], catalogue)


def test_letter_heading_uses_its_fields_or_falls_back():
    letter = {"empfaenger": ["Beispiel AG", "Musterstrasse 5"], "betreff": "Bewerbung als Data Engineer"}

    assert dossier_data.letter_heading(letter, "de") == {
        "company": "Beispiel AG", "position": None, "workload": None, "reference": None, "intro": None,
        "line": "Bewerbung als Data Engineer"}
    assert dossier_data.letter_heading({**letter, "firma": "Muster GmbH", "stelle": "Data Engineer",
                                        "pensum": "80 %", "referenz": "DE-7"}, "de") == {
        "company": "Muster GmbH", "position": "Data Engineer", "workload": "80 %", "reference": "DE-7",
        "intro": "Bewerbung als", "line": "Bewerbung als Data Engineer"}


def test_dossier_file_fields_are_read_and_missing_ones_are_empty():
    pages = dossier_data.dossier_pages({
        "gruss": "Guten Tag.", "kennzahlen": [{"wert": 10, "text": "Jahre Praxis"}],
        "anlagen": ["Arbeitszeugnis", {"name": "Diplom", "datum": "2015-06"}]})

    assert pages == {"greeting": "Guten Tag.", "thanks": None,
                     "figures": [{"value": "10", "text": "Jahre Praxis"}],
                     "attachments": [{"name": "Arbeitszeugnis", "date": None}, {"name": "Diplom", "date": "2015-06"}]}
    assert dossier_data.dossier_pages({}) == {"greeting": None, "thanks": None, "figures": [], "attachments": []}


@pytest.mark.parametrize("data", [{"gruss": 3}, {"kennzahlen": [{"wert": 1}]}, {"anlagen": [{"datum": "2020"}]},
                                  {"farbe": "rot"}])
def test_invalid_dossier_file_is_refused(data):
    with pytest.raises(ValueError):
        dossier_data.dossier_pages(data)


# Lucide icons


def test_icons_are_a_small_lucide_subset_with_its_isc_licence():
    licence = (THEMES / "icons" / "LICENSE").read_text(encoding="utf-8")
    catalogue = dossier.icon_catalogue()

    assert "ISC License" in licence and "Lucide Contributors" in licence
    assert 0 < len(catalogue) <= 20
    for name in catalogue:
        svg = (THEMES / "icons" / f"{name}.svg").read_text(encoding="utf-8")
        assert 'stroke="currentColor"' in svg and 'viewBox="0 0 24 24"' in svg


# The built files


def test_entry_point_builds_the_dossier_and_the_two_single_files(example):
    for pdf in (example.dossier, example.cv, example.letter):
        assert pdf.read_bytes().startswith(b"%PDF")
    assert example.dossier.name == "dossier.pdf"
    assert {example.cv.name, example.letter.name} == {"lebenslauf.pdf", "anschreiben.pdf"}


def test_dossier_page_sequence(example):
    pages = page_texts(example.dossier)

    assert "Kurz vorgestellt" in pages[1]
    assert "Sehr geehrte Frau Meier" in pages[2]
    assert "Berufserfahrung" in flat(" ".join(pages[3:-1]))
    assert "Danke" in pages[-1]
    assert "Sehr geehrte Frau Meier" not in flat(" ".join(pages[3:]))


def test_cover_reads_name_application_and_contact_in_order(example):
    cover = page_texts(example.dossier)[0]

    assert_in_order(cover, ["Erika Beispiel", "Software-Entwicklerin – Web und Daten", "Bewerbung als",
                            "Data Engineer", "Beispiel AG", "Musterweg 1", "3000 Bern", "079 000 00 00",
                            "erika@example.ch"])


def test_cv_reads_period_before_title_company_and_bullets(example):
    text = pdftotext(example.cv)

    assert_in_order(text, ["Erika Beispiel", "Profil", "Berufserfahrung", "März 2019 – heute",
                           "Software-Entwicklerin", "Beispiel AG", "Entwicklung einer Plattform für Kundendaten",
                           "2015 – 2019", "Junior-Entwicklerin", "Muster GmbH", "Wartung von Webshops"])
    for word in ("Python", "Deutsch", "Muttersprache", "Wandern", "Fotografie", "Bachelor Informatik"):
        assert word in text


def test_cv_section_titles_are_headings(example):
    titles = [entry.title for entry in PdfReader(example.cv).outline if not isinstance(entry, list)]

    assert {"Profil", "Berufserfahrung", "Fähigkeiten", "Sprachen", "Interessen"} <= set(titles)


def test_single_files_hold_only_their_part(example):
    cv = flat(pdftotext(example.cv))
    letter = flat(pdftotext(example.letter))

    assert "Sehr geehrte Frau Meier" not in cv and "Kurz vorgestellt" not in cv
    assert_in_order(letter, ["Erika Beispiel", "Software-Entwicklerin – Web und Daten", "Beispiel AG",
                             "Data Engineer", "Sehr geehrte Frau Meier", "Freundliche Grüsse"])
    assert "Berufserfahrung" not in letter and "Danke" not in letter


def test_optional_pages_without_content_are_dropped(make):
    full = make()
    bare = make(dossier_file={})

    full_pages, bare_pages = page_texts(full.dossier), page_texts(bare.dossier)
    assert len(bare_pages) == len(full_pages) - 2
    assert "Kurz vorgestellt" not in flat(" ".join(bare_pages))
    assert "Danke" not in bare_pages[-1]
    assert "Sehr geehrte Frau Meier" in bare_pages[1]


def levels_drawn(result, part: str = "cv") -> list:
    return dossier.query(result, "<dossier-level>", part=part)


def test_no_level_anywhere_draws_no_graphic(make):
    cv = example_cv()
    for language in cv["languages"]:
        language.pop("x-level", None)

    assert levels_drawn(make(cv=cv)) == []


def test_partial_levels_draw_the_empty_form_and_never_invent(make):
    cv = example_cv()
    for language in cv["languages"]:
        language.pop("x-level", None)
    cv["skills"][1]["keywords"] = [{"name": "Vue.js", "level": 4}, "Django", "REST-APIs"]

    assert levels_drawn(make(cv=cv)) == [{"level": 4}, {"level": None}, {"level": None}]


def test_all_levels_drawn_as_given(make):
    cv = example_cv()
    cv["languages"] = [{"language": "Deutsch", "fluency": "Muttersprache", "x-level": "C2"},
                       {"language": "Englisch", "fluency": "Fliessend", "x-level": 5}]

    assert levels_drawn(make(cv=cv)) == [{"level": 6}, {"level": 5}]


def test_interest_icons_are_drawn_with_the_word(make):
    cv = example_cv()
    cv["interests"] = [{"name": "Wandern", "x-icon": "mountain"}, {"name": "Lesen"}]
    result = make(cv=cv)

    assert dossier.query(result, "<dossier-icon>") == [{"icon": "mountain"}]
    assert_in_order(pdftotext(result.cv), ["Interessen", "Wandern", "Lesen"])


def test_cover_counts_stations_with_an_upper_bound(make):
    cv = example_cv()
    cv["work"] = [copy.deepcopy(cv["work"][1]) for _ in range(9)]
    result = make(cv=cv)

    assert dossier.query(result, "<dossier-steps>", part="dossier") == [{"done": 6}]


@pytest.mark.parametrize("theme", ["zweispaltig", "einspaltig"])
def test_other_themes_print_keywords_with_a_level_by_name(baue, theme):
    cv = example_cv()
    cv["skills"][1]["keywords"] = [{"name": "Vue.js", "level": 4}, "Django"]

    text = flat(" ".join(baue(cv, "--theme", theme)))

    assert "Vue.js, Django" in text
