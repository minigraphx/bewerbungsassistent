"""Approving the letter (MIN-369): it holds for exactly that text, an own PDF needs none, the AI review stays with it."""
import json

import apply
import letter_approval
import unterlagen
from sample_folder import BRIEF_ID
from register import Register
from test_app import get, post, server  # noqa: F401  (server is a fixture)
from test_routes_ai import REVIEW, ki, use  # noqa: F401  (ki is a fixture)
from test_ai_tasks import FakeClient

PDF = b"%PDF-1.4\n%eigenes Anschreiben\n"


def details(s):
    _, _, body = get(s, "/api/bewerbung", id=BRIEF_ID)
    return json.loads(body)


def test_a_draft_needs_an_approval_that_an_edit_makes_void(server):  # noqa: F811
    daten = server.kontext.daten
    assert details(server)["anschreiben_freigabe"] == {"noetig": True, "freigegeben": False, "am": None}
    assert details(server)["anschreiben_text"]["absaetze"]

    status, answer = post(server, "/api/anschreiben/freigeben", {"id": BRIEF_ID})
    assert status == 200 and answer["freigegeben"] is True and answer["am"]

    source = unterlagen.letter_source(daten, BRIEF_ID)
    source.write_text(source.read_text(encoding="utf-8") + "\n# geändert\n", encoding="utf-8")
    assert details(server)["anschreiben_freigabe"]["freigegeben"] is False


def test_an_unapproved_draft_keeps_the_form_closed(server):  # noqa: F811
    daten = server.kontext.daten
    entry = Register(daten).hole(BRIEF_ID)
    entry = {**entry, "status": "Bewerben", "link": "https://www.jobs.ch/de/stellenangebote/detail/1/", "versand": None}
    unterlagen.pdf_pfade(daten, BRIEF_ID)["lebenslauf"].parent.mkdir(parents=True, exist_ok=True)
    unterlagen.pdf_pfade(daten, BRIEF_ID)["lebenslauf"].write_bytes(PDF)
    assert apply.blocker(daten, entry) == apply.NOT_APPROVED

    letter_approval.approve(daten, entry, server.kontext.heute())
    assert apply.blocker(daten, entry) is None


def test_an_own_letter_needs_no_approval_and_cannot_get_one(server):  # noqa: F811
    daten = server.kontext.daten
    unterlagen.own_letter_path(daten, BRIEF_ID).write_bytes(PDF)
    assert details(server)["anschreiben_freigabe"]["noetig"] is False

    status, answer = post(server, "/api/anschreiben/freigeben", {"id": BRIEF_ID})
    assert status == 400 and answer["fehler"] == letter_approval.OWN_LETTER


def test_without_a_letter_there_is_nothing_to_approve(server):  # noqa: F811
    _, entry = post(server, "/api/bewerbung/neu", {"firma": "Ohne AG", "stelle": "Test"})
    status, answer = post(server, "/api/anschreiben/freigeben", {"id": entry["id"]})
    assert status == 400 and answer["fehler"] == letter_approval.NOTHING_TO_APPROVE


def test_the_ai_review_stays_until_the_letter_changes(ki, monkeypatch):  # noqa: F811
    use(monkeypatch, FakeClient(reply=REVIEW))
    status, _ = post(ki, "/api/ki/pruefen", {}, id=BRIEF_ID)
    assert status == 200

    kept = details(ki)["ki_pruefung"]
    assert kept["requirements"] == REVIEW["requirements"] and kept["am"]

    source = unterlagen.letter_source(ki.kontext.daten, BRIEF_ID)
    source.write_text(source.read_text(encoding="utf-8") + "\n# geändert\n", encoding="utf-8")
    assert details(ki)["ki_pruefung"] is None
