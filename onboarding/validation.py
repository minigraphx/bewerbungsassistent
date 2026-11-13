"""Validate onboarding bundles (`einstieg.json`) against the form definition `form.json`.

The bundle comes from outside (the HTML template, or a file someone edited), so every value is
checked: known sections and fields for the track, types, required values, lengths, formats and
date order. A field marked requiredUnless is required only while the named field of its entry is empty (G25: a free
text or a display stands in for the fields it replaces). `src/validate.js` implements the same rules for the browser; both run the shared cases
in `tests/cases.json`. Tags (G24) are a list per entry, or per line of a list marked "tags" ({text, tags}); a tag
holds no comma and no control character. The limits of length and count hold for typed tags only: tags already in the
data folder (`known`, see known_tags.py) never block saving. In the same way the values already in cv.yaml (`loaded`,
the answers cv_read.py reads from it, G23) never block saving: an entry, a value or a line the file holds at that place
is not checked, two-language values {de, en} included, and a section or list may keep as many entries as the file has.
What the person types or changes keeps to the rules. Since G30 (#181) those rules take everything cv.yaml may hold:
the fields of the CV sections have no limit of length or count (`field_rules`, `entry_limit`; the limits in form.json
still bound suggestions from documents, prefill.py), a field marked "bilingual" takes {de, en} with each language
checked as its text, and dates may be full (2024-08-15). Tags keep their rules (G24).
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
LEVELED_LINE_KEYS = frozenset({"text", "level"})
LEVELS = ("", "1", "2", "3", "4", "5", "6")  # "" leaves a line without level (#123)
TOP_LEVEL_KEYS = frozenset({"format", "version", "track", "data", "saved"})
LANGUAGES = ("de", "en")  # of a two-language value, as lebenslauf/README.md writes it
UNBOUNDED = {"max": math.inf, "maxItems": math.inf}


@dataclasses.dataclass(frozen=True)
class ValidationError:
    path: str
    code: str


def load_form(path: pathlib.Path = FORM_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def is_bilingual(value) -> bool:
    """A two-language value as lebenslauf/README.md writes it: {de, en} with text in each."""
    return (isinstance(value, dict) and bool(value) and set(value) <= set(LANGUAGES)
            and all(isinstance(text, str) for text in value.values()))


def bilingual_value(value) -> dict | None:
    """A two-language value as the form shows and compares it: trimmed, in the order de, en, without an empty
    language; None if it is none or holds no text."""
    if not is_bilingual(value):
        return None
    texts = {key: value[key].strip() for key in LANGUAGES if key in value and value[key].strip()}
    return texts or None


def in_cv(section: dict, field: dict | None = None) -> bool:
    """True for a section of the CV (and a field of it that goes into cv.yaml)."""
    return bool(section.get("cv")) and (field is None or field.get("cv") is not False)


def field_rules(form: dict, section: dict, field: dict) -> dict:
    """The rules of a field as they hold for what the person types: in the CV without limit of length or count (G30)."""
    return {**field, **UNBOUNDED} if in_cv(section, field) else field


def entry_limit(form: dict, section: dict) -> float:
    """How many entries a repeated section takes; the CV takes as many as cv.yaml may hold (G30)."""
    return math.inf if in_cv(section) else section.get("maxItems", form["limits"]["repeatItems"])


def applies(item: dict, track: str) -> bool:
    return track in item.get("tracks", [track])


def for_track(value, track: str):
    """Texts in form.json are either plain or per track ({"job": …, "apprenticeship": …})."""
    if isinstance(value, dict):
        return value.get(track)
    return value


def validate_bundle(form: dict, bundle, known: frozenset[str] = frozenset(),
                    loaded: dict | None = None) -> list[ValidationError]:
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
        before = loaded_entries(section, loaded)
        errors += _validate_section(form, section, track, data.get(section["id"]), known, before)
    return errors


def field_errors(form: dict, field: dict, track: str, value) -> list[ValidationError]:
    """The errors of one value on its own, as for a value read back from the basics (#217)."""
    return _validate_field(form, field, track, {field["id"]: value}, field["id"], frozenset(), [])


def section_errors(form: dict, section: dict, track: str, value) -> list[ValidationError]:
    """The errors of one section on its own, as for entries read back from the basics (#217)."""
    return _validate_section(form, section, track, value, frozenset(), [])


def loaded_entries(section: dict, loaded: dict | None) -> list[dict]:
    """The entries of a section as read from cv.yaml; one entry for a section that does not repeat."""
    value = loaded.get(section["id"]) if isinstance(loaded, dict) and section.get("cv") else None
    entries = value if isinstance(value, list) else [value]
    return [entry for entry in entries if isinstance(entry, dict)]


def comparable(value):
    """A value as it counts when compared with cv.yaml: trimmed, blank as "", a line without tags as its text."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        lines = [line for line in map(comparable_line, value) if line != ""]
        return lines or ""
    if is_bilingual(value):
        return bilingual_value(value) or ""
    return value


def comparable_line(value):
    if isinstance(value, dict) and "level" in value and set(value) <= LEVELED_LINE_KEYS:
        text = comparable(value["text"]) if isinstance(value.get("text"), str) else value.get("text")
        level = value["level"].strip() if isinstance(value["level"], str) else value["level"]
        return {"text": text, "level": level} if level and text != "" else text
    if isinstance(value, dict) and set(value) <= TAGGED_LINE_KEYS and "text" in value:
        text = comparable(value["text"]) if isinstance(value["text"], (str, dict)) else value["text"]
        tags = comparable(value["tags"]) if isinstance(value.get("tags"), list) else value.get("tags")
        return {"text": text, "tags": tags} if tags and text != "" else text
    return comparable(value) if isinstance(value, (str, dict)) else value


def _is_loaded_entry(section: dict, track: str, item: dict, before: list[dict]) -> bool:
    """True if every field of the entry that cv.yaml holds is as in one of its entries."""
    ids = [f["id"] for f in section["fields"] if applies(f, track) and f.get("cv") is not False]
    return any(all(comparable(item.get(key)) == comparable(entry.get(key)) for key in ids) for entry in before)


def _is_loaded_value(key: str, value, before: list[dict]) -> bool:
    shown = comparable(value)
    return shown != "" and any(comparable(entry.get(key)) == shown for entry in before)


def _loaded_lines(key: str, before: list[dict]) -> list:
    return [line for entry in before for line in (comparable(entry.get(key)) or [])]


def _loaded_count(key: str, before: list[dict]) -> int:
    return max((len(comparable(entry.get(key)) or []) for entry in before), default=0)


def _validate_section(form: dict, section: dict, track: str, value, known: frozenset[str],
                      before: list[dict]) -> list[ValidationError]:
    sid = section["id"]
    if not section.get("repeat"):
        if value is None:
            value = {}
        if not isinstance(value, dict):
            return [ValidationError(sid, "type")]
        return _validate_item(form, section, track, value, sid, known, before)
    if value is None:
        return []
    if not isinstance(value, list):
        return [ValidationError(sid, "type")]
    errors = []
    if len(value) > max(entry_limit(form, section), len(before)):
        errors.append(ValidationError(sid, "maxItems"))
    for index, item in enumerate(value):
        path = f"{sid}.{index}"
        if not isinstance(item, dict):
            errors.append(ValidationError(path, "type"))
            continue
        errors += _validate_item(form, section, track, item, path, known, before)
    return errors


def _validate_item(form: dict, section: dict, track: str, item: dict, path: str,
                   known: frozenset[str], before: list[dict]) -> list[ValidationError]:
    fields = {f["id"]: field_rules(form, section, f) for f in section["fields"] if applies(f, track)}
    errors = [ValidationError(f"{path}.{key}", "unknown") for key in item if key not in fields]
    same = _is_loaded_entry(section, track, item, before)
    for field in fields.values():
        key = field["id"]
        if (same and field.get("cv") is not False) or _is_loaded_value(key, item.get(key), before):
            continue
        errors += _validate_field(form, field, track, item, f"{path}.{key}", known, before)
    return errors


def _validate_field(form: dict, field: dict, track: str, item: dict, path: str,
                    known: frozenset[str], before: list[dict]) -> list[ValidationError]:
    value = item.get(field["id"])
    if field["type"] == "tags":
        return _validate_tags(form, value, path, known)
    if field["type"] == "list":
        return _validate_list(form, field, value, path, known, before)
    if value is None:
        value = ""
    if not isinstance(value, str) and not (field.get("bilingual") and is_bilingual(value)):
        return [ValidationError(path, "type")]
    texts = value_texts(value)
    if not texts:
        return [ValidationError(path, "required")] if is_required(field, item) else []
    error = next(filter(None, (check_text(form, field, track, text) for text in texts)), None)
    if error:
        return [ValidationError(path, error)]
    if field.get("notBefore") and _is_before(value, item.get(field["notBefore"])):
        return [ValidationError(path, "notBefore")]
    return []


def value_texts(value) -> list[str]:
    """The texts of a value that hold something: the text itself, or each language of a two-language value."""
    texts = value.values() if is_bilingual(value) else [value] if isinstance(value, str) else []
    return [text for text in texts if text.strip()]


def is_required(field: dict, item: dict) -> bool:
    """Required, unless the field named by requiredUnless holds text: a free text stands in for what it replaces."""
    return bool(field.get("required")) and not value_texts(item.get(field.get("requiredUnless")))


def tag_rules(form: dict) -> dict:
    """The rules of one list of tags, on an entry or on a line."""
    return {"type": "tags", "format": "tag", "max": form["limits"]["tag"], "maxItems": form["limits"]["tags"]}


def is_tagged_line(value, bilingual: bool = False) -> bool:
    """A line with tags, as cv.yaml writes it: {text, tags}; with bilingual its text may be {de, en}."""
    text = value.get("text") if isinstance(value, dict) else None
    return (isinstance(value, dict) and set(value) <= TAGGED_LINE_KEYS and isinstance(value.get("tags", []), list)
            and (isinstance(text, str) or (bilingual and is_bilingual(text))))


def is_leveled_line(value) -> bool:
    """A line with a level, as the page sends it: {text, level} with level as text."""
    return (isinstance(value, dict) and set(value) <= LEVELED_LINE_KEYS and isinstance(value.get("text"), str)
            and isinstance(value.get("level", ""), str))


def line_text(value):
    return value["text"] if isinstance(value, dict) and "text" in value else value


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


def _validate_list(form: dict, field: dict, value, path: str, known: frozenset[str],
                   before: list[dict]) -> list[ValidationError]:
    """A list of lines; lines cv.yaml holds in this field are not checked, two-language ones included."""
    if value is None:
        value = []
    if not isinstance(value, list):
        return [ValidationError(path, "type")]
    tagged, leveled, bilingual = field.get("tags") is True, field.get("levels") is True, bool(field.get("bilingual"))
    lines = _loaded_lines(field["id"], before)
    in_file = [comparable_line(v) in lines for v in value]
    if not all(kept or isinstance(v, str) or (tagged and is_tagged_line(v, bilingual))
               or (leveled and is_leveled_line(v)) or (bilingual and is_bilingual(v))
               for v, kept in zip(value, in_file)):
        return [ValidationError(path, "type")]
    items = [v for v, kept in zip(value, in_file) if kept or value_texts(line_text(v))]
    if not items:
        return [ValidationError(path, "required")] if field.get("required") else []
    errors = []
    if len(items) > max(field.get("maxItems", form["limits"]["listItems"]), _loaded_count(field["id"], before)):
        errors.append(ValidationError(path, "maxItems"))
    for index, (entry, kept) in enumerate(zip(value, in_file)):
        texts = [] if kept else value_texts(line_text(entry))
        if not texts:
            continue
        error = next(filter(None, (check_text(form, field, None, text) for text in texts)), None)
        if error:
            errors.append(ValidationError(f"{path}.{index}", error))
        if isinstance(entry, dict) and tagged:
            errors += _validate_tags(form, entry.get("tags"), f"{path}.{index}.tags", known)
        if isinstance(entry, dict) and leveled and entry.get("level", "").strip() not in LEVELS:
            errors.append(ValidationError(f"{path}.{index}.level", "option"))
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


def _is_before(end, start) -> bool:
    """True if `end` lies before `start`, compared as far as both go: a year by year, a month by month (G30)."""
    if not isinstance(start, str) or not start.strip() or not isinstance(end, str):
        return False
    end, start = end.strip(), start.strip()
    common = min(len(end), len(start))
    return end[:common] < start[:common]


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
    own = (field or {}).get("messages", {})  # a field may say it in its own words, as the search does (#291)
    text = own.get(error.code) or MESSAGES.get(error.code, error.code).format(**params)
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
