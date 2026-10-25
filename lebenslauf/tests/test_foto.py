"""Bildtests für das runde Foto: Typst rendert als PNG, geprüft werden einzelne Pixel.

Testbild `halbe.png`: 300×400, linke Hälfte rot, rechte Hälfte blau.
"""
import io

import pytest
import typst
from PIL import Image

import build

GROESSE = 200  # Pixel bei 72 ppi


def rendere(optionen: str) -> Image.Image:
    quelle = (
        '#import "/themes/common.typ": foto-rund\n'
        f"#set page(width: {GROESSE}pt, height: {GROESSE}pt, margin: 0pt, fill: white)\n"
        f'#foto-rund("/tests/halbe.png", {GROESSE}pt, {optionen})\n'
    )
    datei = build.ROOT / "build" / "foto-test.typ"
    datei.parent.mkdir(exist_ok=True)
    datei.write_text(quelle, encoding="utf-8")
    png = typst.compile(str(datei), root=str(build.ROOT), format="png", ppi=72)
    return Image.open(io.BytesIO(png)).convert("RGB")


def farbe(bild: Image.Image, x: float, y: float) -> str:
    r, g, b = bild.getpixel((int(x * GROESSE), int(y * GROESSE)))
    if r > 200 and g < 60 and b < 60:
        return "rot"
    if b > 200 and r < 60 and g < 60:
        return "blau"
    if min(r, g, b) > 230:
        return "weiss"
    return f"({r},{g},{b})"


def test_ohne_optionen_links_rot_rechts_blau():
    bild = rendere("none")

    assert farbe(bild, 0.25, 0.5) == "rot"
    assert farbe(bild, 0.75, 0.5) == "blau"


def test_kreis_ist_bis_unten_gefuellt():
    bild = rendere("none")

    assert farbe(bild, 0.5, 0.95) != "weiss"
    assert farbe(bild, 0.02, 0.02) == "weiss"  # ausserhalb des Kreises


def test_spiegeln():
    bild = rendere("(mirror: true)")

    assert farbe(bild, 0.25, 0.5) == "blau"
    assert farbe(bild, 0.75, 0.5) == "rot"
    assert farbe(bild, 0.5, 0.95) != "weiss"


@pytest.mark.parametrize("x, erwartet", [(0, "rot"), (1, "blau")])
def test_ausschnitt_mit_zoom(x, erwartet):
    bild = rendere(f"(zoom: 2, x: {x})")

    assert farbe(bild, 0.25, 0.5) == erwartet
    assert farbe(bild, 0.75, 0.5) == erwartet
