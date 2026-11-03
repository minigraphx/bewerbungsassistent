"""Put documents from the template into `dokumente/` and list them as pending for the einstieg skill.

Documents keep their names; a different file with the same name gets " (2)", " (3)", … and an identical
one is not stored twice. `dokumente/neu.yaml` lists what the skill einstieg still has to take over
(step 1a); the skill removes entries once a document is processed. `dokumente/` stays out of Git.
"""
import datetime
import pathlib

import paths  # noqa: F401  (makes the module bewerbungen importable)
from archive import DOCUMENTS_DIR, Document
from dateien import im_ordner, lies_yaml, schreibe_atomar, schreibe_yaml, sichere_gitignore

PENDING = f"{DOCUMENTS_DIR}/neu.yaml"
BUNDLE_COPY = f"{DOCUMENTS_DIR}/einstieg.json"
PENDING_HEADER = ("# Unterlagen aus der Einstiegsvorlage, die der Skill „einstieg“ noch übernehmen muss (Schritt 1a).\n"
                  "# Einträge werden nach dem Übernehmen entfernt.\n")
MAX_SAME_NAME = 100


def store_documents(data_dir: pathlib.Path, found: tuple[Document, ...], today: datetime.date,
                    bundle_copy: bytes | None = None) -> list[str]:
    """Write the documents (and, for unfinished answers, the bundle itself); return the new paths."""
    if not found and bundle_copy is None:
        return []
    sichere_gitignore(data_dir, [f"{DOCUMENTS_DIR}/"])
    new = []
    for document in found:
        target = _free_target(data_dir, document)
        if target is not None:
            schreibe_atomar(target, document.data)
            new.append(target.relative_to(data_dir).as_posix())
    if bundle_copy is not None:
        schreibe_atomar(im_ordner(data_dir, BUNDLE_COPY), bundle_copy)
        new.append(BUNDLE_COPY)
    _add_pending(data_dir, new, today)
    return [rel for rel in new if rel != BUNDLE_COPY]


def _free_target(data_dir: pathlib.Path, document: Document) -> pathlib.Path | None:
    """Where to write the document, or None if the same content is already there."""
    first = im_ordner(data_dir, document.path)
    stem, suffix = first.stem, first.suffix
    for number in range(1, MAX_SAME_NAME + 1):
        candidate = first if number == 1 else first.with_name(f"{stem} ({number}){suffix}")
        if not candidate.exists():
            return candidate
        if candidate.read_bytes() == document.data:
            return None
    raise ValueError(f"Zu viele Dateien mit dem Namen {first.name}")


def _add_pending(data_dir: pathlib.Path, new: list[str], today: datetime.date) -> None:
    path = im_ordner(data_dir, PENDING)
    entries = lies_yaml(path, [])
    if not isinstance(entries, list):
        entries = []
    known = {e.get("datei") for e in entries if isinstance(e, dict)}
    added = [{"datei": rel, "eingang": today.isoformat()} for rel in new if rel not in known]
    if added:
        schreibe_yaml(path, [*entries, *added], PENDING_HEADER)
