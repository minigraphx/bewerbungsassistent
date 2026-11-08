"""Import the file saved by the HTML template into a data folder.

The file is `einstieg.json` or a ZIP with `einstieg.json` plus uploaded documents (`dokumente/<art>/…`).
Writes cv.yaml, suchprofil.md, anschreiben/stil.md and anschreiben/bausteine.md, and puts documents
into `dokumente/` with a list for the skill einstieg (`dokumente/neu.yaml`). The file is external input:
it is size-limited, parsed and validated against form.json before anything is written. Existing files
are only replaced with --force, and every file is saved as a draft before and after (like
`bewerbungen/entwurf.py`), so the previous state can be restored in the app under „Entwürfe“.
Replacing keeps what the form cannot show: see `cv_merge.py` for the CV and `search_terms.py` for the search.

If documents came along and answers are only missing (not wrong), the basics are not written yet: the
answers are kept as `dokumente/einstieg.json` and the skill einstieg completes them from the documents.

  python import_bundle.py <datenordner> einstieg.json|einstieg.zip [--force]
"""
import argparse
import dataclasses
import datetime
import json
import pathlib
import sys

import paths  # noqa: F401  (makes the module bewerbungen importable)
import archive
import convert
import cv_merge
import import_documents
import search_plan
import search_terms
import validation
from dateien import im_ordner, schreibe_atomar
from entwurf import sichere
from rejected import ImportRejected

__all__ = ["ImportRejected", "ImportResult", "import_answers", "import_file", "main", "read_bundle"]

MAX_BYTES = 1_000_000
DRAFT_BEFORE = "Vor dem Import der Einstiegsdatei"
DRAFT_AFTER = "Import der Einstiegsdatei"
NOT_A_BUNDLE = "Die Datei ist keine gültige Einstiegsdatei (JSON)."
CV = "cv.yaml"


@dataclasses.dataclass(frozen=True)
class ImportResult:
    """What the import wrote, relative to the data folder."""
    written: list[str]
    documents: list[str]
    incomplete: bool
    kept_terms: tuple[str, ...] = ()
    kept_files: tuple[str, ...] = ()  # left as they were: replacing would lose what the form cannot show


def read_bundle(path: pathlib.Path) -> object:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ImportRejected([f"Die Datei {path} lässt sich nicht lesen ({exc.strerror})."]) from exc
    if size > MAX_BYTES:
        raise ImportRejected([f"Die Datei ist zu gross (höchstens {MAX_BYTES // 1000} KB)."])
    return _parse(path.read_bytes())


def _parse(raw: bytes) -> object:
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ImportRejected([NOT_A_BUNDLE]) from exc


def _load(path: pathlib.Path, form: dict) -> tuple[object, bytes | None, tuple[archive.Document, ...]]:
    """The answers, their raw bytes (ZIP only) and the documents in the file."""
    if not archive.is_zip(path):
        return read_bundle(path), None, ()
    found = archive.read_archive(path, form, MAX_BYTES)
    return _parse(found.bundle), found.bundle, found.documents


def import_file(data_dir: pathlib.Path, bundle_path: pathlib.Path, today: datetime.date,
                force: bool = False) -> ImportResult:
    """Validate, convert and write; incomplete answers with documents are kept for the skill einstieg."""
    form = validation.load_form()
    bundle, raw, found = _load(bundle_path, form)
    return _import(form, bundle, raw, found, bool(found), data_dir, today, force)


def import_answers(data_dir: pathlib.Path, bundle: object, today: datetime.date, force: bool = False) -> ImportResult:
    """The same for answers from the page „Meine Angaben“ of the app; documents are already in the data folder."""
    raw = json.dumps(bundle, ensure_ascii=False, indent=2).encode("utf-8", "surrogatepass")
    if len(raw) > MAX_BYTES:
        raise ImportRejected([f"Die Angaben sind zu gross (höchstens {MAX_BYTES // 1000} KB)."])
    has_documents = bool(import_documents.pending_documents(data_dir.resolve()))
    return _import(validation.load_form(), bundle, raw, (), has_documents, data_dir, today, force)


def _import(form: dict, bundle: object, raw: bytes | None, found: tuple[archive.Document, ...], has_documents: bool,
            data_dir: pathlib.Path, today: datetime.date, force: bool) -> ImportResult:
    errors = validation.validate_bundle(form, bundle)
    incomplete = bool(errors and has_documents) and all(e.code == "required" for e in errors)
    if errors and not incomplete:
        track = bundle.get("track") if isinstance(bundle, dict) else None
        raise ImportRejected([validation.describe(form, track, e) for e in errors])
    data_dir = data_dir.resolve()
    written, kept, unchanged = ([], (), ()) if incomplete else _write_basics(form, bundle, data_dir, today, force)
    data_dir.mkdir(parents=True, exist_ok=True)
    stored = import_documents.store_documents(data_dir, found, today, raw if incomplete else None)
    if not incomplete:
        import_documents.discard_kept_answers(data_dir)
    return ImportResult(written, stored, incomplete, kept, unchanged)


def _keeping_search_terms(files: dict[str, str], data_dir: pathlib.Path) -> tuple[dict[str, str], tuple[str, ...]]:
    """Terms added on the page of the app are unknown to the form; replacing must not lose them."""
    path = data_dir / search_plan.PROFILE
    if search_plan.PROFILE not in files or not path.is_file():
        return files, ()
    text, kept = search_terms.kept_on_replace(path.read_text(encoding="utf-8", errors="replace"), files[search_plan.PROFILE])
    return {**files, search_plan.PROFILE: text}, kept


def _keeping_cv_content(files: dict[str, str], bundle: dict, data_dir: pathlib.Path,
                        today: datetime.date) -> tuple[dict[str, str], tuple[str, ...]]:
    """Content the form cannot show must survive replacing; if merging cannot keep it, the CV stays as it was."""
    path = data_dir / CV
    if not path.is_file():
        return files, ()
    try:
        existing = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        existing = None
    cv = None if existing is None else cv_merge.merged(existing, convert.build_cv(bundle["data"], bundle["track"]))
    if cv is None:
        return {rel: text for rel, text in files.items() if rel != CV}, (CV,)
    return {**files, CV: convert.cv_file(cv, convert.made_on(today))}, ()


def _write_basics(form: dict, bundle: dict, data_dir: pathlib.Path, today: datetime.date,
                  force: bool) -> tuple[list[str], tuple[str, ...], tuple[str, ...]]:
    files = convert.convert_bundle(form, bundle, today)
    files, unchanged = _keeping_cv_content(files, bundle, data_dir, today) if force else (files, ())
    merged, kept = _keeping_search_terms(files, data_dir) if force else (files, ())
    encoded = _encode(merged)
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
    return list(encoded), kept, unchanged


def _encode(files: dict[str, str]) -> dict[str, bytes]:
    """Encode every file before writing any, so a bad character cannot leave a partial import."""
    try:
        return {rel: content.encode("utf-8") for rel, content in files.items()}
    except UnicodeEncodeError as exc:
        raise ImportRejected(["Die Datei enthält ungültige Zeichen (z.B. aus einer Bearbeitung von Hand)."]) from exc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Einstiegsdatei aus der HTML-Vorlage in den Datenordner übernehmen")
    ap.add_argument("daten", help="Datenordner")
    ap.add_argument("datei", help="einstieg.json oder einstieg-….zip aus der Vorlage")
    ap.add_argument("--force", action="store_true", help="bestehende Dateien ersetzen (alter Stand als Entwurf)")
    args = ap.parse_args(argv)
    try:
        result = import_file(pathlib.Path(args.daten), pathlib.Path(args.datei), datetime.date.today(), args.force)
    except ImportRejected as rejected:
        print("Import abgebrochen:", *(f"- {m}" for m in rejected.messages), sep="\n", file=sys.stderr)
        return 1
    _report(result)
    return 0


def _report(result: ImportResult) -> None:
    if result.written:
        print("Übernommen:", *(f"- {rel}" for rel in result.written), sep="\n")
    if result.kept_terms:
        print("Aus der bisherigen Suche behalten:", *(f"- {term}" for term in result.kept_terms), sep="\n")
    if result.kept_files:
        print("Unverändert gelassen, weil sie mehr enthalten, als das Formular zeigt:",
              *(f"- {rel}" for rel in result.kept_files), sep="\n")
    if result.documents:
        print("Unterlagen abgelegt:", *(f"- {rel}" for rel in result.documents), sep="\n")
    if result.incomplete:
        print("Die Antworten sind noch nicht vollständig; sie liegen in dokumente/einstieg.json.")
    if result.documents or result.incomplete:
        print("Nächster Schritt: Skill „einstieg“ starten; er übernimmt die Unterlagen aus dokumente/neu.yaml "
              "und ergänzt, was fehlt.")
    else:
        print("Nächster Schritt: Lebenslauf bauen und gemeinsam durchgehen.")


if __name__ == "__main__":
    sys.exit(main())
