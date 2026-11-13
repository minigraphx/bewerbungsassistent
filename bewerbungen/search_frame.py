"""Region, Pensum, exclusions and title filter, changed on Suche einstellen (#286, G64).

Each value is one line `- Label: value` in its section of suchprofil.md: the lines Meine Angaben reads and writes
(onboarding/basics_slots.py) and the search reads (search_plan.py). A change replaces the first line whose label
starts the way the search looks for it, keeping the label and indentation as written; an empty list removes the line,
and a missing line goes to the end of its section. Every other line of the profile stays as it is.
"""
import dataclasses
import re

import search_plan

MAX_EXCLUSIONS = 30
PAIR_LINE = re.compile(r"^(\s*)-\s+([^:]+):\s*(.*)$")
ONLY_JOBS = "„{name}“ gilt nur für die Stellensuche."
ONLY_APPRENTICESHIPS = "Den Umkreis gibt es nur bei der Lehrstellensuche."
UNKNOWN = "Unbekannte Angabe: {key}."
NOTHING = "Nichts zu ändern."
REQUIRED = "Bitte {name} angeben."
TOO_LONG = "„{value}…“ ist zu lang: höchstens {limit} Zeichen."
NOT_A_LIST = "{name}: bitte als Liste senden."
BAD_CANTON = "Unbekannter Kanton: {value}."
TOO_MANY = "{name}: höchstens {limit} Begriffe."
BAD_RADIUS = (f"Umkreis: erlaubt sind {search_plan.MIN_RADIUS_KM} bis {search_plan.MAX_RADIUS_KM} km.")


@dataclasses.dataclass(frozen=True)
class Field:
    name: str  # for messages to the person
    section: str
    prefix: str  # what the label starts with, as search_plan reads it
    label: str  # for a line that is not there yet
    before: str  # where a missing section goes; at the end if this one is missing too
    kinds: tuple[str, ...] = (search_plan.KIND_JOB,)
    label_apprenticeship: str = ""


BOTH = (search_plan.KIND_JOB, search_plan.KIND_APPRENTICESHIP)
FIELDS = {
    "wohnort": Field("den Wohnort", "## Region", "wohnort", "Wohnort", "## Keywords", BOTH),
    "kantone": Field("Kantone", "## Region", "kantone", "Kantone (job-room)", "## Keywords", BOTH, "Kantone"),
    "umkreis_km": Field("Umkreis", "## Region", "umkreis", "Umkreis", "## Schule", (search_plan.KIND_APPRENTICESHIP,)),
    "pensum": Field("das Pensum", "## Rahmen", "pensum", "Pensum", "## Zielfirmen mit Karriereseite"),
    "ausschluss": Field("Ausschlüsse", "## Suchrichtungen", "ausschluss", "Ausschluss", "## Region"),
    "titel_positiv": Field("Titel, die passen", "## Titelfilter", "positiv", "Positiv", "## Sprachen"),
    "titel_ausschluss": Field("Titel, die nicht passen", "## Titelfilter", "ausschluss", "Ausschluss", "## Sprachen"),
}
TEXT_FIELDS = ("wohnort", "pensum")
OPTIONAL_FOR_JOBS = ("wohnort",)  # without it the search uses the cantons or Orte; an apprenticeship searches around it
TITLE_LISTS = ("titel_positiv", "titel_ausschluss")


def kind_of(text: str) -> str:
    return search_plan.KIND_APPRENTICESHIP if search_plan.APPRENTICESHIP_MARK in text else search_plan.KIND_JOB


def _line(lines: list[str], field: Field) -> int | None:
    """The first line of the field's section whose label starts like the field, as the search finds it."""
    start, end = search_plan.section_bounds(lines, field.section[3:].strip().lower())
    if start is None:
        return None
    return next((i for i in range(start + 1, end)
                 if (m := PAIR_LINE.match(lines[i])) and m.group(2).strip().lower().startswith(field.prefix)), None)


def _raw(text: str, key: str) -> str:
    lines = text.split("\n")
    found = _line(lines, FIELDS[key])
    return PAIR_LINE.match(lines[found]).group(3).strip() if found is not None else ""


def _listed(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def values(text: str) -> dict:
    """What the cards show in their fields: the values as the person wrote them, a slash stays inside its entry."""
    cantons = [c for c in (item.upper() for item in _listed(_raw(text, "kantone"))) if c in search_plan.CANTONS]
    radius = search_plan.NUMBER.search(_raw(text, "umkreis_km"))
    return {"wohnort": _raw(text, "wohnort"), "kantone": list(dict.fromkeys(cantons)),
            "umkreis_km": int(radius.group()) if radius else None, "pensum": _raw(text, "pensum"),
            **{key: _listed(_raw(text, key)) for key in ("ausschluss", *TITLE_LISTS)}}


def _one_line(value: str) -> str:
    """Line breaks and runs of spaces become one space, so a value never reaches another line."""
    return " ".join(value.split())


def _checked_text(field: Field, value, required: bool) -> str:
    if not isinstance(value, str) or (required and not _one_line(value)):
        raise ValueError(REQUIRED.format(name=field.name))
    return _bounded(_one_line(value))


def _bounded(value: str) -> str:
    if len(value) > search_plan.MAX_VALUE:
        raise ValueError(TOO_LONG.format(value=value[:20], limit=search_plan.MAX_VALUE))
    return value


def _checked_list(field: Field, value) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(NOT_A_LIST.format(name=field.name))
    unique: dict[str, str] = {}
    for item in (_bounded(_one_line(item)) for item in value if _one_line(item)):
        unique.setdefault(item.lower(), item)  # the first spelling counts, as the search reads it
    return list(unique.values())


def _checked_cantons(field: Field, value) -> list[str]:
    cantons = [item.upper() for item in _checked_list(field, value)]
    wrong = next((c for c in cantons if c not in search_plan.CANTONS), None)
    if wrong:
        raise ValueError(BAD_CANTON.format(value=wrong))
    return cantons


def _checked_terms(field: Field, value, limit: int, count) -> list[str]:
    items = _checked_list(field, value)
    if count(items) > limit:
        raise ValueError(TOO_MANY.format(name=field.name, limit=limit))
    return items


def _checked_radius(value) -> str:
    if value in (None, ""):
        return ""
    if type(value) is not int or not search_plan.MIN_RADIUS_KM <= value <= search_plan.MAX_RADIUS_KM:
        raise ValueError(BAD_RADIUS)
    return f"{value} km"


def _written(key: str, value, kind: str) -> str:
    """The value as it goes into its line; empty means the line goes."""
    field = FIELDS[key]
    if key in TEXT_FIELDS:
        return _checked_text(field, value, kind != search_plan.KIND_JOB or key not in OPTIONAL_FOR_JOBS)
    if key == "umkreis_km":
        return _checked_radius(value)
    if key == "kantone":
        return ", ".join(_checked_cantons(field, value))
    if key in TITLE_LISTS:
        terms = _checked_terms(field, value, search_plan.MAX_TITLE_TERMS, lambda items: len(search_plan.split_terms(", ".join(items))))
        return ", ".join(terms)
    return ", ".join(_checked_terms(field, value, MAX_EXCLUSIONS, len))


def _with_line(text: str, field: Field, label: str, value: str) -> str:
    lines = text.split("\n")
    found = _line(lines, field)
    if found is not None:
        indent, written_label = PAIR_LINE.match(lines[found]).group(1, 2)
        kept = [f"{indent}- {written_label.strip()}: {value}"] if value else []
        return "\n".join([*lines[:found], *kept, *lines[found + 1:]])
    if not value:
        return text
    return search_plan.with_section_line(text, field.section, f"- {label}: {value}", field.before)


def _check_kind(change: dict, kind: str) -> None:
    if not isinstance(change, dict) or not change:
        raise ValueError(NOTHING)
    unknown = next((key for key in change if key not in FIELDS), None)
    if unknown:
        raise ValueError(UNKNOWN.format(key=unknown))
    for key in change:
        if kind not in FIELDS[key].kinds:
            raise ValueError(ONLY_APPRENTICESHIPS if key == "umkreis_km" else ONLY_JOBS.format(name=FIELDS[key].name))


def with_values(text: str, change: dict) -> str:
    """The profile with these values; ValueError with a message for the person if the search cannot take one."""
    kind = kind_of(text)
    _check_kind(change, kind)
    written = {key: _written(key, value, kind) for key, value in change.items()}
    result = text
    for key, value in written.items():
        field = FIELDS[key]
        label = field.label_apprenticeship if kind == search_plan.KIND_APPRENTICESHIP and field.label_apprenticeship else field.label
        result = _with_line(result, field, label, value)
    return result
