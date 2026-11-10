"""Applying through a company's form (MIN-346): what may be opened, the values for the fields, the files to upload.

The extension fills a form only for applications the person chose in the app, and it never sends one: a dispatch
is recorded when the person says it happened. The values stay on this computer and in the person's own browser.
"""
import hashlib
import itertools
import mimetypes
import pathlib
import re
import shutil
from dataclasses import dataclass

import yaml

import certificates
import letter_approval
import form_copy
import merged_pdf
from ai.personal import strip_titles
from hits import company_key
from dateien import schreibe_atomar
from pruefung import SURNAME_PARTICLES
from unterlagen import wirksame_pdfs

MAX_PER_RUN = 5
OPEN_STATUS = ("Gemerkt", "Bewerben")
RUNNING_STATUS = ("Beworben", "Gespräch")
PART_BYTES = 699_000  # a multiple of 3: the Base64 of the parts can be joined; stays below the host's limit of 1 MB
WEB_LINK = re.compile(r"^https?://", re.IGNORECASE)
SWISS_POSTAL_CODE = re.compile(r"^[1-9]\d{3}$")
BLOCKS_FILE = "anschreiben/bausteine.md"
FRAME_LINE = re.compile(r"^-\s*(Verfügbar ab|Kündigungsfrist|Lohnvorstellung)\s*:\s*(.+?)\s*$", re.MULTILINE)
FRAME_KEYS = {"Verfügbar ab": "availability", "Kündigungsfrist": "notice", "Lohnvorstellung": "salary"}
REFERENCES_FOLDER = merged_pdf.REFERENCES_FOLDER
REFERENCE_KEY_LENGTH = 12
ALREADY_SENT = "Schon versendet"
NOT_OPEN = "Status „{status}“"
NO_LINK = "Kein Link zum Formular: öffnen und Link eintragen"
NO_CV = "Lebenslauf-PDF fehlt: öffnen und „Unterlagen erstellen“ oder unter „Meine Dateien“ hochladen"
NOT_APPROVED = "Anschreiben noch nicht freigegeben: öffnen, lesen und „Freigeben“"
UNKNOWN_FILE = "Diese Datei gehört nicht zu dieser Bewerbung."
UNKNOWN_PART = "Dieser Teil der Datei fehlt."
NO_FILES = "Für diese Bewerbung gibt es noch keine Dateien. Bitte zuerst „Unterlagen erstellen“ oder unter „Meine Dateien“ hochladen."
FOLDER_FAILED = "Der Ordner liess sich nicht vorbereiten. Bitte nochmals versuchen."


@dataclass(frozen=True)
class Upload:
    path: pathlib.Path
    name: str


def form_link(entry: dict) -> str | None:
    """Where the form is: its own link if there is one, otherwise the ad."""
    for link in (entry.get("formular_link"), entry.get("link")):
        if isinstance(link, str) and WEB_LINK.match(link):
            return link
    return None


def blocker(data_dir: pathlib.Path, entry: dict) -> str | None:
    """Why this application cannot be opened, as far as it shows without reading the PDFs."""
    if entry.get("versand"):
        return ALREADY_SENT
    if entry.get("status") not in OPEN_STATUS:
        return NOT_OPEN.format(status=entry.get("status"))
    if not form_link(entry):
        return NO_LINK
    if not wirksame_pdfs(data_dir, entry)["lebenslauf"].is_file():
        return NO_CV
    if letter_approval.missing(data_dir, entry):  # MIN-369: no AI letter goes out unread
        return NOT_APPROVED
    return None


def duplicates(everyone: list[dict], chosen: list[dict]) -> list[dict]:
    """Where the person already applied at this company, or is about to do so twice in one run."""
    found = []
    for entry in chosen:
        key = company_key(entry.get("firma"))
        if not key:
            continue
        others = [b for b in everyone if b["id"] != entry["id"] and company_key(b.get("firma")) == key
                  and (b.get("status") in RUNNING_STATUS or b in chosen)]
        found += [{"id": entry["id"], "firma": entry.get("firma"), "stelle": other.get("stelle"),
                   "status": other.get("status")} for other in others]
    return found


def _split_name(full_name: str) -> tuple[str, str]:
    """„Hans von Allmen“ → Hans, von Allmen; „Anna Maria Muster“ → Anna Maria, Muster."""
    words = strip_titles(full_name).split()
    if len(words) < 2:
        return ("", words[0] if words else "")
    start = next((i for i, w in enumerate(words) if i > 0 and w.lower() in SURNAME_PARTICLES), len(words) - 1)
    return " ".join(words[:start]), " ".join(words[start:])


def _profile_links(basics: dict) -> dict[str, str]:
    found = {}
    for profile in basics.get("profiles") or []:
        network = str(profile.get("network", "")).lower() if isinstance(profile, dict) else ""
        if network in ("linkedin", "github") and profile.get("url"):
            found[network] = str(profile["url"])
    return found


def _read_cv(data_dir: pathlib.Path) -> dict:
    path = data_dir / "cv.yaml"
    if not path.is_file():
        return {}  # whoever only uploaded their files fills in the form themselves
    cv = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    basics = cv.get("basics") if isinstance(cv, dict) else None
    if not isinstance(basics, dict):
        raise ValueError("Im Lebenslauf fehlen die Angaben zur Person.")
    return basics


def _frame_values(data_dir: pathlib.Path) -> dict[str, str]:
    path = data_dir / BLOCKS_FILE
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    return {FRAME_KEYS[label]: value for label, value in FRAME_LINE.findall(text)}


def form_values(data_dir: pathlib.Path) -> dict[str, str]:
    """What rules may put into a form, only from the person's own files; empty values are left out."""
    basics = _read_cv(data_dir)
    location = basics.get("location") if isinstance(basics.get("location"), dict) else {}
    full_name = str(basics.get("name") or "")
    first_name, last_name = _split_name(full_name)
    postal_code = str(location.get("postalCode") or "")
    city = str(location.get("city") or "")
    values = {"full_name": strip_titles(full_name), "first_name": first_name, "last_name": last_name,
              "last_first": f"{last_name}, {first_name}" if first_name else last_name,
              "postal_city": f"{postal_code} {city}".strip(),
              "email": basics.get("email"), "phone": basics.get("phone"), "street": location.get("address"),
              "postal_code": postal_code, "city": location.get("city"),
              "country": "Schweiz" if SWISS_POSTAL_CODE.match(postal_code) else None,
              "website": basics.get("url"), **_profile_links(basics), **_frame_values(data_dir)}
    return {key: str(value) for key, value in values.items() if value}


def _reference_key(rel: str) -> str:
    """From the file, not its place in the list: a form asks later, and the list can have changed by then."""
    return f"zeugnis-{hashlib.sha256(rel.encode('utf-8')).hexdigest()[:REFERENCE_KEY_LENGTH]}"


def uploads(data_dir: pathlib.Path, entry: dict) -> dict[str, Upload]:
    """The files of this application by key; only these can be asked for."""
    found = {kind: Upload(path, certificates.upload_name(data_dir, kind.capitalize(), ".pdf"))
             for kind, path in wirksame_pdfs(data_dir, entry).items() if path.is_file()}
    packed = certificates.zip_path(data_dir, entry["id"])
    if packed.is_file():
        found["zertifikate"] = Upload(packed, certificates.upload_name(data_dir))
    references = certificates.files_in(data_dir, REFERENCES_FOLDER)
    joined = {key: Upload(form_copy.copy_path(data_dir, entry["id"], key),  # exists once a form or person asks for it
                          certificates.upload_name(data_dir, merged_pdf.label(data_dir, entry, key), ".pdf"))
               for key in merged_pdf.offered(data_dir, entry)}
    return found | {_reference_key(rel): Upload(data_dir / rel, pathlib.PurePath(rel).name) for rel in references} | joined


def describe_uploads(files: dict[str, Upload]) -> list[dict]:
    return [{"schluessel": key, "name": upload.name} for key, upload in files.items()]


def handed_over(data_dir: pathlib.Path, entry: dict, key: str, upload: Upload, part: int) -> Upload:
    """What this request reads from. The first part keeps a copy, the others read it: all parts are one version.

    Call with the lock held."""
    copy = form_copy.copy_path(data_dir, entry["id"], key)
    if copy is None:
        return upload
    if part == 0 and key in merged_pdf.KEYS:
        return Upload(merged_pdf.keep(data_dir, entry, key), upload.name)
    if part == 0:
        return Upload(form_copy.keep(data_dir, entry["id"], key, upload.path), upload.name)
    if not copy.is_file():
        raise ValueError(UNKNOWN_PART)
    return Upload(copy, upload.name)


@dataclass(frozen=True)
class HandFolder:
    path: pathlib.Path
    names: list[str]
    notes: list[str]


def _file_for_hand(data_dir: pathlib.Path, entry: dict, key: str, upload: Upload) -> bytes:
    return merged_pdf.build(merged_pdf.sources(data_dir, entry)[key]) if key in merged_pdf.KEYS else upload.path.read_bytes()


def _free_name(name: str, taken: list[str]) -> str:
    """A reference may be called like a generated file: both stay, and file systems may ignore case."""
    used = {other.casefold() for other in taken}
    path = pathlib.PurePath(name)
    candidates = itertools.chain([name], (f"{path.stem} ({n}){path.suffix}" for n in itertools.count(2)))
    return next(candidate for candidate in candidates if candidate.casefold() not in used)


def prepare_folder(data_dir: pathlib.Path, entry: dict) -> HandFolder:
    """All files of this application as they count now, with their names for the employer. Call with the lock held."""
    files = uploads(data_dir, entry)
    if not files:
        raise ValueError(NO_FILES)
    folder = form_copy.hand_folder(data_dir, entry["id"])
    names, notes = [], []
    try:
        if folder.is_dir():
            shutil.rmtree(folder)
        folder.mkdir(parents=True)
        for key, upload in files.items():
            try:
                name = _free_name(upload.name, names)
                schreibe_atomar(folder / name, _file_for_hand(data_dir, entry, key, upload))
                names.append(name)
            except ValueError as error:  # the joined PDF is a help; the single files are still there
                notes.append(str(error))
    except OSError as error:
        raise ValueError(FOLDER_FAILED) from error
    return HandFolder(folder, names, notes)


def read_part(upload: Upload, part: int) -> tuple[bytes, int]:
    """One part of a file and how many there are; an empty file has one empty part."""
    size = upload.path.stat().st_size
    parts = max(1, (size + PART_BYTES - 1) // PART_BYTES)
    if not 0 <= part < parts:
        raise ValueError(UNKNOWN_PART)
    with upload.path.open("rb") as stream:
        stream.seek(part * PART_BYTES)
        return stream.read(PART_BYTES), parts


def content_type(name: str) -> str:
    return mimetypes.guess_type(name)[0] or "application/octet-stream"
