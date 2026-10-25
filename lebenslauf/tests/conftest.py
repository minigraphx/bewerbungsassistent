"""Gemeinsame Hilfen: Lebenslauf bauen und Text pro Seite lesen."""
import copy

import pytest
import yaml
from pypdf import PdfReader

import build

BEISPIEL = build.ROOT / "data" / "beispiel.yaml"
FOTO = build.ROOT / "tests" / "foto.jpg"


def beispiel() -> dict:
    return yaml.safe_load(BEISPIEL.read_text(encoding="utf-8"))


def lang(cv: dict, faktor: int = 8) -> dict:
    """Beispieldaten mit so vielen Stationen, dass die rechte Spalte auf Seite 2 läuft."""
    neu = copy.deepcopy(cv)
    neu["work"] = [
        {**station, "position": f"{station['position']} {i}", "highlights": station["highlights"] * 3}
        for i in range(faktor)
        for station in cv["work"]
    ]
    return neu


@pytest.fixture
def baue(tmp_path):
    """Schreibt Daten nach tmp_path, baut das PDF und liefert den Text je Seite."""

    def _baue(cv: dict, *optionen: str) -> list[str]:
        ordner = tmp_path / "daten"
        ordner.mkdir(exist_ok=True)
        (ordner / "foto.jpg").write_bytes(FOTO.read_bytes())
        daten = ordner / "cv.yaml"
        daten.write_text(yaml.safe_dump(cv, allow_unicode=True), encoding="utf-8")
        out = tmp_path / "cv.pdf"
        build.main([str(daten), "--build-dir", str(tmp_path / "zwischenstand"), "-o", str(out), *optionen])
        return [seite.extract_text() for seite in PdfReader(out).pages]

    return _baue


@pytest.fixture
def mit_foto():
    def _mit_foto(cv: dict, **optionen) -> dict:
        neu = copy.deepcopy(cv)
        neu["basics"]["image"] = "foto.jpg"
        if optionen:
            neu["basics"]["x-image"] = optionen
        return neu

    return _mit_foto

