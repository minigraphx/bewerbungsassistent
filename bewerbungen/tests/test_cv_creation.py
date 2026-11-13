"""Creating a CV on the page of an application (G17, #118): content from Meine Angaben, design apart from it."""
import json

import pytest
import yaml

import unterlagen
from register import Register
from sample_folder import BRIEF_ID
from test_app import get, post, server  # noqa: F401  (server is a fixture)
from varianten import Varianten

ROUTE = "/api/lebenslauf/erstellen"


def form(s, entry_id: str = BRIEF_ID) -> dict:
    status, _, body = get(s, ROUTE, id=entry_id)
    assert status == 200, body
    return json.loads(body)


def section(answer: dict, name: str) -> dict:
    return next(part for part in answer["abschnitte"] if part["abschnitt"] == name)


def choice(answer: dict, **changes) -> dict:
    return {"id": BRIEF_ID, "stand": answer["stand"], "stationen": {"work": [1, 0], "education": [0]},
            "berufsbezeichnung": "Data Engineer", "kurzprofil": "Baut Datenpipelines.",
            "design": "einspaltig", "bezeichnung": "Daten, Beispiel AG", **changes}


def test_the_form_lists_the_stations_and_the_summary_from_meine_angaben(server):  # noqa: F811
    answer = form(server)

    work = section(answer, "work")
    assert work["titel"] == "Berufserfahrung"
    assert [station["titel"] for station in work["stationen"]] == ["Software-Entwicklerin", "Junior-Entwicklerin"]
    assert [station["zusatz"] for station in work["stationen"]] == ["Beispiel AG", "Muster GmbH"]
    assert [station["zeit"] for station in work["stationen"]] == ["03.2019 – heute", "2015 – 2019"]
    assert all(station["gewaehlt"] for station in work["stationen"])
    assert section(answer, "education")["titel"] == "Bildung und Weiterbildung"
    assert answer["kurzprofil"].startswith("Software-Entwicklerin mit zehn Jahren")
    assert answer["berufsbezeichnung"] == "Software-Entwicklerin – Web und Daten"
    assert answer["design"] == "zweispaltig" and answer["designs"] == ["zweispaltig", "einspaltig"]
    assert answer["bezeichnung"] == "Data Engineer, Beispiel AG"


def test_creating_writes_the_tailoring_and_the_variant_and_chooses_both(server):  # noqa: F811
    daten = server.kontext.daten

    status, answer = post(server, ROUTE, choice(form(server)))

    assert status == 200, answer
    variant = answer["variante"]
    assert variant["id"] == BRIEF_ID and variant["quelle"] == f"jobs/{BRIEF_ID}.yaml"
    assert variant["beschreibung"] == "Daten, Beispiel AG"
    assert Varianten(daten).hole(BRIEF_ID)["quelle"] == f"jobs/{BRIEF_ID}.yaml"
    job = yaml.safe_load((daten / "jobs" / f"{BRIEF_ID}.yaml").read_text(encoding="utf-8"))
    assert job["created_for"] == BRIEF_ID
    assert job["basics"] == {"label": "Data Engineer", "summary": "Baut Datenpipelines."}
    assert [station["name"] for station in job["select"]["work"]] == ["Muster GmbH", "Beispiel AG"]
    entry = Register(daten).hole(BRIEF_ID)
    assert entry["variante"] == BRIEF_ID and entry["lebenslauf_design"] == "einspaltig"


def test_the_new_cv_is_built_as_pdf_from_the_choice(server):  # noqa: F811
    daten = server.kontext.daten

    status, answer = post(server, ROUTE, choice(form(server)))

    assert status == 200 and answer["gebaut"] is True
    assert unterlagen.pdf_pfade(daten, BRIEF_ID)["lebenslauf"].is_file()
    tailored = unterlagen.tailored_cv(daten, Register(daten).hole(BRIEF_ID))
    assert [station["name"] for station in tailored["work"]] == ["Muster GmbH", "Beispiel AG"]
    assert tailored["basics"]["summary"] == "Baut Datenpipelines."
    assert "projects" in tailored  # a section the choice does not name stays as it is


def test_every_file_is_saved_with_drafts_before_and_after(server):  # noqa: F811
    daten = server.kontext.daten
    ablage = server.kontext.ablage

    post(server, ROUTE, choice(form(server)))

    assert len(ablage.liste(daten / "jobs" / f"{BRIEF_ID}.yaml")) >= 1
    assert len(ablage.liste(daten / "varianten.yaml")) >= 2
    assert len(ablage.liste(daten / "bewerbungen.yaml")) >= 2


def test_the_new_cv_stands_among_the_variants_of_the_page(server):  # noqa: F811
    post(server, ROUTE, choice(form(server)))

    _, _, body = get(server, "/api/bewerbung", id=BRIEF_ID)

    assert BRIEF_ID in [variant["id"] for variant in json.loads(body)["varianten"]]


def test_opening_again_shows_the_choice_and_saving_again_keeps_one_variant(server):  # noqa: F811
    post(server, ROUTE, choice(form(server)))

    again = form(server)
    work = section(again, "work")
    assert [station["index"] for station in work["stationen"] if station["gewaehlt"]] == [1, 0]
    assert again["kurzprofil"] == "Baut Datenpipelines." and again["design"] == "einspaltig"
    status, _ = post(server, ROUTE, choice(again, stationen={"work": [0], "education": []}))

    assert status == 200
    ids = [variant["id"] for variant in Varianten(server.kontext.daten).alle()]
    assert ids.count(BRIEF_ID) == 1 and "daten" in ids


def test_a_variant_of_the_same_name_from_claude_is_never_overwritten(server):  # noqa: F811
    daten = server.kontext.daten
    Varianten(daten).speichere({"id": BRIEF_ID, "quelle": "jobs/daten.yaml", "beschreibung": "Von Claude"})

    status, answer = post(server, ROUTE, choice(form(server)))

    assert status == 200
    assert answer["variante"]["id"] == f"{BRIEF_ID}-2"
    assert Varianten(daten).hole(BRIEF_ID)["beschreibung"] == "Von Claude"


@pytest.mark.parametrize("changes", [
    {"stationen": {"work": [7]}},
    {"stationen": {"basics": [0]}},
    {"stationen": {"work": ["0"]}},
    {"stationen": {"work": [], "education": []}},
    {"design": "dossier-siegel"},
    {"kurzprofil": 3},
    {"stand": "anders"},
])
def test_a_wrong_choice_is_refused_and_nothing_is_written(server, changes):  # noqa: F811
    daten = server.kontext.daten

    status, answer = post(server, ROUTE, choice(form(server), **changes))

    assert status == 400 and answer["fehler"]
    assert not (daten / "jobs" / f"{BRIEF_ID}.yaml").exists()
    assert [variant["id"] for variant in Varianten(daten).alle()] == ["daten"]


def test_a_sent_application_keeps_its_cv(server):  # noqa: F811
    daten = server.kontext.daten
    answer = form(server)
    register = Register(daten)
    register.speichere({**register.hole(BRIEF_ID), "versand": {"datum": "2026-10-20", "art": "elektronisch"}})

    status, refused = post(server, ROUTE, choice(answer))

    assert status == 400 and refused["fehler"] == unterlagen.SENT_STAYS
    assert not (daten / "jobs" / f"{BRIEF_ID}.yaml").exists()
