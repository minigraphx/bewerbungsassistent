"""Certificates per application (MIN-346): which fit the ad, the choice in the register, one ZIP file.

Suggestions are a plain comparison of file names with the ad, so no text leaves the computer; the person confirms
or changes them. The ZIP lies with the documents of the application and goes along with an upload or a dispatch.
"""
import io
import os
import pathlib
import re
import unicodedata
import zipfile

import yaml

from dateien import im_ordner, schreibe_atomar
from unterlagen import bewerbungsordner

FOLDER = "dokumente/zertifikate"
ZIP_FILE = "zertifikate.zip"
FIXED_TIME = (1980, 1, 1, 0, 0, 0)  # the same choice gives the same bytes, so a sent copy is not kept twice
MIN_WORD = 3
GENERAL_WORDS = {"zertifikat", "zertifikate", "certificate", "certificat", "diplom", "diploma", "kurs", "course", "bestätigung",
                 "nachweis", "und", "and", "der", "die", "das", "von", "für", "grundlagen", "abschluss", "scan", "kopie"}
WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def files_in(data_dir: pathlib.Path, relative: str) -> list[str]:
    """Paths in one folder of the data folder, relative to it: regular files only, no links out of it."""
    folder = data_dir / relative
    if not folder.is_dir():
        return []
    found = (entry for entry in os.scandir(folder) if entry.is_file(follow_symlinks=False) and not entry.name.startswith("."))
    return sorted(f"{relative}/{entry.name}" for entry in found)


def available(data_dir: pathlib.Path) -> list[str]:
    return files_in(data_dir, FOLDER)


def _name_words(path: str) -> list[str]:
    words = WORD.findall(pathlib.PurePosixPath(path).stem)
    return [word for word in words if len(word) >= MIN_WORD and word.lower() not in GENERAL_WORDS]


def suggest(files: list[str], ad_text: str) -> list[dict]:
    """The certificates whose name appears in the ad as a whole word, each with the reason."""
    ad_words = {word.lower() for word in WORD.findall(ad_text or "")}
    found = []
    for path in files:
        hit = next((word for word in _name_words(path) if word.lower() in ad_words), None)
        if hit:
            found.append({"datei": path, "grund": f"{hit}: steht im Inserat"})
    return found


def checked_choice(data_dir: pathlib.Path, choice: object) -> list[str]:
    """Only certificates that exist; a path from a request never reaches anything else."""
    if not isinstance(choice, list) or not all(isinstance(path, str) for path in choice):
        raise ValueError("Die Auswahl der Zertifikate hat eine unbekannte Form.")
    known = set(available(data_dir))
    unknown = [path for path in choice if path not in known]
    if unknown:
        raise ValueError(f"Dieses Zertifikat gibt es nicht: {pathlib.PurePosixPath(unknown[0]).name}")
    return sorted(set(choice))


def zip_path(data_dir: pathlib.Path, application_id: str) -> pathlib.Path:
    return bewerbungsordner(data_dir, application_id) / ZIP_FILE


def write_zip(data_dir: pathlib.Path, application_id: str, choice: list[str]) -> pathlib.Path | None:
    """The ZIP with exactly this choice; without a choice there is no file."""
    path = zip_path(data_dir, application_id)
    if not choice:
        path.unlink(missing_ok=True)
        return None
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for rel in sorted(choice):
            source = im_ordner(data_dir, rel)
            archive.writestr(zipfile.ZipInfo(source.name, FIXED_TIME), source.read_bytes(), zipfile.ZIP_DEFLATED)
    schreibe_atomar(path, buffer.getvalue())
    return path


def upload_name(data_dir: pathlib.Path, label: str = "Zertifikate", suffix: str = ".zip") -> str:
    """Name of a file for the employer, e.g. Zertifikate_Erika_Beispiel.zip."""
    try:
        cv = yaml.safe_load((data_dir / "cv.yaml").read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        cv = {}
    name = (cv.get("basics") or {}).get("name") if isinstance(cv, dict) else None
    words = WORD.findall(unicodedata.normalize("NFC", name)) if isinstance(name, str) else []
    return "_".join([label, *words]) + suffix
