"""What one application leaves out of its CV, and whether it may have three pages (G92, #323).

Stored in `bewerbungen/<id>/kuerzungen.yaml`: `stichpunkte` and `abschnitte` as lebenslauf/cuts.py writes them, and
`drei_seiten`. Every build of the CV and the dossier of that application takes the file over the chosen variant or the
base CV (unterlagen.py); Meine Angaben and the variants stay as they are. What the person chooses and takes back is
cut_choice.py; this module only reads and places the file, so unterlagen.py can use it.
"""
import pathlib

import yaml

import page_limit
from register import ID_MUSTER

FILE = "kuerzungen.yaml"
FOLDER = "bewerbungen"
THREE_PAGES = "drei_seiten"


def path(daten: pathlib.Path, entry_id: str) -> pathlib.Path:
    if not ID_MUSTER.fullmatch(entry_id or ""):
        raise ValueError(f"Ungültige Bewerbungs-id: {entry_id!r}")
    return daten.resolve() / FOLDER / entry_id / FILE


def load(daten: pathlib.Path, entry_id: str) -> dict:
    """The stored choice; empty without a file or with a broken one."""
    file = path(daten, entry_id)
    try:
        stored = yaml.safe_load(file.read_text(encoding="utf-8")) if file.is_file() else {}
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return {}
    return stored if isinstance(stored, dict) else {}


def three_pages(daten: pathlib.Path, entry_id: str) -> bool:
    return load(daten, entry_id).get(THREE_PAGES) is True


def pages(daten: pathlib.Path, entry_id: str) -> int:
    """The pages the CV of this application may have: three where it allows them, else the setting for all (G51)."""
    return page_limit.MOST if three_pages(daten, entry_id) else page_limit.load(daten)


def build_arguments(daten: pathlib.Path, entry_id: str) -> list[str]:
    """The file for `--kuerzungen` of build.py and dossier.py, when there is one."""
    file = path(daten, entry_id)
    return ["--kuerzungen", str(file)] if file.is_file() else []
