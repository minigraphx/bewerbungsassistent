"""Backup of the data folder as a ZIP (MIN-359), without Git, GitHub or a cloud.

The browser saves the file where the person chooses, so nothing here writes outside the data folder. Only regular
files inside the folder go in: symlinks are neither followed nor packed. Whether a backup was saved only the page
knows, so it reports that afterwards; until then the reminder stays.
"""
import datetime
import io
import logging
import os
import pathlib
import zipfile

import yaml

from dateien import schreibe_yaml

log = logging.getLogger(__name__)

NOTE_FILE = ".sicherung.yaml"
LEFT_OUT = {".build", ".git"}
FILE_PREFIX = "bewerbungsbegleiter-sicherung-"
OLD_FILE_PREFIX = "bewerbungsassistent-sicherung-"  # up to version 0.2.10 (MIN-395)
ALREADY_COMPRESSED = {".pdf", ".jpg", ".jpeg", ".png", ".zip", ".docx"}
REMIND_AFTER_DAYS = 30
REMIND_AFTER_SENT = 5


def file_name(today: datetime.date) -> str:
    return f"{FILE_PREFIX}{today.isoformat()}.zip"


def _earlier_backup(path: pathlib.Path, data_dir: pathlib.Path) -> bool:
    """Saved in the folder itself, every further backup would contain all earlier ones."""
    return path.parent == data_dir and path.name.startswith((FILE_PREFIX, OLD_FILE_PREFIX)) and path.suffix == ".zip"


def _files(data_dir: pathlib.Path):
    for folder, subfolders, names in os.walk(data_dir, followlinks=False):
        here = pathlib.Path(folder)
        subfolders[:] = [s for s in subfolders if not (here / s).is_symlink() and not (here == data_dir and s in LEFT_OUT)]
        paths = (here / name for name in names)
        yield from (p for p in paths if not p.is_symlink() and p.is_file() and not _earlier_backup(p, data_dir))


def _pack(archive: zipfile.ZipFile, path: pathlib.Path, name: str) -> None:
    """A file gone meanwhile was a temporary one. Any other gap would make the backup look complete when it is not."""
    try:
        method = zipfile.ZIP_STORED if path.suffix.lower() in ALREADY_COMPRESSED else zipfile.ZIP_DEFLATED
        archive.write(path, name, compress_type=method)
    except FileNotFoundError:
        log.info("Beim Sichern nicht mehr vorhanden: %s", name)
    except OSError as error:
        log.warning("Nicht gesichert: %s (%s)", name, error)
        raise ValueError(f"Die Datei {name} liess sich nicht lesen. Falls sie in einem Programm offen ist: dort schliessen und nochmals versuchen.") from error


def create(data_dir: pathlib.Path) -> bytes:
    """The folder as a ZIP. Packed in memory, because the answer of the server is a block of bytes anyway."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED, strict_timestamps=False) as archive:
        for path in _files(data_dir):
            _pack(archive, path, path.relative_to(data_dir).as_posix())
    return buffer.getvalue()


def _date(value: object) -> datetime.date | None:
    if isinstance(value, datetime.date):
        return value
    try:
        return datetime.date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def _last_backup(data_dir: pathlib.Path) -> datetime.date | None:
    """A broken note must not keep anyone from working; it counts as no backup, which only means a reminder."""
    try:
        note = yaml.safe_load((data_dir / NOTE_FILE).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return None
    return _date(note.get("zuletzt")) if isinstance(note, dict) else None


def mark_done(data_dir: pathlib.Path, today: datetime.date) -> None:
    schreibe_yaml(data_dir / NOTE_FILE, {"zuletzt": today.isoformat()})


def reminder(data_dir: pathlib.Path, register: list[dict], today: datetime.date) -> dict:
    """When the last backup was, and whether a calm hint is due: after some days or some sent applications."""
    last = _last_backup(data_dir)
    entered = [d for d in (_date(b.get("eingetragen_am")) for b in register) if d]
    # Dates have no time: a send on the day of the backup counts as contained in it, the 30 days still catch it.
    sent = [d for d in (_date(b.get("beworben_am")) for b in register) if d and (last is None or d > last)]
    since = last or (min(entered) if entered else None)
    old = since is not None and (today - since).days >= REMIND_AFTER_DAYS
    return {"zuletzt": last.isoformat() if last else None, "faellig": old or len(sent) >= REMIND_AFTER_SENT,
            "datei": file_name(today)}
