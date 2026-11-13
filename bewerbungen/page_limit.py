"""How many pages the CV may have (G51): two, or three where the person allows it under Einstellungen > Erweitert.

Stored in the data folder (`unterlagen.yaml`, shared with the photo switch of G62, see document_settings.py), so it
moves with the person's files; written with drafts before and after. Every build of the CV takes it (unterlagen.py),
and the check before sending measures against it (pruefung.py). The cover letter always has one page.
"""
import pathlib

import pfade  # noqa: F401  (makes the module lebenslauf importable)
import document_settings
import page_fill

FILE = document_settings.FILE
KEY = "lebenslauf_seiten"
DEFAULT = page_fill.LIMITS["cv"]
MOST = max(page_fill.CV_PAGES)
BAD_PAGES = "Bitte wählen: zwei oder drei Seiten für den Lebenslauf."


def parse(values) -> int:
    """The pages as the page sends them; ValueError with a German message."""
    pages = values.get(KEY) if isinstance(values, dict) else None
    if isinstance(pages, bool) or pages not in page_fill.CV_PAGES:
        raise ValueError(BAD_PAGES)
    return pages


def load(data_dir: pathlib.Path) -> int:
    """The stored pages; without a choice, or with a broken file, two."""
    try:
        return parse(document_settings.read(data_dir))
    except ValueError:
        return DEFAULT


def as_dict(pages: int) -> dict:
    return {KEY: pages}


def save(k, values) -> int:
    """Store the choice, with drafts before and after like every file in the data folder."""
    pages = parse(values)
    description = f"Lebenslauf: höchstens {'drei' if pages == 3 else 'zwei'} Seiten"
    document_settings.write(k, KEY, pages, description)
    return pages
