"""Validate onboarding bundles (`einstieg.json`) against the form definition `form.json`.

The bundle comes from outside (the HTML template, or a file someone edited), so every value is
checked: known sections and fields for the track, types, required values, lengths, formats and
date order. `src/validate.js` implements the same rules for the browser; both run the shared cases
in `tests/cases.json`. Tags (G24) are a list per entry, or per line of a list marked "tags" ({text, tags}); a tag
holds no comma and no control character. The limits of length and count hold for typed tags only: tags already in the
data folder (`known`, see known_tags.py) never block saving.
"""
import dataclasses
import json
import math
import pathlib
import re

ASCII_INDEX = re.compile(r"[0-9]+")
FORM_PATH = pathlib.Path(__file__).resolve().parent / "form.json"
FIELD_TYPES = frozenset({"text", "textarea", "list", "select", "choice", "tags"})
SINGLE_LINE = frozenset({"text", "list", "select", "choice", "tags"})
TAGGED_LINE_KEYS = frozenset({"text", "tags"})
TOP_LEVEL_KEYS = frozenset({"format", "version", "track", "data", "saved"})


@dataclasses.dataclass(frozen=True)
class ValidationError:
    path: str
    code: str


def load_form(path: pathlib.Path = FORM_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def applies(item: dict, track: str) -> bool:
    return track in item.get("tracks", [track])


def for_track(value, track: str):
    """Texts in form.json are either plain or per track ({"job": …, "apprenticeship": …})."""
    if isinstance(value, dict):
        return value.get(track)
    return value


def validate_bundle(form: dict, bundle, known: frozenset[str] = frozenset()) -> list[ValidationError]:
    if not isinstance(bundle, dict):
        return [ValidationError("", "type")]
    if bundle.get("format") != form["format"]:
        return [ValidationError("format", "bundle")]
    version = bundle.get("version")
    if type(version) is not int or version != form["version"]:
        return [ValidationError("version", "bundle")]
    track = bundle.get("track")
    if not isinstance(track, str) or track not in form["tracks"]:
        return [ValidationError("track", "track")]
    data = bundle.get("data")
    if not isinstance(data, dict):
        return [ValidationError("data", "type")]
    errors = [ValidationError(key, "unknown") for key in bundle if key not in TOP_LEVEL_KEYS]
    sections = {s["id"]: s for s in form["sections"] if applies(s, track)}
    errors += [ValidationError(key, "unknown") for key in data if key not in sections]
    for section in sections.values():
        errors += _validate_section(form, section, track, data.get(section["id"]), known)
    return errors


def _validate_section(form: dict, section: dict, track: str, value, known: frozenset[str]) -> list[ValidationError]:
    sid = section["id"]
    if not section.get("repeat"):
        if value is None:
            value = {}
        if not isinstance(value, dict):
            return [ValidationError(sid, "type")]
        return _validate_item(form, section, track, value, sid, known)
    if value is None:
        return []
    if not isinstance(value, list):
        return [ValidationError(sid, "type")]
    errors = []
    if len(value) > section.get("maxItems", form["limits"]["repeatItems"]):
        errors.append(ValidationError(sid, "maxItems"))
    for index, item in enumerate(value):
        path = f"{sid}.{index}"
        if not isinstance(item, dict):
            errors.append(ValidationError(path, "type"))
            continue
        errors += _validate_item(form, section, track, item, path, known)
    return errors


def _validate_item(form: dict, section: dict, track: str, item: dict, path: str,
                   known: frozenset[str]) -> list[ValidationError]:
    fields = {f["id"]: f for f in section["fields"] if applies(f, track)}
    errors = [ValidationError(f"{path}.{key}", "unknown") for key in item if key not in fields]
    for field in fields.values():
        errors += _validate_field(form, field, track, item, f"{path}.{field['id']}", known)
    return errors


def _validate_field(form: dict, field: dict, track: str, item: dict, path: str,
                    known: frozenset[str]) -> list[ValidationError]:
    value = item.get(field["id"])
    if field["type"] == "tags":
        return _validate_tags(form, value, path, known)
    if field["type"] == "list":
        return _validate_list(form, field, value, path, known)
    if value is None:
        value = ""
    if not isinstance(value, str):
        return [ValidationError(path, "type")]
    if not value.strip():
        return [ValidationError(path, "required")] if field.get("required") else []
    error = check_text(form, field, track, value)
    if error:
        return [ValidationError(path, error)]
    if field.get("notBefore") and _is_before(value, item.get(field["notBefore"])):
        return [ValidationError(path, "notBefore")]
    return []


def tag_rules(form: dict) -> dict:
    """The rules of one list of tags, on an entry or on a line."""
    return {"type": "tags", "format": "tag", "max": form["limits"]["tag"], "maxItems": form["limits"]["tags"]}


def is_tagged_line(value) -> bool:
    """A line with tags, as cv.yaml writes it: {text, tags}."""
    return (isinstance(value, dict) and set(value) <= TAGGED_LINE_KEYS and isinstance(value.get("text"), str)
            and isinstance(value.get("tags", []), list))


def line_text(value) -> str:
    return value["text"] if isinstance(value, dict) else value


def _validate_tags(form: dict, value, path: str, known: frozenset[str]) -> list[ValidationError]:
    """A list of tags: known ones may be longer or more than the limits allow, typed ones may not."""
    if value is None:
        value = []
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        return [ValidationError(path, "type")]
    rules = tag_rules(form)
    tags = [v.strip() for v in value if v.strip()]
    typed = [tag for tag in tags if tag not in known]
    errors = [ValidationError(path, "maxItems")] if len(tags) > rules["maxItems"] and typed else []
    for index, tag in enumerate(value):
        if not tag.strip():
            continue
        error = check_text(form, {**rules, "max": math.inf} if tag.strip() in known else rules, None, tag)
        if error:
            errors.append(ValidationError(f"{path}.{index}", error))
    return errors


def _validate_list(form: dict, field: dict, value, path: str, known: frozenset[str]) -> list[ValidationError]:
    if value is None:
        value = []
    tagged = field.get("tags") is True
    if not isinstance(value, list) or not all(isinstance(v, str) or (tagged and is_tagged_line(v)) for v in value):
        return [ValidationError(path, "type")]
    items = [v for v in value if line_text(v).strip()]
    if not items:
        return [ValidationError(path, "required")] if field.get("required") else []
    errors = []
    if len(items) > field.get("maxItems", form["limits"]["listItems"]):
        errors.append(ValidationError(path, "maxItems"))
    for index, entry in enumerate(value):
        text = line_text(entry)
        if not text.strip():
            continue
        error = check_text(form, field, None, text)
        if error:
            errors.append(ValidationError(f"{path}.{index}", error))
        if isinstance(entry, dict):
            errors += _validate_tags(form, entry.get("tags"), f"{path}.{index}.tags", known)
    return errors


def check_text(form: dict, field: dict, track: str | None, value: str) -> str | None:
    """Return the error code for a single non-empty text value, or None."""
    kind = field["type"]
    if kind in SINGLE_LINE and ("\n" in value or "\r" in value):
        return "newline"
    limit = field.get("max", form["limits"]["textarea" if kind == "textarea" else "text"])
    if len(value) > limit:
        return "max"
    fmt = field.get("format")
    if fmt and not re.fullmatch(form["formats"][fmt]["pattern"], value.strip()):
        return "format"
    if kind == "select" and value not in field["options"]:
        return "option"
    if kind == "choice" and not field.get("allowOwn") and value not in for_track(field["options"], track):
        return "option"
    return None


def _is_before(end: str, start) -> bool:
    """True if `end` lies before `start`; year-only dates compare by year."""
    if not isinstance(start, str) or not start.strip():
        return False
    end, start = end.strip(), start.strip()
    if len(end) == 4 or len(start) == 4:
        return end[:4] < start[:4]
    return end < start


LINE, TAG, TAGS_NAME = "Zeile", "Tag", "Tags"

MESSAGES = {
    "required": "Bitte ausfüllen.",
    "type": "Unerwarteter Wert, bitte neu eingeben.",
    "max": "Zu lang (höchstens {max} Zeichen).",
    "maxItems": "Zu viele Einträge (höchstens {maxItems}).",
    "format": "Ungültiges Format, zum Beispiel: {example}.",
    "option": "Bitte einen der vorgeschlagenen Werte wählen.",
    "notBefore": "Liegt vor dem Beginn.",
    "newline": "Bitte ohne Zeilenumbruch.",
    "unknown": "Gehört nicht zu dieser Vorlage.",
    "bundle": "Die Datei ist keine Einstiegsdatei dieser Version.",
    "track": "Unbekannte Art der Suche.",
}


def describe(form: dict, track: str, error: ValidationError) -> str:
    """German message for people: where (section, item, field) and what is wrong."""
    where, field = _locate(form, track, error.path)
    params = {"max": "?", "maxItems": "?", "example": "?"}
    if field:
        params["max"] = field.get("max", form["limits"]["textarea" if field["type"] == "textarea" else "text"])
        params["maxItems"] = field.get("maxItems", form["limits"]["listItems"])
        if field.get("format"):
            params["example"] = form["formats"][field["format"]]["example"]
    elif where:
        section = next((s for s in form["sections"] if s["id"] == error.path.split(".")[0]), None)
        if section:
            params["maxItems"] = section.get("maxItems", form["limits"]["repeatItems"])
    text = MESSAGES.get(error.code, error.code).format(**params)
    return f"{where}: {text}" if where else text


def _locate(form: dict, track: str, path: str) -> tuple[str, dict | None]:
    """Where an error is, by names, and the rules that hold there: those of the field, or of its tags."""
    parts = path.split(".") if path else []
    section = next((s for s in form["sections"] if parts and s["id"] == parts[0]), None)
    if section is None:
        return "", None
    names = [for_track(section["title"], track) or section["id"]]
    rest = parts[1:]
    if section.get("repeat") and rest and ASCII_INDEX.fullmatch(rest[0]):
        names.append(f"{for_track(section['itemTitle'], track)} {int(rest[0]) + 1}")
        rest = rest[1:]
    field = next((f for f in section["fields"] if rest and f["id"] == rest[0]), None)
    if field:
        label = for_track(field["label"], track) or field["id"]
        names.append(label.split(" (")[0])
        below, in_tags = _line_names(rest[1:], TAG if field["type"] == "tags" else LINE)
        names += below
        if field["type"] == "tags" or in_tags:
            field = tag_rules(form)
    return ", ".join(names), field


def _line_names(rest: list[str], unit: str) -> tuple[list[str], bool]:
    """Names below a field, the line ("Zeile 2") and on a line its tags ("Tags, Tag 1"); True if it reaches tags."""
    if not rest or not ASCII_INDEX.fullmatch(rest[0]):
        return [], False
    line = f"{unit} {int(rest[0]) + 1}"
    if len(rest) < 2 or rest[1] != "tags":
        return [line], False
    tag, _ = _line_names(rest[2:3], TAG)
    return [line, TAGS_NAME, *tag], True
