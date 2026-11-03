"""What the browser extension searches for (MIN-339): keywords and places per portal, from suchprofil.md.

The profile is Markdown for people and the skill `jobsuche`. Read here are the lines `- Label: value` in the
sections Region, Keywords and Titelfilter, and the table in „Portale und Rhythmus“. A profile from the
einstieg template only has place of residence and cantons; the rest is derived from them.
"""
import dataclasses
import pathlib
import re

import yaml

PORTALS = ("job-room", "jobs.ch", "jobscout24", "ictjobs")
CANTONS = ("AG", "AI", "AR", "BE", "BL", "BS", "FR", "GE", "GL", "GR", "JU", "LU", "NE", "NW", "OW", "SG", "SH",
           "SO", "SZ", "TG", "TI", "UR", "VD", "VS", "ZG", "ZH")
# Regions of ictjobs (filter fltr_location) per canton
ICTJOBS_REGIONS = {
    "ZH": "grossraum-zuerich", "BE": "grossraum-bern", "BS": "grossraum-basel", "BL": "grossraum-basel",
    "AG": "aargau", "SO": "solothurn", "LU": "zentralschweiz", "ZG": "zentralschweiz", "SZ": "zentralschweiz",
    "OW": "zentralschweiz", "NW": "zentralschweiz", "UR": "zentralschweiz", "SG": "nord-ostschweiz-fl",
    "TG": "nord-ostschweiz-fl", "AR": "nord-ostschweiz-fl", "AI": "nord-ostschweiz-fl", "SH": "nord-ostschweiz-fl",
    "GL": "nord-ostschweiz-fl", "GR": "graubuenden", "VS": "wallis", "GE": "westschweiz", "VD": "westschweiz",
    "NE": "westschweiz", "JU": "westschweiz", "FR": "westschweiz", "TI": "tessin",
}
MAX_KEYWORDS = 15
MAX_PLACES = 6
MAX_PAGES = 3  # per keyword and place, as in the skill
MAX_QUERIES = 30  # keyword × place combinations per portal
MAX_AGE_DAYS = 45
MAX_VALUE = 80
APPRENTICESHIP_MARK = "## Lehrbeginn"
PROFILE = "suchprofil.md"
DIRECTION = re.compile(r"^\d+\.\s+(.+)$")
PAIR = re.compile(r"^-\s+([^:]+):\s*(.*)$")
MODE_OFF = "aus"


@dataclasses.dataclass(frozen=True)
class SearchPlan:
    keywords: tuple[str, ...]
    niche_keywords: tuple[str, ...] = ()
    cantons: tuple[str, ...] = ()
    places: tuple[str, ...] = ()
    postal_codes: tuple[str, ...] = ()
    regions: tuple[str, ...] = ()
    title_exclude: tuple[str, ...] = ()
    portals: tuple[str, ...] = PORTALS
    hints: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {"portale": list(self.portals), "stichworte": list(self.keywords), "nischen": list(self.niche_keywords),
                "kantone": list(self.cantons), "orte": list(self.places), "plz": list(self.postal_codes),
                "regionen": list(self.regions), "titel_ausschluss": list(self.title_exclude),
                "max_seiten": MAX_PAGES, "max_abfragen": MAX_QUERIES, "max_alter_tage": MAX_AGE_DAYS,
                "hinweise": list(self.hints)}


def _sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip().lower()
            sections[current] = []
        elif current is not None and line.strip():
            sections[current].append(line.strip())
    return sections


def _pairs(lines: list[str]) -> dict[str, str]:
    found = {}
    for line in lines:
        match = PAIR.match(line)
        if match:
            found.setdefault(match.group(1).strip().lower(), match.group(2).strip())
    return found


def _value(pairs: dict[str, str], *prefixes: str) -> str:
    return next((v for label, v in pairs.items() for p in prefixes if label.startswith(p)), "")


def _items(text: str, limit: int) -> tuple[str, ...]:
    """Comma-separated values: trimmed, without duplicates (ignoring case), bounded in number and length."""
    seen, result = set(), []
    for raw in text.split(","):
        value = " ".join(raw.replace("`", "").split())[:MAX_VALUE]
        if value and value.lower() not in seen:
            seen.add(value.lower())
            result.append(value)
    return tuple(result[:limit])


def _directions(lines: list[str]) -> tuple[str, ...]:
    """Numbered search directions without the remark in brackets, e.g. „(Priorität 2, …)“."""
    names = [DIRECTION.match(line).group(1) for line in lines if DIRECTION.match(line)]
    return _items(",".join(re.sub(r"\s*\(.*$", "", name) for name in names), MAX_KEYWORDS)


def _modes(lines: list[str]) -> dict[str, str]:
    modes = {}
    for line in lines:
        cells = [c.strip().lower() for c in line.strip("|").split("|")]
        if len(cells) >= 2:
            modes[cells[0]] = cells[1]
    return modes


def _regions(cantons: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(ICTJOBS_REGIONS[c] for c in cantons if c in ICTJOBS_REGIONS))


def parse(text: str, postal_code: str | None = None) -> SearchPlan:
    """The search plan from the profile text; postal_code (from cv.yaml) stands in for missing PLZ."""
    if APPRENTICESHIP_MARK in text:
        raise ValueError("Die Suche nach Lehrstellen über die Erweiterung kommt später. "
                         "Bis dahin Lehrstellen als Text in einer neuen Bewerbung einfügen.")
    sections = _sections(text)
    region = _pairs(sections.get("region", []))
    words = _pairs(sections.get("keywords", []))
    titles = _pairs(sections.get("titelfilter", []))
    keywords = _items(_value(words, "kernliste"), MAX_KEYWORDS) or _directions(sections.get("suchrichtungen", []))
    if not keywords:
        raise ValueError("Im Suchprofil fehlen Stichworte für die Suche (Abschnitt „Keywords“, Zeile „Kernliste“) "
                         "oder gesuchte Stellen (Abschnitt „Suchrichtungen“).")
    cantons = tuple(c for c in dict.fromkeys(_items(_value(region, "kantone"), len(CANTONS))) if c in CANTONS)
    places = _items(_value(region, "orte"), MAX_PLACES) or _items(_value(region, "wohnort"), 1)
    postal_codes = _items(_value(region, "plz"), MAX_PLACES) or _items(postal_code or "", 1)
    regions = _items(_value(region, "regionen"), MAX_PLACES) or _regions(cantons)
    modes = _modes(sections.get("portale und rhythmus", []))
    portals, hints = [], []
    needs = {"job-room": cantons, "jobs.ch": places, "jobscout24": postal_codes, "ictjobs": regions}
    missing = {"job-room": "Kantone", "jobs.ch": "Wohnort oder Orte", "jobscout24": "PLZ",
               "ictjobs": "Kantone oder Regionen"}
    for portal in PORTALS:
        if modes.get(portal) == MODE_OFF:
            continue
        if not needs[portal]:
            hints.append(f"{portal}: im Suchprofil fehlen {missing[portal]}, darum wird dort nicht gesucht.")
            continue
        portals.append(portal)
    return SearchPlan(keywords=keywords, niche_keywords=_items(_value(words, "nischen"), MAX_KEYWORDS),
                      cantons=cantons, places=places, postal_codes=postal_codes, regions=regions,
                      title_exclude=_items(_value(titles, "ausschluss"), 30), portals=tuple(portals),
                      hints=tuple(hints))


def _postal_code(data_dir: pathlib.Path) -> str | None:
    try:
        cv = yaml.safe_load((data_dir / "cv.yaml").read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return None
    location = (cv.get("basics") or {}).get("location") if isinstance(cv, dict) else None
    code = location.get("postalCode") if isinstance(location, dict) else None
    return str(code) if code else None


def for_folder(data_dir: pathlib.Path) -> SearchPlan:
    path = data_dir / PROFILE
    if not path.is_file():
        raise ValueError("Es gibt noch kein Suchprofil. Zuerst den Einstieg abschliessen.")
    return parse(path.read_text(encoding="utf-8"), _postal_code(data_dir))
