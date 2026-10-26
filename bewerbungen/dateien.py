"""Hilfen für Dateien im privaten Datenordner: sicher schreiben, Pfade prüfen, .gitignore ergänzen."""
import os
import pathlib
import tempfile

import yaml


def relativ(pfad: pathlib.Path, ordner: pathlib.Path) -> str:
    """Pfad relativ zum Datenordner; ausserhalb davon ist ein Fehler (kein Zugriff auf fremde Dateien)."""
    try:
        return pfad.resolve().relative_to(ordner.resolve()).as_posix()
    except ValueError:
        raise ValueError(f"{pfad} liegt nicht im Datenordner {ordner}") from None


def im_ordner(ordner: pathlib.Path, rel: str) -> pathlib.Path:
    """Relativen Pfad aus Daten (z.B. Index, Anfrage) auflösen und sicherstellen, dass er im Ordner bleibt."""
    pfad = (ordner / rel).resolve()
    relativ(pfad, ordner)
    return pfad


def schreibe_atomar(pfad: pathlib.Path, inhalt: bytes) -> None:
    """Erst in eine temporäre Datei im selben Ordner schreiben, dann ersetzen: nie eine halbe Datei."""
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=pfad.parent, delete=False, suffix=".tmp") as tmp:
        tmp.write(inhalt)
    os.replace(tmp.name, pfad)


def lies_yaml(pfad: pathlib.Path, standard):
    if not pfad.is_file():
        return standard
    wert = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    return standard if wert is None else wert


def schreibe_yaml(pfad: pathlib.Path, wert, kopf: str = "") -> None:
    text = yaml.safe_dump(wert, allow_unicode=True, sort_keys=False, width=4096)
    schreibe_atomar(pfad, (kopf + text).encode("utf-8"))


def sichere_gitignore(ordner: pathlib.Path, eintraege: list[str]) -> None:
    """Fehlende Einträge an die .gitignore des Datenordners anhängen."""
    pfad = ordner / ".gitignore"
    vorhanden = pfad.read_text(encoding="utf-8").splitlines() if pfad.is_file() else []
    fehlend = [e for e in eintraege if e not in vorhanden]
    if not fehlend:
        return
    text = "\n".join(vorhanden + fehlend) + "\n"
    schreibe_atomar(pfad, text.encode("utf-8"))
