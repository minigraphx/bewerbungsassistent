"""`unterlagen.yaml` of the data folder: how the app builds the person's documents.

It holds the page limit of the CV (G51, page_limit.py) and whether the CV shows the photo (G62, photo_shown.py). Each
writes only its own key and keeps the others; every write has drafts before and after.
"""
import pathlib

import yaml

from dateien import schreibe_atomar

FILE = "unterlagen.yaml"
HEADER = "# Unterlagen: Seiten des Lebenslaufs und Foto. Geschrieben vom Bewerbungsbegleiter.\n"


def read(data_dir: pathlib.Path) -> dict:
    """Everything stored; empty without a file or with a broken one."""
    path = data_dir / FILE
    try:
        stored = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, yaml.YAMLError):
        return {}
    return stored if isinstance(stored, dict) else {}


def write(k, key: str, value: object, description: str) -> None:
    """Store one setting next to the others, with drafts before and after."""
    path = k.daten / FILE

    def store() -> None:
        settings = {**read(k.daten), key: value}
        text = HEADER + yaml.safe_dump(settings, allow_unicode=True, sort_keys=False)
        schreibe_atomar(path, text.encode("utf-8"))

    k.mit_entwurf(path, description, store)
