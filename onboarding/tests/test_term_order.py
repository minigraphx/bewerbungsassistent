"""The order set on Suche einstellen (#285, G87) is the app's own section: Meine Angaben keeps it and lists none of it.

All data is invented.
"""
import pytest

import basics_read
import markdown_files
import search_terms
from basics_slots import APPRENTICESHIP, JOB, PROFILE
from form_cases import base_bundle

TERMS = {JOB: ("searchJob", "keywords", ["Empfang", "Logistik", "Buchhaltung"]),
         APPRENTICESHIP: ("searchApprenticeship", "professions", ["Koch/Köchin EFZ", "Maler/in EFZ", "Gärtner/in EFZ"])}


def ordered_profile(track: str) -> tuple[str, list[str]]:
    section_id, field_id, terms = TERMS[track]
    data = base_bundle(track)["data"]
    written = markdown_files.search_profile({**data, section_id: {**data[section_id], field_id: terms}}, track, "")
    order = [*reversed(search_terms.current(written))]
    return search_terms.reordered(written, order), order


@pytest.mark.parametrize("track", list(TERMS))
def test_meine_angaben_lists_no_line_of_the_order_as_unknown(form, tmp_path, track):
    text, _ = ordered_profile(track)
    (tmp_path / PROFILE).write_text(text, encoding="utf-8")

    unknown = basics_read.read_back(form, tmp_path, track, None)["fremd"]

    assert not [group for group in unknown if group["ueberschrift"] == "Reihenfolge der Suche"]


@pytest.mark.parametrize("track", list(TERMS))
def test_the_order_still_holds_after_meine_angaben_saved_the_profile(form, tmp_path, track):
    text, order = ordered_profile(track)
    (tmp_path / PROFILE).write_text(text, encoding="utf-8")
    section_id, field_id, terms = TERMS[track]
    data = base_bundle(track)["data"]
    replaced = markdown_files.search_profile({**data, section_id: {**data[section_id], field_id: terms}}, track, "")

    kept, _ = search_terms.kept_on_replace(text, replaced)

    assert list(search_terms.current(kept)) == order
