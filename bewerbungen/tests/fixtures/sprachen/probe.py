"""Fixture for the language check (#414): every message for the person is in the fixture catalog. Never imported."""
from ui_texts import T

LOCKED = "Die Datei ist gesperrt."


def check(value: str) -> None:
    if not value:
        raise ValueError(T("Bitte einen Wert angeben."))
    if value == "gesperrt":
        raise ValueError(LOCKED)
    raise KeyError(f"Interner Schlüssel {value}")  # kein UI-Text
