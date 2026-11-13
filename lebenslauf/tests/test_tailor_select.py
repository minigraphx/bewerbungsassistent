"""Choosing and ordering stations in a tailoring (`select`, G17): a CV made on the page of an application."""
import copy

from tailor import tailor

CV = {
    "basics": {"name": "Erika Beispiel", "summary": "Alt"},
    "work": [
        {"position": "Entwicklerin", "name": "Beispiel AG", "startDate": "2019-03", "highlights": ["A"]},
        {"position": "Junior", "name": "Muster GmbH", "startDate": 2015},
        {"position": "Praktikantin", "name": "Probe AG", "startDate": 2014, "tags": ["web"]},
    ],
    "education": [{"studyType": "Bachelor", "institution": "Beispiel-Hochschule", "startDate": 2011}],
}


def test_select_keeps_only_the_named_stations_in_the_given_order():
    job = {"select": {"work": [{"position": "Praktikantin", "name": "Probe AG", "startDate": 2014},
                               {"position": "Entwicklerin", "name": "Beispiel AG", "startDate": "2019-03"}]}}

    out = tailor(CV, job)

    assert [w["name"] for w in out["work"]] == ["Probe AG", "Beispiel AG"]
    assert "tags" not in out["work"][0]


def test_a_section_select_does_not_name_stays_as_it_is():
    out = tailor(CV, {"select": {"work": []}})

    assert out["work"] == []
    assert out["education"] == CV["education"]


def test_a_station_that_no_longer_exists_is_left_out_and_nothing_else_is_taken():
    out = tailor(CV, {"select": {"work": [{"position": "Entwicklerin", "name": "Beispiel AG", "startDate": "2020"},
                                          {"position": "Junior", "name": "Muster GmbH", "startDate": 2015}]}})

    assert [w["name"] for w in out["work"]] == ["Muster GmbH"]


def test_select_with_the_overrides_of_basics_leaves_the_master_cv_unchanged():
    before = copy.deepcopy(CV)

    out = tailor(CV, {"basics": {"summary": "Neu"}, "select": {"work": [{"name": "Muster GmbH"}]}})

    assert out["basics"]["summary"] == "Neu"
    assert [w["name"] for w in out["work"]] == ["Muster GmbH"]
    assert CV == before


def test_a_station_is_taken_once_even_when_two_matchers_fit():
    out = tailor(CV, {"select": {"work": [{"name": "Muster GmbH"}, {"name": "Muster GmbH"}]}})

    assert [w["name"] for w in out["work"]] == ["Muster GmbH"]
