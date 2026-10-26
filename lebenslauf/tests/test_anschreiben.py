"""Tests für den Anschreiben-Generator: Daten prüfen, Absender aus dem Lebenslauf, PDF im Theme-Design."""
import datetime

import pytest
import yaml
from pypdf import PdfReader

import anschreiben
import build

BEISPIEL = build.ROOT / "data" / "anschreiben-beispiel.yaml"
CV = build.ROOT / "data" / "beispiel.yaml"


def brief(**ueberschreiben) -> dict:
    daten = yaml.safe_load(BEISPIEL.read_text(encoding="utf-8"))
    return {**daten, "lebenslauf": str(CV), **ueberschreiben}


def cv() -> dict:
    return yaml.safe_load(CV.read_text(encoding="utf-8"))


@pytest.fixture
def baue(tmp_path):
    """Schreibt die Briefdaten nach tmp_path, baut das PDF und liefert den Text je Seite."""

    def _baue(daten: dict, *optionen: str) -> list[str]:
        pfad = tmp_path / "brief.yaml"
        pfad.write_text(yaml.safe_dump(daten, allow_unicode=True), encoding="utf-8")
        out = tmp_path / "brief.pdf"
        anschreiben.main([str(pfad), "--build-dir", str(tmp_path / "zwischenstand"), "-o", str(out), *optionen])
        return [seite.extract_text() for seite in PdfReader(out).pages]

    return _baue


# Datum


@pytest.mark.parametrize(
    "sprache, erwartet",
    [("de", "24. Oktober 2026"), ("en", "24 October 2026")],
)
def test_datum(sprache, erwartet):
    assert anschreiben.formatiere_datum(datetime.date(2026, 10, 24), sprache) == erwartet


def test_datum_aus_text():
    assert anschreiben.formatiere_datum("2026-03-01", "de") == "1. März 2026"


# Absender


def test_absender_aus_lebenslauf():
    cv = yaml.safe_load(CV.read_text(encoding="utf-8"))

    absender = anschreiben.absender_aus_cv(cv)

    assert absender["name"] == "Erika Beispiel"
    assert absender["zeile"] == "Musterweg 1, 3000 Bern · 079 000 00 00 · erika@example.ch"


def test_absender_aus_brief_hat_vorrang():
    cv = yaml.safe_load(CV.read_text(encoding="utf-8"))
    daten = anschreiben.bereite_vor(
        brief(absender={"name": "E. Muster", "zeile": "Postfach"}), cv, datetime.date(2026, 10, 24)
    )

    assert daten["absender"] == {"name": "E. Muster", "zeile": "Postfach"}


# Prüfen


@pytest.mark.parametrize("feld", ["empfaenger", "betreff", "anrede", "text", "gruss"])
def test_pflichtfelder(feld):
    daten = {k: v for k, v in brief().items() if k != feld}

    with pytest.raises(ValueError, match=feld):
        anschreiben.pruefe_brief(daten)


def test_empfaenger_muss_liste_sein():
    with pytest.raises(ValueError, match="empfaenger"):
        anschreiben.pruefe_brief(brief(empfaenger="Beispiel AG"))


def test_unbekannte_sprache():
    with pytest.raises(ValueError, match="sprache"):
        anschreiben.pruefe_brief(brief(sprache="fr"))


def test_ohne_absender_und_ohne_lebenslauf():
    daten = {k: v for k, v in brief().items() if k not in ("absender", "lebenslauf")}

    with pytest.raises(ValueError, match="absender"):
        anschreiben.bereite_vor(daten, None, datetime.date(2026, 10, 24))


# Vorbereiten


def test_absaetze_aus_leerzeilen():
    daten = anschreiben.bereite_vor(brief(text="Erster\nAbsatz.\n\nZweiter Absatz.\n"), cv(), datetime.date(2026, 10, 24))

    assert daten["absaetze"] == ["Erster Absatz.", "Zweiter Absatz."]


def test_ort_und_datum():
    daten = anschreiben.bereite_vor(brief(), cv(), datetime.date(2026, 10, 24))

    assert daten["ort_datum"] == "Bern, 24. Oktober 2026"


def test_datum_aus_daten_hat_vorrang():
    daten = anschreiben.bereite_vor(brief(datum="2026-09-28"), cv(), datetime.date(2026, 10, 24))

    assert daten["ort_datum"] == "Bern, 28. September 2026"


# PDF


@pytest.mark.parametrize("theme", ["zweispaltig", "einspaltig"])
def test_pdf_eine_seite_mit_allen_teilen(baue, theme):
    seiten = baue(brief(datum="2026-10-24"), "--theme", theme)

    text = seiten[0]
    assert len(seiten) == 1
    assert "Erika Beispiel" in text
    assert "Beispiel AG" in text
    assert "Bern, 24. Oktober 2026" in text
    assert "Bewerbung als Data Engineer" in text
    assert "Sehr geehrte Frau Meier" in text
    assert "Freundliche Grüsse" in text


def test_pdf_englisch(baue):
    seiten = baue(brief(datum="2026-10-24", sprache="en", gruss="Kind regards"))

    assert "Bern, 24 October 2026" in seiten[0]


def test_text_wird_nicht_als_markup_ausgewertet(baue):
    seiten = baue(brief(text="Preis #1 und *nicht fett* und $x$ und <b>.\n"))

    assert "Preis #1 und *nicht fett* und $x$ und <b>." in seiten[0]
