"""Suggestions for the form from uploaded documents (MIN-367).

Reads the documents on this computer (`read_documents`), masks the person's values through the Gateway and
checks every answer against `form.json`: only known sections and fields, values that pass the same rules as
the form, each entry with a source. Nothing is saved here; the page shows the suggestions and the person
decides. Sections about the person's contact details and search wishes are not asked for at all.
"""
import pathlib

import yaml

import paths  # noqa: F401  (makes the module bewerbungen importable)
import read_documents
import validation
from ai import prompts, tasks
from ai.errors import AiError
from ai.gateway import Gateway
from ai.personal import people_secrets, secrets_from_building_blocks, secrets_from_cv, secrets_in_own_documents
from ai.pseudonym import Pseudonymizer, Secret
from ai.usage import UsageLog
from dateien import im_ordner, lies_yaml
from import_documents import pending_documents

SECTIONS = ("summary", "work", "education", "certificates", "languages", "skills", "interests", "strengths", "style")
LEFT_OUT_FIELDS = {"style": {"address", "place"}}  # the person's own decision; the place is personal
APPRENTICESHIP = "apprenticeship"
MAX_PLACE_CHARS = 100
MAX_SUSPICIOUS_LINES = 20
MAX_SUSPICIOUS_CHARS = 300
NO_DOCUMENTS = "Zuerst Unterlagen hochladen."
NO_NAME = ("Zuerst den Namen unter „Person und Kontakt“ eintragen: So erkennt der Assistent ihn in den Unterlagen "
           "und schickt ihn nicht an die KI.")
BROKEN_CV = "cv.yaml lässt sich nicht lesen."
UNKNOWN_TRACK = "Unbekannte Art der Suche."
_TEXT = {"type": "string"}


def _object(properties: dict) -> dict:
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def _fields(section: dict, track: str) -> list[dict]:
    left_out = LEFT_OUT_FIELDS.get(section["id"], set())
    return [f for f in section["fields"] if validation.applies(f, track) and f["id"] not in left_out]


def _sections(form: dict, track: str) -> list[dict]:
    return [s for s in form["sections"] if s["id"] in SECTIONS and validation.applies(s, track)]


def _field_schema(field: dict, track: str) -> dict:
    if field["type"] == "list":
        return {"type": "array", "items": _TEXT}
    if field["type"] == "select":
        return {"type": "string", "enum": [*validation.for_track(field["options"], track), ""]}
    return _TEXT


def build_schema(form: dict, track: str) -> dict:
    """JSON schema of the answer, from the form itself, so both stay the same."""
    source = _object({"document": {"type": "integer"}, "place": _TEXT})
    properties = {}
    for section in _sections(form, track):
        item = _object({**{f["id"]: _field_schema(f, track) for f in _fields(section, track)}, "source": source})
        properties[section["id"]] = {"type": "array", "items": item} if section.get("repeat") else item
    return _object({**properties, "suspicious_lines": {"type": "array", "items": _TEXT}})


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _as_cv(data: dict) -> dict:
    """The answers so far in the shape of cv.yaml, as far as they are personal; nothing here has to be complete."""
    person = data.get("person") if isinstance(data.get("person"), dict) else {}
    profiles = person.get("profiles") if isinstance(person.get("profiles"), list) else []
    birth = _text(person.get("birthDate"))
    education = data.get("education") if isinstance(data.get("education"), list) else []
    return {
        "basics": {
            "name": _text(person.get("name")), "email": _text(person.get("email")), "phone": _text(person.get("phone")),
            "location": {"address": _text(person.get("address")), "postalCode": _text(person.get("postalCode"))},
            "profiles": [{"url": url} for url in profiles if isinstance(url, str) and url.strip()],
            "details": [f"geboren {birth}"] if birth.strip() else [],
        },
        "education": [item for item in education if isinstance(item, dict)],
    }


def _section_text(data: dict, section: str, field: str) -> str:
    values = data.get(section) if isinstance(data.get(section), dict) else {}
    return _text(values.get(field)).strip()


def _person_secrets(data: dict, track: str) -> list[Secret]:
    minor = track == APPRENTICESHIP
    result = secrets_from_cv(_as_cv(data), minor=minor)
    nationality = _section_text(data, "person", "nationality")
    result += [Secret("NATIONALITY", nationality)] if nationality else []
    reference = _section_text(data, "frame", "reference").split(",")[0]
    result += people_secrets("REFERENCE", reference) if reference else []
    companion = _section_text(data, "searchApprenticeship", "companion").split(",")[0]
    return result + (people_secrets("COMPANION", companion) if companion else [])


def _existing_cv(data_dir: pathlib.Path) -> dict:
    """A broken cv.yaml stops the request: its personal values could not be masked."""
    try:
        cv = lies_yaml(im_ordner(data_dir, "cv.yaml"), {})
    except yaml.YAMLError as error:
        raise AiError(BROKEN_CV) from error
    return cv if isinstance(cv, dict) else {}


def _secrets(data_dir: pathlib.Path, track: str, data: dict, texts: list[str]) -> list[Secret]:
    existing = _existing_cv(data_dir)
    basics = existing.get("basics") if isinstance(existing.get("basics"), dict) else {}
    if not _section_text(data, "person", "name") and not _text(basics.get("name")).strip():
        raise AiError(NO_NAME)
    result = _person_secrets(data, track) + secrets_from_cv(existing, minor=track == APPRENTICESHIP)
    blocks = im_ordner(data_dir, "anschreiben/bausteine.md")
    if blocks.is_file():
        result += secrets_from_building_blocks(blocks.read_text(encoding="utf-8"))
    return result + secrets_in_own_documents(texts)


def _clean_list(form: dict, field: dict, value: object) -> tuple[list[str], int]:
    lines = [line.strip() for line in value if isinstance(line, str) and line.strip()] if isinstance(value, list) else []
    good = [line for line in lines if validation.check_text(form, field, None, " ".join(line.split())) is None]
    limit = field.get("maxItems", form["limits"]["listItems"])
    return [" ".join(line.split()) for line in good][:limit], len(lines) - len(good)


def _clean_values(form: dict, section: dict, track: str, raw: dict) -> tuple[dict, int]:
    values, dropped = {}, 0
    for field in _fields(section, track):
        value = raw.get(field["id"])
        if field["type"] == "list":
            lines, bad = _clean_list(form, field, value)
            dropped += bad
            if lines:
                values[field["id"]] = lines
            continue
        text = _text(value).strip()
        if not text:
            continue
        text = text if field["type"] == "textarea" else " ".join(text.split())
        if validation.check_text(form, field, track, text) is None:
            values[field["id"]] = text
        else:
            dropped += 1
    return values, dropped


def _clean_source(raw: object, files: list[str]) -> dict | None:
    if not isinstance(raw, dict) or type(raw.get("document")) is not int or not 1 <= raw["document"] <= len(files):
        return None
    return {"file": files[raw["document"] - 1], "place": " ".join(_text(raw.get("place")).split())[:MAX_PLACE_CHARS]}


def _clean_item(form: dict, section: dict, track: str, raw: object, files: list[str]) -> tuple[dict | None, int]:
    """(suggestion, values dropped). An entry without a real source, or without any value, is no suggestion."""
    if not isinstance(raw, dict):
        return None, 1
    values, dropped = _clean_values(form, section, track, raw)
    if not values:
        return None, dropped
    source = _clean_source(raw.get("source"), files)
    if source is None:
        return None, dropped + 1
    return {"values": values, "source": source}, dropped


def _clean_section(form: dict, section: dict, track: str, raw: object, files: list[str]) -> tuple[object, int]:
    if not section.get("repeat"):
        return _clean_item(form, section, track, raw, files) if raw else (None, 0)
    limit = section.get("maxItems", form["limits"]["repeatItems"])
    results = [_clean_item(form, section, track, item, files) for item in raw] if isinstance(raw, list) else []
    items = [item for item, _ in results if item][:limit]
    return items or None, sum(dropped for _, dropped in results)


def clean_answer(form: dict, track: str, answer: dict, files: list[str]) -> tuple[dict, int]:
    """Only what fits the form stays. Returns the suggestions per section and how many values were dropped."""
    suggestions, dropped = {}, 0
    for section in _sections(form, track):
        cleaned, bad = _clean_section(form, section, track, answer.get(section["id"]), files)
        dropped += bad
        if cleaned:
            suggestions[section["id"]] = cleaned
    return suggestions, dropped


def _suspicious(answer: dict) -> list[str]:
    lines = answer.get("suspicious_lines") if isinstance(answer.get("suspicious_lines"), list) else []
    return [line[:MAX_SUSPICIOUS_CHARS] for line in lines if isinstance(line, str)][:MAX_SUSPICIOUS_LINES]


def _kind(form: dict, category: str, track: str) -> str:
    known = {c["id"]: c["title"] for c in form["documents"]["categories"]}
    return validation.for_track(known.get(category, "Unterlage"), track)


def suggest(form: dict, data_dir: pathlib.Path, track: object, data: dict, new_client) -> dict:
    """Suggestions from the pending documents. `new_client` is called only when something is really sent."""
    if not isinstance(track, str) or track not in form["tracks"]:
        raise ValueError(UNKNOWN_TRACK)
    documents = pending_documents(data_dir)
    if not documents:
        raise AiError(NO_DOCUMENTS)
    reading = read_documents.collect_texts(data_dir, documents)
    skipped = [{"name": s.name, "reason": s.reason} for s in reading.skipped]
    result = {"suggestions": {}, "skipped": skipped, "read": [], "datei": [], "shortened": [], "dropped": 0,
              "suspicious_lines": [], "cost_usd": None}
    if not reading.texts:
        return result
    secrets = _secrets(data_dir, track, data, [t.text for t in reading.texts])
    gateway = Gateway(new_client(), Pseudonymizer(secrets), UsageLog(data_dir))
    prompt = prompts.prefill_prompt([(_kind(form, t.category, track), t.text) for t in reading.texts])
    answer = tasks.suggest_from_documents(gateway, prompt, build_schema(form, track))
    files = [t.name for t in reading.texts]
    suggestions, dropped = clean_answer(form, track, answer, files)
    return {**result, "suggestions": suggestions, "dropped": dropped, "read": files,
            "datei": [t.datei for t in reading.texts], "shortened": [t.name for t in reading.texts if t.shortened],
            "suspicious_lines": _suspicious(answer), "cost_usd": answer.get("cost_usd")}
