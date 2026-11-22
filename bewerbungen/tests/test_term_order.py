"""The order of the search terms (#285, G87): set on Suche einstellen, saved in the search profile, searched in it.

A numbered list carries the order itself, since its number is the priority the rating reads; terms from unnumbered
lines get a section of their own. Profiles are the invented templates or short invented texts. A profile without an
order searches as it always did.
"""
import json
import pathlib
import shutil

import pytest

import search_plan
import search_terms
from ai import tasks
from test_app import get, post, server  # noqa: F401  (server is a fixture)

VORLAGEN = pathlib.Path(__file__).resolve().parents[2] / "vorlagen"
KERN = "# Suchprofil\n\n## Region\n- Wohnort: Bern\n\n## Keywords\n- Kernliste: Daten, Python, Empfang\n- Nischen: dbt\n"
DIRECTIONS = ("## Suchrichtungen\n1. Administration, Empfang (Priorität 1)\n2. Bildung (Priorität 2)\n"
              "   - Nur mit IT-Bezug\n\n## Region\n- Wohnort: Bern\n")
LEHRE = ("## Lehrbeginn\n- 2027\n\n## Berufe (mit Priorität)\n1. Koch/Köchin EFZ (Priorität 1)\n"
         "2. Fachfrau Betreuung EFZ, Fachrichtung Kinder (Priorität 2)\n3. Maler/in EFZ\n\n## Region\n- Wohnort: Bern\n")
JOB_TERMS = ["Python", "TypeScript", "Softwareentwickler", "Data Engineer", "E-Learning", "Kursleiter"]
PROFESSIONS = ["Fachfrau Gesundheit EFZ", "Fachfrau Betreuung EFZ, Fachrichtung Kinder", "Assistentin Gesundheit und Soziales EBA"]


# Reading the order


def test_a_profile_without_an_order_searches_as_written():
    assert search_plan.parse(KERN).keywords == ("Daten", "Python", "Empfang")
    assert search_terms.current(DIRECTIONS) == ("Administration", "Empfang", "Bildung")


@pytest.mark.parametrize("text, order", [
    (KERN, ["Empfang", "Daten", "Python"]),
    (DIRECTIONS, ["Bildung", "Administration", "Empfang"]),
    (LEHRE, ["Maler/in EFZ", "Koch/Köchin EFZ", "Fachfrau Betreuung EFZ, Fachrichtung Kinder"]),
])
def test_the_search_runs_the_terms_in_the_saved_order(text, order):
    changed = search_terms.reordered(text, order)

    assert list(search_terms.current(changed)) == order
    assert list(search_plan.parse(changed).keywords) == order
    assert search_plan.parse(changed).as_dict()["stichworte"] == order


def test_the_order_is_its_own_section_and_the_rest_stays_as_written():
    changed = search_terms.reordered(KERN, ["Python", "Empfang", "Daten"])

    assert "## Reihenfolge der Suche\n" in changed
    assert "1. Python\n2. Empfang\n3. Daten\n" in changed
    assert "- Kernliste: Daten, Python, Empfang\n- Nischen: dbt\n" in changed
    assert search_plan.parse(changed).niche_keywords == ("dbt",)


def test_ordering_again_replaces_the_order_and_keeps_one_section():
    once = search_terms.reordered(KERN, ["Python", "Empfang", "Daten"])
    twice = search_terms.reordered(once, ["Empfang", "Daten", "Python"])

    assert twice.count("## Reihenfolge der Suche") == 1
    assert search_terms.current(twice) == ("Empfang", "Daten", "Python")


def test_terms_the_order_does_not_name_come_after_it_in_the_profile_order():
    text = f"{KERN}\n## Reihenfolge der Suche\n1. Empfang\n2. Cobol\n"

    assert search_terms.current(text) == ("Empfang", "Daten", "Python")


def test_another_form_of_a_term_keeps_its_place():
    text = ("## Keywords\n- Kernliste: Koch/Köchin EFZ, Maler/in EFZ, Gärtner/in EFZ\n\n"
            "## Reihenfolge der Suche\n1. Maler EFZ\n2. Koch EFZ\n")

    assert search_terms.current(text)[:2] == ("Maler/in EFZ", "Koch/Köchin EFZ")


# A numbered list carries the order itself


def test_moving_a_profession_renumbers_the_priority_list_and_its_priorities():
    changed = search_terms.reordered(LEHRE, ["Maler/in EFZ", "Koch/Köchin EFZ", "Fachfrau Betreuung EFZ, Fachrichtung Kinder"])

    assert ("## Berufe (mit Priorität)\n1. Maler/in EFZ\n2. Koch/Köchin EFZ (Priorität 2)\n"
            "3. Fachfrau Betreuung EFZ, Fachrichtung Kinder (Priorität 3)\n\n## Region\n") in changed
    assert search_plan.ORDER_SECTION not in changed


def test_a_remark_stays_with_its_profession():
    text = (VORLAGEN / "suchprofil-lehrstelle.md").read_text(encoding="utf-8")

    changed = search_terms.reordered(text, [PROFESSIONS[2], PROFESSIONS[0], PROFESSIONS[1]])

    assert ("1. Assistentin Gesundheit und Soziales EBA (Ersatz, falls 1 und 2 nicht klappen)\n"
            "2. Fachfrau Gesundheit EFZ (Priorität 2)\n3. Fachfrau Betreuung EFZ, Fachrichtung Kinder (Priorität 3)\n") in changed


def test_an_apprenticeship_searches_its_list_not_an_old_order_section():
    stale = f"{LEHRE}\n## Reihenfolge der Suche\n1. Maler EFZ\n2. Koch EFZ\n"

    assert search_terms.current(stale)[0] == "Koch/Köchin EFZ"
    assert search_plan.ORDER_SECTION not in search_terms.reordered(stale, list(search_terms.current(stale)))


def test_moving_a_search_direction_moves_its_line_with_the_lines_below_it():
    changed = search_terms.reordered(DIRECTIONS, ["Bildung", "Administration", "Empfang"])

    assert ("## Suchrichtungen\n1. Bildung (Priorität 1)\n   - Nur mit IT-Bezug\n"
            "2. Administration, Empfang (Priorität 2)\n\n## Region\n") in changed
    assert search_plan.ORDER_SECTION not in changed


def test_moving_a_term_within_its_direction_keeps_the_line():
    changed = search_terms.reordered(DIRECTIONS, ["Empfang", "Administration", "Bildung"])

    assert "## Suchrichtungen\n1. Empfang, Administration (Priorität 1)\n2. Bildung (Priorität 2)\n" in changed


def test_moving_one_term_of_a_direction_away_from_the_other_gives_it_a_line_of_its_own():
    changed = search_terms.reordered(DIRECTIONS, ["Empfang", "Bildung", "Administration"])

    assert ("## Suchrichtungen\n1. Empfang (Priorität 1)\n2. Bildung (Priorität 2)\n   - Nur mit IT-Bezug\n"
            "3. Administration (Priorität 3)\n\n## Region\n") in changed
    assert search_terms.current(changed) == ("Empfang", "Bildung", "Administration")


def test_the_same_order_changes_nothing():
    for text in (LEHRE, DIRECTIONS):
        assert search_terms.reordered(text, list(search_terms.current(text))) == text


# Both kinds in one profile


def test_core_list_terms_get_the_section_and_directions_with_other_names_stay():
    text = (VORLAGEN / "suchprofil.md").read_text(encoding="utf-8")

    changed = search_terms.reordered(text, [*reversed(JOB_TERMS)])

    assert "## Reihenfolge der Suche\n" in changed
    assert search_plan.section_lines(changed, "## Suchrichtungen") == search_plan.section_lines(text, "## Suchrichtungen")


def test_directions_naming_core_list_terms_follow_the_order():
    text = ("## Suchrichtungen\n1. Logistik (Priorität 1)\n2. Bildung (Priorität 2)\n3. Empfang (Priorität 3)\n\n"
            "## Keywords\n- Kernliste: Bildung, Empfang\n")

    changed = search_terms.reordered(text, ["Empfang", "Bildung"])

    assert "1. Logistik (Priorität 1)\n2. Empfang (Priorität 2)\n3. Bildung (Priorität 3)\n" in changed
    assert "## Reihenfolge der Suche\n" in changed and search_terms.current(changed) == ("Empfang", "Bildung")


@pytest.mark.parametrize("order", [["Daten", "Python"], ["Daten", "Python", "Empfang", "Cobol"],
                                   ["Daten", "Python", "Cobol"], ["Daten", "Daten", "Python"]])
def test_an_order_that_is_not_the_searched_terms_is_refused(order):
    with pytest.raises(ValueError, match="inzwischen geändert"):
        search_terms.reordered(KERN, order)


# New, removed and kept terms


def test_a_new_term_goes_to_the_end_of_an_ordered_search():
    ordered = search_terms.reordered(KERN, ["Empfang", "Python", "Daten"])

    assert search_terms.current(search_terms.added(ordered, "Logistik")) == ("Empfang", "Python", "Daten", "Logistik")


def test_a_term_added_again_goes_to_the_end_not_to_its_former_place():
    ordered = f"{KERN}\n## Reihenfolge der Suche\n1. Logistik\n2. Empfang\n3. Daten\n4. Python\n"

    changed = search_terms.added(ordered, "Logistik")

    assert search_terms.current(changed) == ("Empfang", "Daten", "Python", "Logistik")


def test_removing_a_term_takes_it_out_of_the_order_too():
    ordered = search_terms.reordered(KERN, ["Python", "Empfang", "Daten"])

    changed = search_terms.removed(ordered, "Empfang")

    assert "Empfang" not in changed
    assert "1. Python\n2. Daten\n" in changed
    assert search_terms.current(search_terms.added(changed, "Empfang"))[-1] == "Empfang"


def test_a_profession_added_after_moving_comes_last():
    ordered = search_terms.reordered(LEHRE, ["Maler/in EFZ", "Koch/Köchin EFZ", "Fachfrau Betreuung EFZ, Fachrichtung Kinder"])

    assert "4. Gärtner/in EFZ\n" in search_terms.added(ordered, "Gärtner/in EFZ")


def test_a_profile_from_the_form_keeps_the_order():
    old = search_terms.reordered(KERN, ["Empfang", "Daten", "Python"])
    new = "# Suchprofil\n\n## Region\n- Wohnort: Bern\n\n## Keywords\n- Kernliste: Daten, Python\n"

    text, _ = search_terms.kept_on_replace(old, new)

    assert search_terms.current(text) == ("Empfang", "Daten", "Python")


# The route


@pytest.fixture
def job_seeker(server):  # noqa: F811
    shutil.copy(VORLAGEN / "suchprofil.md", server.kontext.daten / search_plan.PROFILE)
    return server


@pytest.fixture
def apprentice(server):  # noqa: F811
    shutil.copy(VORLAGEN / "suchprofil-lehrstelle.md", server.kontext.daten / search_plan.PROFILE)
    return server


def profile(s) -> str:
    return (s.kontext.daten / search_plan.PROFILE).read_text(encoding="utf-8")


def drafts(s) -> list[str]:
    return [d.beschreibung for d in s.kontext.ablage.liste(s.kontext.daten / search_plan.PROFILE)]


@pytest.mark.parametrize("fixture, order", [
    ("job_seeker", ["Data Engineer", "Python", "Kursleiter", "E-Learning", "TypeScript", "Softwareentwickler"]),
    ("apprentice", [PROFESSIONS[2], PROFESSIONS[0], PROFESSIONS[1]]),
])
def test_the_order_from_the_page_is_saved_with_drafts_and_searched(request, fixture, order):
    s = request.getfixturevalue(fixture)

    status, answer = post(s, "/api/beruf/reihenfolge", {"berufe": order})

    assert status == 200 and answer["berufe"] == order
    assert list(search_plan.for_folder(s.kontext.daten).keywords) == order
    assert json.loads(get(s, "/api/suche/plan")[2])["plan"]["stichworte"] == order
    assert drafts(s) == ["Reihenfolge der Suche geändert", "Stand vor: Reihenfolge der Suche geändert"]


def test_the_rating_reads_the_moved_priority_list(apprentice):
    order = [PROFESSIONS[0], PROFESSIONS[2], PROFESSIONS[1]]

    assert post(apprentice, "/api/beruf/reihenfolge", {"berufe": order})[0] == 200

    berufe = ("## Berufe (mit Priorität)\n1. Fachfrau Gesundheit EFZ (Priorität 1)\n"
              "2. Assistentin Gesundheit und Soziales EBA (Ersatz, falls 1 und 2 nicht klappen)\n"
              "3. Fachfrau Betreuung EFZ, Fachrichtung Kinder (Priorität 3)\n")
    context = tasks.load_material(apprentice.kontext.daten, partial=True).context
    assert berufe in profile(apprentice) and berufe in context
    assert search_plan.ORDER_SECTION not in context


def test_a_term_added_on_the_page_after_ordering_comes_last(job_seeker):
    order = ["E-Learning", "Python", "TypeScript", "Softwareentwickler", "Kursleiter", "Data Engineer"]
    assert post(job_seeker, "/api/beruf/reihenfolge", {"berufe": order})[0] == 200

    status, answer = post(job_seeker, "/api/beruf/aufnehmen", {"beruf": "Projektleitung Bau"})

    assert status == 200 and answer["berufe"] == [*order, "Projektleitung Bau"]


def test_an_outdated_order_is_refused_and_changes_nothing(job_seeker):
    before = profile(job_seeker)

    status, answer = post(job_seeker, "/api/beruf/reihenfolge", {"berufe": ["Python", "TypeScript"]})

    assert status == 400 and "inzwischen geändert" in answer["fehler"]
    assert profile(job_seeker) == before


@pytest.mark.parametrize("body", [{}, {"berufe": "Python"}, {"berufe": [1, 2]}, {"berufe": ["x" * 500]}, []])
def test_the_order_wants_a_list_of_terms(job_seeker, body):
    assert post(job_seeker, "/api/beruf/reihenfolge", body)[0] == 400
