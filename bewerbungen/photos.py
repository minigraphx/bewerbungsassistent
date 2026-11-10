"""Several photos on the page Foto, one of them active (#129, G21).

The active photo is the one cv.yaml names (`basics.image`, its crop in `basics.x-image`): every CV and dossier is built
from there, as before. `fotos.yaml` in the data folder lists all photos with their own crop. A folder from before #129
has no such file; its one photo is the first, active one without any step. An upload never overwrites a photo, and a
deleted one is kept as a draft first, so drafts and versions that name a photo keep it.
"""
import hashlib
import pathlib
from typing import Callable, TypeVar

import yaml

import pfade  # noqa: F401  (makes the module lebenslauf importable)
import fotoausschnitt
from build import pruefe_foto_optionen
from dateien import im_ordner, lies_yaml, relativ, schreibe_atomar, schreibe_yaml

T = TypeVar("T")

LIST_FILE = "fotos.yaml"
FOLDER = "fotos"
FIRST_NAME = "foto"  # foto.jpg or foto.png: the first photo lies where the skill einstieg puts it (#128)
SUFFIXES = (".jpg", ".jpeg", ".png")
HASH_DIGITS = 12
NOT_LISTED = "Dieses Foto gibt es nicht mehr. Bitte die Seite neu laden."
ACTIVE_STAYS = "Das aktive Foto lässt sich nicht löschen. Zuerst ein anderes Foto verwenden."
UPLOADED = "Foto hochgeladen"
SWITCHED = "Aktives Foto gewechselt"
DELETED = "Foto gelöscht"
HEADER = "# Fotos für den Lebenslauf, geschrieben vom Bewerbungsbegleiter; das aktive nennt cv.yaml\n"


def _crop(raw) -> dict:
    try:
        return {**fotoausschnitt.STANDARD, **pruefe_foto_optionen(raw if isinstance(raw, dict) else {})}
    except ValueError:
        return dict(fotoausschnitt.STANDARD)  # the file is data the person may have edited


def _name(daten: pathlib.Path, raw) -> str | None:
    """A photo file in the data folder, relative to it, or None for anything else."""
    if not isinstance(raw, str) or not raw:
        return None
    try:
        path = im_ordner(daten, raw)
    except ValueError:
        return None
    return relativ(path, daten) if path.suffix.lower() in SUFFIXES and path.is_file() else None


def _active(daten: pathlib.Path) -> tuple[str | None, dict]:
    cv = daten / "cv.yaml"
    try:
        basics = (yaml.safe_load(cv.read_text(encoding="utf-8")) or {}).get("basics") or {}
    except (OSError, yaml.YAMLError, AttributeError):
        return None, {}
    return _name(daten, basics.get("image")), _crop(basics.get("x-image"))


def _stored(daten: pathlib.Path) -> list[dict]:
    raw = lies_yaml(daten / LIST_FILE, [])
    found: list[dict] = []
    for item in raw if isinstance(raw, list) else []:
        name = _name(daten, item.get("datei")) if isinstance(item, dict) else None
        if name and all(entry["datei"] != name for entry in found):
            found.append({"datei": name, "ausschnitt": _crop(item.get("ausschnitt"))})
    return found


def entries(daten: pathlib.Path) -> list[dict]:
    """Every photo with its crop and whether it is active; the active one with the crop from cv.yaml."""
    name, crop = _active(daten)
    stored = _stored(daten)
    if name is not None and all(entry["datei"] != name for entry in stored):
        stored = [{"datei": name, "ausschnitt": crop}, *stored]
    return [{**entry, "aktiv": entry["datei"] == name, **({"ausschnitt": crop} if entry["datei"] == name else {})}
            for entry in stored]


def listing(daten: pathlib.Path) -> list[dict]:
    return [{"datei": entry["datei"], "aktiv": entry["aktiv"]} for entry in entries(daten)]


def listed(daten: pathlib.Path, datei) -> dict:
    """The entry of a photo the page names; only listed photos, so no other file of the folder is reachable."""
    found = next((entry for entry in entries(daten) if entry["datei"] == datei), None)
    if found is None:
        raise KeyError(NOT_LISTED)
    return found


def _save_list(daten: pathlib.Path, photos: list[dict]) -> None:
    schreibe_yaml(daten / LIST_FILE, [{"datei": p["datei"], "ausschnitt": p["ausschnitt"]} for p in photos], HEADER)


def _with_drafts(k, paths: tuple[pathlib.Path, ...], description: str, write: Callable[[], T]) -> T:
    """Like `mit_entwurf`, for changes that touch several files together."""
    with k.sperre:
        for path in paths:
            if path.is_file():
                k.ablage.speichere(path, f"Stand vor: {description}")
        result = write()
        for path in paths:
            if path.is_file():
                k.ablage.speichere(path, description)
        return result


def upload_name(daten: pathlib.Path, extension: str, data: bytes) -> str:
    """Where a new photo goes: the very first one to foto.<ext>, every further one to its own file under fotos/."""
    first = f"{FIRST_NAME}.{extension}"
    if not entries(daten) and not (daten / first).exists():
        return first
    return f"{FOLDER}/{FIRST_NAME}-{hashlib.sha256(data).hexdigest()[:HASH_DIGITS]}.{extension}"


def add(k, name: str, data: bytes) -> dict:
    """Store an uploaded photo and make it the active one; the same photo again keeps its file and its crop."""
    daten = k.daten
    path = im_ordner(daten, name)

    def write() -> dict:
        current = entries(daten)
        known = next((entry for entry in current if entry["datei"] == name), None)
        if not path.is_file():
            path.parent.mkdir(parents=True, exist_ok=True)
            schreibe_atomar(path, data)
        crop = known["ausschnitt"] if known else dict(fotoausschnitt.STANDARD)
        _save_list(daten, current if known else [*current, {"datei": name, "ausschnitt": crop}])
        fotoausschnitt.speichere_foto(daten / "cv.yaml", name, crop)
        return crop

    return _with_drafts(k, (daten / "cv.yaml", daten / LIST_FILE, path), UPLOADED, write)


def activate(k, datei) -> dict:
    """Make a listed photo the active one, with its own crop; the one active so far keeps its crop in the list."""
    daten = k.daten

    def write() -> dict:
        current = entries(daten)
        chosen = listed(daten, datei)
        _save_list(daten, current)
        fotoausschnitt.speichere_foto(daten / "cv.yaml", chosen["datei"], chosen["ausschnitt"])
        return chosen["ausschnitt"]

    return _with_drafts(k, (daten / "cv.yaml", daten / LIST_FILE), SWITCHED, write)


def delete(k, datei) -> None:
    """Delete a photo that is not active; its content stays in the drafts, for versions that used it."""
    daten = k.daten

    def write() -> None:
        chosen = listed(daten, datei)
        if chosen["aktiv"]:
            raise ValueError(ACTIVE_STAYS)
        path = im_ordner(daten, chosen["datei"])
        k.ablage.speichere(path, f"Stand vor: {DELETED}")
        _save_list(daten, [entry for entry in entries(daten) if entry["datei"] != chosen["datei"]])
        path.unlink()

    _with_drafts(k, (daten / LIST_FILE,), DELETED, write)
