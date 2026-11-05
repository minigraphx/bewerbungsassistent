"""Read the ZIP saved by the onboarding template: `einstieg.json` plus documents under `dokumente/<art>/`.

The file is external input. Everything is checked before anything is written: only the expected entries,
names and types by the document rules in form.json (see documents.py), declared sizes against the limits
before reading, real sizes and CRCs while reading. Entries are read into memory, never extracted, so
names cannot reach outside the data folder.
"""
import dataclasses
import pathlib
import zipfile
import zlib

import documents
from rejected import ImportRejected

BUNDLE_NAME = "einstieg.json"
DOCUMENTS_DIR = "dokumente"
ZIP_MAGIC = b"PK\x03\x04"
FLAG_ENCRYPTED = 0x1
NOT_A_ZIP = "Die Datei ist keine gültige Einstiegsdatei (ZIP)."


@dataclasses.dataclass(frozen=True)
class Document:
    category: str
    name: str
    data: bytes

    @property
    def path(self) -> str:
        return f"{DOCUMENTS_DIR}/{self.category}/{self.name}"


@dataclasses.dataclass(frozen=True)
class Archive:
    bundle: bytes
    documents: tuple[Document, ...]


def is_zip(path: pathlib.Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(len(ZIP_MAGIC)) == ZIP_MAGIC
    except OSError:
        return False


def read_archive(path: pathlib.Path, form: dict, max_bundle_bytes: int) -> Archive:
    try:
        with zipfile.ZipFile(path) as zf:
            infos = [i for i in zf.infolist() if not i.is_dir()]
            _check_limits(form, infos, max_bundle_bytes)
            bundle_info, document_infos = _sort_entries(form, infos, max_bundle_bytes)
            bundle = _read(zf, bundle_info)
            found = tuple(Document(*_split(i.filename), _read(zf, i)) for i in document_infos)
    except (zipfile.BadZipFile, zlib.error, NotImplementedError, EOFError, OSError) as exc:
        raise ImportRejected([NOT_A_ZIP]) from exc
    return Archive(bundle, found)


def _check_limits(form: dict, infos: list[zipfile.ZipInfo], max_bundle_bytes: int) -> None:
    rules = form["documents"]
    max_entries = 1 + sum(c["maxFiles"] for c in rules["categories"])
    if len(infos) > max_entries:
        raise ImportRejected([f"Die Datei enthält zu viele Einträge (höchstens {max_entries})."])
    limit = rules["maxTotalBytes"] + max_bundle_bytes
    if sum(i.file_size for i in infos) > limit:
        raise ImportRejected([f"Der Inhalt ist zu gross (höchstens {limit // documents.BYTES_PER_MB} MB)."])
    if any(i.flag_bits & FLAG_ENCRYPTED for i in infos):
        raise ImportRejected(["Verschlüsselte ZIP-Dateien gehen nicht."])


def _split(name: str) -> tuple[str, str]:
    parts = name.split("/")
    if len(parts) != 3 or parts[0] != DOCUMENTS_DIR:
        raise ImportRejected([f"Unerwarteter Inhalt in der Datei: {name}"])
    return parts[1], parts[2]


def _sort_entries(form: dict, infos: list[zipfile.ZipInfo],
                  max_bundle_bytes: int) -> tuple[zipfile.ZipInfo, list[zipfile.ZipInfo]]:
    bundles = [i for i in infos if i.filename == BUNDLE_NAME]
    if len(bundles) != 1:
        raise ImportRejected([f"Die Datei muss genau eine {BUNDLE_NAME} enthalten."])
    if bundles[0].file_size > max_bundle_bytes:
        raise ImportRejected([f"Die {BUNDLE_NAME} ist zu gross (höchstens {max_bundle_bytes // 1000} KB)."])
    others = [i for i in infos if i.filename != BUNDLE_NAME]
    entries = []
    for info in others:
        category, name = _split(info.filename)
        entries.append({"category": category, "name": name, "size": info.file_size})
    errors = documents.validate_documents(form, entries)
    if errors:
        raise ImportRejected([documents.describe(form, "job", entries, e) for e in errors])
    return bundles[0], others


def _read(zf: zipfile.ZipFile, info: zipfile.ZipInfo) -> bytes:
    with zf.open(info) as handle:
        data = handle.read(info.file_size + 1)
    if len(data) != info.file_size:
        raise ImportRejected([f"Die Datei ist beschädigt ({info.filename})."])
    return data
