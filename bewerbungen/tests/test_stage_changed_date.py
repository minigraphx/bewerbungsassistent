"""The date of the last change of stage (#458, G135): every way of changing the stage records it, the same stage again
does not. Entries are invented; the server fixture's today is 2026-10-26."""
import datetime
import json

import register
from register import Register
from test_app import get, post, server  # noqa: F401  (server is a fixture)
from test_apply import ready

TODAY = "2026-10-26"
EARLIER = "2026-10-01"
FIELD = "stand_geaendert_am"


def entry(folder, status="Beworben", **fields):
    return Register(folder).neu(firma="Muster GmbH", stelle="Analyst", status=status, **fields)


def saved(server, entry_id):
    return Register(server.kontext.daten).hole(entry_id)


# The register


def test_with_stage_records_the_day_of_a_real_change():
    changed = register.with_stage({"id": "a", "status": "Beworben"}, "Gespräch", datetime.date(2026, 11, 3))

    assert changed[FIELD] == "2026-11-03"


def test_with_stage_keeps_the_date_when_the_stage_stays():
    same = register.with_stage({"id": "a", "status": "Beworben", FIELD: EARLIER}, "Beworben", datetime.date(2026, 11, 3))

    assert same[FIELD] == EARLIER


def test_an_entry_without_a_stage_counts_as_saved():
    same = register.with_stage({"id": "a"}, "Gemerkt", datetime.date(2026, 11, 3))

    assert FIELD not in same


def test_the_date_is_a_known_date_field():
    checked = register.pruefe_bewerbung({"id": "a", "firma": "Muster GmbH", "stelle": "Analyst", FIELD: "03.11.2026"})

    assert checked[FIELD] == "2026-11-03"


def test_saving_a_new_stage_records_the_registers_today(tmp_path):
    reg = Register(tmp_path, today=lambda: datetime.date(2026, 11, 3))
    first = reg.neu(firma="Muster GmbH", stelle="Analyst", status="Gemerkt")

    reg.speichere({**first, "status": "Bewerben"})

    assert reg.hole(first["id"])[FIELD] == "2026-11-03"


def test_saving_other_fields_or_the_same_stage_keeps_the_date(tmp_path):
    reg = Register(tmp_path, today=lambda: datetime.date(2026, 11, 3))
    first = reg.neu(firma="Muster GmbH", stelle="Analyst", status="Beworben", **{FIELD: EARLIER})

    reg.speichere({**first, "notiz": "nachgefragt"})
    reg.speichere({**reg.hole(first["id"]), "status": "Beworben"})

    assert reg.hole(first["id"])[FIELD] == EARLIER


def test_a_new_entry_has_no_date_of_a_change(tmp_path):
    reg = Register(tmp_path, today=lambda: datetime.date(2026, 11, 3))

    first = reg.neu(firma="Muster GmbH", stelle="Analyst", status="Bewerben")

    assert FIELD not in first


# The application's page, and Claude's update_application, which posts to the same route


def test_the_application_page_records_the_day_of_the_change(server):
    first = entry(server.kontext.daten)

    status, answer = post(server, "/api/bewerbung", {"id": first["id"], "status": "Gespräch"})

    assert status == 200
    assert answer[FIELD] == TODAY
    assert saved(server, first["id"])[FIELD] == TODAY


def test_the_application_page_keeps_the_date_when_the_stage_stays(server):
    first = entry(server.kontext.daten, **{FIELD: EARLIER})

    post(server, "/api/bewerbung", {"id": first["id"], "status": "Beworben", "notiz": "nachgefragt"})

    assert saved(server, first["id"])[FIELD] == EARLIER


def test_the_application_page_cannot_write_the_date_itself(server):
    first = entry(server.kontext.daten, **{FIELD: EARLIER})

    post(server, "/api/bewerbung", {"id": first["id"], FIELD: "2026-10-20"})

    assert saved(server, first["id"])[FIELD] == EARLIER


def test_the_list_shows_the_date(server):
    first = entry(server.kontext.daten)
    post(server, "/api/bewerbung", {"id": first["id"], "status": "Absage"})

    status, _, content = get(server, "/api/bewerbungen")

    listed = {b["id"]: b for b in json.loads(content)["bewerbungen"]}
    assert status == 200 and listed[first["id"]][FIELD] == TODAY


# Bulk change on Bewerbungen; the pass on Heute and „Merken“ on Stellen use the same route


def test_the_bulk_change_records_the_day_only_where_the_stage_changes(server):
    moved = entry(server.kontext.daten, status="Beworben")
    stays = entry(server.kontext.daten, status="Gespräch", **{FIELD: EARLIER})

    status, _ = post(server, "/api/bewerbungen/stand", {"ids": [moved["id"], stays["id"]], "status": "Gespräch"})

    assert status == 200
    assert saved(server, moved["id"])[FIELD] == TODAY
    assert saved(server, stays["id"])[FIELD] == EARLIER


# Recording the dispatch on the application's page, and from the form through the extension


def test_recording_the_dispatch_records_the_day_of_the_change(server):
    first = ready(server)

    status, answer = post(server, "/api/versand", {"datum": "2026-10-20", "art": "elektronisch"}, id=first["id"])

    assert status == 200, answer
    assert answer["bewerbung"]["status"] == "Beworben"
    assert saved(server, first["id"])[FIELD] == TODAY


def test_the_extension_records_the_day_when_the_form_was_sent(server):
    first = ready(server)

    status, _ = post(server, "/api/bewerben/abgeschickt", {"id": first["id"]})

    assert status == 200
    assert saved(server, first["id"])[FIELD] == TODAY
