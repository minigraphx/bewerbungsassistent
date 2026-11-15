"""Save every rated hit from a chosen grade on in one step (#214); invented hits only."""
import json
import pathlib

import pytest

from hits import Hits
from test_app import get, post, server  # noqa: F401  (server is a fixture)
from test_routes_search import HIT, listing, search  # noqa: F401  (search is a fixture)

PAGES = pathlib.Path(__file__).resolve().parents[1] / "seiten"
ROUTE = "/api/suche/ab-note"


def hit(number: int, title: str, company: str) -> dict:
    return {**HIT, "portal_id": f"abc-{number}", "stelle": title, "firma": company,
            "link": f"https://www.jobs.ch/de/stellenangebote/detail/abc-{number}/"}


HITS = {
    "best": hit(1, "Data Engineer", "Muster Daten AG"),
    "good": hit(2, "Python Entwicklerin", "Beispiel Software GmbH"),
    "edge": hit(3, "Backend Engineer", "Probe Systeme AG"),
    "low": hit(4, "Support Techniker", "Erfunden Service AG"),
    "unrated": hit(5, "Cloud Architektin", "Fiktiv Cloud GmbH"),
    "saved": hit(6, "Software Tester", "Muster Test AG"),
    "gone": hit(7, "Frontend Entwickler", "Beispiel Web AG"),
}
GRADES = {"best": 5.5, "good": 4.5, "edge": 4, "low": 3, "saved": 5, "gone": 5}


@pytest.fixture
def hits(search):  # noqa: F811
    """Seven hits: rated ones above and below 4, one unrated, one already saved and one discarded."""
    status, _ = post(search, "/api/suche/treffer", {"treffer": list(HITS.values())})
    assert status == 200
    by_title = {h["stelle"]: h["id"] for h in listing(search)["treffer"]}
    ids = {name: by_title[raw["stelle"]] for name, raw in HITS.items()}
    store = Hits(search.kontext.daten)
    for name, grade in GRADES.items():
        store.update(ids[name], bewertung={"note": grade, "zusammenfassung": f"Zu {name}"})
    assert post(search, "/api/suche/uebernehmen", {}, id=ids["saved"])[0] == 200
    assert post(search, "/api/suche/verwerfen", {}, id=ids["gone"])[0] == 200
    return ids


def preview(s, grade):
    status, _, content = get(s, ROUTE, note=grade)
    return status, json.loads(content)


def states(s) -> dict[str, str]:
    return {h["id"]: h["zustand"] for h in listing(s)["treffer"]}


def register_count(s) -> int:
    return len(s.kontext.register().alle())


def test_the_preview_names_how_many_and_which_hits_and_saves_nothing(search, hits):  # noqa: F811
    before = (states(search), register_count(search))

    status, answer = preview(search, "4")

    assert status == 200 and answer["note"] == 4
    assert answer["anzahl"] == 3
    assert [h["id"] for h in answer["treffer"]] == [hits["best"], hits["good"], hits["edge"]]
    assert answer["treffer"][0] == {"id": hits["best"], "stelle": "Data Engineer", "firma": "Muster Daten AG", "note": 5.5}
    assert (states(search), register_count(search)) == before


def test_the_chosen_grade_decides_which_hits_count(search, hits):  # noqa: F811
    assert [h["id"] for h in preview(search, "4.5")[1]["treffer"]] == [hits["best"], hits["good"]]
    assert [h["id"] for h in preview(search, "3")[1]["treffer"]] == [hits["best"], hits["good"], hits["edge"], hits["low"]]
    assert preview(search, "6")[1] == {"note": 6, "anzahl": 0, "treffer": []}


def test_confirming_saves_exactly_those_hits_and_leaves_the_others(search, hits):  # noqa: F811
    before = states(search)
    known = {e["id"] for e in search.kontext.register().alle()}
    ids = [h["id"] for h in preview(search, "3.5")[1]["treffer"]]

    status, answer = post(search, ROUTE, {"note": 3.5, "ids": ids})

    assert status == 200 and sorted(answer["gemerkt"]) == sorted(ids) and answer["uebersprungen"] == []
    after = states(search)
    for name in ("best", "good", "edge"):
        assert after[hits[name]] == "uebernommen"
    for name in ("low", "unrated", "gone"):
        assert after[hits[name]] == before[hits[name]]
    assert after[hits["saved"]] == "uebernommen"
    added = [e for e in search.kontext.register().alle() if e["id"] not in known]
    assert sorted(e["firma"] for e in added) == ["Beispiel Software GmbH", "Muster Daten AG", "Probe Systeme AG"]
    assert all(e["status"] == "Gemerkt" for e in added)


def test_hits_that_do_not_qualify_are_never_saved_this_way(search, hits):  # noqa: F811
    others = [hits[name] for name in ("low", "unrated", "saved", "gone")]
    before = (states(search), register_count(search))

    status, answer = post(search, ROUTE, {"note": 4, "ids": [*others, "jobs-ch-000000000000"]})

    assert status == 200 and answer["gemerkt"] == []
    assert sorted(answer["uebersprungen"]) == sorted([*others, "jobs-ch-000000000000"])
    assert (states(search), register_count(search)) == before


def test_only_the_confirmed_hits_are_saved(search, hits):  # noqa: F811
    status, answer = post(search, ROUTE, {"note": 4, "ids": [hits["good"]]})

    assert status == 200 and answer["gemerkt"] == [hits["good"]]
    after = states(search)
    assert after[hits["good"]] == "uebernommen"
    assert after[hits["best"]] == "neu" and after[hits["edge"]] == "neu"


def test_a_hit_rated_lower_since_the_preview_is_skipped(search, hits):  # noqa: F811
    ids = [h["id"] for h in preview(search, "4")[1]["treffer"]]
    Hits(search.kontext.daten).update(hits["edge"], bewertung={"note": 3.5, "zusammenfassung": "Neu bewertet"})

    answer = post(search, ROUTE, {"note": 4, "ids": ids})[1]

    assert sorted(answer["gemerkt"]) == sorted([hits["best"], hits["good"]])
    assert answer["uebersprungen"] == [hits["edge"]] and states(search)[hits["edge"]] == "neu"


@pytest.mark.parametrize("grade", ["0.5", "6.5", "3.3", "vier", ""])
def test_a_grade_outside_one_to_six_in_half_steps_is_refused_in_the_preview(search, hits, grade):  # noqa: F811
    assert preview(search, grade)[0] == 400


@pytest.mark.parametrize("body", [{"note": 7, "ids": []}, {"note": True, "ids": []}, {"note": "4", "ids": []},
                                  {"note": 4}, {"note": 4, "ids": "alle"}, {"note": 4, "ids": [4]}])
def test_a_bad_confirmation_is_refused_and_saves_nothing(search, hits, body):  # noqa: F811
    before = (states(search), register_count(search))

    assert post(search, ROUTE, body)[0] == 400
    assert (states(search), register_count(search)) == before


def test_the_page_offers_the_step_with_a_chosen_grade():
    page = (PAGES / "treffer.html").read_text(encoding="utf-8")

    assert 'src="/merken-ab-note.js"' in page and 'id="ab-note"' in page
    assert "Alle ab Note" in page
