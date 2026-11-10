"""Greeting and thanks of the dossier (G19): drafted by the AI with placeholders, adjusted by the person, saved with
drafts in bewerbungen/<id>/dossier.yaml; without text the page is left out of the dossier."""
import io
import json
import shutil

import pypdf
import pytest
import yaml

import routes_ai
import unterlagen
from ai import errors, tasks
from ai.connection import ACCESS_VARIABLE, KEY_VARIABLE, URL_VARIABLE
from register import Register
from sample_folder import BRIEF_ID
from test_ai_tasks import VORLAGEN, FakeClient, gateway_for, sent_text
from test_app import get, post, server  # noqa: F401  (server is a fixture)

AD = "Data Engineer bei der Beispiel AG. Python, Airflow, SQL. Kontakt: Petra Meier, petra.meier@beispiel.ch"
TEXTS = {"greeting": "Guten Tag. Ich bin {{NAME}} und baue seit zehn Jahren Datenpipelines.",
         "thanks": "Danke für Ihre Zeit, {{NAME}}.", "suspicious_lines": []}
PERSONAL = ("Erika", "erika@example.ch", "079 000 00 00", "Musterweg", "Petra", "petra.meier@beispiel.ch")


@pytest.fixture
def dossier(server, monkeypatch):  # noqa: F811
    data = server.kontext.daten
    shutil.copy(VORLAGEN / "suchprofil.md", data / "suchprofil.md")
    shutil.copytree(VORLAGEN / "anschreiben", data / "anschreiben", dirs_exist_ok=True)
    (data / "bewerbungen" / BRIEF_ID / "stelle.md").write_text(AD, encoding="utf-8")
    register = Register(data)
    register.speichere({**register.hole(BRIEF_ID), "kontaktperson": "Frau Petra Meier",
                        "kontakt": "petra.meier@beispiel.ch"})
    for name in (URL_VARIABLE, ACCESS_VARIABLE):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(KEY_VARIABLE, "sk-test")
    post(server, "/api/bewerbung", {"id": BRIEF_ID, "unterlagen": "dossier"})
    return server


def pages_file(s):
    return unterlagen.bewerbungsordner(s.kontext.daten, BRIEF_ID) / unterlagen.DOSSIER_PAGES


def stored(s) -> dict:
    return yaml.safe_load(pages_file(s).read_text(encoding="utf-8"))


def built_dossier(s) -> pypdf.PdfReader:
    status, answer = post(s, "/api/unterlagen", {}, id=BRIEF_ID)
    assert status == 200, answer
    return pypdf.PdfReader(io.BytesIO(unterlagen.dossier_path(s.kontext.daten, BRIEF_ID).read_bytes()))


def text_of(reader: pypdf.PdfReader) -> str:
    return " ".join(" ".join((page.extract_text() or "").split()) for page in reader.pages)


def test_the_ai_draft_sends_no_personal_data_and_is_saved_with_drafts(dossier, monkeypatch):
    client = FakeClient(reply=TEXTS)
    monkeypatch.setattr(routes_ai, "new_client", lambda: client)

    status, answer = post(dossier, "/api/ki/dossier-texte", {}, id=BRIEF_ID)

    sent = sent_text(client)
    assert status == 200, answer
    assert [value for value in PERSONAL if value in sent] == []
    assert "{{NAME}}" in sent
    assert answer["gruss"] == "Guten Tag. Ich bin Erika Beispiel und baue seit zehn Jahren Datenpipelines."
    assert stored(dossier) == {"gruss": answer["gruss"], "dank": "Danke für Ihre Zeit, Erika Beispiel."}
    assert len(dossier.kontext.ablage.liste(pages_file(dossier))) == 1


def test_the_draft_keeps_the_other_fields_of_the_dossier_file(dossier, monkeypatch):
    pages_file(dossier).write_text("kennzahlen:\n  - wert: 10\n    text: Jahre Praxis\ngruss: Alt\n", encoding="utf-8")
    monkeypatch.setattr(routes_ai, "new_client", lambda: FakeClient(reply=TEXTS))

    post(dossier, "/api/ki/dossier-texte", {}, id=BRIEF_ID)

    assert stored(dossier)["kennzahlen"] == [{"wert": 10, "text": "Jahre Praxis"}]
    assert stored(dossier)["gruss"].startswith("Guten Tag.")
    assert len(dossier.kontext.ablage.liste(pages_file(dossier))) == 2


def test_a_bad_answer_of_the_ai_writes_nothing(dossier, monkeypatch):
    monkeypatch.setattr(routes_ai, "new_client", lambda: FakeClient(reply={"greeting": 3}))

    status, answer = post(dossier, "/api/ki/dossier-texte", {}, id=BRIEF_ID)

    assert status == 400 and answer["fehler"] == errors.BAD_ANSWER
    assert not pages_file(dossier).exists()


def test_the_person_adjusts_the_texts_and_they_appear_in_the_dossier(dossier):
    texts = {"gruss": "Guten Tag. Ich freue mich auf Ihre Lektüre.", "dank": "Herzlichen Dank fürs Lesen."}

    status, saved = post(dossier, "/api/dossier/texte", texts, id=BRIEF_ID)
    shown = json.loads(get(dossier, "/api/dossier/texte", id=BRIEF_ID)[2])

    assert status == 200 and saved == shown == texts
    assert len(dossier.kontext.ablage.liste(pages_file(dossier))) == 1
    text = text_of(built_dossier(dossier))
    assert "Ich freue mich auf Ihre Lektüre." in text and "Herzlichen Dank fürs Lesen." in text


def test_an_empty_text_leaves_its_page_out(dossier):
    post(dossier, "/api/dossier/texte", {"gruss": "Guten Tag. Ich freue mich.", "dank": "Danke fürs Lesen."},
         id=BRIEF_ID)
    with_both = len(built_dossier(dossier).pages)

    status, saved = post(dossier, "/api/dossier/texte", {"gruss": "  ", "dank": "Danke fürs Lesen."}, id=BRIEF_ID)
    reader = built_dossier(dossier)

    assert status == 200 and saved == {"gruss": "", "dank": "Danke fürs Lesen."}
    assert "gruss" not in stored(dossier)
    assert len(reader.pages) == with_both - 1
    assert "Kurz vorgestellt" not in text_of(reader)


def test_without_any_text_the_dossier_has_neither_page(dossier):
    post(dossier, "/api/dossier/texte", {"gruss": "Guten Tag.", "dank": "Danke."}, id=BRIEF_ID)
    with_both = len(built_dossier(dossier).pages)

    post(dossier, "/api/dossier/texte", {"gruss": "", "dank": ""}, id=BRIEF_ID)

    assert stored(dossier) == {}
    assert len(built_dossier(dossier).pages) == with_both - 2


def test_without_a_file_the_texts_are_empty(dossier):
    status, _, body = get(dossier, "/api/dossier/texte", id=BRIEF_ID)

    assert status == 200 and json.loads(body) == {"gruss": "", "dank": ""}


@pytest.mark.parametrize("body", [{"gruss": 3, "dank": ""}, {"gruss": "x" * 2001, "dank": ""}, ["gruss"]])
def test_texts_that_are_no_text_or_too_long_are_refused(dossier, body):
    status, answer = post(dossier, "/api/dossier/texte", body, id=BRIEF_ID)

    assert status == 400 and answer["fehler"]
    assert not pages_file(dossier).exists()


def test_after_sending_the_texts_stay(dossier, monkeypatch):
    register = Register(dossier.kontext.daten)
    register.speichere({**register.hole(BRIEF_ID), "versand": {"datum": "2026-11-01"}})
    monkeypatch.setattr(routes_ai, "new_client", lambda: FakeClient(reply=TEXTS))

    saved = post(dossier, "/api/dossier/texte", {"gruss": "Neu", "dank": ""}, id=BRIEF_ID)
    drafted = post(dossier, "/api/ki/dossier-texte", {}, id=BRIEF_ID)

    assert saved[0] == drafted[0] == 400 and saved[1]["fehler"] == unterlagen.SENT_STAYS
    assert not pages_file(dossier).exists()


def test_the_task_restores_the_placeholders_and_checks_the_answer(datenordner):
    shutil.copy(VORLAGEN / "suchprofil.md", datenordner / "suchprofil.md")
    shutil.copytree(VORLAGEN / "anschreiben", datenordner / "anschreiben", dirs_exist_ok=True)
    client = FakeClient(reply=TEXTS)
    gateway, material = gateway_for(datenordner, client)

    result = tasks.draft_dossier_texts(gateway, material, {"firma": "Beispiel AG", "stelle": "Data Engineer"},
                                       AD, "Sehr geehrte Damen und Herren", "de")

    assert result["greeting"].startswith("Guten Tag. Ich bin Erika Beispiel")
    assert "Erika" not in sent_text(client)
    with pytest.raises(errors.AiError):
        tasks.draft_dossier_texts(gateway_for(datenordner, FakeClient(reply={"greeting": "x"}))[0], material,
                                  {"firma": "Beispiel AG"}, AD, "", "de")


def test_the_page_offers_the_texts_only_with_a_dossier(dossier):
    html = get(dossier, "/bewerbung", id=BRIEF_ID)[2].decode("utf-8")
    script = get(dossier, "/dossier-texte.js")

    assert 'id="dossier-texte" hidden' in html and 'src="/dossier-texte.js"' in html
    assert script[0] == 200 and b"/api/dossier/texte" in script[2] and b"/api/ki/dossier-texte" in script[2]
