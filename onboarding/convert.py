"""Turn a validated onboarding bundle into the four basics of a data folder.

`convert_bundle` is pure: it returns the file contents by relative path and writes nothing.
The CV follows the JSON Resume schema used by `lebenslauf/` (see its README); the Markdown
files follow the templates in `vorlagen/`.
"""
import datetime
import functools
import urllib.parse

import yaml

import markdown_files
from cv_read import KEPT_BASICS, KEPT_SECTIONS
from validation import bilingual_value
from values import items, text

APPRENTICESHIP_HEADINGS = {"erfahrung": "Schnupperlehren & Erfahrungen", "bildung": "Schule & Eignungstests"}
DISPLAY = ("x-display",)  # the text a station shows instead of its dates (teaching G25, work G30)
LEVEL_KEY = "x-level"  # of a language, read by lebenslauf/dossier_data.py
NETWORKS = {"linkedin": "LinkedIn", "github": "GitHub", "xing": "XING", "gitlab": "GitLab"}


BASICS = ("cv.yaml", "suchprofil.md", "anschreiben/stil.md", "anschreiben/bausteine.md")


def convert_bundle(form: dict, bundle: dict, today: datetime.date) -> dict[str, str]:
    """Map a bundle that passed validation.validate_bundle to {relative path: file text}."""
    data = bundle["data"]
    track = bundle["track"]
    note = made_on(today)
    return {
        "cv.yaml": cv_file(build_cv(data, track), note),
        "suchprofil.md": markdown_files.search_profile(data, track, note),
        "anschreiben/stil.md": markdown_files.style_profile(form, data, track, note),
        "anschreiben/bausteine.md": markdown_files.building_blocks(data, track, note),
    }


def made_on(today: datetime.date) -> str:
    return f"Erstellt mit der Einstiegsvorlage am {today.day}.{today.month}.{today.year}"


def cv_file(cv: dict, note: str) -> str:
    return f"# {note}. Format: lebenslauf/README.md\n" + _dump_yaml(cv)


def build_cv(data: dict, track: str, answer_keys: bool = False) -> dict:
    """The CV of the answers. With answer_keys an answer's tags stay as given, an empty list too, a highlight given
    as {text, tags} stays one, and so do the empty sections and fields marked keepUnlessGiven in form.json (G25):
    cv_merge.py tells "none" (empty) from "not given" (no key)."""
    tag_keys = answer_keys
    person = data.get("person", {})
    basics = _basics(person, data.get("summary", {}))
    given = {key: "" for key in KEPT_BASICS if answer_keys and key in person and key not in basics}
    cv = {"basics": {**basics, **given}}
    tagged = functools.partial(_tagged, tag_keys=tag_keys)
    sections = {
        "work": [_work(w, tag_keys) for w in data.get("work", [])],
        "teaching": [_work(t, tag_keys) for t in data.get("teaching", [])],
        "projects": [tagged(_pick(p, "name", "description", "group"), p) for p in data.get("projects", [])],
        "education": [_pick(e, "studyType", "area", "institution", "startDate", "endDate", "text", keep_end=True)
                      for e in data.get("education", [])],
        "certificates": [tagged(_pick(c, "name", "issuer", "date", "text"), c) for c in data.get("certificates", [])],
        "languages": [_language(lang, answer_keys) for lang in data.get("languages", [])],
        "skills": [tagged({"name": value(s["name"]), "keywords": _keywords(s.get("keywords"), answer_keys)}, s)
                   for s in data.get("skills", [])],
        "interests": [{"name": name} for name in items(data.get("interests", {}).get("interests"))],
    }
    cv.update({key: value for key, value in sections.items()
               if value or (answer_keys and key in KEPT_SECTIONS and key in data)})
    if track == "apprenticeship":
        cv["x-beschriftungen"] = dict(APPRENTICESHIP_HEADINGS)
    return cv


def _basics(person: dict, summary: dict) -> dict:
    location = _pick(person, "address", "postalCode", "city")
    details = [f"geboren {text(person.get('birthDate'))}" if text(person.get("birthDate")) else "",
               text(person.get("nationality"))]
    basics = {
        "name": value(person.get("name")),
        "label": value(person.get("label")),
        "email": text(person.get("email")),
        "url": text(person.get("url")),
        "phone": text(person.get("phone")),
        "location": location,
        "details": [d for d in details if d],
        "summary": value(summary.get("summary")),
        "profiles": [_profile(url) for url in items(person.get("profiles"))],
    }
    return {key: value for key, value in basics.items() if value}


def full_url(url: str) -> str:
    return url if url.startswith(("http://", "https://")) else f"https://{url}"


def _profile(url: str) -> dict:
    full = full_url(url)
    try:
        host = urllib.parse.urlsplit(full).hostname or url
    except ValueError:  # e.g. an unclosed "[" that urlsplit reads as an IPv6 host
        host = url
    host = host.removeprefix("www.")
    network = next((name for key, name in NETWORKS.items() if host.startswith(key + ".")), host)
    return {"network": network, "url": full}


def _work(entry: dict, tag_keys: bool) -> dict:
    """A station; with tag_keys an emptied display stays as "" so that cv_merge.py removes the one of the file, while
    answers without the key (from before G30 for work) leave it to the file."""
    work = _pick(entry, "position", "name", "location", "startDate", "endDate", *DISPLAY, keep_end=True)
    work = {**work, **{key: "" for key in DISPLAY if tag_keys and key in entry and key not in work}}
    highlights = [line for line in (_highlight(h, tag_keys) for h in entry.get("highlights") or []) if line]
    return _tagged({**work, "highlights": highlights} if highlights else work, entry, tag_keys)


def _highlight(line, tag_keys: bool) -> str | dict | None:
    """A highlight as lebenslauf/README.md has it: text, or {text, tags} when it has tags (G24); the text may be
    {de, en} (G30)."""
    if not isinstance(line, dict) or bilingual_value(line):
        return value(line) or None
    line_text, tags = value(line.get("text")), items(line.get("tags"))
    if not line_text:
        return None
    return {"text": line_text, "tags": tags} if tags or (tag_keys and "tags" in line) else line_text


def _language(entry: dict, answer_keys: bool) -> dict:
    """A language; with answer_keys an empty x-level stays as "" so that cv_merge.py removes the one of the file."""
    language = _pick(entry, "language", "fluency", LEVEL_KEY)
    return {**language, LEVEL_KEY: ""} if answer_keys and LEVEL_KEY in entry and LEVEL_KEY not in language else language


def _keywords(lines, answer_keys: bool) -> list:
    """Keywords as lebenslauf/README.md has them: text, or {name, level} with a level 1–6 (#123).

    With answer_keys a line without level that the page sent as {text, level} becomes {name, level: None}: cv_merge.py
    removes the level of the file then, while a plain line leaves it alone.
    """
    keywords = []
    for line in lines or []:
        if isinstance(line, str):
            keywords += [text(line)] if text(line) else []
            continue
        name, level = text(line.get("text")), text(line.get("level"))
        if not name:
            continue
        if level.isdigit():
            keywords.append({"name": name, "level": int(level)})
        else:
            keywords.append({"name": name, "level": None} if answer_keys else name)
    return keywords


def _tagged(cv_entry: dict, entry: dict, tag_keys: bool) -> dict:
    tags = items(entry.get("tags"))
    return {**cv_entry, "tags": tags} if tags or (tag_keys and "tags" in entry) else cv_entry


def value(answer) -> str | dict:
    """A text answer as cv.yaml takes it: trimmed text, or {de, en} for one in two languages (G30)."""
    return bilingual_value(answer) or text(answer)


def _pick(entry: dict, *keys: str, keep_end: bool = False) -> dict:
    """Selected non-empty text fields; with keep_end an empty endDate means 'ongoing' (None)."""
    picked = {key: value(entry.get(key)) for key in keys}
    result = {key: found for key, found in picked.items() if found}
    if keep_end and result.get("startDate") and not result.get("endDate"):
        result["endDate"] = None
    return result


def _dump_yaml(value: dict) -> str:
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=4096)
