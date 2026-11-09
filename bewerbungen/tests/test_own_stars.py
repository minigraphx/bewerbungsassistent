"""Own stars per hit and the order of the list (G22, #158); invented hits only."""
import json

import pytest
import yaml

import routes_ai
from test_ai_tasks import PackageClient, rating_entry
from test_app import post, server  # noqa: F401  (server is a fixture)
from test_routes_search import HIT, listing, search  # noqa: F401  (search is a fixture)


def stored_hit(s):
    post(s, "/api/suche/treffer", {"treffer": [HIT]})
    return listing(s)["treffer"][0]["id"]


def on_disk(s, hit_id):
    hits = yaml.safe_load((s.kontext.daten / "suche" / "treffer.yaml").read_text(encoding="utf-8"))
    return next(h for h in hits if h["id"] == hit_id)


def test_a_hit_gets_own_stars_that_can_change_and_go_again(search):  # noqa: F811
    hit_id = stored_hit(search)

    status, hit = post(search, "/api/suche/sterne", {"sterne": 4}, id=hit_id)
    assert status == 200 and hit["eigene_sterne"] == 4 and on_disk(search, hit_id)["eigene_sterne"] == 4

    assert post(search, "/api/suche/sterne", {"sterne": 2}, id=hit_id)[1]["eigene_sterne"] == 2
    status, hit = post(search, "/api/suche/sterne", {"sterne": 0}, id=hit_id)
    assert status == 200 and "eigene_sterne" not in hit and "eigene_sterne" not in on_disk(search, hit_id)


@pytest.mark.parametrize("stars", [6, -1, "3", True, 2.5, None])
def test_bad_stars_are_refused(search, stars):  # noqa: F811
    hit_id = stored_hit(search)

    assert post(search, "/api/suche/sterne", {"sterne": stars}, id=hit_id)[0] == 400


def test_stars_for_an_unknown_hit_are_refused(search):  # noqa: F811
    assert post(search, "/api/suche/sterne", {"sterne": 3}, id="jobs-ch-000000000000")[0] == 404


def test_own_stars_leave_the_grade_of_the_ai_and_never_reach_the_ai(search, monkeypatch):  # noqa: F811
    client = PackageClient(lambda labels: [rating_entry(label, 5) for label in labels])
    monkeypatch.setattr(routes_ai, "new_client", lambda: client)
    hit_id = stored_hit(search)
    post(search, "/api/suche/sterne", {"sterne": 1}, id=hit_id)

    rated = post(search, "/api/suche/bewerten", {}, id=hit_id)[1]
    after = post(search, "/api/suche/sterne", {"sterne": 3}, id=hit_id)[1]

    assert rated["bewertung"]["note"] == 5 and after["bewertung"] == rated["bewertung"]
    sent = json.dumps(client.messages.calls, ensure_ascii=False)
    assert "eigene_sterne" not in sent and "Sterne" not in sent and "★" not in sent


def test_the_order_of_the_list_is_remembered(search):  # noqa: F811
    assert listing(search)["einstellungen"]["sortierung"] == "note"

    status, settings = post(search, "/api/suche/einstellungen", {"sortierung": "eigene"})

    assert status == 200 and settings["sortierung"] == "eigene"
    assert listing(search)["einstellungen"]["sortierung"] == "eigene"
    assert post(search, "/api/suche/einstellungen", {"sortierung": "datum"})[1]["sortierung"] == "datum"


def test_an_unknown_order_is_refused(search):  # noqa: F811
    assert post(search, "/api/suche/einstellungen", {"sortierung": "zufall"})[0] == 400


def test_taking_over_does_not_carry_the_stars_into_the_register(search):  # noqa: F811
    hit_id = stored_hit(search)
    post(search, "/api/suche/sterne", {"sterne": 5}, id=hit_id)

    taken = post(search, "/api/suche/uebernehmen", {}, id=hit_id)[1]

    entry = next(b for b in search.kontext.register().alle() if b["id"] == taken["bewerbung_id"])
    assert "eigene_sterne" not in entry and "★" not in (entry.get("notiz") or "")
