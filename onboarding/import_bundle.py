"""Import an `einstieg.json` from the HTML template into a data folder.

Writes cv.yaml, suchprofil.md, anschreiben/stil.md and anschreiben/bausteine.md. The file is
external input: it is size-limited, parsed as JSON and validated against form.json before
anything is written. Existing files are only replaced with --force, and every file is saved as a
draft before and after (like `bewerbungen/entwurf.py`), so the previous state can be restored in
the app under „Entwürfe“.

  python import_bundle.py <datenordner> einstieg.json [--force]
"""
import argparse
import datetime
import json
import pathlib
import sys

import paths  # noqa: F401  (makes the module bewerbungen importable)
import convert
import validation
from dateien import im_ordner, schreibe_atomar
from entwurf import sichere

MAX_BYTES = 1_000_000
DRAFT_BEFORE = "Vor dem Import aus der Einstiegsvorlage"
DRAFT_AFTER = "Import aus der Einstiegsvorlage"


class ImportRejected(Exception):
    """The file cannot be imported; `messages` explains why, in German, one line per problem."""

    def __init__(self, messages: list[str]) -> None:
        super().__init__("\n".join(messages))
        self.messages = messages


def read_bundle(path: pathlib.Path) -> object:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ImportRejected([f"Die Datei {path} lässt sich nicht lesen ({exc.strerror})."]) from exc
    if size > MAX_BYTES:
        raise ImportRejected([f"Die Datei ist zu gross (höchstens {MAX_BYTES // 1000} KB)."])
    try:
        return json.loads(path.read_bytes().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ImportRejected(["Die Datei ist keine gültige JSON-Datei aus der Einstiegsvorlage."]) from exc


def import_file(data_dir: pathlib.Path, bundle_path: pathlib.Path, today: datetime.date,
                force: bool = False) -> list[str]:
    """Validate, convert and write; return the written files relative to the data folder."""
    form = validation.load_form()
    bundle = read_bundle(bundle_path)
    errors = validation.validate_bundle(form, bundle)
    if errors:
        track = bundle.get("track") if isinstance(bundle, dict) else None
        raise ImportRejected([validation.describe(form, track, e) for e in errors])
    encoded = _encode(convert.convert_bundle(form, bundle, today))
    data_dir = data_dir.resolve()
    targets = {rel: im_ordner(data_dir, rel) for rel in encoded}
    existing = [rel for rel, target in targets.items() if target.exists()]
    if existing and not force:
        raise ImportRejected([f"Diese Dateien gibt es schon: {', '.join(existing)}. "
                              "Zum Ersetzen mit --force aufrufen; der alte Stand bleibt als Entwurf erhalten."])
    data_dir.mkdir(parents=True, exist_ok=True)
    if existing:
        sichere(data_dir, existing, DRAFT_BEFORE)
    for rel, content in encoded.items():
        schreibe_atomar(targets[rel], content)
    sichere(data_dir, list(encoded), DRAFT_AFTER)
    return list(encoded)


def _encode(files: dict[str, str]) -> dict[str, bytes]:
    """Encode every file before writing any, so a bad character cannot leave a partial import."""
    try:
        return {rel: content.encode("utf-8") for rel, content in files.items()}
    except UnicodeEncodeError as exc:
        raise ImportRejected(["Die Datei enthält ungültige Zeichen (z.B. aus einer Bearbeitung von Hand)."]) from exc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Einstiegsdatei aus der HTML-Vorlage in den Datenordner übernehmen")
    ap.add_argument("daten", help="Datenordner")
    ap.add_argument("datei", help="einstieg.json aus der Vorlage")
    ap.add_argument("--force", action="store_true", help="bestehende Dateien ersetzen (alter Stand als Entwurf)")
    args = ap.parse_args(argv)
    try:
        written = import_file(pathlib.Path(args.daten), pathlib.Path(args.datei), datetime.date.today(), args.force)
    except ImportRejected as rejected:
        print("Import abgebrochen:", *(f"- {m}" for m in rejected.messages), sep="\n", file=sys.stderr)
        return 1
    print("Übernommen:", *(f"- {rel}" for rel in written), sep="\n")
    print("Nächster Schritt: Lebenslauf bauen und gemeinsam durchgehen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
