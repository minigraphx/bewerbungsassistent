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
from values import items, text

APPRENTICESHIP_HEADINGS = {"erfahrung": "Schnupperlehren & Erfahrungen", "bildung": "Schule & Eignungstests"}
TEACHING_EXTRA = ("x-display",)  # teaching is shaped like work; the form shows its display text too (G25)
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
        "teaching": [_work(t, tag_keys, TEACHING_EXTRA) for t in data.get("teaching", [])],
        "projects": [tagged(_pick(p, "name", "description", "group"), p) for p in data.get("projects", [])],
        "education": [_pick(e, "studyType", "area", "institution", "startDate", "endDate", "text", keep_end=True)
                      for e in data.get("education", [])],
        "certificates": [tagged(_pick(c, "name", "issuer", "date", "text"), c) for c in data.get("certificates", [])],
        "languages": [_language(lang, answer_keys) for lang in data.get("languages", [])],
        "skills": [tagged({"name": text(s["name"]), "keywords": _keywords(s.get("keywords"), answer_keys)}, s)
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
        "name": text(person.get("name")),
        "label": text(person.get("label")),
        "email": text(person.get("email")),
        "url": text(person.get("url")),
        "phone": text(person.get("phone")),
        "location": location,
        "details": [d for d in details if d],
        "summary": text(summary.get("summary")),
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


def _work(entry: dict, tag_keys: bool, extra: tuple[str, ...] = ()) -> dict:
    work = _pick(entry, "position", "name", "location", "startDate", "endDate", *extra, keep_end=True)
    highlights = [line for line in (_highlight(h, tag_keys) for h in entry.get("highlights") or []) if line]
    return _tagged({**work, "highlights": highlights} if highlights else work, entry, tag_keys)


def _highlight(line, tag_keys: bool) -> str | dict | None:
    """A highlight as lebenslauf/README.md has it: text, or {text, tags} when it has tags (G24)."""
    if not isinstance(line, dict):
        return text(line) or None
    line_text, tags = text(line.get("text")), items(line.get("tags"))
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


def _pick(entry: dict, *keys: str, keep_end: bool = False) -> dict:
    """Selected non-empty text fields; with keep_end an empty endDate means 'ongoing' (None)."""
    picked = {key: text(entry.get(key)) for key in keys}
    result = {key: value for key, value in picked.items() if value}
    if keep_end and result.get("startDate") and not result.get("endDate"):
        result["endDate"] = None
    return result


def _dump_yaml(value: dict) -> str:
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=4096)
