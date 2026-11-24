"""The live preview in „Lebenslauf erstellen“ (G76, #294): the CV a choice gives, before the person takes it.

Built like the CV after „Lebenslauf übernehmen“ (unterlagen.build_cv_preview), but from a tailoring that is not
saved: tailoring, build files and PDF live in a temporary folder under .build/ that is gone when the build ends.
The PDF stays in memory (`k.cache`), the last few per application, so a page that asks for an older answer still gets
it; the pages come as PNG on demand. Nothing of it goes to the AI, and nothing is written to the data folder.
"""
import dataclasses
import hashlib
import io
import logging
import pathlib
import tempfile

import typst
import yaml
from pypdf import PdfReader
from pypdf.errors import PdfReadError

import cv_creation
import pdf_thumbnail
import unterlagen
from server import ActionError, message_of

log = logging.getLogger("bewerbungsbegleiter")

CACHE_TAG = "cv-vorschau"
IMAGE_TAG = "cv-vorschau-seite"
KEEP = 3  # answers to requests still under way stay reachable; a newer request wins on the page
SIZES = {"klein": 300, "gross": 595}  # points wide: beside the choice, and A4 width for «Gross ansehen»
# The page words the problem itself (lebenslauf-vorschau-logik.js); `fehler` is the detail under «Genauer».
CHECK_DATA = "angaben-pruefen"  # Meine Angaben hold something the build cannot read
REOPEN = "neu-oeffnen"  # Meine Angaben changed since the panel opened
BROKEN = "Der Lebenslauf liess sich nicht setzen."
GONE = "Diese Vorschau gibt es nicht mehr. Bitte die Seite neu laden."
WRONG_SIZE = "Bitte klein oder gross wählen."


@dataclasses.dataclass(frozen=True)
class Preview:
    key: str
    pdf: bytes
    pages: int


def _pages(pdf: bytes) -> int:
    try:
        return len(PdfReader(io.BytesIO(pdf)).pages)
    except (PdfReadError, ValueError, KeyError, IndexError, TypeError) as error:
        raise ActionError(BROKEN, CHECK_DATA) from error


def build(daten: pathlib.Path, entry: dict, cv: dict, choice: cv_creation.Choice, build_dir: pathlib.Path) -> Preview:
    """The CV of the choice as PDF in memory; ActionError(CHECK_DATA) with the reason when it cannot be built.

    The choice itself was checked before (cv_creation.parse), so what fails here comes from Meine Angaben: a field
    the build does not know, a photo that is gone, text Typst cannot set.
    """
    build_dir.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(dir=build_dir, prefix="vorschau-") as folder:
            build_folder = pathlib.Path(folder)
            job = build_folder / "zuschnitt.yaml"
            cv_creation.write_tailoring(job, cv_creation.tailoring(cv, entry["id"], choice))
            target = build_folder / "lebenslauf.pdf"
            unterlagen.build_cv_preview(daten, entry, job, choice.design, build_folder / "satz", target)
            pdf = target.read_bytes()
    except ValueError as error:
        raise ActionError(message_of(error), CHECK_DATA) from error
    except (TypeError, KeyError, OSError, yaml.YAMLError, typst.TypstError) as error:
        log.warning("preview of the CV for %s failed: %r", entry["id"], error)
        raise ActionError(BROKEN, CHECK_DATA) from error
    return Preview(key=hashlib.sha256(pdf).hexdigest()[:16], pdf=pdf, pages=_pages(pdf))


def remember(cache: dict, entry_id: str, preview: Preview) -> None:
    """The newest first; what falls out takes its page images along."""
    kept = cache.get((CACHE_TAG, entry_id), ())
    newest = (preview, *(old for old in kept if old.key != preview.key))[:KEEP]
    cache[(CACHE_TAG, entry_id)] = newest
    keys = {old.key for old in newest}
    for stale in [key for key in cache if isinstance(key, tuple) and key[:2] == (IMAGE_TAG, entry_id)
                  and key[2] not in keys]:
        cache.pop(stale, None)


def find(cache: dict, entry_id: str, key: str) -> Preview:
    found = next((preview for preview in cache.get((CACHE_TAG, entry_id), ()) if preview.key == key), None)
    if found is None:
        raise KeyError(GONE)
    return found


def page_image(cache: dict, entry_id: str, key: str, page: int, size: str, build_dir: pathlib.Path) -> bytes:
    """One page of a kept preview as PNG, rendered once per size."""
    if size not in SIZES:
        raise ValueError(WRONG_SIZE)
    preview = find(cache, entry_id, key)
    if not 1 <= page <= preview.pages:
        raise KeyError(GONE)
    image_key = (IMAGE_TAG, entry_id, key, page, size)
    if image_key not in cache:
        cache[image_key] = pdf_thumbnail.render_bytes(preview.pdf, build_dir, page, SIZES[size])
    return cache[image_key]
