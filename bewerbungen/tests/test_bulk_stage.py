"""Changing the stage of several applications at once from the overview (#170, G29)."""
import pytest

import register as register_module
from register import Register
from sample_folder import BRIEF_ID
from test_app import get, post, server  # noqa: F401  (fixtures)

ROUTE = "/api/bewerbungen/stand"
TODAY = "2026-10-26"  # the server fixture's today


def add_entries(folder):
    reg = Register(folder)
    first = reg.neu(firma="Muster GmbH", stelle="Analyst", status="Beworben", beworben_am="2026-10-01")
    second = reg.neu(firma="Probe AG", stelle="Entwickler", status="Beworben", absage_am="2026-10-20")
    return first["id"], second["id"]


def drafts(s):
    return s.kontext.ablage.liste(s.kontext.daten / "bewerbungen.yaml")


def register_bytes(s):
    return (s.kontext.daten / "bewerbungen.yaml").read_bytes()


def count_writes(monkeypatch):
    writes = []
    original = register_module.Register._schreibe

    def counting(self, entries):
        writes.append(len(entries))
        return original(self, entries)

    monkeypatch.setattr(register_module.Register, "_schreibe", counting)
    return writes


def test_sets_the_stage_of_several_applications_in_one_write(server, monkeypatch):
    first, second = add_entries(server.kontext.daten)
    writes = count_writes(monkeypatch)

    status, answer = post(server, ROUTE, {"ids": [first, second], "status": "Zurückgezogen"})

    assert status == 200
    assert sorted(b["id"] for b in answer["bewerbungen"]) == sorted([first, second])
    reg = Register(server.kontext.daten)
    assert [reg.hole(i)["status"] for i in (first, second)] == ["Zurückgezogen", "Zurückgezogen"]
    assert reg.hole(BRIEF_ID)["status"] == "Gemerkt"
    assert writes == [3]


def test_one_draft_before_and_one_after(server):
    first, second = add_entries(server.kontext.daten)
    before = register_bytes(server)

    post(server, ROUTE, {"ids": [first, second], "status": "Verworfen"})

    saved = drafts(server)
    assert len(saved) == 2
    assert server.kontext.ablage.inhalt(saved[-1].id) == before
    assert server.kontext.ablage.inhalt(saved[0].id) == register_bytes(server)


def test_a_rejection_gets_today_only_where_the_date_is_missing(server):
    first, second = add_entries(server.kontext.daten)

    status, _ = post(server, ROUTE, {"ids": [first, second], "status": "Absage"})

    assert status == 200
    reg = Register(server.kontext.daten)
    assert reg.hole(first)["absage_am"] == TODAY
    assert reg.hole(second)["absage_am"] == "2026-10-20"


def test_other_stages_leave_the_rejection_date_alone(server):
    first, _ = add_entries(server.kontext.daten)

    status, _ = post(server, ROUTE, {"ids": [first], "status": "Gespräch"})

    assert status == 200
    changed = Register(server.kontext.daten).hole(first)
    assert changed["status"] == "Gespräch"
    assert "absage_am" not in changed


def test_an_unknown_id_changes_nothing(server):
    first, _ = add_entries(server.kontext.daten)
    before = register_bytes(server)

    status, answer = post(server, ROUTE, {"ids": [first, "gibt-es-nicht"], "status": "Absage"})

    assert status == 400
    assert "gibt-es-nicht" in answer["fehler"]
    assert "Bewerbung" in answer["fehler"]
    assert register_bytes(server) == before
    assert drafts(server) == []


def test_an_unknown_stage_changes_nothing(server):
    first, _ = add_entries(server.kontext.daten)
    before = register_bytes(server)

    status, answer = post(server, ROUTE, {"ids": [first], "status": "Kaputt"})

    assert status == 400
    assert "Kaputt" in answer["fehler"]
    assert "Stand" in answer["fehler"]
    assert register_bytes(server) == before
    assert drafts(server) == []


@pytest.mark.parametrize("body", [
    {"ids": [], "status": "Absage"},
    {"ids": "muster", "status": "Absage"},
    {"ids": [3], "status": "Absage"},
    {"status": "Absage"},
    {"ids": [BRIEF_ID]},
    ["kein", "objekt"],
])
def test_a_request_without_ids_or_stage_is_refused(server, body):
    before = register_bytes(server)

    status, answer = post(server, ROUTE, body)

    assert status == 400
    assert answer["fehler"]
    assert register_bytes(server) == before


def test_the_same_id_twice_counts_once(server):
    first, _ = add_entries(server.kontext.daten)

    status, answer = post(server, ROUTE, {"ids": [first, first], "status": "Zusage"})

    assert status == 200
    assert [b["id"] for b in answer["bewerbungen"]] == [first]
