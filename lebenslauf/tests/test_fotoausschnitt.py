"""Tests für den Fotoausschnitt: Optionen lesen, prüfen, als Vorschau rendern und speichern."""
import io
import shutil

import pytest
from PIL import Image

import build
import fotoausschnitt

HALBE = build.ROOT / "tests" / "halbe.png"

CV = """\
basics:
  name: Erika Muster
  image: foto.png
  # Foto im runden Ausschnitt
  # x-image: {mirror: true}
  email: erika@example.org
work:
  - name: Beispiel AG
    startDate: "2019-03"
    endDate: null
    highlights:
      - Plattform für Kundendaten  # Kommentar am Stichpunkt
"""


@pytest.fixture
def daten(tmp_path):
    ordner = tmp_path / "daten"
    ordner.mkdir()
    shutil.copy(HALBE, ordner / "foto.png")
    pfad = ordner / "cv.yaml"
    pfad.write_text(CV, encoding="utf-8")
    return pfad


def farbe(png: bytes, x: float, y: float) -> str:
    bild = Image.open(io.BytesIO(png)).convert("RGB")
    r, g, b = bild.getpixel((int(x * bild.width), int(y * bild.height)))
    if r > 200 and g < 60 and b < 60:
        return "rot"
    if b > 200 and r < 60 and g < 60:
        return "blau"
    return f"({r},{g},{b})"


# Lesen


def test_lies_foto_ohne_optionen(daten):
    foto, optionen = fotoausschnitt.lies_foto(daten)

    assert foto == daten.parent / "foto.png"
    assert optionen == fotoausschnitt.STANDARD


def test_lies_foto_ergaenzt_fehlende_optionen(daten):
    daten.write_text(CV.replace("  email:", "  x-image: {zoom: 2}\n  email:"), encoding="utf-8")

    _, optionen = fotoausschnitt.lies_foto(daten)

    assert optionen == {**fotoausschnitt.STANDARD, "zoom": 2}


def test_lies_foto_ohne_bild(daten):
    daten.write_text("basics:\n  name: Erika\n", encoding="utf-8")

    with pytest.raises(ValueError, match="basics.image"):
        fotoausschnitt.lies_foto(daten)


def test_lies_foto_bild_fehlt(daten):
    (daten.parent / "foto.png").unlink()

    with pytest.raises(ValueError, match="nicht gefunden"):
        fotoausschnitt.lies_foto(daten)


# Anfrage prüfen


def test_optionen_aus_anfrage():
    werte = {"mirror": "true", "zoom": "1.5", "x": "0", "y": "0.25"}

    assert fotoausschnitt.optionen_aus_anfrage(werte) == {"mirror": True, "zoom": 1.5, "x": 0.0, "y": 0.25}


@pytest.mark.parametrize(
    "werte, meldung",
    [
        ({"mirror": "vielleicht", "zoom": "1", "x": "0.5", "y": "0.5"}, "mirror"),
        ({"mirror": "false", "zoom": "abc", "x": "0.5", "y": "0.5"}, "zoom"),
        ({"mirror": "false", "zoom": "9", "x": "0.5", "y": "0.5"}, "zoom"),
        ({"mirror": "false", "zoom": "1", "x": "nan", "y": "0.5"}, "x"),
        ({"mirror": "false", "zoom": "1", "x": "0.5"}, "y"),
    ],
)
def test_optionen_aus_anfrage_ungueltig(werte, meldung):
    with pytest.raises(ValueError, match=meldung):
        fotoausschnitt.optionen_aus_anfrage(werte)


# Vorschau


def test_vorschau_rendert_png(daten, tmp_path):
    vorschau = fotoausschnitt.Vorschau(daten.parent / "foto.png", tmp_path / "build")

    png = vorschau.png(fotoausschnitt.STANDARD)

    assert png.startswith(b"\x89PNG")
    assert farbe(png, 0.25, 0.5) == "rot"
    assert farbe(png, 0.75, 0.5) == "blau"


def test_vorschau_uebernimmt_aenderungen(daten, tmp_path):
    vorschau = fotoausschnitt.Vorschau(daten.parent / "foto.png", tmp_path / "build")

    normal = vorschau.png(fotoausschnitt.STANDARD)
    gespiegelt = vorschau.png({**fotoausschnitt.STANDARD, "mirror": True})
    links = vorschau.png({**fotoausschnitt.STANDARD, "zoom": 2, "x": 0})

    assert farbe(normal, 0.25, 0.5) == "rot"
    assert farbe(gespiegelt, 0.25, 0.5) == "blau"
    assert farbe(links, 0.75, 0.5) == "rot"


def test_vorschau_prueft_optionen(daten, tmp_path):
    vorschau = fotoausschnitt.Vorschau(daten.parent / "foto.png", tmp_path / "build")

    with pytest.raises(ValueError, match="zoom"):
        vorschau.png({**fotoausschnitt.STANDARD, "zoom": 7})


# Speichern


def test_speichern_setzt_x_image_und_behaelt_den_rest(daten, tmp_path):
    optionen = {"mirror": True, "zoom": 1.3, "x": 0.5, "y": 0.2}

    fotoausschnitt.speichere_optionen(daten, optionen)

    neu = daten.read_text(encoding="utf-8")
    zeilen_neu = [z for z in neu.splitlines() if "x-image: {mirror: true, zoom: 1.3" not in z]
    assert zeilen_neu == CV.splitlines()
    assert "  x-image: {mirror: true, zoom: 1.3, x: 0.5, y: 0.2}" in neu.splitlines()
    assert fotoausschnitt.lies_foto(daten)[1] == optionen


def test_speichern_ersetzt_vorhandene_optionen(daten, tmp_path):
    fotoausschnitt.speichere_optionen(daten, {**fotoausschnitt.STANDARD, "zoom": 2})
    fotoausschnitt.speichere_optionen(daten, {**fotoausschnitt.STANDARD, "zoom": 3})

    zeilen = daten.read_text(encoding="utf-8").splitlines()
    assert sum(z.startswith("  x-image:") for z in zeilen) == 1
    assert fotoausschnitt.lies_foto(daten)[1]["zoom"] == 3


def test_speichern_rundet(daten, tmp_path):
    fotoausschnitt.speichere_optionen(daten, {**fotoausschnitt.STANDARD, "x": 0.123456789})

    assert fotoausschnitt.lies_foto(daten)[1]["x"] == 0.123


def test_speichern_legt_keine_sicherungsdateien_an(daten):
    """Sicherungen übernimmt die Ablage der Entwürfe (bewerbungen/ablage.py, MIN-303)."""
    fotoausschnitt.speichere_optionen(daten, fotoausschnitt.STANDARD)

    assert sorted(p.name for p in daten.parent.iterdir()) == ["cv.yaml", "foto.png"]


def test_speichern_ungueltig_laesst_datei_unveraendert(daten, tmp_path):
    with pytest.raises(ValueError, match="zoom"):
        fotoausschnitt.speichere_optionen(daten, {**fotoausschnitt.STANDARD, "zoom": 0})

    assert daten.read_text(encoding="utf-8") == CV
