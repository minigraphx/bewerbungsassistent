"""Tests für die automatische Prüfung vor dem Absenden (MIN-262)."""
import datetime

import pytest
import yaml

import pruefung
import unterlagen
from conftest import BRIEF_ID
from register import Register

HEUTE = datetime.date(2026, 10, 25)
BEWERBUNG = {"id": "x", "firma": "Beispiel AG", "stelle": "Data Engineer", "status": "Gemerkt"}
BRIEF = """Erika Muster
Beispiel AG
Bern, 24. Oktober 2026
Bewerbung als Data Engineer
Sehr geehrte Frau Meier
Aufgrund Ihrer Stellenausschreibung erhalten Sie hiermit meine Bewerbung.
Freundliche Grüsse"""


def stufen(befunde):
    return {b.stufe for b in befunde}


def texte(befunde):
    return " | ".join(b.text for b in befunde)


@pytest.mark.parametrize(
    "aenderung, stufe, stichwort",
    [
        (("Beispiel AG", "Andere GmbH"), "fehler", "Firma"),
        (("Data Engineer", "Tester"), "hinweis", "Stelle"),
        (("24. Oktober 2026", "24. August 2026"), "hinweis", "Datum"),
        (("24. Oktober 2026", "24. November 2026"), "hinweis", "Datum"),
        (("Freundliche Grüsse", "TODO Gruss"), "fehler", "Platzhalter"),
        (("Sehr geehrte Frau Meier", "Liebes Beispiel-Team"), "hinweis", "Du"),
    ],
)
def test_anschreiben_inhalt(aenderung, stufe, stichwort):
    alt, neu = aenderung

    befunde = pruefung.pruefe_anschreiben_text(BRIEF.replace(alt, neu), BEWERBUNG, HEUTE)

    assert any(b.stufe == stufe and stichwort in b.text for b in befunde), texte(befunde)


def test_anschreiben_alles_gut():
    befunde = pruefung.pruefe_anschreiben_text(BRIEF, BEWERBUNG, HEUTE)

    assert stufen(befunde) == {"ok"}, texte(befunde)


def test_firma_ohne_rechtsform_genuegt():
    befunde = pruefung.pruefe_anschreiben_text(BRIEF.replace("Beispiel AG", "Beispiel"), BEWERBUNG, HEUTE)

    assert "fehler" not in stufen(befunde), texte(befunde)


def test_pdf_fehlt(tmp_path):
    befunde = pruefung.pruefe_pdf(tmp_path / "fehlt.pdf", "lebenslauf")

    assert stufen(befunde) == {"fehler"}


def test_pdf_ohne_text(tmp_path):
    pdf = tmp_path / "bild.pdf"
    pdf.write_bytes(b"%PDF-1.4 kaputt")

    befunde = pruefung.pruefe_pdf(pdf, "lebenslauf")

    assert "fehler" in stufen(befunde)


def test_ganze_bewerbung(datenordner, tmp_path):
    b = Register(datenordner).hole(BRIEF_ID)
    unterlagen.baue(datenordner, b, tmp_path / "build")

    befunde = pruefung.pruefe(datenordner, b, HEUTE)

    assert "fehler" not in stufen(befunde), texte(befunde)
    assert any("Lebenslauf" in x.text for x in befunde)
    assert any("Anschreiben" in x.text for x in befunde)


def test_anschreiben_zu_lang(datenordner, tmp_path):
    brief = datenordner / "bewerbungen" / BRIEF_ID / "anschreiben.yaml"
    daten = yaml.safe_load(brief.read_text(encoding="utf-8"))
    daten["text"] = "Viel zu langer Absatz mit vielen Wörtern und Sätzen.\n\n" * 60
    brief.write_text(yaml.safe_dump(daten, allow_unicode=True), encoding="utf-8")
    b = Register(datenordner).hole(BRIEF_ID)
    unterlagen.baue(datenordner, b, tmp_path / "build")

    befunde = pruefung.pruefe(datenordner, b, HEUTE)

    assert any(x.stufe == "fehler" and "Seite" in x.text for x in befunde), texte(befunde)


def test_ohne_unterlagen(datenordner):
    befunde = pruefung.pruefe(datenordner, Register(datenordner).hole(BRIEF_ID), HEUTE)

    assert any(x.stufe == "fehler" and "Lebenslauf" in x.text for x in befunde)


@pytest.mark.parametrize("firma, im_brief", [
    ("C5I (RUAG)", "RUAG AG"),
    ("C5I (RUAG)", "C5I-Campus"),
    ("unbekannt (über ONE Agency)", "ONE Agency GmbH"),
])
def test_firma_mit_zweitem_namen_in_klammern(firma, im_brief):
    befunde = pruefung.pruefe_anschreiben_text(BRIEF.replace("Beispiel AG", im_brief), {**BEWERBUNG, "firma": firma}, HEUTE)

    assert "fehler" not in stufen(befunde), texte(befunde)


def test_unbekannt_allein_genuegt_nicht():
    brief = BRIEF.replace("Beispiel AG", "unbekannt")

    befunde = pruefung.pruefe_anschreiben_text(brief, {**BEWERBUNG, "firma": "unbekannt (über ONE Agency)"}, HEUTE)

    assert "fehler" in stufen(befunde)
