"""The pages of each shown document and how the app balanced them (G93, #324), for the tiles of the check.

The levels come from the record the build keeps beside each PDF (lebenslauf/fill_record.py). A file the app did not
build for this application, such as an own PDF, has none and names only its pages. A sent file is a copy of the built
one, so its record still lies beside the built file. The page asks for the details again and again, so counting and
fingerprinting are cached per state of the files.
"""
import pathlib

from pypdf import PdfReader
from pypdf.errors import PdfReadError

import pfade  # noqa: F401  (makes the module lebenslauf importable)
import fill_record
import page_fill
import unterlagen

CACHE_TAG = "seiten-notiz"


def note(pdf: pathlib.Path, built_as: pathlib.Path | None = None) -> dict | None:
    """Pages and the change per part (`ausgleich`, only parts the app changed); None when the PDF cannot be read."""
    try:
        pages = len(PdfReader(pdf).pages)
    except (PdfReadError, ValueError, OSError, KeyError, IndexError, TypeError):
        return None
    if not pages:
        return None
    levels = fill_record.read(pdf, built_as) or {}
    changes = {part: page_fill.change(level) for part, level in levels.items()}
    return {"seiten": pages, "ausgleich": {part: kind for part, kind in changes.items() if kind}}


def _state(path: pathlib.Path) -> tuple[int, int] | None:
    try:
        stat = path.stat()
    except OSError:
        return None
    return stat.st_mtime_ns, stat.st_size


def cached(cache: dict, pdf: pathlib.Path, built_as: pathlib.Path | None = None) -> dict | None:
    """The note of a PDF, counted again only when the PDF or its record changed."""
    record = fill_record.path_for(built_as or pdf)
    key = (CACHE_TAG, str(pdf), _state(pdf), _state(record))
    if key not in cache:
        for old in [old for old in cache if isinstance(old, tuple) and old[:2] == key[:2]]:
            cache.pop(old)
        cache[key] = note(pdf, built_as)
    return cache[key]


def notes(cache: dict, daten: pathlib.Path, entry: dict, shown: dict[str, pathlib.Path]) -> dict[str, dict]:
    """The note of each shown document that is there and readable."""
    built = {**unterlagen.pdf_pfade(daten, entry["id"]), unterlagen.DOSSIER: unterlagen.dossier_path(daten, entry["id"])}
    sent = bool(entry.get("versand"))
    found = {art: cached(cache, pdf, built.get(art) if sent else None) for art, pdf in shown.items() if pdf.is_file()}
    return {art: found_note for art, found_note in found.items() if found_note}
