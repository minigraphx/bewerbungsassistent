"""Greeting and thanks of the dossier (G19) in `bewerbungen/<id>/dossier.yaml`.

The other fields of that file (figures, attachments) stay as they are. An empty text removes its field, so the
dossier leaves the page out (`lebenslauf/dossier_data.dossier_pages`).
"""
import pathlib

import yaml

import unterlagen
from dateien import schreibe_atomar

FIELDS = ("gruss", "dank")
MAX_CHARS = 2000
NOT_TEXT = "Begrüssung und Dank müssen Text sein."
TOO_LONG = f"Begrüssung und Dank haben je höchstens {MAX_CHARS} Zeichen."
UNREADABLE = f"{unterlagen.DOSSIER_PAGES} lässt sich nicht lesen. Bitte unter „Entwürfe“ einen früheren Stand holen."


def path(daten: pathlib.Path, entry_id: str) -> pathlib.Path:
    return unterlagen.bewerbungsordner(daten, entry_id) / unterlagen.DOSSIER_PAGES


def _load(file: pathlib.Path) -> dict:
    if not file.is_file():
        return {}
    try:
        data = yaml.safe_load(file.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ValueError(UNREADABLE) from error
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(UNREADABLE)
    return data


def read(daten: pathlib.Path, entry_id: str) -> dict[str, str]:
    """Both texts, empty where there is none."""
    data = _load(path(daten, entry_id))
    return {key: data[key].strip() if isinstance(data.get(key), str) else "" for key in FIELDS}


def checked(body: object) -> dict[str, str]:
    """The texts of a request, trimmed; a missing field counts as empty."""
    if not isinstance(body, dict) or not all(isinstance(body.get(key, ""), str) for key in FIELDS):
        raise ValueError(NOT_TEXT)
    texts = {key: body.get(key, "").strip() for key in FIELDS}
    if any(len(text) > MAX_CHARS for text in texts.values()):
        raise ValueError(TOO_LONG)
    return texts


def with_texts(data: dict, texts: dict[str, str]) -> dict:
    """A new dossier file with these texts; an empty one drops its field and with it the page."""
    kept = {key: value for key, value in data.items() if key not in FIELDS}
    return {**kept, **{key: text for key, text in texts.items() if text}}


def write(daten: pathlib.Path, entry_id: str, texts: dict[str, str]) -> dict[str, str]:
    """Writes the texts into the dossier file; the caller holds the lock and saves drafts around it."""
    file = path(daten, entry_id)
    data = with_texts(_load(file), texts)
    file.parent.mkdir(parents=True, exist_ok=True)
    schreibe_atomar(file, yaml.safe_dump(data, allow_unicode=True, sort_keys=False).encode("utf-8"))
    return read(daten, entry_id)
