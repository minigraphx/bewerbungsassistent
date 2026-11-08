"""Read an existing cv.yaml back into the answers of the form (#160, G23): the inverse of convert.build_cv.

The page „Meine Angaben“ opens with these answers. Only what the form can show comes back; an entry without
anything the form shows does not come back at all. All of it stays in the file: cv_merge.py puts the answers back
without touching the rest. The keys below are the field ids of form.json (sections marked "cv"). Tags (G24) come
along on entries and on highlights; a highlight with tags is {text, tags}, as in the file. Projects, teaching, the free
texts of education and certificates and basics.url came with G25; a project group the form does not offer stays out.
"""
import datetime
import logging
import pathlib
import re

import yaml

import validation

log = logging.getLogger(__name__)

CV = "cv.yaml"
BIRTH = "geboren "  # convert._basics writes the birth date as the detail "geboren <date>"
TEXT_BASICS = ("name", "label", "email", "url", "phone")
LOCATION = ("address", "postalCode", "city")
DATES = ("startDate", "endDate")
SECTIONS = {
    "work": ("position", "name", "location", *DATES, "highlights", "tags"),
    "teaching": ("position", "name", "location", *DATES, "x-display", "highlights", "tags"),
    "projects": ("name", "description", "group", "tags"),
    "education": ("studyType", "area", "institution", *DATES, "text"),
    "certificates": ("name", "issuer", "date", "text", "tags"),
    "languages": ("language", "fluency"),
    "skills": ("name", "keywords", "tags"),
}
INTERESTS = ("name",)
FORM = validation.load_form()
TAG = re.compile(FORM["formats"]["tag"]["pattern"])
# a bundle without these keys keeps them in the file, an empty value removes them (G25, the rule of tags in G24)
KEPT_SECTIONS = frozenset(s["id"] for s in FORM["sections"] if s.get("cv") and s.get("keepUnlessGiven"))
KEPT_BASICS = frozenset(f["id"] for s in FORM["sections"] if s["id"] == "person"
                        for f in s["fields"] if f.get("keepUnlessGiven"))
CHOICES = {"group": next(f["options"] for s in FORM["sections"] if s["id"] == "projects"
                         for f in s["fields"] if f["id"] == "group")}


def shown_text(value: object) -> str | None:
    """A value as the form shows it: text for scalars, "" for nothing, None where the form cannot show it."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, datetime.date):
        return value.isoformat()
    return None


def field_text(key: str, value: object) -> str | None:
    """A field of an entry as the form shows it; a choice the form does not offer it cannot show."""
    text = shown_text(value)
    return None if key in CHOICES and text and text not in CHOICES[key] else text


def item_text(item: object) -> str | None:
    """A list line (highlight, keyword) as text, also from {text, tags}; None if blank or not text."""
    text = shown_text(item["text"]) if isinstance(item, dict) and "text" in item else line_text(item)
    return text or None


def line_text(item: object) -> str | None:
    """One line of a list of plain lines (keywords) as text; None if blank or not text."""
    return None if isinstance(item, (dict, list)) else shown_text(item) or None


def tag_text(item: object) -> str | None:
    """One tag as the form can show it; None if blank, not text, or holding a comma or a control character."""
    text = line_text(item)
    return text if text and TAG.fullmatch(text) else None


def shown_tags(value: object) -> list[str]:
    """The tags of a list the form can show; the others stay out (and stay in the file)."""
    return [t for t in map(tag_text, value) if t] if isinstance(value, list) else []


def highlight_shown(item: object) -> str | dict | None:
    """A highlight as the form shows it: its text, or {text, tags} when it has tags; None if it cannot."""
    text = item_text(item)
    tags = shown_tags(item.get("tags")) if isinstance(item, dict) else []
    return {"text": text, "tags": tags} if text and tags else text


LIST_SHOWN = {"highlights": highlight_shown, "keywords": item_text, "tags": tag_text}


def entry_shown(entry: object, fields: tuple[str, ...]) -> dict | None:
    """What the form shows of an entry; None if it shows nothing of it."""
    if not isinstance(entry, dict):
        return None
    shown = {}
    for key in fields:
        value = entry.get(key)
        if key in LIST_SHOWN:
            lines = [line for line in map(LIST_SHOWN[key], value) if line] if isinstance(value, list) else []
            if lines:
                shown[key] = lines
        elif text := field_text(key, value):
            shown[key] = text
    return shown or None


def detail_places(details: list) -> tuple[int | None, int | None]:
    """Positions of the birth date and the nationality in basics.details, as the form reads them."""
    texts = [shown_text(d) if isinstance(d, str) else None for d in details]
    birth = next((i for i, t in enumerate(texts) if t and t.startswith(BIRTH)), None)
    nationality = next((i for i, t in enumerate(texts) if t and i != birth), None)
    return birth, nationality


def detail_values(details: object) -> tuple[str, str]:
    """Birth date and nationality from basics.details; empty where there is none."""
    if not isinstance(details, list):
        return "", ""
    birth, nationality = detail_places(details)
    return (details[birth].strip()[len(BIRTH):].strip() if birth is not None else "",
            details[nationality].strip() if nationality is not None else "")


def form_data(cv: dict) -> dict:
    """The answers of the CV sections of the form; every one of them, empty ones included."""
    basics = cv.get("basics") if isinstance(cv.get("basics"), dict) else {}
    entries = {key: _entries(cv.get(key), fields) for key, fields in SECTIONS.items()}
    names = [item["name"] for item in _entries(cv.get("interests"), INTERESTS)]
    return {"person": _person(basics), "summary": _texts(basics, ("summary",)), **entries,
            "interests": {"interests": names} if names else {}}


def read_form_data(folder: pathlib.Path) -> dict | None:
    """The answers from the cv.yaml of a data folder; None without a readable one."""
    path = folder / CV
    if not path.is_file():
        return None
    try:
        cv = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
        log.warning("cv.yaml nicht lesbar: %s", error)
        return None
    return form_data(cv) if isinstance(cv, dict) else None


def _texts(source: dict, keys: tuple[str, ...]) -> dict:
    return {key: text for key in keys if (text := shown_text(source.get(key)))}


def _person(basics: dict) -> dict:
    location = basics.get("location") if isinstance(basics.get("location"), dict) else {}
    birth, nationality = detail_values(basics.get("details"))
    profiles = basics.get("profiles") if isinstance(basics.get("profiles"), list) else []
    urls = [shown["url"] for shown in (entry_shown(p, ("url",)) for p in profiles) if shown]
    person = {**_texts(basics, TEXT_BASICS), **_texts(location, LOCATION),
              "birthDate": birth, "nationality": nationality, "profiles": urls}
    return {key: value for key, value in person.items() if value}


def _entries(value: object, fields: tuple[str, ...]) -> list[dict]:
    return [shown for shown in (entry_shown(e, fields) for e in value) if shown] if isinstance(value, list) else []
