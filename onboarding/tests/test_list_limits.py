"""Directions and professions: as many and as long on Meine Angaben as on Suche einstellen and in the search (#316).

Suche einstellen adds a term as a direction when the profile has no keywords, and a profession to the list of
professions; Meine Angaben reads both lists back and checks them against onboarding/form.json. A list one page accepts
the other shows in full and accepts. All data is invented.
"""
import pathlib

import pytest

import basics_read
import markdown_files
import search_plan
import search_terms
import validation
from basics_slots import APPRENTICESHIP, JOB, PROFILE
from form_cases import base_bundle

LISTS = {
    JOB: ("searchJob", "directions", "Richtung {n} Sachbearbeitung "),
    APPRENTICESHIP: ("searchApprenticeship", "professions", "Beruf{letter} EFZ, Fachrichtung "),
}
FIRST = {JOB: "Empfang", APPRENTICESHIP: "Empfang EFZ"}
KINDS = {JOB: search_plan.KIND_JOB, APPRENTICESHIP: search_plan.KIND_APPRENTICESHIP}
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"  # a profession is the same as another if their words are, so no digits


def field(form: dict, track: str) -> dict:
    section_id, field_id, _ = LISTS[track]
    section = next(s for s in form["sections"] if s["id"] == section_id)
    return next(f for f in section["fields"] if f["id"] == field_id)


def entry(form: dict, track: str, n: int, length: int | None = None) -> str:
    start = LISTS[track][2].format(n=n + 1, letter=LETTERS[n])
    if length is None:
        return start.split(",")[0].strip()
    return start + "x" * (length - len(start))


def written_by_meine_angaben(track: str, entries: list[str]) -> str:
    data = base_bundle(track)["data"]
    section_id, field_id, _ = LISTS[track]
    return markdown_files.search_profile({**data, section_id: {**data[section_id], field_id: entries}}, track, "")


def read_back(form: dict, folder: pathlib.Path, track: str, text: str) -> list[str]:
    (folder / PROFILE).write_text(text, encoding="utf-8")
    section_id, field_id, _ = LISTS[track]
    return basics_read.read_back(form, folder, track, None)["daten"][section_id].get(field_id, [])


def added_until_full(form: dict, track: str) -> str:
    """The profile after Suche einstellen added entries until it refused one."""
    text = written_by_meine_angaben(track, [FIRST[track]])
    for n in range(len(LETTERS)):
        try:
            text = search_terms.added(text, entry(form, track, n), KINDS[track])
        except ValueError:
            return text
    raise AssertionError("Suche einstellen never refused an entry")


@pytest.mark.parametrize("track", list(LISTS))
def test_meine_angaben_accepts_every_entry_suche_einstellen_added(form, tmp_path, track):
    text = added_until_full(form, track)
    searched = list(search_terms.current(text))

    shown = read_back(form, tmp_path, track, text)

    assert shown == searched
    assert not validation.field_errors(form, field(form, track), track, shown)


@pytest.mark.parametrize("track", list(LISTS))
def test_suche_einstellen_shows_in_full_a_list_as_full_and_long_as_meine_angaben_takes_it(form, track):
    rules = field(form, track)
    entries = [entry(form, track, n, rules.get("max", form["limits"]["text"]))
               for n in range(rules.get("maxItems", form["limits"]["listItems"]))]
    assert not validation.field_errors(form, rules, track, entries)

    saved = written_by_meine_angaben(track, entries)

    assert list(search_terms.current(saved)) == entries
    assert list(search_plan.parse(saved).keywords) == entries
