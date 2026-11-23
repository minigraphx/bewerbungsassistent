"""Region, Pensum, exclusions and title filter, changed on Suche einstellen (#286, G64).

Each value is one line `- Label: value` in its section of suchprofil.md: the lines Meine Angaben reads and writes
(onboarding/basics_slots.py) and the search reads (search_plan.py). A change replaces the first line whose label
starts the way the search looks for it, keeping the label and indentation as written; an empty list removes the line,
and a missing line goes to the end of its section. Every other line of the profile stays as it is. A value is taken
within the limits of the field in Meine Angaben that reads the same line (`profile_limits.py`, #302). The place
lines of single portals (Orte, PLZ, Regionen) have no field there; `portal_places.py` checks them (#301).
"""
import dataclasses
import re
from typing import Callable

import jobscout24_regions
import portal_places
import profile_limits
import search_plan
from ui_message import T

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
BAD_RADIUS = T("Umkreis: erlaubt sind {min} bis {max} km.", min=search_plan.MIN_RADIUS_KM, max=search_plan.MAX_RADIUS_KM)


@dataclasses.dataclass(frozen=True)
class Field:
    name: str  # for messages to the person
    section: str
    prefix: str  # what the label starts with, as search_plan reads it
    label: str  # for a line that is not there yet
    before: str  # where a missing section goes; at the end if this one is missing too
    form_id: str  # the field of Meine Angaben that reads the line; empty for one without limits there
    kinds: tuple[str, ...] = (search_plan.KIND_JOB,)
    label_apprenticeship: str = ""
    # for two lines whose labels start alike, the Regionen of ictjobs and of jobscout24 (G107): which label is this one
    matches: Callable[[str], bool] | None = None

    def reads(self, label: str) -> bool:
        return self.matches(label) if self.matches else label.strip().lower().startswith(self.prefix)


def _place_field(key: str, label: str) -> Field:
    matches = {"regionen": search_plan.is_ictjobs_regions,
               portal_places.JOBSCOUT24_REGIONS: search_plan.is_jobscout24_regions}.get(key)
    return Field(portal_places.NAMES[key], "## Region", key, f"{label} ({portal_places.PORTAL_OF[key]})", "## Keywords",
                 "", matches=matches)


PLACE_KEYS = (*portal_places.KEYS, portal_places.JOBSCOUT24_REGIONS)
BOTH = (search_plan.KIND_JOB, search_plan.KIND_APPRENTICESHIP)
FIELDS = {
    "wohnort": Field(T("den Wohnort"), "## Region", "wohnort", "Wohnort", "## Keywords", "home", BOTH),
    "kantone": Field(T("Kantone"), "## Region", "kantone", "Kantone (job-room)", "## Keywords", "cantons", BOTH,
                     "Kantone"),
    "umkreis_km": Field(T("Umkreis"), "## Region", "umkreis", "Umkreis", "## Schule", "",
                        (search_plan.KIND_APPRENTICESHIP,)),
    "pensum": Field(T("das Pensum"), "## Rahmen", "pensum", "Pensum", "## Zielfirmen mit Karriereseite", "workload"),
    "ausschluss": Field(T("Ausschlüsse"), "## Suchrichtungen", "ausschluss", "Ausschluss", "## Region", "exclusions"),
    "titel_positiv": Field(T("Titel, die passen"), "## Titelfilter", "positiv", "Positiv", "## Sprachen",
                           "titlePositive"),
    "titel_ausschluss": Field(T("Titel, die nicht passen"), "## Titelfilter", "ausschluss", "Ausschluss",
                              "## Sprachen", "titleExclude"),
    **{key: _place_field(key, label) for key, label in (("orte", "Orte"), ("plz", "PLZ"), ("regionen", "Regionen"),
                                                         (portal_places.JOBSCOUT24_REGIONS, "Regionen"))},
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
    return next((i for i in range(start + 1, end) if (m := PAIR_LINE.match(lines[i])) and field.reads(m.group(2))), None)


def _raw(text: str, key: str) -> str:
    lines = text.split("\n")
    found = _line(lines, FIELDS[key])
    return PAIR_LINE.match(lines[found]).group(3).strip() if found is not None else ""


def raw_value(text: str, key: str) -> str:
    """The value of the field's line exactly as written, or empty without the line."""
    return _raw(text, key)


def with_raw_value(text: str, key: str, value: str) -> str:
    """The profile with this value in the field's line, unchecked: for a value built from the line itself."""
    return _with_line(text, FIELDS[key], FIELDS[key].label, value)


def _listed(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def values(text: str) -> dict:
    """What the cards show in their fields: the values as the person wrote them, a slash stays inside its entry."""
    cantons = [c for c in (item.upper() for item in _listed(_raw(text, "kantone"))) if c in search_plan.CANTONS]
    radius = search_plan.NUMBER.search(_raw(text, "umkreis_km"))
    return {"wohnort": _raw(text, "wohnort"), "kantone": list(dict.fromkeys(cantons)),
            "umkreis_km": int(radius.group()) if radius else None, "pensum": _raw(text, "pensum"),
            **{key: _listed(_raw(text, key)) for key in ("ausschluss", *TITLE_LISTS, *portal_places.KEYS)},
            portal_places.JOBSCOUT24_REGIONS: [jobscout24_regions.written(entry)
                                               for entry in _listed(_raw(text, portal_places.JOBSCOUT24_REGIONS))]}


def lengths(text: str) -> dict[str, int]:
    """How long the single-line fields of the cards may be, as Meine Angaben takes them."""
    kind = kind_of(text)
    return {key: profile_limits.of(kind, FIELDS[key].form_id).chars for key in TEXT_FIELDS if kind in FIELDS[key].kinds}


def _one_line(value: str) -> str:
    """Line breaks and runs of spaces become one space, so a value never reaches another line."""
    return " ".join(value.split())


def _checked_text(field: Field, value, required: bool, limit: profile_limits.Limit) -> str:
    if not isinstance(value, str) or (required and not _one_line(value)):
        raise ValueError(T(REQUIRED, name=field.name))
    return _bounded(_one_line(value), limit)


def _bounded(value: str, limit: profile_limits.Limit) -> str:
    if len(value) > limit.chars:
        raise ValueError(T(TOO_LONG, value=value[:20], limit=limit.chars))
    return value


def _checked_list(field: Field, value, limit: profile_limits.Limit) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(T(NOT_A_LIST, name=field.name))
    unique: dict[str, str] = {}
    for item in (_bounded(_one_line(item), limit) for item in value if _one_line(item)):
        unique.setdefault(item.lower(), item)  # the first spelling counts, as the search reads it
    return list(unique.values())


def _checked_cantons(field: Field, value, limit: profile_limits.Limit) -> list[str]:
    cantons = [item.upper() for item in _checked_list(field, value, limit)]
    wrong = next((c for c in cantons if c not in search_plan.CANTONS), None)
    if wrong:
        raise ValueError(T(BAD_CANTON, value=wrong))
    return cantons


def _checked_terms(field: Field, value, limit: profile_limits.Limit) -> list[str]:
    """One entry per line, counted as Meine Angaben counts them: a slash stays inside its entry."""
    items = _checked_list(field, value, limit)
    if len(items) > limit.lines:
        raise ValueError(T(TOO_MANY, name=field.name, limit=limit.lines))
    return items


def _checked_radius(value) -> str:
    if value in (None, ""):
        return ""
    if type(value) is not int or not search_plan.MIN_RADIUS_KM <= value <= search_plan.MAX_RADIUS_KM:
        raise ValueError(BAD_RADIUS)
    return f"{value} km"


def _written(key: str, value, kind: str, text: str) -> str:
    """The value as it goes into its line; empty means the line goes."""
    field = FIELDS[key]
    if key == "umkreis_km":
        return _checked_radius(value)
    if key in PLACE_KEYS:
        return ", ".join(portal_places.checked(key, value, _listed(_raw(text, key))))
    limit = profile_limits.of(kind, field.form_id)
    if key in TEXT_FIELDS:
        return _checked_text(field, value, kind != search_plan.KIND_JOB or key not in OPTIONAL_FOR_JOBS, limit)
    if key == "kantone":
        return ", ".join(_checked_cantons(field, value, limit))
    return ", ".join(_checked_terms(field, value, limit))


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
        raise ValueError(T(UNKNOWN, key=unknown))
    for key in change:
        if kind not in FIELDS[key].kinds:
            raise ValueError(T(ONLY_APPRENTICESHIPS) if key == "umkreis_km" else T(ONLY_JOBS, name=FIELDS[key].name))


def with_values(text: str, change: dict) -> str:
    """The profile with these values; ValueError with a message for the person if the search cannot take one."""
    kind = kind_of(text)
    _check_kind(change, kind)
    written = {key: _written(key, value, kind, text) for key, value in change.items()}
    result = text
    for key, value in written.items():
        field = FIELDS[key]
        label = field.label_apprenticeship if kind == search_plan.KIND_APPRENTICESHIP and field.label_apprenticeship else field.label
        result = _with_line(result, field, label, value)
    return result
