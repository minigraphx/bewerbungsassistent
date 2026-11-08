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
# the person's own decision; the place is personal; a free text replaces what the documents give field by field (G25)
LEFT_OUT_FIELDS = {"style": {"address", "place"}, "education": {"text"}, "certificates": {"text"}}
LEFT_OUT_TYPES = {"tags"}  # tags choose what goes into which version of the CV: the person's own decision (G24)
APPRENTICESHIP = "apprenticeship"
MAX_PLACE_CHARS = 100
MAX_SUSPICIOUS_LINES = 20
MAX_SUSPICIOUS_CHARS = 300
NO_DOCUMENTS = "Zuerst Unterlagen hochladen."
NO_NAME = ("Zuerst den Namen unter „Person und Kontakt“ eintragen: So erkennt die App ihn in den Unterlagen "
           "und schickt ihn nicht an die KI.")
BROKEN_CV = "cv.yaml lässt sich nicht lesen."
UNKNOWN_TRACK = "Unbekannte Art der Suche."
SINGLE_ENTRY = "ein Eintrag"
MANY_ENTRIES = "ein Eintrag pro Station"
SEVERAL_VALUES = "mehrere Werte, pro Wert ein Paar"
ONLY_VALUES = "nur: {values}"


def _fields(section: dict, track: str) -> list[dict]:
    left_out = LEFT_OUT_FIELDS.get(section["id"], set())
    return [f for f in section["fields"]
            if validation.applies(f, track) and f["id"] not in left_out and f["type"] not in LEFT_OUT_TYPES]


def _sections(form: dict, track: str) -> list[dict]:
    return [s for s in form["sections"] if s["id"] in SECTIONS and validation.applies(s, track)]


def _field_guide(field: dict, track: str) -> str:
    if field["type"] == "list":
        return f"{field['id']} ({SEVERAL_VALUES})"
    if field["type"] == "select":
        return f"{field['id']} ({ONLY_VALUES.format(values=', '.join(validation.for_track(field['options'], track)))})"
    return field["id"]


def field_guide(form: dict, track: str) -> str:
    """Sections and fields of the form for the instructions. They cannot be in the schema of the answer: a schema with
    every field is too large for the API ("compiled grammar is too large"). `clean_answer` holds answers to the form."""
    lines = []
    for section in _sections(form, track):
        amount = MANY_ENTRIES if section.get("repeat") else SINGLE_ENTRY
        fields = ", ".join(_field_guide(field, track) for field in _fields(section, track))
        lines = [*lines, f"- {section['id']} ({amount}): {fields}"]
    return "\n".join(lines)


def _entry_values(entry: dict, section: dict, track: str) -> dict:
    """One entry of the answer as {field: value}; a list field collects its values, otherwise the first value counts."""
    kinds = {field["id"]: field["type"] for field in _fields(section, track)}
    pairs = entry.get("fields") if isinstance(entry.get("fields"), list) else []
    values: dict = {}
    for pair in pairs:
        name = pair.get("field") if isinstance(pair, dict) else None
        if name not in kinds:
            continue
        value = _text(pair.get("value"))
        if kinds[name] == "list":
            values = {**values, name: [*values.get(name, []), value]}
        elif name not in values:
            values = {**values, name: value}
    return {**values, "source": entry.get("source")}


def from_entries(form: dict, track: str, answer: dict) -> dict:
    """The flat answer of the AI as sections: a list per repeating section, one set of values otherwise."""
    sections = {section["id"]: section for section in _sections(form, track)}
    entries = answer.get("entries") if isinstance(answer.get("entries"), list) else []
    result: dict = {}
    for entry in entries:
        section = sections.get(entry.get("section")) if isinstance(entry, dict) else None
        if section is None:
            continue
        values = _entry_values(entry, section, track)
        if section.get("repeat"):
            result = {**result, section["id"]: [*result.get(section["id"], []), values]}
        elif section["id"] not in result:
            result = {**result, section["id"]: values}
    return result


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
            "url": _text(person.get("url")),
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
    answer = tasks.suggest_from_documents(gateway, prompt, field_guide(form, track))
    files = [t.name for t in reading.texts]
    suggestions, dropped = clean_answer(form, track, from_entries(form, track, answer), files)
    return {**result, "suggestions": suggestions, "dropped": dropped, "read": files,
            "datei": [t.datei for t in reading.texts], "shortened": [t.name for t in reading.texts if t.shortened],
            "suspicious_lines": _suspicious(answer), "cost_usd": answer.get("cost_usd")}
