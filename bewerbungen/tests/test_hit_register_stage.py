"""#373: a hit taken into the register shows the current stage of its application, read from the register and never
written into the hits. All data here is invented."""
import yaml

from test_app import post, server  # noqa: F401  (server is a fixture)
from test_routes_search import HIT, listing, search  # noqa: F401  (search is a fixture)


def taken_over(s) -> tuple[str, str]:
    post(s, "/api/suche/treffer", {"treffer": [HIT]})
    hit_id = listing(s)["treffer"][0]["id"]
    status, taken = post(s, "/api/suche/uebernehmen", {}, id=hit_id)
    assert status == 200
    return hit_id, taken["bewerbung_id"]


def listed(s, hit_id: str) -> dict:
    return next(hit for hit in listing(s)["treffer"] if hit["id"] == hit_id)


def stored_hits(s) -> str:
    return (s.kontext.daten / "suche" / "treffer.yaml").read_text(encoding="utf-8")


def test_merken_answers_with_the_stage_gemerkt(search):
    post(search, "/api/suche/treffer", {"treffer": [HIT]})
    hit_id = listing(search)["treffer"][0]["id"]
    assert post(search, "/api/suche/uebernehmen", {}, id=hit_id)[1]["stand"] == "Gemerkt"


def test_the_list_follows_the_stage_of_the_application(search):
    hit_id, entry_id = taken_over(search)
    assert listed(search, hit_id)["stand"] == "Gemerkt"
    assert post(search, "/api/bewerbungen/stand", {"ids": [entry_id], "status": "Beworben"})[0] == 200
    assert listed(search, hit_id)["stand"] == "Beworben"
    post(search, "/api/bewerbungen/stand", {"ids": [entry_id], "status": "Absage"})
    hit = listed(search, hit_id)
    assert (hit["stand"], hit["zustand"]) == ("Absage", "uebernommen")


def test_the_stage_is_read_and_never_stored_in_the_hits(search):
    hit_id, entry_id = taken_over(search)
    post(search, "/api/bewerbungen/stand", {"ids": [entry_id], "status": "Beworben"})
    assert listed(search, hit_id)["stand"] == "Beworben"
    stored = yaml.safe_load(stored_hits(search))
    assert stored and all("stand" not in hit for hit in stored)
    assert "Beworben" not in stored_hits(search)


def test_a_deleted_application_leaves_the_stage_empty(search):
    hit_id, entry_id = taken_over(search)
    path = search.kontext.daten / "bewerbungen.yaml"
    entries = yaml.safe_load(path.read_text(encoding="utf-8"))
    path.write_text(yaml.safe_dump([e for e in entries if e["id"] != entry_id], allow_unicode=True), encoding="utf-8")
    hit = listed(search, hit_id)
    assert "stand" in hit and hit["stand"] is None


def test_new_and_discarded_hits_carry_no_stage(search):
    post(search, "/api/suche/treffer", {"treffer": [HIT, {**HIT, "portal_id": "abc-2", "stelle": "Data Analyst",
                                                         "link": "https://www.jobs.ch/de/stellenangebote/detail/abc-2/"}]})
    first, second = (hit["id"] for hit in listing(search)["treffer"])
    post(search, "/api/suche/verwerfen", {}, id=second)
    assert "stand" not in listed(search, first)
    assert "stand" not in listed(search, second)


def test_own_stars_on_a_saved_hit_keep_its_stage(search):
    hit_id, entry_id = taken_over(search)
    post(search, "/api/bewerbungen/stand", {"ids": [entry_id], "status": "Gespräch"})
    assert post(search, "/api/suche/sterne", {"sterne": 4}, id=hit_id)[1]["stand"] == "Gespräch"
