"""The remark with the required words belongs to its term (G110, #386): every change the app writes keeps it.

Removing, adding, reordering, moving to the niches or to some portals, Rückgängig and a profile from Meine Angaben;
the term's key ignores it. Invented profiles only.
"""
import pathlib
import shutil

import pytest

import required_words
import search_plan
import search_terms
import term_pairs
from test_app import post, server  # noqa: F401  (server is a fixture)

VORLAGEN = pathlib.Path(__file__).resolve().parents[2] / "vorlagen"
BROAD = "Berufsbildner (nur mit Informatik, ICT, Plattform)"
REGION = "## Region\n- Kantone (job-room): BE\n- Orte (jobs.ch): Bern\n\n"


def keywords(core: str, *more: str) -> str:
    return "\n".join([f"# Suchprofil\n\n{REGION}## Keywords", f"- Kernliste: {core}", *more, "", "## Titelfilter", ""])


def core_of(text: str) -> str:
    return next(line for line in text.split("\n") if line.startswith("- Kernliste:"))


TEXT = keywords(f"Lernbegleiter, {BROAD}, Kursplaner")


# The key and the plan

def test_the_key_of_a_term_ignores_its_remark():
    assert search_terms.key(BROAD) == search_terms.key("Berufsbildner")
    assert search_terms.is_searched(TEXT, BROAD)
    assert search_terms.current(TEXT) == ("Lernbegleiter", "Berufsbildner", "Kursplaner")


# Removing

def test_removing_another_term_keeps_the_remark_where_it_was():
    assert core_of(search_terms.removed(TEXT, "Kursplaner")) == f"- Kernliste: Lernbegleiter, {BROAD}"
    assert core_of(search_terms.removed(TEXT, "Lernbegleiter")) == f"- Kernliste: {BROAD}, Kursplaner"


def test_removing_the_term_takes_its_remark_with_it():
    after = search_terms.removed(TEXT, "Berufsbildner")
    assert core_of(after) == "- Kernliste: Lernbegleiter, Kursplaner"
    assert "nur mit" not in after


def test_removing_one_alternative_of_a_slash_group_keeps_the_remark_on_the_rest():
    text = keywords("Ausbilder/Berufsbildner (nur mit ICT), Lernbegleiter")
    assert core_of(search_terms.removed(text, "Ausbilder")) == "- Kernliste: Berufsbildner (nur mit ICT), Lernbegleiter"


def test_removing_from_one_line_keeps_the_remark_of_the_others():
    text = keywords(f"{BROAD}, Kursplaner", "- Nischen (ohne Ort suchen): Kursplaner")
    index = text.split("\n").index(core_of(text))
    assert core_of(search_terms.removed_from_line(text, "Kursplaner", index)) == f"- Kernliste: {BROAD}"


# Adding

def test_a_term_added_with_a_remark_keeps_it():
    after = search_terms.added(keywords("Lernbegleiter"), BROAD)
    assert core_of(after) == f"- Kernliste: Lernbegleiter, {BROAD}"
    assert search_plan.parse(after).keywords == ("Lernbegleiter", "Berufsbildner")
    assert required_words.of_profile(after).of_term("Berufsbildner") == ("Informatik", "ICT", "Plattform")


def test_a_term_with_a_remark_is_the_same_term_as_without():
    assert search_terms.added(TEXT, "Berufsbildner") == TEXT
    assert search_terms.added(keywords("Berufsbildner"), BROAD) == keywords("Berufsbildner")


# Reordering and moving

def test_reordering_keeps_the_remark_in_its_line():
    after = search_terms.reordered(TEXT, ["Kursplaner", "Berufsbildner", "Lernbegleiter"])
    assert core_of(after) == core_of(TEXT)
    assert search_plan.parse(after).keywords == ("Kursplaner", "Berufsbildner", "Lernbegleiter")


def test_moving_the_term_to_the_niches_takes_its_remark_along():
    after = search_terms.moved_to_niches(TEXT, "Berufsbildner")
    assert f"- Nischen (ohne Ort suchen): {BROAD}" in after
    assert required_words.of_profile(after).of_term("Berufsbildner") == ("Informatik", "ICT", "Plattform")


def test_limiting_the_term_to_portals_takes_its_remark_along():
    after = search_terms.limited_to(TEXT, "Berufsbildner", ("jobs.ch",))
    assert f"- Nur jobs.ch: {BROAD}" in after
    assert core_of(after) == "- Kernliste: Lernbegleiter, Kursplaner"


# Meine Angaben and Rückgängig

def test_a_profile_from_the_form_without_the_term_gets_it_back_with_its_remark():
    replaced, kept = search_terms.kept_on_replace(TEXT, keywords("Lernbegleiter"))
    assert kept == ("Berufsbildner", "Kursplaner")
    assert core_of(replaced) == f"- Kernliste: Lernbegleiter, {BROAD}, Kursplaner"


def test_undo_in_one_line_after_another_change_brings_the_remark_back():
    former = keywords(f"Lernbegleiter, {BROAD}", "- Nischen (ohne Ort suchen): Berufsbildner")
    index = former.split("\n").index(core_of(former))
    line_id = term_pairs.lines_of(former)[0].id
    removed = search_terms.removed_from_line(former, "Berufsbildner", index)
    changed_since = search_terms.added(removed, "Kursplaner")

    restored = term_pairs.restored(former, changed_since, "Berufsbildner", line_id)

    assert core_of(restored) == f"- Kernliste: Lernbegleiter, Kursplaner, {BROAD}"


# Through the routes

@pytest.fixture
def job_seeker(server):  # noqa: F811
    shutil.copy(VORLAGEN / "suchprofil.md", server.kontext.daten / search_plan.PROFILE)
    return server


def written(s) -> str:
    return (s.kontext.daten / search_plan.PROFILE).read_text(encoding="utf-8")


def test_the_add_field_keeps_a_typed_remark(job_seeker):
    status, answer = post(job_seeker, "/api/beruf/aufnehmen", {"beruf": "  Berufsbildner (nur mit  Informatik, ICT) "})

    assert status == 200 and answer["berufe"][-1] == "Berufsbildner"
    assert "Berufsbildner (nur mit Informatik, ICT)" in core_of(written(job_seeker))
    assert required_words.of_profile(written(job_seeker)).of_term("Berufsbildner") == ("Informatik", "ICT")


@pytest.mark.parametrize("typed", ["Berufsbildner (Informatik)", "Berufsbildner (nur mit )", "Berufsbildner (nur mit <b>)"])
def test_other_brackets_in_the_add_field_are_still_refused(job_seeker, typed):
    before = written(job_seeker)
    status, answer = post(job_seeker, "/api/beruf/aufnehmen", {"beruf": typed})
    assert status == 400 and answer["fehler"] == "Das passt nicht als Suchbegriff."
    assert written(job_seeker) == before


def test_a_remark_is_refused_where_the_profile_searches_numbered_directions(job_seeker):
    path = job_seeker.kontext.daten / search_plan.PROFILE
    path.write_text("## Suchrichtungen\n1. Lernbegleiter\n\n## Region\n- Kantone (job-room): BE\n", encoding="utf-8")

    status, answer = post(job_seeker, "/api/beruf/aufnehmen", {"beruf": "Berufsbildner (nur mit ICT)"})

    assert status == 400 and answer["fehler"] == search_terms.NO_REMARK_IN_DIRECTIONS
    assert "Berufsbildner" not in written(job_seeker)


def test_removing_and_undoing_through_the_page_keep_the_remark(job_seeker):
    post(job_seeker, "/api/beruf/aufnehmen", {"beruf": "Berufsbildner (nur mit ICT)"})
    status, removed = post(job_seeker, "/api/beruf/entfernen", {"beruf": "Berufsbildner"})
    assert status == 200 and "Berufsbildner" not in written(job_seeker)

    status, _ = post(job_seeker, "/api/beruf/rueckgaengig", {"beruf": "Berufsbildner", "vorher": removed["rueckgaengig"]})

    assert status == 200 and "Berufsbildner (nur mit ICT)" in core_of(written(job_seeker))
