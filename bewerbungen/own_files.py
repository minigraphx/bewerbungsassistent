"""Files the person uploads and uses as they are: a finished CV as PDF, certificates, references (MIN-346).

The CV counts for every application without a chosen variant (`unterlagen.wirksame_pdfs`). Certificates and references
live in the same folders as those uploaded under „Meine Angaben“. None of this goes to the AI.
"""
import pathlib
import re
import unicodedata

import certificates
from apply import REFERENCES_FOLDER
from unterlagen import OWN_CV

CV_KIND = "lebenslauf"
CERTIFICATE_KIND = "zertifikat"
REFERENCE_KIND = "zeugnis"
FOLDERS = {CERTIFICATE_KIND: certificates.FOLDER, REFERENCE_KIND: REFERENCES_FOLDER}
KINDS = (CV_KIND, *FOLDERS)
CV_FILE = OWN_CV
MAX_FILE_BYTES = 15_000_000  # as for uploads under „Meine Angaben“ (onboarding/form.json)
MAX_STEM = 100
PDF_SEARCH_BYTES = 1024  # some PDFs start with a few bytes before the marker; readers accept them

TYPES = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
SIGNATURES = {"image/jpeg": b"\xff\xd8\xff", "image/png": b"\x89PNG\r\n\x1a\n"}
PDF_MARKER = b"%PDF-"
UNSAFE = re.compile(r'[\x00-\x1f\x7f<>:"|?*]')
RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{n}" for n in range(1, 10)), *(f"LPT{n}" for n in range(1, 10))}

UNKNOWN_KIND = "Unbekannte Art von Datei."
BAD_NAME = "Dieser Dateiname geht nicht. Bitte die Datei umbenennen."
CV_ONLY_PDF = "Der Lebenslauf muss ein PDF sein."
ONLY_THESE_TYPES = "Möglich sind PDF, JPG und PNG."
NOT_WHAT_IT_SAYS = "Diese Datei ist kein echtes {typ}. Vielleicht wurde sie nur umbenannt."
TOO_LARGE = "Die Datei ist zu gross, höchstens {mb} MB."
NOT_THERE = "Diese Datei gibt es nicht (mehr)."
CANNOT_SHOW = "Diese Datei lässt sich hier nicht anzeigen."


def clean_name(raw: object) -> str:
    """Only the last part of what the browser names, without characters that some systems refuse."""
    if not isinstance(raw, str):
        raise ValueError(BAD_NAME)
    last = unicodedata.normalize("NFC", re.split(r"[\\/]", raw)[-1])
    name = UNSAFE.sub("", last).strip(" .")
    path = pathlib.PurePosixPath(name)
    # Windows treats NUL.x.pdf and "CON .pdf" as the device, whatever follows the first dot.
    if not path.stem or len(path.stem) > MAX_STEM or name.split(".")[0].strip().upper() in RESERVED:
        raise ValueError(BAD_NAME)
    return name


def _is_type(content_type: str, data: bytes) -> bool:
    if content_type == TYPES[".pdf"]:
        return PDF_MARKER in data[:PDF_SEARCH_BYTES]
    return data.startswith(SIGNATURES[content_type])


def check_upload(kind: object, name: str, data: bytes) -> None:
    """Fail unless this file may be kept; what it claims to be is compared with what it is."""
    if kind not in KINDS:
        raise ValueError(UNKNOWN_KIND)
    suffix = pathlib.PurePosixPath(name).suffix.lower()
    if kind == CV_KIND and suffix != ".pdf":
        raise ValueError(CV_ONLY_PDF)
    if suffix not in TYPES:
        raise ValueError(ONLY_THESE_TYPES)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(TOO_LARGE.format(mb=MAX_FILE_BYTES // 1_000_000))
    if not _is_type(TYPES[suffix], data):
        raise ValueError(NOT_WHAT_IT_SAYS.format(typ=suffix[1:].upper()))


def _same_name_key(name: str) -> str:
    return unicodedata.normalize("NFC", name).casefold()


def relative_target(data_dir: pathlib.Path, kind: str, name: str) -> str:
    """Where a checked upload belongs, relative to the data folder. macOS and Windows see a.pdf and A.pdf as one file,
    so a file of that name keeps its path, and with it its place in what the person chose for an application."""
    if kind == CV_KIND:
        return CV_FILE
    existing = certificates.files_in(data_dir, FOLDERS[kind])
    wanted = _same_name_key(name)
    same = (rel for rel in existing if _same_name_key(pathlib.PurePosixPath(rel).name) == wanted)
    return next(same, f"{FOLDERS[kind]}/{name}")


def _describe(data_dir: pathlib.Path, rel: str) -> dict:
    return {"datei": rel, "name": pathlib.PurePosixPath(rel).name, "groesse": (data_dir / rel).stat().st_size}


def listing(data_dir: pathlib.Path) -> dict[str, list[dict]]:
    """What is there, by kind."""
    cv = [CV_FILE] if (data_dir / CV_FILE).is_file() else []
    in_folders = {kind: certificates.files_in(data_dir, folder) for kind, folder in FOLDERS.items()}
    return {kind: [_describe(data_dir, rel) for rel in files] for kind, files in {CV_KIND: cv, **in_folders}.items()}


def checked_listed(data_dir: pathlib.Path, rel: object) -> pathlib.Path:
    """A path from a request only ever leads to a file of the list."""
    known = {entry["datei"] for entries in listing(data_dir).values() for entry in entries}
    if not isinstance(rel, str) or rel not in known:
        raise ValueError(NOT_THERE)
    return data_dir / rel


def content_type_to_show(path: pathlib.Path) -> str:
    """Older files in the folders can be of any type; a page must never run from there."""
    found = TYPES.get(path.suffix.lower())
    if found is None:
        raise ValueError(CANNOT_SHOW)
    return found


def chosen_by_unsent(entries: list[dict], rel: str) -> list[dict]:
    """Applications not yet sent whose certificates include this file."""
    return [entry for entry in entries if not entry.get("versand") and rel in (entry.get("zertifikate") or [])]
