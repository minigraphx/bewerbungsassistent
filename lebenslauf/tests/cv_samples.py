"""Sample CV for the tests; imported by name, not from conftest (#93).

A plain `from conftest import` finds another module's conftest when several modules run in one pytest call.
"""
import copy

import yaml

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
