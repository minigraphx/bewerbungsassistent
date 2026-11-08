"""Import the file saved by the HTML template into a data folder.

The file is `einstieg.json` or a ZIP with `einstieg.json` plus uploaded documents (`dokumente/<art>/…`).
Writes cv.yaml, suchprofil.md, anschreiben/stil.md and anschreiben/bausteine.md, and puts documents
into `dokumente/` with a list for the skill einstieg (`dokumente/neu.yaml`). The file is external input:
it is size-limited, parsed and validated against form.json before anything is written. Existing files
are only replaced with --force, and every file is saved as a draft before and after (like
`bewerbungen/entwurf.py`), so the previous state can be restored in the app under „Entwürfe“.
Replacing keeps what the form cannot show: the answers merge into the CV (`cv_merge.py`), and `search_terms.py`
keeps the terms of the search. The pages of the app pass a `MarkdownChoice` instead (G26): cv.yaml always merges,
and each existing Markdown file is replaced only when chosen; without a choice they come back with their diffs.

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
import cv_read
import import_documents
import known_tags
import search_plan
import search_terms
import validation
from dateien import im_ordner, schreibe_atomar
from entwurf import sichere
from rejected import ExistingFiles, ImportRejected
from text_diff import line_diff

__all__ = ["ExistingFiles", "ImportRejected", "ImportResult", "MarkdownChoice", "import_answers", "import_file",
           "main", "read_bundle"]

MAX_BYTES = 1_000_000
DRAFT_BEFORE = "Vor dem Import der Einstiegsdatei"
DRAFT_AFTER = "Import der Einstiegsdatei"
NOT_A_BUNDLE = "Die Datei ist keine gültige Einstiegsdatei (JSON)."
CV = "cv.yaml"
MARKDOWN_TITLES = {"suchprofil.md": "Suchprofil", "anschreiben/stil.md": "Stilprofil",
                   "anschreiben/bausteine.md": "Bausteine"}
MARKDOWN = tuple(rel for rel in convert.BASICS if rel != CV)
CHOOSE_PER_FILE = ("Diese Dateien gibt es schon: {files}. Pro Datei wählen, ob sie bleibt oder ersetzt wird; "
                   "der alte Stand bleibt als Entwurf erhalten.")


@dataclasses.dataclass(frozen=True)
class ImportResult:
    """What the import wrote, relative to the data folder."""
    written: list[str]
    documents: list[str]
    incomplete: bool
    kept_terms: tuple[str, ...] = ()
    kept_files: tuple[str, ...] = ()  # left as they were: they could not be read, so nothing could merge in
    not_replaced: tuple[str, ...] = ()  # existing Markdown files the person chose to keep


@dataclasses.dataclass(frozen=True)
class MarkdownChoice:
    """Which existing Markdown files to replace; None means not chosen yet, so existing ones are refused with diffs."""
    replace: frozenset[str] | None = None


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
                force: bool = False, choice: MarkdownChoice | None = None) -> ImportResult:
    """Validate, convert and write; incomplete answers with documents are kept for the skill einstieg."""
    form = validation.load_form()
    bundle, raw, found = _load(bundle_path, form)
    return _import(form, bundle, raw, found, bool(found), data_dir, today, force, choice)


def import_answers(data_dir: pathlib.Path, bundle: object, today: datetime.date, force: bool = False,
                   choice: MarkdownChoice | None = None) -> ImportResult:
    """The same for answers from the page „Meine Angaben“ of the app; documents are already in the data folder."""
    raw = json.dumps(bundle, ensure_ascii=False, indent=2).encode("utf-8", "surrogatepass")
    if len(raw) > MAX_BYTES:
        raise ImportRejected([f"Die Angaben sind zu gross (höchstens {MAX_BYTES // 1000} KB)."])
    has_documents = bool(import_documents.pending_documents(data_dir.resolve()))
    return _import(validation.load_form(), bundle, raw, (), has_documents, data_dir, today, force, choice)


def _import(form: dict, bundle: object, raw: bytes | None, found: tuple[archive.Document, ...], has_documents: bool,
            data_dir: pathlib.Path, today: datetime.date, force: bool, choice: MarkdownChoice | None) -> ImportResult:
    # tags already in the data folder never block saving, only typed ones keep to the limits (G24); nor do the values
    # cv.yaml holds, only those typed or changed keep to the rules (#167, G23)
    errors = validation.validate_bundle(form, bundle, known=frozenset(known_tags.known_tags(data_dir, form)),
                                        loaded=cv_read.read_form_data(data_dir))
    incomplete = bool(errors and has_documents) and all(e.code == "required" for e in errors)
    if errors and not incomplete:
        track = bundle.get("track") if isinstance(bundle, dict) else None
        raise ImportRejected([validation.describe(form, track, e) for e in errors])
    data_dir = data_dir.resolve()
    written, kept, unchanged, not_replaced = (
        ([], (), (), ()) if incomplete else _write_basics(form, bundle, data_dir, today, force, choice))
    data_dir.mkdir(parents=True, exist_ok=True)
    stored = import_documents.store_documents(data_dir, found, today, raw if incomplete else None)
    if not incomplete:
        import_documents.discard_kept_answers(data_dir)
    return ImportResult(written, stored, incomplete, kept, unchanged, not_replaced)


def _keeping_search_terms(files: dict[str, str], data_dir: pathlib.Path) -> tuple[dict[str, str], tuple[str, ...]]:
    """Terms added on the page of the app are unknown to the form; replacing must not lose them."""
    path = data_dir / search_plan.PROFILE
    if search_plan.PROFILE not in files or not path.is_file():
        return files, ()
    text, kept = search_terms.kept_on_replace(path.read_text(encoding="utf-8", errors="replace"), files[search_plan.PROFILE])
    return {**files, search_plan.PROFILE: text}, kept


def _keeping_cv_content(files: dict[str, str], bundle: dict, data_dir: pathlib.Path,
                        today: datetime.date) -> tuple[dict[str, str], tuple[str, ...]]:
    """The answers are merged into an existing CV; one that cannot be read stays as it was."""
    path = data_dir / CV
    if not path.is_file():
        return files, ()
    try:
        existing = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        existing = None
    new_cv = convert.build_cv(bundle["data"], bundle["track"], answer_keys=True)
    text = None if existing is None else cv_merge.merged_text(existing, new_cv, bundle["track"], convert.made_on(today))
    if text is None:
        return {rel: content for rel, content in files.items() if rel != CV}, (CV,)
    return {**files, CV: text}, ()


def _write_basics(form: dict, bundle: dict, data_dir: pathlib.Path, today: datetime.date, force: bool,
                  choice: MarkdownChoice | None) -> tuple[list[str], tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    files = convert.convert_bundle(form, bundle, today)
    merging = force or choice is not None
    files, unchanged = _keeping_cv_content(files, bundle, data_dir, today) if merging else (files, ())
    merged, kept = _keeping_search_terms(files, data_dir) if merging else (files, ())
    encoded = _encode(merged)
    existing = [rel for rel in encoded if im_ordner(data_dir, rel).exists()]
    if choice is not None:
        not_replaced = _not_replaced(choice, existing, merged, data_dir)
        encoded = {rel: content for rel, content in encoded.items() if rel not in not_replaced}
        existing = [rel for rel in existing if rel not in not_replaced]
        kept = kept if search_plan.PROFILE in encoded else ()
    elif existing and not force:
        raise ImportRejected([f"Diese Dateien gibt es schon: {', '.join(existing)}. "
                              "Zum Ersetzen mit --force aufrufen; der alte Stand bleibt als Entwurf erhalten."])
    else:
        not_replaced = ()
    data_dir.mkdir(parents=True, exist_ok=True)
    if existing:
        sichere(data_dir, existing, DRAFT_BEFORE)
    for rel, content in encoded.items():
        schreibe_atomar(im_ordner(data_dir, rel), content)
    sichere(data_dir, list(encoded), DRAFT_AFTER)
    return list(encoded), kept, unchanged, not_replaced


def _not_replaced(choice: MarkdownChoice, existing: list[str], merged: dict[str, str],
                  data_dir: pathlib.Path) -> tuple[str, ...]:
    """The existing Markdown files that stay as they are; without a choice they are refused with their diffs."""
    present = [rel for rel in existing if rel in MARKDOWN]
    if choice.replace is None and present:
        raise ExistingFiles([CHOOSE_PER_FILE.format(files=", ".join(present))],
                            [_file_diff(rel, merged[rel], data_dir) for rel in present])
    return tuple(rel for rel in present if rel not in (choice.replace or frozenset()))


def _file_diff(rel: str, new: str, data_dir: pathlib.Path) -> dict:
    old = im_ordner(data_dir, rel).read_text(encoding="utf-8", errors="replace")
    return {"datei": rel, "titel": MARKDOWN_TITLES[rel], "zeilen": line_diff(old, new)}


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
        print("Unverändert gelassen, weil sie sich nicht lesen lassen:",
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
