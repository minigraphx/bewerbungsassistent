"""Fixture for the language check (#414): every message for the person is in the fixture catalog. Never imported."""

LOCKED = "Die Datei ist gesperrt."


def check(value: str) -> None:
    if not value:
        raise ValueError(T("Bitte einen Wert angeben."))  # noqa: F821  (T arrives with #415)
    if value == "gesperrt":
        raise ValueError(LOCKED)
    raise KeyError(f"Interner Schlüssel {value}")  # kein UI-Text
