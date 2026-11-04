"""Turn a validated onboarding bundle into the four basics of a data folder.

`convert_bundle` is pure: it returns the file contents by relative path and writes nothing.
The CV follows the JSON Resume schema used by `lebenslauf/` (see its README); the Markdown
files follow the templates in `vorlagen/`.
"""
import datetime
import urllib.parse

import yaml

import markdown_files
from values import items, text

APPRENTICESHIP_HEADINGS = {"erfahrung": "Schnupperlehren & Erfahrungen", "bildung": "Schule & Eignungstests"}
NETWORKS = {"linkedin": "LinkedIn", "github": "GitHub", "xing": "XING", "gitlab": "GitLab"}


BASICS = ("cv.yaml", "suchprofil.md", "anschreiben/stil.md", "anschreiben/bausteine.md")


def convert_bundle(form: dict, bundle: dict, today: datetime.date) -> dict[str, str]:
    """Map a bundle that passed validation.validate_bundle to {relative path: file text}."""
    data = bundle["data"]
    track = bundle["track"]
    note = f"Erstellt mit der Einstiegsvorlage am {today.day}.{today.month}.{today.year}"
    return {
        "cv.yaml": f"# {note}. Format: lebenslauf/README.md\n" + _dump_yaml(build_cv(data, track)),
        "suchprofil.md": markdown_files.search_profile(data, track, note),
        "anschreiben/stil.md": markdown_files.style_profile(form, data, track, note),
        "anschreiben/bausteine.md": markdown_files.building_blocks(data, track, note),
    }


def build_cv(data: dict, track: str) -> dict:
    person = data.get("person", {})
    cv = {"basics": _basics(person, data.get("summary", {}))}
    sections = {
        "work": [_work(w) for w in data.get("work", [])],
        "education": [_pick(e, "studyType", "area", "institution", "startDate", "endDate", keep_end=True)
                      for e in data.get("education", [])],
        "certificates": [_pick(c, "name", "issuer", "date") for c in data.get("certificates", [])],
        "languages": [_pick(lang, "language", "fluency") for lang in data.get("languages", [])],
        "skills": [{"name": text(s["name"]), "keywords": items(s.get("keywords"))} for s in data.get("skills", [])],
        "interests": [{"name": name} for name in items(data.get("interests", {}).get("interests"))],
    }
    cv.update({key: value for key, value in sections.items() if value})
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
        "phone": text(person.get("phone")),
        "location": location,
        "details": [d for d in details if d],
        "summary": text(summary.get("summary")),
        "profiles": [_profile(url) for url in items(person.get("profiles"))],
    }
    return {key: value for key, value in basics.items() if value}


def _profile(url: str) -> dict:
    full = url if url.startswith(("http://", "https://")) else f"https://{url}"
    try:
        host = urllib.parse.urlsplit(full).hostname or url
    except ValueError:  # e.g. an unclosed "[" that urlsplit reads as an IPv6 host
        host = url
    host = host.removeprefix("www.")
    network = next((name for key, name in NETWORKS.items() if host.startswith(key + ".")), host)
    return {"network": network, "url": full}


def _work(entry: dict) -> dict:
    work = _pick(entry, "position", "name", "location", "startDate", "endDate", keep_end=True)
    highlights = items(entry.get("highlights"))
    return {**work, "highlights": highlights} if highlights else work


def _pick(entry: dict, *keys: str, keep_end: bool = False) -> dict:
    """Selected non-empty text fields; with keep_end an empty endDate means 'ongoing' (None)."""
    picked = {key: text(entry.get(key)) for key in keys}
    result = {key: value for key, value in picked.items() if value}
    if keep_end and result.get("startDate") and not result.get("endDate"):
        result["endDate"] = None
    return result


def _dump_yaml(value: dict) -> str:
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=4096)
