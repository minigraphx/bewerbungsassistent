"""Which folder may become the data folder (MIN-342).

Allowed: a folder that does not exist yet (created on confirmation), an empty folder, or an existing data
folder. A folder with other files is refused, so the app never writes its files into e.g. Documents itself.
Folders of the app are refused too: an update replaces them.
"""
import dataclasses
import pathlib
from collections.abc import Sequence

import settings

DATA_MARKERS = ("cv.yaml", "bewerbungen.yaml", "suchprofil.md")
SYSTEM_FILES = {"desktop.ini", "thumbs.db"}  # Windows puts them into folders on its own
PLACEHOLDER = "noch-kein-datenordner"  # inside the app folder, used until the person has chosen a folder
TEXTS = {
    "neu": "Der Ordner wird neu angelegt.",
    "leer": "Der Ordner ist leer und wird verwendet.",
    "datenordner": "Der Ordner enthält schon Bewerbungsdaten; sie werden weiter verwendet.",
}


@dataclasses.dataclass(frozen=True)
class FolderCheck:
    path: pathlib.Path
    state: str  # neu, leer, datenordner

    @property
    def text(self) -> str:
        return TEXTS[self.state]


def placeholder_dir(paths: settings.Paths) -> pathlib.Path:
    folder = paths.app_dir / PLACEHOLDER
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _inside(path: pathlib.Path, folder: pathlib.Path) -> bool:
    return path == folder or folder in path.parents


def check_folder(raw: str, forbidden: Sequence[pathlib.Path] = ()) -> FolderCheck:
    text = (raw or "").strip()
    path = pathlib.Path(text).expanduser() if text else None
    if path is None or not path.is_absolute():
        raise ValueError("Bitte den vollständigen Pfad des Ordners angeben, z.B. C:\\Users\\…\\Documents\\Bewerbung.")
    path = path.resolve()
    if any(_inside(path, folder.resolve()) for folder in forbidden):
        raise ValueError("Dieser Ordner gehört zur App und wird bei Updates ersetzt. Bitte einen eigenen Ordner wählen.")
    try:
        return _classify(path)
    except OSError as error:
        raise ValueError(f"Der Ordner lässt sich nicht lesen ({error.strerror or error}).") from error


def _classify(path: pathlib.Path) -> FolderCheck:
    if path.exists() and not path.is_dir():
        raise ValueError("Das ist eine Datei, kein Ordner.")
    if not path.exists():
        return FolderCheck(path, "neu")
    entries = [e for e in path.iterdir() if not e.name.startswith(".") and e.name.lower() not in SYSTEM_FILES]
    if not entries:
        return FolderCheck(path, "leer")
    if any((path / marker).is_file() for marker in DATA_MARKERS):
        return FolderCheck(path, "datenordner")
    raise ValueError("Der Ordner enthält schon andere Dateien. Bitte einen leeren Ordner wählen "
                     "oder am Ende einen neuen Namen angeben, z.B. …\\Bewerbungsassistent.")


def prepare(check: FolderCheck) -> pathlib.Path:
    try:
        check.path.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise ValueError(f"Der Ordner lässt sich nicht anlegen ({error.strerror}).") from error
    return check.path
