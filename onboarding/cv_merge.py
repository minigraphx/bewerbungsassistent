"""Replace a cv.yaml with what the form made without losing what the form cannot show (#159).

The form writes only part of the format in lebenslauf/README.md. Keys it never writes (basics.image,
basics.x-image, projects, teaching, x-* and any other) are carried over unchanged. Inside the parts it
does write, it can only show certain fields; when an existing entry holds more (tags, x-display,
highlights as {text, tags}, …), merging would lose them, so the file stays as it was. A safeguard until
the form reads the CV back (G23).
"""
import yaml

import convert

FORM_BASICS = frozenset({"name", "label", "email", "phone", "location", "details", "summary", "profiles"})
FORM_TEXT_BASICS = ("name", "label", "email", "phone", "summary")
LOCATION_FIELDS = frozenset({"address", "postalCode", "city"})
PROFILE_FIELDS = frozenset({"network", "url"})
DATES = frozenset({"startDate", "endDate"})
FORM_SECTIONS = {
    "work": frozenset({"position", "name", "location", "highlights"}) | DATES,
    "education": frozenset({"studyType", "area", "institution"}) | DATES,
    "certificates": frozenset({"name", "issuer", "date"}),
    "languages": frozenset({"language", "fluency"}),
    "skills": frozenset({"name", "keywords"}),
    "interests": frozenset({"name"}),
}
TEXT_LISTS = ("highlights", "keywords")
HEADINGS = "x-beschriftungen"


def merged(existing_text: str, new_cv: dict) -> dict | None:
    """The new CV with everything the form does not own taken from the old one; None to keep the old file."""
    try:
        existing = yaml.safe_load(existing_text)
    except yaml.YAMLError:
        return None
    if existing is None:
        return new_cv
    if not isinstance(existing, dict) or not _form_can_show(existing):
        return None
    basics = existing.get("basics") or {}
    carried_basics = {key: value for key, value in basics.items() if key not in FORM_BASICS}
    carried = {key: value for key, value in existing.items()
               if key != "basics" and key not in FORM_SECTIONS and not _form_made_headings(key, value)}
    rest = {key: value for key, value in new_cv.items() if key != "basics" and key not in carried}
    return {"basics": {**new_cv.get("basics", {}), **carried_basics}, **rest, **carried}


def _form_made_headings(key: str, value: object) -> bool:
    """The headings the apprenticeship track sets follow the track; any others are the person's own."""
    return key == HEADINGS and value == convert.APPRENTICESHIP_HEADINGS


def _form_can_show(cv: dict) -> bool:
    basics = cv.get("basics") or {}
    return (isinstance(basics, dict) and _basics_fit(basics)
            and all(_entries_fit(cv[key], fields) for key, fields in FORM_SECTIONS.items() if key in cv))


def _basics_fit(basics: dict) -> bool:
    texts = all(isinstance(basics[key], str) for key in FORM_TEXT_BASICS if key in basics)
    location = basics.get("location", {})
    profiles = basics.get("profiles", [])
    return (texts and _text_list(basics.get("details", []))
            and isinstance(location, dict) and set(location) <= LOCATION_FIELDS
            and _entries_fit(profiles, PROFILE_FIELDS))


def _entries_fit(entries: object, fields: frozenset[str]) -> bool:
    return isinstance(entries, list) and all(_entry_fits(entry, fields) for entry in entries)


def _entry_fits(entry: object, fields: frozenset[str]) -> bool:
    return (isinstance(entry, dict) and set(entry) <= fields
            and all(_text_list(entry[key]) for key in TEXT_LISTS if key in entry))


def _text_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)
