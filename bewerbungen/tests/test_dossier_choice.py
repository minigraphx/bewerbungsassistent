"""Dossier or cover letter and CV per application (G40, G41): preset to the two files, stored with the application."""
import io
import json
import pathlib
import subprocess

import pypdf

import unterlagen
from register import Register
from sample_folder import BRIEF_ID
from test_app import get, post, server  # noqa: F401  (server is a fixture)
from varianten import Varianten

TESTS = pathlib.Path(__file__).parent
PDF = b"%PDF-1.4\n" + b"x" * 300


def details(s, entry_id=BRIEF_ID):
    return json.loads(get(s, "/api/bewerbung", id=entry_id)[2])


def choose(s, value, entry_id=BRIEF_ID):
    return post(s, "/api/bewerbung", {"id": entry_id, "unterlagen": value})


def pages(path: pathlib.Path) -> int:
    return len(pypdf.PdfReader(io.BytesIO(path.read_bytes())).pages)


def test_preset_builds_only_the_two_files(server):
    shown = details(server)
    status, answer = post(server, "/api/unterlagen", {}, id=BRIEF_ID)

    assert "unterlagen" not in shown["bewerbung"]
    assert status == 200 and answer["gebaut"] == ["anschreiben", "lebenslauf"]
    assert not unterlagen.dossier_path(server.kontext.daten, BRIEF_ID).exists()
    assert set(details(server)["pdfs"]) == {"lebenslauf", "anschreiben"}


def test_the_choice_is_stored_with_the_application(server):
    status, saved = choose(server, "dossier")

    assert status == 200 and saved["unterlagen"] == "dossier"
    assert Register(server.kontext.daten).hole(BRIEF_ID)["unterlagen"] == "dossier"
    assert choose(server, "einzeln")[1]["unterlagen"] == "einzeln"


def test_an_unknown_choice_is_refused(server):
    status, answer = choose(server, "mappe")

    assert status == 400 and "dossier" in answer["fehler"]
    assert "unterlagen" not in Register(server.kontext.daten).hole(BRIEF_ID)


def test_with_dossier_the_app_builds_the_dossier_and_both_single_files(server):
    choose(server, "dossier")
    status, answer = post(server, "/api/unterlagen", {}, id=BRIEF_ID)
    folder = unterlagen.bewerbungsordner(server.kontext.daten, BRIEF_ID)
    shown = details(server)
    code, kind, body = get(server, "/api/pdf", id=BRIEF_ID, art="dossier")

    assert status == 200 and answer["gebaut"] == ["anschreiben", "dossier", "lebenslauf"]
    assert pages(folder / "dossier.pdf") > pages(folder / "lebenslauf.pdf") + pages(folder / "anschreiben.pdf")
    assert shown["pdfs"] == {"lebenslauf": True, "anschreiben": True, "dossier": True}
    assert isinstance(shown["pdf_stand"]["dossier"], int)
    assert (code, kind, body[:5]) == (200, "application/pdf", b"%PDF-")


def test_back_to_two_files_the_dossier_no_longer_counts(server):
    folder = unterlagen.bewerbungsordner(server.kontext.daten, BRIEF_ID)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "dossier.pdf").write_bytes(PDF)  # left from an earlier choice
    choose(server, "einzeln")

    status, answer = post(server, "/api/unterlagen", {}, id=BRIEF_ID)

    assert answer["gebaut"] == ["anschreiben", "lebenslauf"]
    assert "dossier" not in details(server)["pdfs"]
    assert get(server, "/api/pdf", id=BRIEF_ID, art="dossier")[0] == 400


def test_a_dossier_is_not_built_around_an_own_letter_pdf(server):
    unterlagen.own_letter_path(server.kontext.daten, BRIEF_ID).write_bytes(PDF)
    choose(server, "dossier")

    status, answer = post(server, "/api/unterlagen", {}, id=BRIEF_ID)

    assert status == 400 and "Anschreiben und Lebenslauf" in answer["fehler"]
    assert not unterlagen.dossier_path(server.kontext.daten, BRIEF_ID).exists()


def test_a_dossier_is_not_built_from_a_fixed_cv_pdf(server):
    data = server.kontext.daten
    (data / "fertig.pdf").write_bytes(PDF)
    Varianten(data).speichere({"id": "fertig", "datei": "fertig.pdf", "beschreibung": "Fertiges PDF"})
    post(server, "/api/bewerbung", {"id": BRIEF_ID, "variante": "fertig", "unterlagen": "dossier"})

    status, answer = post(server, "/api/unterlagen", {}, id=BRIEF_ID)

    assert status == 400 and "Anschreiben und Lebenslauf" in answer["fehler"]


def test_the_page_offers_the_choice_preset_to_the_two_files(server):
    status, _, page = get(server, "/bewerbung", id=BRIEF_ID)
    html = page.decode("utf-8")
    script = get(server, "/unterlagen-wahl.js")

    assert status == 200 and script[0] == 200
    assert 'name="unterlagen" value="einzeln" checked' in html
    assert 'name="unterlagen" value="dossier"' in html
    assert html.index("/unterlagen-wahl.js") < html.index("/bewerbung.js")


def test_the_page_logic():
    result = subprocess.run(["node", "--test", "tests/unterlagen_wahl.test.cjs"], cwd=TESTS.parent,
                            capture_output=True, text=True, timeout=120)

    assert result.returncode == 0, result.stdout + result.stderr
