"""Which translations in the master data were checked (MIN-309), so that only changed ones are checked again.

A check is recorded as a hash of the German text and its translation, in a file of its own: `cv.yaml` stays as the
person wrote it, comments included, and a moved field stays checked. The record holds no text.

  python translations.py open <data folder>             lists what needs a check, as JSON
  python translations.py checked <data folder> <hash>…  records the checks of these fields
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import sys
from collections.abc import Iterator

import yaml

import pfade  # noqa: F401  (makes build importable)
import build
from dateien import lies_yaml, schreibe_yaml

RECORD = "uebersetzungen.yaml"
RECORD_HEAD = "# Geprüfte Übersetzungen (Hashes, kein Text). Geschrieben von bewerbungen/translations.py.\n"
SOURCE_LANGUAGE = "de"
CV_FILE = "cv.yaml"
VARIANTS = "jobs/*.yaml"
MISSING = "fehlt"
UNCHECKED = "ungeprüft"
STALE = "{count} Prüfung(en) passen nicht mehr zum aktuellen Text. Nichts gespeichert; bitte neu auflisten."


def _fields(value: object, path: str = "") -> Iterator[tuple[str, dict]]:
    if build.ist_mehrsprachig(value):
        yield path, value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _fields(item, f"{path}.{key}" if path else str(key))
    elif isinstance(value, list):
        for position, item in enumerate(value):
            yield from _fields(item, f"{path}[{position}]")


def _hash(german: str, language: str, translation: str) -> str:
    return hashlib.sha256("\0".join((german, language, translation)).encode("utf-8")).hexdigest()


def _sources(data_dir: pathlib.Path) -> list[pathlib.Path]:
    return [path for path in (data_dir / CV_FILE, *sorted(data_dir.glob(VARIANTS))) if path.is_file()]


def _entries(data_dir: pathlib.Path) -> list[dict]:
    entries = []
    for source in _sources(data_dir):
        rel = source.relative_to(data_dir).as_posix()
        for path, field in _fields(yaml.safe_load(source.read_text(encoding="utf-8"))):
            german = field.get(SOURCE_LANGUAGE)
            if german is None:
                continue
            for language in build.SPRACHEN:
                if language != SOURCE_LANGUAGE:
                    entries.append(_entry(rel, path, language, german, field.get(language)))
    return entries


def _entry(rel: str, path: str, language: str, german: str, translation: str | None) -> dict:
    return {"datei": rel, "feld": path, "sprache": language, "de": german, "uebersetzung": translation,
            "stand": UNCHECKED if translation else MISSING,
            "hash": _hash(german, language, translation) if translation else None}


def _record(data_dir: pathlib.Path) -> dict:
    record = lies_yaml(data_dir / RECORD, {})
    checked = record.get("geprueft", {}) if isinstance(record, dict) else None
    if not isinstance(checked, dict):
        raise ValueError(f"{RECORD} lässt sich nicht lesen. Bitte die Datei prüfen oder löschen; dann wird alles neu geprüft.")
    return checked


def open_fields(data_dir: pathlib.Path) -> list[dict]:
    checked = _record(data_dir)
    return [entry for entry in _entries(data_dir) if entry["hash"] not in checked]


def mark_checked(data_dir: pathlib.Path, hashes: list[str], today: datetime.date) -> int:
    """Records these checks; a hash of a text that has changed since refuses all of them. What is gone is forgotten."""
    current = {entry["hash"] for entry in _entries(data_dir) if entry["hash"]}
    stale = set(hashes) - current
    if stale:
        raise ValueError(STALE.format(count=len(stale)))
    kept = {key: value for key, value in _record(data_dir).items() if key in current}
    new = {key: today.isoformat() for key in hashes}
    schreibe_yaml(data_dir / RECORD, {"geprueft": {**kept, **new}}, RECORD_HEAD)
    return len(new)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Übersetzungen pro Feld prüfen")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("open", help="Felder, die eine Prüfung brauchen").add_argument("data_dir", type=pathlib.Path)
    checked = commands.add_parser("checked", help="Prüfung dieser Felder festhalten")
    checked.add_argument("data_dir", type=pathlib.Path)
    checked.add_argument("hashes", nargs="+")
    args = parser.parse_args(argv)
    try:
        if args.command == "open":
            result = open_fields(args.data_dir)
        else:
            result = {"geprueft": mark_checked(args.data_dir, args.hashes, datetime.date.today())}
    except (ValueError, OSError, yaml.YAMLError) as error:
        print(error, file=sys.stderr)
        sys.exit(1)
    print(json.dumps(result, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
