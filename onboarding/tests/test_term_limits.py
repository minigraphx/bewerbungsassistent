"""A search term saved on Suche einstellen or on Meine Angaben is shown in full on the other page (#310).

Suche einstellen adds a job term to the line Kernliste, the keywords of Meine Angaben, and a profession to the list of
professions; both pages take a term as long as that field of onboarding/form.json does. All data is invented.
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

TRACKS = {
    JOB: ("searchJob", "keywords", search_plan.KIND_JOB, "Sachbearbeitung Kundendienst "),
    APPRENTICESHIP: ("searchApprenticeship", "professions", search_plan.KIND_APPRENTICESHIP,
                     "Lebensmitteltechnologin/Lebensmitteltechnologe EFZ, Fachrichtung "),
}


def field(form: dict, track: str) -> dict:
    section_id, field_id, _, _ = TRACKS[track]
    section = next(s for s in form["sections"] if s["id"] == section_id)
    return next(f for f in section["fields"] if f["id"] == field_id)


def longest_term(form: dict, track: str) -> str:
    start = TRACKS[track][3]
    return start + "x" * (field(form, track).get("max", form["limits"]["text"]) - len(start))


def with_terms(track: str, terms: list[str]) -> dict:
    data = base_bundle(track)["data"]
    section_id, field_id, _, _ = TRACKS[track]
    return {**data, section_id: {**data[section_id], field_id: terms}}


def read_back(form: dict, folder: pathlib.Path, track: str, text: str) -> dict:
    (folder / PROFILE).write_text(text, encoding="utf-8")
    return basics_read.read_back(form, folder, track, None)["daten"][TRACKS[track][0]]


@pytest.mark.parametrize("track", list(TRACKS))
def test_meine_angaben_shows_in_full_a_term_suche_einstellen_added(form, tmp_path, track):
    term = longest_term(form, track)
    written = markdown_files.search_profile(with_terms(track, ["Empfang EFZ" if track == APPRENTICESHIP else "Empfang"]),
                                            track, "")

    added = search_terms.added(written, term, TRACKS[track][2])

    assert term in read_back(form, tmp_path, track, added)[TRACKS[track][1]]


@pytest.mark.parametrize("track", list(TRACKS))
def test_suche_einstellen_shows_in_full_a_term_meine_angaben_saved(form, track):
    term = longest_term(form, track)
    assert not validation.field_errors(form, field(form, track), track, [term])

    saved = markdown_files.search_profile(with_terms(track, [term]), track, "")

    assert term in search_terms.current(saved)
