"""Whether new documents show the active photo (G62, #281): „Im Lebenslauf zeigen“ on „Lebenslauf und Dateien“.

On by default once a photo exists. Off, every new CV and dossier is built without it (`--ohne-foto` for
lebenslauf/build.py and dossier.py); the photo stays active and `cv.yaml` stays as it is. PDFs built or sent before
keep their photo, as nothing is rebuilt by the switch.
"""
import pathlib

import document_settings

FILE = document_settings.FILE
KEY = "foto_im_lebenslauf"
FIELD = "zeigen"  # what the page sends and reads
DEFAULT = True
BAD_VALUE = "Bitte wählen: Foto im Lebenslauf zeigen oder nicht."
WITHOUT_PHOTO = "--ohne-foto"


def parse(values) -> bool:
    """The choice as the page sends it; ValueError with a German message."""
    shown = values.get(FIELD) if isinstance(values, dict) else None
    if not isinstance(shown, bool):
        raise ValueError(BAD_VALUE)
    return shown


def load(data_dir: pathlib.Path) -> bool:
    """The stored choice; without one, or with a value that is neither on nor off, the photo is shown."""
    stored = document_settings.read(data_dir).get(KEY)
    return stored if isinstance(stored, bool) else DEFAULT


def as_dict(shown: bool) -> dict:
    return {FIELD: shown}


def save(k, values) -> bool:
    shown = parse(values)
    description = "Foto im Lebenslauf zeigen" if shown else "Lebenslauf ohne Foto"
    document_settings.write(k, KEY, shown, description)
    return shown


def build_arguments(data_dir: pathlib.Path) -> list[str]:
    """For lebenslauf/build.py and dossier.py."""
    return [] if load(data_dir) else [WITHOUT_PHOTO]
