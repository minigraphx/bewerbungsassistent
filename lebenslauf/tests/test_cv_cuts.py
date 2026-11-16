"""Cuts for one application (G92): what the person ticks under the check goes only from that application's CV.

`cuts.options` names each cut with what goes, `cuts.apply` takes the stored cuts out of a tailored CV, and the builds
take them with `--kuerzungen`. `tailor` limits the points of single stations for it. All CVs are invented.
"""
import copy
import json

import yaml

import build
import cuts
import dossier
from page_fill_samples import cv_of_length, example_cv, example_letter
from tailor import tailor

FIRST = {"position": "Projektleiterin Daten 0", "name": "Muster Informatik 0 AG", "startDate": "2000-01"}


def _station(cv: dict, position: str) -> dict:
    return next(s for s in cv["work"] if s["position"] == position)


def test_tailor_limits_the_points_of_one_station_and_leaves_the_others():
    cv = cv_of_length(9)
    job = {"max_highlights_per_station": [{**FIRST, "max": 1}]}

    out = tailor(cv, job)

    assert len(_station(out, "Projektleiterin Daten 0")["highlights"]) == 1
    assert len(_station(out, "Projektleiterin Daten 1")["highlights"]) == 3
    assert len(_station(cv, "Projektleiterin Daten 0")["highlights"]) == 3, "the base CV stays as it is"


def test_a_station_is_found_by_its_fields_also_with_a_year_as_number():
    cv = example_cv()  # Junior-Entwicklerin starts in 2015, a number in YAML
    job = {"max_highlights_per_station": [{"position": "Junior-Entwicklerin", "name": "Muster GmbH",
                                           "startDate": "2015", "max": 1}]}

    assert len(_station(tailor(cv, job), "Junior-Entwicklerin")["highlights"]) == 1


def test_each_cut_names_what_goes_with_the_years_of_its_station():
    options = cuts.options(cv_of_length(9))  # two stations of three points and one of one point

    assert options[0].text == "2 Stichpunkte bei «Projektleiterin Daten 0, Muster Informatik 0 AG» (2000–2001)"
    assert options[1].text == "2 Stichpunkte bei «Projektleiterin Daten 1, Muster Informatik 1 AG» (2001–2002)"
    assert all("Daten 99" not in option.text for option in options), "a single point is no cut worth naming"
    assert len({option.id for option in options}) == len(options)


def test_a_station_until_today_and_a_section_are_named_as_such():
    texts = [option.text for option in cuts.options(example_cv())]

    assert "2 Stichpunkte bei «Software-Entwicklerin, Beispiel AG» (2019–heute)" in texts
    assert "Abschnitt «Weitere Projekte»" in texts
    assert cuts.options({"basics": {"name": "Erika Beispiel"}}) == []


def test_the_ids_stay_the_same_for_the_same_cv():
    assert [o.id for o in cuts.options(cv_of_length(9))] == [o.id for o in cuts.options(cv_of_length(9))]


def test_chosen_cuts_are_stored_as_records_and_applied_to_a_copy():
    cv = example_cv()
    chosen = [o for o in cuts.options(cv) if o.id in {cuts.options(cv)[0].id, "abschnitt:more-projects"}]
    stored = cuts.chosen(chosen, {})
    before = copy.deepcopy(cv)

    out = cuts.apply(cv, stored)

    assert cv == before
    assert len(_station(out, "Software-Entwicklerin")["highlights"]) == 1
    assert not [p for p in out["projects"] if p.get("group") == "more"]
    assert [p for p in out["projects"] if p.get("group") != "more"]
    assert stored["abschnitte"] == ["more-projects"]


def test_after_a_cut_the_next_one_comes_first():
    cv = cv_of_length(9)
    stored = cuts.chosen([cuts.options(cv)[0]], {})

    after = cuts.options(cuts.apply(cv, stored))

    assert after[0].text.startswith("2 Stichpunkte bei «Projektleiterin Daten 1")


def test_cutting_a_station_again_keeps_fewer_points_in_the_same_record():
    cv = cv_of_length(4)
    cv["work"][-1]["highlights"] *= 2  # six points
    first = cuts.chosen([cuts.options(cv)[0]], {})
    again = cuts.chosen([cuts.options(cuts.apply(cv, first))[0]], first)

    assert [r["behalten"] for r in first["stichpunkte"]] == [3]
    assert [r["behalten"] for r in again["stichpunkte"]] == [1]


def test_a_stored_record_names_what_is_left_out_and_can_be_taken_back():
    cv = example_cv()
    stored = cuts.chosen([cuts.options(cv)[0], *[o for o in cuts.options(cv) if o.id == "abschnitt:interests"]], {})

    left_out = cuts.left_out(cv, stored)

    assert [entry.text for entry in left_out] == ["2 Stichpunkte bei «Software-Entwicklerin, Beispiel AG» (2019–heute)",
                                                  "Abschnitt «Interessen»"]
    back = cuts.without(stored, left_out[0].id)
    assert back == {"stichpunkte": [], "abschnitte": ["interests"]}


def test_broken_stored_cuts_change_nothing():
    cv = example_cv()
    for stored in (None, [], {"stichpunkte": "x", "abschnitte": [7, "unbekannt"]}, {"stichpunkte": [{"behalten": "x"}]}):
        assert cuts.apply(cv, stored) == tailor(cv, {})


def _cut_file(folder, cv: dict) -> str:
    stored = cuts.chosen([cuts.options(cv)[0]], {})
    path = folder / "kuerzungen.yaml"
    path.write_text(yaml.safe_dump(stored, allow_unicode=True), encoding="utf-8")
    return str(path)


def test_the_cv_build_takes_the_cuts_of_the_application(tmp_path):
    cv = example_cv()
    (tmp_path / "cv.yaml").write_text(yaml.safe_dump(cv, allow_unicode=True), encoding="utf-8")

    build.main([str(tmp_path / "cv.yaml"), "--kuerzungen", _cut_file(tmp_path, cv), "--build-dir", str(tmp_path / "b"),
                "-o", str(tmp_path / "cv.pdf")])

    built = json.loads((tmp_path / "b" / "cv.json").read_text(encoding="utf-8"))
    assert len(_station(built, "Software-Entwicklerin")["highlights"]) == 1


def test_the_dossier_build_takes_the_cuts_of_the_application(tmp_path):
    cv = example_cv()
    (tmp_path / "cv.yaml").write_text(yaml.safe_dump(cv, allow_unicode=True), encoding="utf-8")
    (tmp_path / "brief.yaml").write_text(yaml.safe_dump(example_letter(), allow_unicode=True), encoding="utf-8")
    (tmp_path / "dossier.yaml").write_text(yaml.safe_dump({"lebenslauf": "cv.yaml", "anschreiben": "brief.yaml"}),
                                           encoding="utf-8")

    result = dossier.main([str(tmp_path / "dossier.yaml"), "--kuerzungen", _cut_file(tmp_path, cv),
                           "--build-dir", str(tmp_path / "b"), "--out-dir", str(tmp_path / "out")])

    built = json.loads(result.data.read_text(encoding="utf-8"))["cv"]
    assert len(_station(built, "Software-Entwicklerin")["highlights"]) == 1
