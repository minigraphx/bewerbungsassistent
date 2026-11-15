"""Suche einstellen and Meine Angaben take the same values for region, exclusions and title filter (#302).

A value saved on one page is taken in full by the other: Meine Angaben reads it back into its fields, and Suche
einstellen shows it and saves it again. All data is invented.
"""
import pathlib

import pytest

import basics_read
import markdown_files
import search_frame
import validation
from basics_slots import JOB, PROFILE
from form_cases import base_bundle

LISTS = {"ausschluss": "exclusions", "titel_ausschluss": "titleExclude", "titel_positiv": "titlePositive"}
TEXTS = {"wohnort": "home", "pensum": "workload"}


def written_by_meine_angaben() -> str:
    return markdown_files.search_profile(base_bundle(JOB)["data"], JOB, "")


def field(form: dict, field_id: str) -> dict:
    section = next(s for s in form["sections"] if s["id"] == "searchJob")
    return next(f for f in section["fields"] if f["id"] == field_id)


def chars(form: dict, field_id: str) -> int:
    return field(form, field_id).get("max", form["limits"]["text"])


def lines(form: dict, field_id: str) -> int:
    return field(form, field_id).get("maxItems", form["limits"]["listItems"])


def as_long_as(text: str, length: int) -> str:
    return text + "x" * (length - len(text))


def at_the_limits(form: dict) -> dict:
    """Every list as full as the form takes it, each line as long as it takes; one line holds a slash."""
    values = {}
    for key, field_id in LISTS.items():
        full = [as_long_as(f"{field_id} {n} ", chars(form, field_id)) for n in range(lines(form, field_id))]
        values[key] = ["Entwickler/Developer", *full[1:]]
    for key, field_id in TEXTS.items():
        values[key] = as_long_as(f"{field_id} ", chars(form, field_id))
    return values


def read_back(form: dict, folder: pathlib.Path, text: str) -> dict:
    (folder / PROFILE).write_text(text, encoding="utf-8")
    return basics_read.read_back(form, folder, JOB, None)


def test_meine_angaben_takes_in_full_what_suche_einstellen_saved(form, tmp_path):
    values = at_the_limits(form)
    saved = search_frame.with_values(written_by_meine_angaben(), values)

    answers = read_back(form, tmp_path, saved)

    search = answers["daten"]["searchJob"]
    assert {key: search.get(field_id) for key, field_id in {**LISTS, **TEXTS}.items()} == values
    assert not [group for group in answers["fremd"] if group["ueberschrift"] in ("Suchrichtungen", "Titelfilter")]


def test_suche_einstellen_takes_in_full_what_meine_angaben_saved(form):
    values = at_the_limits(form)
    data = {**base_bundle(JOB)["data"]}
    data["searchJob"] = {**data["searchJob"], **{f: values[k] for k, f in {**LISTS, **TEXTS}.items()}}
    fields = {**LISTS, **TEXTS}.values()
    assert not [e for f in fields for e in validation.field_errors(form, field(form, f), JOB, data["searchJob"][f])]

    saved = markdown_files.search_profile(data, JOB, "")

    assert {key: search_frame.values(saved)[key] for key in values} == values
    assert search_frame.with_values(saved, values) == saved


@pytest.mark.parametrize("key", [*LISTS, *TEXTS])
def test_suche_einstellen_refuses_a_value_longer_than_meine_angaben_takes(form, key):
    limit = chars(form, {**LISTS, **TEXTS}[key])
    value = as_long_as("Wert ", limit + 1)

    with pytest.raises(ValueError, match=f"höchstens {limit} Zeichen"):
        search_frame.with_values(written_by_meine_angaben(), {key: [value] if key in LISTS else value})


@pytest.mark.parametrize("key", list(LISTS))
def test_suche_einstellen_refuses_more_lines_than_meine_angaben_takes(form, key):
    limit = lines(form, LISTS[key])

    with pytest.raises(ValueError, match=f"höchstens {limit} Begriffe"):
        search_frame.with_values(written_by_meine_angaben(), {key: [f"Wort {n}" for n in range(limit + 1)]})
