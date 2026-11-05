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
FILE_NAMES = {"lebenslauf": "lebenslauf.pdf", "anschreiben": "anschreiben.pdf", "zertifikate": "zertifikate.zip"}
LABELS = {"lebenslauf": "Lebenslauf", "anschreiben": "Anschreiben", "zertifikate": "Zertifikate"}
NOT_KEPT = "Die Datei liess sich nicht für das Formular bereitstellen. Bitte nochmals versuchen."


def _folder(data_dir: pathlib.Path, entry_id: str) -> pathlib.Path:
    return unterlagen.bewerbungsordner(data_dir, entry_id) / FOLDER


def copy_path(data_dir: pathlib.Path, entry_id: str, key: str) -> pathlib.Path | None:
    """Where the copy of this file belongs; None for files that are not recorded."""
    name = FILE_NAMES.get(key)
    return _folder(data_dir, entry_id) / name if name else None


def keep(data_dir: pathlib.Path, entry_id: str, key: str, source: pathlib.Path) -> pathlib.Path:
    """Call with the lock held, while the entry is known to be unsent: a dispatch must not leave a copy behind."""
    target = copy_path(data_dir, entry_id, key)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        schreibe_atomar(target, source.read_bytes())
    except OSError as error:
        raise ValueError(NOT_KEPT) from error
    return target


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
    folder = _folder(data_dir, entry_id)
    if folder.is_dir():
        shutil.rmtree(folder)
