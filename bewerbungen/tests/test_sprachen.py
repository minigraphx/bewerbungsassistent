"""Translations of the app (#414, G10): the catalog is consistent, and each file in FERTIG has every text in fr and en.

The scanner behind it is `python -m sprachen_pruefen`; docs/design/sprachen.md explains the mechanism. The fixtures
under tests/fixtures/sprachen stand in for pages until the first page is translated (#95).
"""
import json
import pathlib
import subprocess
import sys

import pytest

import language_sources
import sprachen_pruefen
import translation_catalog

HERE = pathlib.Path(__file__).parent
BASE = HERE.parent
FIXTURES = HERE / "fixtures" / "sprachen"
FIXTURE_CATALOG = FIXTURES / "katalog"
# The fixture files that are complete; probe.html lacks one text on purpose.
COMPLETE_FIXTURES = (FIXTURES / "probe.js", FIXTURES / "probe.py")
MISSING_TEXT = "Dieser Satz steht absichtlich nicht im Katalog."


def fixture_catalog():
    return translation_catalog.load(FIXTURE_CATALOG)


def write_catalog(folder: pathlib.Path, name: str, entries: dict) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")


# The gate: catalog and finished files


def test_the_catalog_of_the_app_is_consistent_and_has_no_orphans():
    catalog = translation_catalog.load(translation_catalog.CATALOG_DIR)
    sets = language_sources.text_sets()

    assert sprachen_pruefen.catalog_problems(catalog, sets) == ()
    assert sprachen_pruefen.orphans(catalog, language_sources.items(sprachen_pruefen.app_sources()), sets) == ()


def test_every_file_in_fertig_has_each_text_in_french_and_english():
    catalog = translation_catalog.load(translation_catalog.CATALOG_DIR)

    assert [str(gap) for gap in sprachen_pruefen.gaps(sprachen_pruefen.FERTIG, catalog)] == []


def test_the_fixture_catalog_is_consistent_and_has_no_orphans():
    sources = (*COMPLETE_FIXTURES, FIXTURES / "probe.html")
    sets = language_sources.text_sets()

    assert sprachen_pruefen.catalog_problems(fixture_catalog(), sets) == ()
    assert sprachen_pruefen.orphans(fixture_catalog(), language_sources.items(sources), sets) == ()


def test_complete_fixtures_have_no_gaps():
    assert [str(gap) for gap in sprachen_pruefen.gaps(COMPLETE_FIXTURES, fixture_catalog())] == []


def test_a_deliberately_missing_text_is_named_with_file_and_line():
    gaps = sprachen_pruefen.gaps((FIXTURES / "probe.html",), fixture_catalog())

    line = next(number for number, text in enumerate((FIXTURES / "probe.html").read_text(encoding="utf-8").splitlines(), 1)
                if MISSING_TEXT in text)
    assert [str(gap) for gap in gaps] == [f"tests/fixtures/sprachen/probe.html:{line}: {MISSING_TEXT} [fr,en]"]


def test_a_text_missing_in_one_language_names_only_that_language(tmp_path):
    write_catalog(tmp_path / "katalog", "a.json", {"Neu laden": {"fr": "Recharger"}})
    page = tmp_path / "seite.html"
    page.write_text("<p>Neu laden</p>", encoding="utf-8")

    gaps = sprachen_pruefen.gaps((page,), translation_catalog.load(tmp_path / "katalog"))

    assert [(gap.text, gap.missing) for gap in gaps] == [("Neu laden", ("en",))]


def test_the_command_prints_each_gap_and_fails(tmp_path):
    result = subprocess.run([sys.executable, "-m", "sprachen_pruefen", "--katalog", str(FIXTURE_CATALOG),
                             "tests/fixtures/sprachen/probe.html"], cwd=BASE, capture_output=True, text=True)

    assert result.returncode == 1
    assert f"tests/fixtures/sprachen/probe.html:17: {MISSING_TEXT} [fr,en]" in result.stdout.splitlines()


def test_the_command_passes_on_complete_files():
    result = subprocess.run([sys.executable, "-m", "sprachen_pruefen", "--katalog", str(FIXTURE_CATALOG),
                             "tests/fixtures/sprachen/probe.js", "tests/fixtures/sprachen/probe.py"],
                            cwd=BASE, capture_output=True, text=True)

    assert (result.returncode, result.stdout) == (0, "")


# What the scanner reads


def test_scanner_reads_page_texts_attributes_and_text_sets():
    found = {(item.kind, item.text) for item in language_sources.items((FIXTURES / "probe.html",))}

    assert {("text", "Probeseite"), ("text", "Gespeichert & gesichert."), ("text", "Suchbegriff"),
            ("text", "Zum Beispiel Informatiker"), ("text", "Zeichen der App"), ("text", "Liste neu laden"),
            ("set", "fragen.label")} <= found
    assert ("text", "Ihre Frage") not in found  # the text set fills the element
    assert ("text", "Bewerbungsbegleiter") not in found  # a name stays


def test_scanner_skips_markers_comparisons_and_data_values():
    found = {(item.kind, item.text) for item in language_sources.items(COMPLETE_FIXTURES)}

    assert found == {("text", "Abgabe bis {datum}"), ("set", "fragen.label"), ("text", "Bitte einen Wert angeben."),
                     ("text", "Die Datei ist gesperrt.")}


def test_a_german_literal_outside_texte_t_is_a_gap(tmp_path):
    script = tmp_path / "seite.js"
    script.write_text('"use strict";\nzeile.textContent = "Noch nicht übersetzt";\n', encoding="utf-8")

    gaps = sprachen_pruefen.gaps((script,), fixture_catalog())

    assert [(gap.line, gap.text, gap.missing) for gap in gaps] == [(2, "Noch nicht übersetzt", ("Texte.t",))]


def test_a_german_template_literal_with_values_is_a_gap_while_code_templates_are_not(tmp_path):
    script = tmp_path / "seite.js"
    script.write_text('"use strict";\n'
                      'zeile.textContent = `Version ${info.version} ist verfügbar.`;\n'
                      'link.href = `/treffer?${suche}`;\n'
                      'zeile.className = `notice ${art} notice--gross`;\n'
                      'zeile.textContent = `${tag}.${monat}.${jahr}`;\n', encoding="utf-8")

    gaps = sprachen_pruefen.gaps((script,), fixture_catalog())

    assert [(gap.line, gap.text, gap.missing) for gap in gaps] == [(2, "Version ${info.version} ist verfügbar.",
                                                                     ("Texte.t",))]


def test_python_reads_t_with_values_and_names_a_formatted_message_that_needs_t(tmp_path):
    module = tmp_path / "routen.py"
    module.write_text("import ui_texts\n\n\n"
                      "def check(datum, name):\n"
                      "    if datum:\n"
                      "        return {'hinweis': ui_texts.T('Abgabe bis {datum}', datum=datum)}\n"
                      "    raise ValueError(f'Parameter {name} fehlt')\n", encoding="utf-8")

    found = {(item.kind, item.text) for item in language_sources.items((module,))}
    gaps = sprachen_pruefen.gaps((module,), fixture_catalog())

    assert ("text", "Abgabe bis {datum}") in found
    assert [(gap.line, gap.text, gap.missing) for gap in gaps] == [(7, "Parameter {name} fehlt", ("T",))]


def test_the_forms_of_a_text_set_are_no_leftovers():
    leftovers = {item.text for item in language_sources.items((language_sources.TEXTE_JS,)) if item.kind == "leftover"}

    assert "Ihre Frage" not in leftovers
    assert "Januar" in leftovers  # MONTH_NAMES are still German for every language


def test_an_unknown_text_set_in_a_page_is_a_gap(tmp_path):
    page = tmp_path / "seite.html"
    page.write_text('<p data-text="nav.suche">Stellen suchen</p>', encoding="utf-8")

    gaps = sprachen_pruefen.gaps((page,), fixture_catalog())

    assert [(gap.text, gap.missing) for gap in gaps] == [("texte:nav.suche", ("fr", "en"))]


def test_text_sets_are_read_as_node_reads_them():
    script = "process.stdout.write(JSON.stringify(require(process.argv[1]).TEXTE))"
    result = subprocess.run(["node", "-e", script, str(BASE / "seiten" / "texte.js")], capture_output=True, text=True,
                            check=True)

    assert language_sources.text_sets() == json.loads(result.stdout)


# The catalog


def test_files_merge_and_an_equal_duplicate_is_fine():
    catalog = fixture_catalog()

    assert catalog.text("Neu laden", "fr") == "Recharger"
    assert catalog.text("Abgabe bis {datum}", "en") == "Due by {datum}"
    assert catalog.form("fragen.label", "fr", "du") == "Ta question"


def test_a_duplicate_with_another_translation_fails_and_names_both_files(tmp_path):
    write_catalog(tmp_path, "a.json", {"Neu laden": {"fr": "Recharger", "en": "Reload"}})
    write_catalog(tmp_path, "b.json", {"Neu laden": {"fr": "Actualiser", "en": "Reload"}})

    with pytest.raises(translation_catalog.CatalogError, match=r"Neu laden.*a\.json.*b\.json"):
        translation_catalog.load(tmp_path)


def test_a_broken_file_fails_with_its_name(tmp_path):
    (tmp_path / "kaputt.json").write_text("[1, 2]", encoding="utf-8")

    with pytest.raises(translation_catalog.CatalogError, match="kaputt.json"):
        translation_catalog.load(tmp_path)


def test_a_missing_folder_is_an_empty_catalog(tmp_path):
    assert translation_catalog.load(tmp_path / "fehlt").entries == {}


@pytest.mark.parametrize("entries, problem", [
    ({"Neu laden": {"fr": "Recharger"}}, "Neu laden: en missing"),
    ({"Neu laden": {"fr": "Recharger", "en": ""}}, "Neu laden: en empty"),
    ({"Neu laden": {"fr": "Recharger", "en": "Reload", "it": "Ricaricare"}}, "Neu laden: unknown language it"),
    ({"Abgabe bis {datum}": {"fr": "À remettre", "en": "Due by {date}"}}, "Abgabe bis {datum}: fr placeholders"),
    ({"texte:gibt.es.nicht": {"fr": {"sie": "a", "du": "b"}, "en": {"sie": "c"}}}, "texte:gibt.es.nicht: not in texte.js"),
    ({"texte:fragen.label": {"fr": {"sie": "Votre question"}, "en": {"sie": "Your question"}}}, "texte:fragen.label: fr du missing"),
    ({"texte:nav.suche": {"fr": {"sie": "Chercher", "du": "Chercher"}, "en": {"sie": "Search"}}},
     "texte:nav.suche: fr lehrstelle missing"),
    ({"texte:fragen.label": {"fr": {"sie": "Votre question", "du": "Ta question", "ihr": "x"}, "en": {"sie": "Your question"}}},
     "texte:fragen.label: fr unknown form ihr"),
])
def test_catalog_problems_are_named(tmp_path, entries, problem):
    write_catalog(tmp_path, "a.json", entries)

    problems = sprachen_pruefen.catalog_problems(translation_catalog.load(tmp_path), language_sources.text_sets())

    assert any(found.startswith(problem) for found in problems), problems


def test_a_catalog_entry_no_source_uses_is_an_orphan(tmp_path):
    write_catalog(tmp_path, "a.json", {"Nirgends verwendet": {"fr": "Nulle part", "en": "Nowhere"}})

    orphans = sprachen_pruefen.orphans(translation_catalog.load(tmp_path),
                                       language_sources.items(COMPLETE_FIXTURES), language_sources.text_sets())

    assert orphans == ("Nirgends verwendet",)
