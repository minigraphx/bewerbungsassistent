"""The check names each document's pages and, only where the app changed the setting, how (G93, #324)."""
import json

import pytest
from pypdf import PdfReader

import page_fill
import unterlagen
from sample_folder import BRIEF_ID
from test_app import get, post, server  # noqa: F401  (server is a fixture)


def notes(server) -> dict:
    status, _, body = get(server, "/api/bewerbung", id=BRIEF_ID)
    assert status == 200
    return json.loads(body)["seiten"]


def pages(server, art: str) -> int:
    folder = unterlagen.bewerbungsordner(server.kontext.daten, BRIEF_ID)
    return len(PdfReader(folder / f"{art}.pdf").pages)


@pytest.fixture
def level(monkeypatch):
    def choose(chosen: int):
        monkeypatch.setattr(page_fill, "choose", lambda probe, limit=None, tight_over_limit=False: chosen)
    return choose


def test_before_building_no_document_has_a_note(server):
    assert notes(server) == {}


def test_each_built_document_names_its_pages_and_how_it_was_balanced(server, level):
    level(1)
    post(server, "/api/unterlagen", {}, id=BRIEF_ID)

    assert notes(server) == {
        "lebenslauf": {"seiten": pages(server, "lebenslauf"), "ausgleich": {"cv": "slightly-tighter"}},
        "anschreiben": {"seiten": pages(server, "anschreiben"), "ausgleich": {"letter": "slightly-tighter"}},
    }


def test_a_document_the_app_did_not_change_names_only_its_pages(server, level):
    level(0)
    post(server, "/api/unterlagen", {}, id=BRIEF_ID)

    assert notes(server)["lebenslauf"] == {"seiten": pages(server, "lebenslauf"), "ausgleich": {}}


def test_the_dossier_names_how_each_of_its_parts_was_balanced(server, level):
    level(page_fill.TIGHTER[-1])
    post(server, "/api/bewerbung", {"id": BRIEF_ID, "unterlagen": "dossier"})
    post(server, "/api/unterlagen", {}, id=BRIEF_ID)

    found = notes(server)

    assert found["dossier"] == {"seiten": pages(server, "dossier"), "ausgleich": {"letter": "tightest", "cv": "tightest"}}
    assert found["lebenslauf"]["ausgleich"] == {"cv": "tightest"}


def test_a_widened_document_says_so(server, level):
    level(-2)
    post(server, "/api/unterlagen", {}, id=BRIEF_ID)

    assert notes(server)["anschreiben"]["ausgleich"] == {"letter": "wider"}


def test_once_sent_the_sent_files_keep_their_note(server, level):
    level(3)
    post(server, "/api/unterlagen", {}, id=BRIEF_ID)
    status, answer = post(server, "/api/versand", {"datum": "2026-10-26", "art": "elektronisch"}, id=BRIEF_ID)
    assert status == 200, answer

    assert notes(server)["lebenslauf"] == {"seiten": pages(server, "lebenslauf"), "ausgleich": {"cv": "tighter"}}


def test_an_own_cv_pdf_names_its_pages_but_nothing_about_balancing(server, level):
    level(1)
    own = server.kontext.daten / unterlagen.OWN_CV
    own.parent.mkdir(parents=True, exist_ok=True)
    folder = unterlagen.bewerbungsordner(server.kontext.daten, BRIEF_ID)
    post(server, "/api/unterlagen", {}, id=BRIEF_ID)
    own.write_bytes((folder / "lebenslauf.pdf").read_bytes())  # a PDF the app did not build for this file
    post(server, "/api/bewerbung", {"id": BRIEF_ID, "variante": ""})

    assert notes(server)["lebenslauf"] == {"seiten": pages(server, "lebenslauf"), "ausgleich": {}}


def test_an_unreadable_pdf_has_no_note_instead_of_a_crash(server):
    own = server.kontext.daten / unterlagen.OWN_CV
    own.parent.mkdir(parents=True, exist_ok=True)
    own.write_bytes(b"%PDF-1.4\n" + b"x" * 300)
    post(server, "/api/bewerbung", {"id": BRIEF_ID, "variante": ""})

    assert "lebenslauf" not in notes(server)
