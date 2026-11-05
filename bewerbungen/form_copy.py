"""What a form got (MIN-346): the version of a file at the moment it went to the form.

The person can replace a file while a form is open, and the form keeps the earlier one. The dispatch record relies on
this copy when the person confirms in the form, so it names what really went out, not what counts by then.
The copies live until the dispatch is recorded or a new form opens for this application. References are not part of that record and are not copied.
"""
import pathlib
import shutil

import unterlagen
from dateien import schreibe_atomar

FOLDER = "an-formular"
HAND_FOLDER = "zum-hochladen"  # the files with their names for the employer, for whoever uploads them by hand
FILE_NAMES = {"lebenslauf": "lebenslauf.pdf", "anschreiben": "anschreiben.pdf", "zertifikate": "zertifikate.zip",
              "unterlagen": "unterlagen.pdf", "nachweise": "nachweise.pdf"}
LABELS = {"lebenslauf": "Lebenslauf", "anschreiben": "Anschreiben", "zertifikate": "Zertifikate",
          "unterlagen": "Unterlagen", "nachweise": "Nachweise"}
NOT_KEPT = "Die Datei liess sich nicht für das Formular bereitstellen. Bitte nochmals versuchen."


def _folder(data_dir: pathlib.Path, entry_id: str) -> pathlib.Path:
    return unterlagen.bewerbungsordner(data_dir, entry_id) / FOLDER


def copy_path(data_dir: pathlib.Path, entry_id: str, key: str) -> pathlib.Path | None:
    """Where the copy of this file belongs; None for files that are not recorded."""
    name = FILE_NAMES.get(key)
    return _folder(data_dir, entry_id) / name if name else None


def hand_folder(data_dir: pathlib.Path, entry_id: str) -> pathlib.Path:
    return unterlagen.bewerbungsordner(data_dir, entry_id) / HAND_FOLDER


def store(data_dir: pathlib.Path, entry_id: str, key: str, data: bytes) -> pathlib.Path:
    target = copy_path(data_dir, entry_id, key)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        schreibe_atomar(target, data)
    except OSError as error:
        raise ValueError(NOT_KEPT) from error
    return target


def keep(data_dir: pathlib.Path, entry_id: str, key: str, source: pathlib.Path) -> pathlib.Path:
    """Call with the lock held, while the entry is known to be unsent: a dispatch must not leave a copy behind."""
    try:
        data = source.read_bytes()
    except OSError as error:
        raise ValueError(NOT_KEPT) from error
    return store(data_dir, entry_id, key, data)


def copies(data_dir: pathlib.Path, entry_id: str) -> dict[str, pathlib.Path]:
    paths = {key: copy_path(data_dir, entry_id, key) for key in FILE_NAMES}
    return {key: path for key, path in paths.items() if path.is_file()}


def same_content(first: pathlib.Path, second: pathlib.Path) -> bool:
    try:
        return first.stat().st_size == second.stat().st_size and first.read_bytes() == second.read_bytes()
    except FileNotFoundError:  # pages ask without the lock, and a dispatch removes the copies
        return False


def differing(kept: dict[str, pathlib.Path], current: dict[str, pathlib.Path]) -> list[str]:
    """The files a form holds in another version than the one that counts now, or that no longer exist."""
    return [key for key, path in kept.items() if key not in current or not same_content(path, current[key])]


def forget(data_dir: pathlib.Path, entry_id: str) -> None:
    """What a form got. The folder for uploading by hand stays: it says nothing about any form."""
    folder = _folder(data_dir, entry_id)
    if folder.is_dir():
        shutil.rmtree(folder)


def forget_all(data_dir: pathlib.Path, entry_id: str) -> None:
    """After the dispatch nothing of this is needed any more."""
    try:
        forget(data_dir, entry_id)
    finally:  # a copy that stays locked must not keep all the documents here as well
        folder = hand_folder(data_dir, entry_id)
        if folder.is_dir():
            shutil.rmtree(folder)
