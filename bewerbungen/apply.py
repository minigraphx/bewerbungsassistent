"""Applying through a company's form (MIN-346): what may be opened, the values for the fields, the files to upload.

The extension fills a form only for applications the person chose in the app, and it never sends one: a dispatch
is recorded when the person says it happened. The values stay on this computer and in the person's own browser.
"""
import mimetypes
import pathlib
import re
from dataclasses import dataclass

import yaml

import certificates
from ai.personal import strip_titles
from hits import company_key
from pruefung import SURNAME_PARTICLES
from unterlagen import pdf_pfade

MAX_PER_RUN = 5
OPEN_STATUS = ("Gemerkt", "Bewerben")
RUNNING_STATUS = ("Beworben", "Gespräch")
PART_BYTES = 699_000  # a multiple of 3: the Base64 of the parts can be joined; stays below the host's limit of 1 MB
WEB_LINK = re.compile(r"^https?://", re.IGNORECASE)
SWISS_POSTAL_CODE = re.compile(r"^[1-9]\d{3}$")
BLOCKS_FILE = "anschreiben/bausteine.md"
FRAME_LINE = re.compile(r"^-\s*(Verfügbar ab|Kündigungsfrist|Lohnvorstellung)\s*:\s*(.+?)\s*$", re.MULTILINE)
FRAME_KEYS = {"Verfügbar ab": "availability", "Kündigungsfrist": "notice", "Lohnvorstellung": "salary"}
REFERENCES_FOLDER = "dokumente/zeugnisse"
ALREADY_SENT = "Schon versendet"
NOT_OPEN = "Status „{status}“"
NO_LINK = "Kein Link zum Formular"
NO_CV = "Lebenslauf-PDF fehlt"
UNKNOWN_FILE = "Diese Datei gehört nicht zu dieser Bewerbung."
UNKNOWN_PART = "Dieser Teil der Datei fehlt."


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
    if not pdf_pfade(data_dir, entry["id"])["lebenslauf"].is_file():
        return NO_CV
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
    cv = yaml.safe_load((data_dir / "cv.yaml").read_text(encoding="utf-8")) or {}
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


def uploads(data_dir: pathlib.Path, application_id: str) -> dict[str, Upload]:
    """The files of this application by key; only these can be asked for."""
    found = {kind: Upload(path, certificates.upload_name(data_dir, kind.capitalize(), ".pdf"))
             for kind, path in pdf_pfade(data_dir, application_id).items() if path.is_file()}
    packed = certificates.zip_path(data_dir, application_id)
    if packed.is_file():
        found["zertifikate"] = Upload(packed, certificates.upload_name(data_dir))
    references = certificates.files_in(data_dir, REFERENCES_FOLDER)
    return found | {f"zeugnis-{nr}": Upload(data_dir / rel, pathlib.PurePath(rel).name) for nr, rel in enumerate(references)}


def describe_uploads(files: dict[str, Upload]) -> list[dict]:
    return [{"schluessel": key, "name": upload.name} for key, upload in files.items()]


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
