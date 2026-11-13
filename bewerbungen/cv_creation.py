"""Creating a CV on the page of an application (G17, #118): content from Meine Angaben, the design apart from it.

The person picks the stations of `cv.yaml` and their order, the job title and the summary. That becomes a tailoring
`jobs/<variant>.yaml` (`select` and `basics`, read by `lebenslauf/tailor.py`) and a variant in `varianten.yaml`, then
the application takes it like any variant. The design goes to the application as `lebenslauf_design` (G61), never
into the tailoring. `created_for` marks the tailoring as the application's own, so saving again replaces it and a
variant Claude wrote under the same name stays untouched.
"""
import dataclasses
import hashlib
import pathlib

import yaml

import cv_design
from dateien import schreibe_yaml
from register import CV_DESIGNS
from varianten import Varianten

# The sections of a JSON Resume whose entries are stations, in the order the page shows them.
SECTIONS = {"work": "Berufserfahrung", "education": "Bildung und Weiterbildung", "teaching": "Lehre und Training",
            "projects": "Projekte", "volunteer": "Freiwilligenarbeit", "certificates": "Zertifikate",
            "awards": "Auszeichnungen", "publications": "Publikationen"}
IDENTITY = ("position", "name", "institution", "studyType", "area", "title", "organization", "issuer", "awarder",
            "publisher", "startDate", "endDate", "date")
TITLE = ("position", "studyType", "title", "name")
SUBTITLE = ("name", "institution", "organization", "issuer", "awarder", "publisher")
JOBS = "jobs"
MAX_TEXT = 2000
MAX_NAME = 120
HEADER = "# Lebenslauf für eine Bewerbung, erstellt auf ihrer Seite (G17). Geschrieben vom Bewerbungsbegleiter.\n"

NO_CV = "Noch keine Angaben. Bitte zuerst „Meine Angaben“ ausfüllen."
UNREADABLE = "Meine Angaben lassen sich nicht lesen. Bitte unter „Meine Angaben“ prüfen."
CHANGED = "Meine Angaben haben sich inzwischen geändert. Bitte „Lebenslauf erstellen“ neu öffnen."
NOTHING_CHOSEN = "Bitte mindestens eine Station wählen."
WRONG_STATION = "Diese Station gibt es in Meinen Angaben nicht. Bitte „Lebenslauf erstellen“ neu öffnen."


@dataclasses.dataclass(frozen=True)
class Choice:
    stations: dict[str, tuple[int, ...]]
    label: str
    summary: str
    design: str
    name: str


def load_cv(data_dir: pathlib.Path) -> tuple[dict, str]:
    """`cv.yaml` and its fingerprint, which tells whether it changed between opening and saving."""
    path = data_dir / "cv.yaml"
    if not path.is_file():
        raise ValueError(NO_CV)
    raw = path.read_bytes()
    try:
        cv = yaml.safe_load(raw)
    except yaml.YAMLError as error:
        raise ValueError(UNREADABLE) from error
    if not isinstance(cv, dict):
        raise ValueError(UNREADABLE)
    return cv, hashlib.sha256(raw).hexdigest()[:16]


def _text(value: object) -> str:
    """A field as one German text; multilingual fields are {de: …, en: …}."""
    if isinstance(value, dict):
        value = value.get("de") or next(iter(value.values()), "")
    return "" if value is None else str(value).strip()


def _sections(cv: dict) -> dict[str, list]:
    return {name: cv[name] for name in SECTIONS if isinstance(cv.get(name), list) and cv[name]}


def identity(entry: object) -> dict:
    """The fields that find a station again in `cv.yaml` (tailor's `select`)."""
    if not isinstance(entry, dict):
        return {}
    return {key: entry[key] for key in IDENTITY if entry.get(key) not in (None, "")}


def _title(entry: dict) -> str:
    if entry.get("studyType") or entry.get("area"):
        return " ".join(part for part in (_text(entry.get("studyType")), _text(entry.get("area"))) if part)
    return next((_text(entry[key]) for key in TITLE if _text(entry.get(key))), "")


def _subtitle(entry: dict, title: str) -> str:
    return next((_text(entry[key]) for key in SUBTITLE if _text(entry.get(key)) and _text(entry[key]) != title), "")


def _date(value: object) -> str:
    """„2019-03“ as „03.2019“, a year as it is."""
    text = _text(value)
    parts = text.split("-")
    return f"{parts[1]}.{parts[0]}" if len(parts) >= 2 and all(part.isdigit() for part in parts[:2]) else text


def _time(entry: dict) -> str:
    if entry.get("x-display"):
        return _text(entry["x-display"])
    start, end = _date(entry.get("startDate")), _date(entry.get("endDate"))
    if start:
        return f"{start} – {end or 'heute'}"
    return _date(entry.get("date"))


def _chosen_indices(entries: list, wanted: object) -> list[int]:
    """The indices tailor's `select` takes, in its order; every station when the tailoring names none."""
    if not isinstance(wanted, list):
        return list(range(len(entries)))
    taken: list[int] = []
    for fields in wanted:
        match = next((i for i, entry in enumerate(entries)
                      if i not in taken and isinstance(fields, dict) and isinstance(entry, dict)
                      and all(entry.get(k) == v for k, v in fields.items())), None)
        if match is not None:
            taken.append(match)
    return taken


def _station_rows(entries: list, chosen: list[int]) -> list[dict]:
    order = chosen + [i for i in range(len(entries)) if i not in chosen]

    def row(index: int) -> dict:
        entry = entries[index] if isinstance(entries[index], dict) else {}
        title = _title(entry) or f"Eintrag {index + 1}"
        return {"index": index, "titel": title, "zusatz": _subtitle(entry, title), "zeit": _time(entry),
                "gewaehlt": index in chosen}

    return [row(index) for index in order]


def job_path(data_dir: pathlib.Path, variant_id: str) -> pathlib.Path:
    return data_dir / JOBS / f"{variant_id}.yaml"


def _read_job(path: pathlib.Path) -> dict:
    try:
        job = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else None
    except (OSError, yaml.YAMLError):
        return {}
    return job if isinstance(job, dict) else {}


def own_variant(data_dir: pathlib.Path, entry_id: str) -> dict | None:
    """The variant created on this application's page earlier, if any."""
    for variant in Varianten(data_dir).alle():
        if variant.get("quelle") != f"{JOBS}/{variant['id']}.yaml":
            continue
        if _read_job(job_path(data_dir, variant["id"])).get("created_for") == entry_id:
            return variant
    return None


def variant_id_for(data_dir: pathlib.Path, entry_id: str) -> str:
    """The application's own variant again, otherwise the first free name: never one Claude wrote."""
    own = own_variant(data_dir, entry_id)
    if own:
        return own["id"]
    taken = {variant["id"] for variant in Varianten(data_dir).alle()}
    candidates = (entry_id if number == 1 else f"{entry_id}-{number}" for number in range(1, 1000))
    return next(c for c in candidates if c not in taken and not job_path(data_dir, c).exists())


def form(data_dir: pathlib.Path, entry: dict) -> dict:
    """What the page shows: the stations (chosen first, in their order), title, summary, design and name."""
    cv, stand = load_cv(data_dir)
    own = own_variant(data_dir, entry["id"])
    job = _read_job(job_path(data_dir, own["id"])) if own else {}
    select = job.get("select") if isinstance(job.get("select"), dict) else {}
    basics = cv.get("basics") if isinstance(cv.get("basics"), dict) else {}
    own_basics = job.get("basics") if isinstance(job.get("basics"), dict) else {}
    parts = [{"abschnitt": name, "titel": SECTIONS[name],
              "stationen": _station_rows(entries, _chosen_indices(entries, select.get(name)))}
             for name, entries in _sections(cv).items()]
    return {"abschnitte": parts, "stand": stand,
            "berufsbezeichnung": _text(own_basics.get("label", basics.get("label"))),
            "kurzprofil": _text(own_basics.get("summary", basics.get("summary"))),
            "design": cv_design.for_application(data_dir, entry), "designs": list(CV_DESIGNS),
            "bezeichnung": (own or {}).get("beschreibung") or f"{entry.get('stelle', '')}, {entry.get('firma', '')}",
            "eigene_variante": own["id"] if own else None}


def _indices(value: object, count: int) -> tuple[int, ...]:
    if not isinstance(value, list) or not all(isinstance(i, int) and not isinstance(i, bool) for i in value):
        raise ValueError(WRONG_STATION)
    if any(i < 0 or i >= count for i in value) or len(set(value)) != len(value):
        raise ValueError(WRONG_STATION)
    return tuple(value)


def _string(body: dict, key: str, limit: int, label: str) -> str:
    value = body.get(key, "")
    if not isinstance(value, str):
        raise ValueError(f"{label} muss ein Text sein.")
    if len(value) > limit:
        raise ValueError(f"{label} ist zu lang, höchstens {limit} Zeichen.")
    return value.strip()


def parse(cv: dict, stand: str, body: dict) -> Choice:
    """The choice as the page sends it; ValueError with a German message, before anything is written."""
    if body.get("stand") != stand:
        raise ValueError(CHANGED)
    sections = _sections(cv)
    wanted = body.get("stationen")
    if not isinstance(wanted, dict) or not set(wanted) <= set(sections):
        raise ValueError(WRONG_STATION)
    stations = {name: _indices(value, len(sections[name])) for name, value in wanted.items()}
    if not any(stations.values()):
        raise ValueError(NOTHING_CHOSEN)
    return Choice(stations=stations, label=_string(body, "berufsbezeichnung", MAX_NAME, "Die Berufsbezeichnung"),
                  summary=_string(body, "kurzprofil", MAX_TEXT, "Das Kurzprofil"),
                  design=cv_design.parse(body.get("design")),
                  name=_string(body, "bezeichnung", MAX_NAME, "Der Name der Fassung"))


def tailoring(cv: dict, entry_id: str, choice: Choice) -> dict:
    """The tailoring for lebenslauf/tailor.py; the design stays out of it."""
    sections = _sections(cv)
    return {"created_for": entry_id, "basics": {"label": choice.label, "summary": choice.summary},
            "select": {name: [identity(sections[name][i]) for i in indices]
                       for name, indices in choice.stations.items()}}


def write_tailoring(path: pathlib.Path, job: dict) -> None:
    schreibe_yaml(path, job, HEADER)


def variant(variant_id: str, entry: dict, choice: Choice) -> dict:
    return {"id": variant_id, "quelle": f"{JOBS}/{variant_id}.yaml",
            "beschreibung": choice.name or f"{entry.get('stelle', '')}, {entry.get('firma', '')}"}
