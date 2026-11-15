"""Meine Angaben reads exclusions indented under a search direction, as vorlagen/suchprofil.md lays them out (#309).

The skill einstieg writes the profile after the template, where „   - Ausschluss:“ stands under the second direction;
the search reads that line, so the page shows it too and saving keeps its place and indentation. All data is invented.
"""
import pathlib

import pytest

from test_angaben import started  # noqa: F401  (fixture)
from test_angaben_read_back import bundle_from, drafts_of, read_back, save, write_basics

TEMPLATE = pathlib.Path(__file__).resolve().parents[2] / "vorlagen" / "suchprofil.md"

PROFILE = """# Suchprofil

Nach der Vorlage geschrieben.

## Suchrichtungen
1. Software-Entwicklung (Priorität 1)
2. Schulung mit IT-Bezug (Priorität 2)
   - Nur mit IT-Bezug im Titel oder Volltext: Informatik, ICT
   - Ausschluss: Vertrieb, Callcenter

## Region
- Wohnort: Thun
- Kantone (job-room): BE, FR
- Remote: ja

## Titelfilter
- Positiv: Entwickler
- Ausschluss: Praktikum

## Rahmen
- Frühester Start: 1. April
- Pensum: 60–80 %
"""
INDENTED = "   - Ausschluss: Vertrieb, Callcenter"


def write_profile(folder: pathlib.Path, text: str = PROFILE) -> None:
    """The style profile and building blocks of #217 beside it, so the form is complete and can be saved."""
    write_basics(folder)
    (folder / "suchprofil.md").write_text(text, encoding="utf-8")


def saved_with(server, folder: pathlib.Path, **search) -> str:
    read = read_back(server)
    bundle = bundle_from(read)
    bundle["data"]["searchJob"] = {**bundle["data"]["searchJob"], **search}
    status, answer = save(server, bundle, read["daten"])
    assert status == 200, answer
    return (folder / "suchprofil.md").read_text(encoding="utf-8")


def unknown_lines(read: dict) -> set[str]:
    return {line for group in read["fremd"] for line in group["zeilen"]}


def test_indented_exclusions_come_back_into_the_form(started):
    server, folder, _ = started
    write_profile(folder)

    read = read_back(server)

    assert read["daten"]["searchJob"]["exclusions"] == ["Vertrieb", "Callcenter"]
    assert INDENTED not in unknown_lines(read)
    assert "   - Nur mit IT-Bezug im Titel oder Volltext: Informatik, ICT" in unknown_lines(read)


def test_the_template_itself_shows_its_exclusions(started):
    server, folder, _ = started
    write_profile(folder, TEMPLATE.read_text(encoding="utf-8"))

    assert read_back(server)["daten"]["searchJob"]["exclusions"] == ["Bildung ohne IT-Bezug", "Recruiting"]


def test_the_page_reads_the_exclusions_the_search_reads(started):
    import search_plan
    server, folder, _ = started
    text = PROFILE.replace(INDENTED, "   - Ausschluss (Branchen): Vertrieb, Callcenter") + "- Ausschluss: Lager\n"
    write_profile(folder, text)

    shown = read_back(server)["daten"]["searchJob"]["exclusions"]

    assert shown == search_plan.frame(text)["ausschluss"] == ["Vertrieb", "Callcenter"]


def test_changing_them_keeps_the_line_in_place_and_indented(started):
    server, folder, _ = started
    write_profile(folder)

    text = saved_with(server, folder, exclusions=["Vertrieb", "Aussendienst"])

    assert text == PROFILE.replace(INDENTED, "   - Ausschluss: Vertrieb, Aussendienst")
    assert len(drafts_of(folder, "suchprofil.md")) == 2  # before and after


def test_a_label_of_their_own_stays_when_they_change(started):
    server, folder, _ = started
    own = PROFILE.replace(INDENTED, "   - Ausschluss (Branchen): Vertrieb, Callcenter")
    write_profile(folder, own)

    text = saved_with(server, folder, exclusions=["Vertrieb"])

    assert text == own.replace("Ausschluss (Branchen): Vertrieb, Callcenter", "Ausschluss (Branchen): Vertrieb")


def test_another_change_leaves_the_indented_line_as_it_is(started):
    server, folder, _ = started
    write_profile(folder)

    text = saved_with(server, folder, workload="100 %")

    assert text == PROFILE.replace("- Pensum: 60–80 %", "- Pensum: 100 %")


def test_saving_without_a_change_writes_nothing(started):
    server, folder, _ = started
    write_profile(folder)

    assert saved_with(server, folder) == PROFILE
    assert drafts_of(folder, "suchprofil.md") == []


def test_removing_every_exclusion_removes_only_their_line(started):
    server, folder, _ = started
    write_profile(folder)

    text = saved_with(server, folder, exclusions=[])

    assert text == PROFILE.replace(INDENTED + "\n", "")


@pytest.mark.parametrize("before", [PROFILE.replace(INDENTED + "\n", ""),
                                    PROFILE.replace(INDENTED, "- Ausschluss: Vertrieb, Callcenter")])
def test_a_profile_without_indented_exclusions_works_as_before(started, before):
    import search_plan
    server, folder, _ = started
    write_profile(folder, before)

    text = saved_with(server, folder, exclusions=["Lager"])

    assert search_plan.frame(text)["ausschluss"] == ["Lager"]
    assert [line for line in text.split("\n") if "Lager" not in line] == \
        [line for line in before.split("\n") if "Ausschluss: Vertrieb" not in line]
