"""How many pages the CV may have (G51): two, or three where the person allows it under Einstellungen > Erweitert.

Stored in the data folder (`unterlagen.yaml`), so it moves with the person's files; written with drafts before and
after. Every build of the CV takes it (unterlagen.py), and the check before sending measures against it
(pruefung.py). The cover letter always has one page.
"""
import pathlib

import yaml

import pfade  # noqa: F401  (makes the module lebenslauf importable)
import page_fill
from dateien import schreibe_atomar

FILE = "unterlagen.yaml"
KEY = "lebenslauf_seiten"
DEFAULT = page_fill.LIMITS["cv"]
MOST = max(page_fill.CV_PAGES)
HEADER = "# Unterlagen: Seiten des Lebenslaufs. Geschrieben vom Bewerbungsbegleiter.\n"
BAD_PAGES = "Bitte wählen: zwei oder drei Seiten für den Lebenslauf."


def parse(values) -> int:
    """The pages as the page sends them; ValueError with a German message."""
    pages = values.get(KEY) if isinstance(values, dict) else None
    if isinstance(pages, bool) or pages not in page_fill.CV_PAGES:
        raise ValueError(BAD_PAGES)
    return pages


def load(data_dir: pathlib.Path) -> int:
    """The stored pages; without a choice, or with a broken file, two."""
    path = data_dir / FILE
    try:
        return parse(yaml.safe_load(path.read_text(encoding="utf-8"))) if path.is_file() else DEFAULT
    except (OSError, yaml.YAMLError, ValueError):
        return DEFAULT


def as_dict(pages: int) -> dict:
    return {KEY: pages}


def save(k, values) -> int:
    """Store the choice, with drafts before and after like every file in the data folder."""
    pages = parse(values)
    path = k.daten / FILE
    text = HEADER + yaml.safe_dump(as_dict(pages), allow_unicode=True, sort_keys=False)
    description = f"Lebenslauf: höchstens {'drei' if pages == 3 else 'zwei'} Seiten"
    k.mit_entwurf(path, description, lambda: schreibe_atomar(path, text.encode("utf-8")))
    return pages
