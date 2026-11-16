"""The order of the search terms (#285, G87): set on Suche einstellen, saved in the search profile, searched in it.

Profiles are the invented templates or short invented texts. A profile without an order searches as it always did.
"""
import json
import pathlib
import shutil

import pytest

import search_plan
import search_terms
from test_app import get, post, server  # noqa: F401  (server is a fixture)

VORLAGEN = pathlib.Path(__file__).resolve().parents[2] / "vorlagen"
KERN = "# Suchprofil\n\n## Region\n- Wohnort: Bern\n\n## Keywords\n- Kernliste: Daten, Python, Empfang\n- Nischen: dbt\n"
DIRECTIONS = ("## Suchrichtungen\n1. Administration, Empfang (Priorität 1)\n2. Bildung (Priorität 2)\n"
              "   - Nur mit IT-Bezug\n\n## Region\n- Wohnort: Bern\n")
LEHRE = ("## Lehrbeginn\n- 2027\n\n## Berufe (mit Priorität)\n1. Koch/Köchin EFZ (Priorität 1)\n"
         "2. Fachfrau Betreuung EFZ, Fachrichtung Kinder (Priorität 2)\n3. Maler/in EFZ\n\n## Region\n- Wohnort: Bern\n")
JOB_TERMS = ["Python", "TypeScript", "Softwareentwickler", "Data Engineer", "E-Learning"]
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
    once = search_terms.reordered(DIRECTIONS, ["Bildung", "Empfang", "Administration"])
    twice = search_terms.reordered(once, ["Empfang", "Administration", "Bildung"])

    assert twice.count("## Reihenfolge der Suche") == 1
    assert search_terms.current(twice) == ("Empfang", "Administration", "Bildung")
    assert "1. Administration, Empfang (Priorität 1)\n2. Bildung (Priorität 2)\n   - Nur mit IT-Bezug\n" in twice


def test_terms_the_order_does_not_name_come_after_it_in_the_profile_order():
    text = f"{KERN}\n## Reihenfolge der Suche\n1. Empfang\n2. Cobol\n"

    assert search_terms.current(text) == ("Empfang", "Daten", "Python")


def test_another_form_of_a_profession_keeps_its_place():
    text = f"{LEHRE}\n## Reihenfolge der Suche\n1. Maler EFZ\n2. Koch EFZ\n"

    assert search_terms.current(text)[:2] == ("Maler/in EFZ", "Koch/Köchin EFZ")


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
    ordered = search_terms.reordered(LEHRE, ["Maler/in EFZ", "Koch/Köchin EFZ", "Fachfrau Betreuung EFZ, Fachrichtung Kinder"])

    changed = search_terms.removed(ordered, "Koch/Köchin EFZ")

    assert "Koch" not in changed
    assert "1. Maler/in EFZ\n2. Fachfrau Betreuung EFZ, Fachrichtung Kinder\n" in changed
    assert search_terms.current(search_terms.added(changed, "Koch/Köchin EFZ"))[-1] == "Koch/Köchin EFZ"


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
    ("job_seeker", ["Data Engineer", "Python", "E-Learning", "TypeScript", "Softwareentwickler"]),
    ("apprentice", [PROFESSIONS[2], PROFESSIONS[0], PROFESSIONS[1]]),
])
def test_the_order_from_the_page_is_saved_with_drafts_and_searched(request, fixture, order):
    s = request.getfixturevalue(fixture)

    status, answer = post(s, "/api/beruf/reihenfolge", {"berufe": order})

    assert status == 200 and answer["berufe"] == order
    assert list(search_plan.for_folder(s.kontext.daten).keywords) == order
    assert json.loads(get(s, "/api/suche/plan")[2])["plan"]["stichworte"] == order
    assert drafts(s) == ["Reihenfolge der Suche geändert", "Stand vor: Reihenfolge der Suche geändert"]


def test_a_term_added_on_the_page_after_ordering_comes_last(job_seeker):
    order = ["E-Learning", "Python", "TypeScript", "Softwareentwickler", "Data Engineer"]
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
