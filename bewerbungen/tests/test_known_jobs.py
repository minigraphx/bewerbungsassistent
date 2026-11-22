"""Known jobs by content (G109, #385) on the store of hits, with invented data."""
import datetime

import pytest

import hits

TODAY = datetime.date(2026, 11, 3)


def ad(number: int, **fields) -> dict:
    base = {"portal": "jobs.ch", "portal_id": f"m-{number}", "stelle": "Data Engineer 80–100 %", "firma": "Muster Mühle AG",
            "ort": "Bern", "pensum": "80–100 %", "link": f"https://www.jobs.ch/de/stellenangebote/detail/m-{number}/",
            "text": "Daten und Python."}
    return {**base, **fields}


@pytest.fixture
def store(tmp_path):
    return hits.Hits(tmp_path)


def test_the_same_ad_five_times_in_one_call_is_stored_once(store):
    result = store.add([ad(n) for n in range(1, 6)], [], TODAY)
    assert (result["neu"], result["zusammengefuehrt"]) == (1, 4)
    [job] = store.all()
    assert [w["link"] for w in job["weitere"]] == [ad(n)["link"] for n in range(2, 6)]


@pytest.mark.parametrize("changed", [{"ort": "Basel"}, {"pensum": "40 %", "stelle": "Data Engineer 40 %"},
                                     {"stelle": "Data Engineer Senior"}])
def test_ads_of_one_portal_that_differ_stay_two_jobs(store, changed):
    assert store.add([ad(1), ad(2, **changed)], [], TODAY)["neu"] == 2


def test_a_trial_and_the_apprenticeship_stay_two(store):
    register = [{"id": "schreinerei-schnupperlehre", "firma": "Schreinerei Beispiel", "stelle": "Schnupperlehre Schreiner/in EFZ",
                 "art": "Schnupperlehre", "ort": "Bern", "status": "Gemerkt",
                 "link": "https://www.yousty.ch/de-CH/lehrstellen/12#schnupperlehre"}]
    apprenticeship = ad(7, portal="yousty", firma="Schreinerei Beispiel", stelle="Schreiner/in EFZ", pensum="",
                        link="https://www.yousty.ch/de-CH/lehrstellen/13")
    assert store.screen([apprenticeship], (), 45, register)["holen"] == ["yousty:m-7"]


def test_a_repost_without_a_company_name_is_never_a_known_job(store):
    register = [{"id": "unbekannt-data-engineer", "firma": "unbekannt", "stelle": "Data Engineer", "ort": "Bern",
                 "status": "Beworben", "link": "https://www.jobs.ch/de/stellenangebote/detail/alt/"}]
    assert store.screen([ad(3, firma="")], (), 45, register)["holen"] == ["jobs.ch:m-3"]


def test_a_repost_of_a_saved_job_is_handed_over_for_the_register(store):
    register = [{"id": "muster-muehle-data-engineer", "firma": "Muster Mühle AG", "firma_schluessel": "muster-muehle",
                 "stelle": "Data Engineer", "ort": "3011 Bern", "status": "Absage",
                 "link": "https://www.jobs.ch/de/stellenangebote/detail/alt/"}]
    handed = []
    result = store.screen([ad(4)], (), 45, register, record_reposts=handed.append, today=TODAY)
    assert result["holen"] == []
    assert handed == [{"muster-muehle-data-engineer": [{"datum": "2026-11-03", "portal": "jobs.ch", "link": ad(4)["link"]}]}]
    assert store.all() == [], "a known job is not stored as a hit"
