"""Meine Angaben reads directions and title filters laid out as in vorlagen/suchprofil.md, as the search does (#313).

A direction whose bracket holds more than its priority, such as „(Priorität 2, auch Teilzeit aufnehmen, …)“, is one the
search reads, so the page shows it, and saving a changed list keeps every other direction with its text and the lines
indented below it. Positiv and Ausschluss under Titelfilter count at any indentation and with labels that start the same
way. All data is invented.
"""
import pathlib

import pytest

from test_angaben import started  # noqa: F401  (fixture)
from test_angaben_indented_exclusions import saved_with, unknown_lines
from test_angaben_indented_exclusions import write_profile as write_basics_with
from test_angaben_read_back import drafts_of, read_back

TEMPLATE = pathlib.Path(__file__).resolve().parents[2] / "vorlagen" / "suchprofil.md"

FIRST = "1. Pflege und Betreuung (Priorität 1)"
SECOND = '2. Spitex mit Fahrdienst (Priorität 2, auch Teilzeit aufnehmen, Notiz-Präfix "Spitex:")'
BELOW = ("   - Nur mit Fahrausweis im Titel oder Volltext: Kategorie B",
         "   - Ausschluss: Nachtdienst, Pikett")
PROFILE = f"""# Suchprofil

Nach der Vorlage geschrieben.

## Suchrichtungen
{FIRST}
{SECOND}
{BELOW[0]}
{BELOW[1]}

## Region
- Wohnort: Thun
- Kantone (job-room): BE, FR
- Remote: nein

## Titelfilter
- Positiv: Pflege, Betreuung
- Ausschluss: Praktikum

## Rahmen
- Frühester Start: 1. Mai
- Pensum: 60–80 %
"""
SHOWN = ["Pflege und Betreuung", "Spitex mit Fahrdienst"]


def write_profile(folder: pathlib.Path, text: str = PROFILE) -> None:
    write_basics_with(folder, text)


def lines_of(text: str) -> list[str]:
    return text.split("\n")


def test_the_template_shows_every_direction_the_search_reads(started):
    server, folder, _ = started
    write_profile(folder, TEMPLATE.read_text(encoding="utf-8"))

    read = read_back(server)

    assert read["daten"]["searchJob"]["directions"] == ["Software-Entwicklung, Web und Daten",
                                                         "Interne Schulung und E-Learning mit IT-Bezug"]
    assert not any(line.startswith("2. Interne Schulung") for line in unknown_lines(read))


def test_a_direction_with_a_long_bracket_comes_back_into_the_form(started):
    server, folder, _ = started
    write_profile(folder)

    read = read_back(server)

    assert read["daten"]["searchJob"]["directions"] == SHOWN
    assert SECOND not in unknown_lines(read)
    assert set(BELOW[:1]) <= unknown_lines(read)


def test_adding_a_direction_keeps_the_others_with_their_text(started):
    server, folder, _ = started
    write_profile(folder)

    text = saved_with(server, folder, directions=[*SHOWN, "Tagesstruktur"])

    assert text == PROFILE.replace(BELOW[1], f"{BELOW[1]}\n3. Tagesstruktur (Priorität 3)")
    assert len(drafts_of(folder, "suchprofil.md")) == 2  # before and after


def test_removing_the_first_direction_keeps_the_second_with_its_text(started):
    server, folder, _ = started
    write_profile(folder)

    text = saved_with(server, folder, directions=["Spitex mit Fahrdienst"])

    assert text == PROFILE.replace(f"{FIRST}\n{SECOND}", SECOND.replace("2.", "1.").replace("Priorität 2", "Priorität 1"))


def test_renaming_one_direction_changes_only_its_name(started):
    server, folder, _ = started
    write_profile(folder)

    text = saved_with(server, folder, directions=["Pflege", "Spitex mit Fahrdienst"])

    assert text == PROFILE.replace(FIRST, "1. Pflege (Priorität 1)")


def test_reordering_keeps_every_direction_and_every_line_below(started):
    import search_plan
    server, folder, _ = started
    write_profile(folder)

    text = saved_with(server, folder, directions=list(reversed(SHOWN)))

    directions = [line for line in lines_of(text) if search_plan.DIRECTION.match(line)]
    assert directions == ['1. Spitex mit Fahrdienst (Priorität 1, auch Teilzeit aufnehmen, Notiz-Präfix "Spitex:")',
                          "2. Pflege und Betreuung (Priorität 2)"]
    assert sorted(set(lines_of(text)) - set(directions)) == sorted(set(lines_of(PROFILE)) - {FIRST, SECOND})


def test_changing_directions_and_exclusions_at_once_keeps_both(started):
    server, folder, _ = started
    write_profile(folder)

    text = saved_with(server, folder, directions=[*SHOWN, "Tagesstruktur"], exclusions=["Nachtdienst"])

    assert text == PROFILE.replace(BELOW[1], "   - Ausschluss: Nachtdienst\n3. Tagesstruktur (Priorität 3)")


def test_another_change_leaves_the_directions_as_they_are(started):
    server, folder, _ = started
    write_profile(folder)

    text = saved_with(server, folder, workload="100 %")

    assert text == PROFILE.replace("- Pensum: 60–80 %", "- Pensum: 100 %")


def test_the_page_reads_the_title_filters_the_search_reads(started):
    import search_plan
    server, folder, _ = started
    text = PROFILE.replace("- Positiv: Pflege, Betreuung", "  - Positiv (Titel): Pflege, Betreuung") \
                  .replace("- Ausschluss: Praktikum", "   - Ausschluss (Titel): Praktikum, Lehrstelle")
    write_profile(folder, text)

    read = read_back(server)
    search = read["daten"]["searchJob"]

    assert search["titlePositive"] == list(search_plan.title_terms(text, "positiv")) == ["Pflege", "Betreuung"]
    assert search["titleExclude"] == list(search_plan.title_terms(text, "ausschluss")) == ["Praktikum", "Lehrstelle"]
    assert not {"  - Positiv (Titel): Pflege, Betreuung", "   - Ausschluss (Titel): Praktikum, Lehrstelle"} & unknown_lines(read)


def test_changing_a_title_filter_keeps_its_label_and_indentation(started):
    server, folder, _ = started
    own = PROFILE.replace("- Positiv: Pflege, Betreuung", "  - Positiv (Titel): Pflege, Betreuung")
    write_profile(folder, own)

    text = saved_with(server, folder, titlePositive=["Pflege", "Spitex"], titleExclude=[])

    assert text == own.replace("Positiv (Titel): Pflege, Betreuung", "Positiv (Titel): Pflege, Spitex") \
                      .replace("- Ausschluss: Praktikum\n", "")


@pytest.mark.parametrize("line, shown", [
    ("1. Informatiker EFZ (Priorität 1, falls kein Platz frei ist)", "Informatiker EFZ"),
    ("1. Informatiker EFZ (Applikationsentwicklung) (Priorität 1)", "Informatiker EFZ (Applikationsentwicklung)"),
])
def test_an_apprenticeship_shows_the_professions_the_search_reads(started, line, shown):
    import search_plan
    server, folder, _ = started
    text = ("# Suchprofil Lehrstelle\n\n## Gesucht\n- Lehrstellen\n\n## Lehrbeginn\n- August 2027\n\n"
            f"## Berufe (mit Priorität)\n{line}\n2. Mediamatiker EFZ (Priorität 2)\n\n## Region\n- Wohnort: Biel\n")
    (folder / "suchprofil.md").write_text(text, encoding="utf-8")

    professions = read_back(server)["daten"]["searchApprenticeship"]["professions"]

    assert professions == list(search_plan.professions_in(text)) == [shown, "Mediamatiker EFZ"]
