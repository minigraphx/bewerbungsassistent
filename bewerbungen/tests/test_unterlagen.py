"""Tests: Lebenslauf und Anschreiben einer Bewerbung bauen."""
import pytest
from pypdf import PdfReader

import unterlagen
from conftest import BRIEF_ID
from register import Register
from varianten import Varianten


def test_pfade(datenordner):
    pfade = unterlagen.pdf_pfade(datenordner, BRIEF_ID)

    assert pfade["lebenslauf"] == datenordner / "bewerbungen" / BRIEF_ID / "lebenslauf.pdf"
    assert pfade["anschreiben"] == datenordner / "bewerbungen" / BRIEF_ID / "anschreiben.pdf"


def test_ungueltige_id(datenordner):
    with pytest.raises(ValueError, match="id"):
        unterlagen.pdf_pfade(datenordner, "../cv")


def test_baue_beide(datenordner, tmp_path):
    gebaut = unterlagen.baue(datenordner, Register(datenordner).hole(BRIEF_ID), tmp_path / "build")

    assert set(gebaut) == {"lebenslauf", "anschreiben"}
    assert "Erika Beispiel" in PdfReader(gebaut["lebenslauf"]).pages[0].extract_text()
    assert "Sehr geehrte Frau Meier" in PdfReader(gebaut["anschreiben"]).pages[0].extract_text()


def test_ohne_variante(datenordner, tmp_path):
    b = {**Register(datenordner).hole(BRIEF_ID)}
    del b["variante"]

    with pytest.raises(ValueError, match="Variante"):
        unterlagen.baue(datenordner, b, tmp_path / "build")


def test_externe_variante_braucht_pdf(datenordner, tmp_path):
    Varianten(datenordner).speichere({"id": "canva", "extern": "Google Drive: Fullstack.pdf"})
    b = {**Register(datenordner).hole(BRIEF_ID), "variante": "canva"}

    with pytest.raises(ValueError, match="lebenslauf.pdf"):
        unterlagen.baue(datenordner, b, tmp_path / "build")


def test_externe_variante_mit_abgelegtem_pdf(datenordner, tmp_path):
    Varianten(datenordner).speichere({"id": "canva", "extern": "Google Drive: Fullstack.pdf"})
    b = {**Register(datenordner).hole(BRIEF_ID), "variante": "canva"}
    ziel = unterlagen.pdf_pfade(datenordner, BRIEF_ID)["lebenslauf"]
    ziel.write_bytes(b"%PDF-1.4 von Hand")

    gebaut = unterlagen.baue(datenordner, b, tmp_path / "build")

    assert gebaut["lebenslauf"].read_bytes() == b"%PDF-1.4 von Hand"


def test_variante_als_fertiges_pdf(datenordner, tmp_path):
    (datenordner / "fertig.pdf").write_bytes(b"%PDF-1.4 fertig")
    Varianten(datenordner).speichere({"id": "fertig", "datei": "fertig.pdf"})
    b = {**Register(datenordner).hole(BRIEF_ID), "variante": "fertig"}

    gebaut = unterlagen.baue(datenordner, b, tmp_path / "build")

    assert gebaut["lebenslauf"].read_bytes() == b"%PDF-1.4 fertig"


def test_ohne_anschreiben(datenordner, tmp_path):
    (datenordner / "bewerbungen" / BRIEF_ID / "anschreiben.yaml").unlink()

    gebaut = unterlagen.baue(datenordner, Register(datenordner).hole(BRIEF_ID), tmp_path / "build")

    assert set(gebaut) == {"lebenslauf"}


def test_englische_variante_wird_englisch_gebaut(datenordner, tmp_path):
    Varianten(datenordner).speichere({"id": "englisch", "quelle": "jobs/daten.yaml", "sprache": "en"})
    b = {**Register(datenordner).hole(BRIEF_ID), "variante": "englisch"}

    gebaut = unterlagen.baue(datenordner, b, tmp_path / "build")

    assert "EXPERIENCE" in PdfReader(gebaut["lebenslauf"]).pages[0].extract_text()
