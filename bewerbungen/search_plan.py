"""What the browser extension searches for (MIN-339): keywords and places per portal, from suchprofil.md.

The profile is Markdown for people and the skill `jobsuche`. Read here are the lines `- Label: value` in the
sections Region, Keywords and Titelfilter, and the table in „Portale und Rhythmus“. A profile from the
einstieg template only has place of residence and cantons; the rest is derived from them.

An apprenticeship profile (section „Lehrbeginn“, MIN-365) searches other portals: its professions take the place
of the keywords, around the place of residence or else in the cantons. Section „Gesucht“ says whether apprenticeships,
trial apprenticeships or both (MIN-373); „Schnupperlehren“ in such a profile lists those already done, not a wish.
"""
import dataclasses
import pathlib
import re

import yaml

PORTALS = ("job-room", "jobs.ch", "jobscout24", "ictjobs")
APPRENTICESHIP_PORTALS = ("LENA", "yousty")
ALL_PORTALS = PORTALS + APPRENTICESHIP_PORTALS
KIND_JOB = "stelle"
KIND_APPRENTICESHIP = "lehrstelle"
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
MAX_PROFESSIONS = 8
MAX_APPRENTICESHIP_PAGES = 20  # the lists are short pages, and only the search area is asked for
DEFAULT_RADIUS_KM = 25
MIN_RADIUS_KM = 5
MAX_RADIUS_KM = 100
APPRENTICESHIP_MARK = "## Lehrbeginn"
OFFERS_SECTION = "## Gesucht"
PROFESSIONS_SECTION = "## Berufe (mit Priorität)"
PROFESSIONS_KEY = PROFESSIONS_SECTION[3:].lower()
FILLER_WORDS = frozenset({"fachrichtung", "schwerpunkt", "und", "mit", "im", "der", "die", "das"})
OFFER_APPRENTICESHIP = "lehrstelle"
OFFER_TRIAL = "schnupperlehre"
CHOICE_BOTH = "beides"
# What the page can choose: the offers it stands for and the words in the profile, the same as in the form.
OFFER_CHOICES = {
    OFFER_APPRENTICESHIP: ((OFFER_APPRENTICESHIP,), "Lehrstellen"),
    OFFER_TRIAL: ((OFFER_TRIAL,), "Schnupperlehren"),
    CHOICE_BOTH: ((OFFER_APPRENTICESHIP, OFFER_TRIAL), "Lehrstellen und Schnupperlehren"),
}
PROFILE = "suchprofil.md"
DIRECTION = re.compile(r"^\d+\.\s+(.+)$")
PAIR = re.compile(r"^-\s+([^:]+):\s*(.*)$")
MODE_OFF = "aus"
REMARK = re.compile(r"\s*\([^()]*\b(?:priorität|ersatz|falls|wenn|notfalls)\b[^()]*\)\s*$", re.IGNORECASE)
YEAR = re.compile(r"\b20\d\d\b")
NUMBER = re.compile(r"\d+")


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
    kind: str = KIND_JOB
    radius_km: int = DEFAULT_RADIUS_KM
    start_years: tuple[int, ...] = ()
    offers: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        pages = MAX_APPRENTICESHIP_PAGES if self.kind == KIND_APPRENTICESHIP else MAX_PAGES
        return {"art": self.kind, "portale": list(self.portals), "stichworte": list(self.keywords),
                "nischen": list(self.niche_keywords), "kantone": list(self.cantons), "orte": list(self.places),
                "plz": list(self.postal_codes), "regionen": list(self.regions),
                "titel_ausschluss": list(self.title_exclude), "umkreis_km": self.radius_km,
                "lehrbeginn_jahre": list(self.start_years), "angebote": list(self.offers), "max_seiten": pages, "max_abfragen": MAX_QUERIES,
                "max_alter_tage": MAX_AGE_DAYS, "hinweise": list(self.hints)}


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


def _professions(lines: list[str]) -> tuple[str, ...]:
    """Numbered professions without the remark at the end; a specialisation in brackets stays."""
    names = (" ".join(REMARK.sub("", m.group(1)).split())[:MAX_VALUE] for m in map(DIRECTION.match, lines) if m)
    return tuple(dict.fromkeys(name for name in names if name))[:MAX_PROFESSIONS]


def _neutral_word(word: str) -> str:
    """One word of a profession without its gender form, as the extension compares them (portals/common.js)."""
    word = re.sub(r"euse$", "eur", "koch" if word == "köchin" else word)
    return re.sub(r"(er|ent|ant|ist|eur|or)in$", r"\1", re.sub(r"(frau|mann)$", "", word))


def profession_words(name: str) -> frozenset[str]:
    """What makes two names the same profession on the portals: „Fachfrau/Fachmann Gesundheit EFZ“ and „Fachfrau Gesundheit EFZ“."""
    plain = re.sub(r"/-?(?:in|frau|mann|euse|r)\b", "", name.lower())
    words = (_neutral_word(word) for word in re.split(r"[\s,;()/]+", plain) if word and word not in FILLER_WORDS)
    return frozenset(word for word in words if word)


def professions_in(text: str) -> tuple[str, ...]:
    return _professions(_sections(text).get(PROFESSIONS_KEY, []))


def _radius(value: str) -> int:
    number = NUMBER.search(value)
    return min(MAX_RADIUS_KM, max(MIN_RADIUS_KM, int(number.group()))) if number else DEFAULT_RADIUS_KM


def _offers(lines: list[str]) -> tuple[str, ...]:
    """What the section „Gesucht“ asks for; without a clear wish, apprenticeships."""
    wish = " ".join(lines).lower()
    trial, apprenticeship = "schnupper" in wish, "lehrstelle" in wish
    if "beid" in wish or (trial and apprenticeship):
        return OFFER_CHOICES[CHOICE_BOTH][0]
    return (OFFER_TRIAL,) if trial else (OFFER_APPRENTICESHIP,)


def with_offers(text: str, choice: str) -> str:
    """The profile text with this wish in section „Gesucht“; everything else stays as it is."""
    if choice not in OFFER_CHOICES:
        raise ValueError("Bitte Lehrstellen, Schnupperlehren oder beides wählen.")
    if APPRENTICESHIP_MARK not in text:
        raise ValueError("Schnupperlehren gibt es nur bei der Lehrstellensuche.")
    section = f"{OFFERS_SECTION}\n- {OFFER_CHOICES[choice][1]}\n\n"
    without = re.sub(rf"^{OFFERS_SECTION}[ \t]*(?:\n|\Z)(?:(?!## ).*\n?)*", "", text, flags=re.MULTILINE)
    return without.replace(APPRENTICESHIP_MARK, section + APPRENTICESHIP_MARK, 1)


def _parse_apprenticeship(sections: dict[str, list[str]]) -> SearchPlan:
    professions = _professions(sections.get(PROFESSIONS_KEY, []))
    if not professions:
        raise ValueError("In deiner Suche steht noch kein Beruf. Unter „Welcher Beruf passt zu dir?“ schlägt dir die KI Berufe vor.")
    region = _pairs(sections.get("region", []))
    cantons = tuple(c for c in dict.fromkeys(_items(_value(region, "kantone"), len(CANTONS))) if c in CANTONS)
    places = _items(_value(region, "wohnort"), 1)
    if not places and not cantons:
        raise ValueError("Im Suchprofil fehlt der Wohnort oder ein Kanton (Abschnitt „Region“).")
    radius = _radius(_value(region, "umkreis"))
    years = sorted({int(y) for line in sections.get("lehrbeginn", []) for y in YEAR.findall(line)})
    hints = ()
    if places and len(cantons) > 1:
        hints = (f"Gesucht wird im Umkreis von {radius} km um {places[0]}. Die Kantone {', '.join(cantons)} "
                 "werden nicht einzeln durchsucht.",)
    modes = _modes(sections.get("portale und rhythmus", []))
    return SearchPlan(keywords=professions, cantons=cantons, places=places, hints=hints, kind=KIND_APPRENTICESHIP,
                      portals=tuple(p for p in APPRENTICESHIP_PORTALS if modes.get(p.lower()) != MODE_OFF),
                      radius_km=radius, start_years=tuple(years), offers=_offers(sections.get("gesucht", [])))


def with_profession(text: str, name: str) -> str:
    """The profile text with this profession at the end of its list; everything else stays as it is."""
    if APPRENTICESHIP_MARK not in text:
        raise ValueError("Berufe aufnehmen gibt es nur bei der Lehrstellensuche.")
    known = professions_in(text)
    if profession_words(name) in map(profession_words, known):
        return text
    if len(known) >= MAX_PROFESSIONS:
        raise ValueError(f"Deine Suche hat schon {MAX_PROFESSIONS} Berufe, mehr sucht sie nicht. Entferne zuerst einen.")
    line = f"{len(known) + 1}. {' '.join(name.split())}"
    return with_section_line(text, PROFESSIONS_SECTION, line, APPRENTICESHIP_MARK)


def section_bounds(lines: list[str], key: str) -> tuple[int | None, int]:
    """Where the section with this key starts, and where the next one does."""
    start = next((i for i, row in enumerate(lines) if row.startswith("## ") and row[3:].strip().lower() == key), None)
    if start is None:
        return None, len(lines)
    return start, next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))


def with_section_line(text: str, title: str, line: str, before: str) -> str:
    """Adds the line after the last filled line of the section, so that it stays last; a missing section comes before `before`."""
    lines = text.split("\n")
    start, end = section_bounds(lines, title[3:].strip().lower())
    if start is None:
        section = [title, line, ""]
        place = next((i for i, row in enumerate(lines) if row.strip() == before), None)
        if place is None:
            return f"{text.rstrip()}\n\n{title}\n{line}\n"
        return "\n".join([*lines[:place], *section, *lines[place:]])
    last = max((i for i in range(start, end) if lines[i].strip()), default=start)
    return "\n".join([*lines[:last + 1], line, *lines[last + 1:]])


def _job_terms(sections: dict[str, list[str]]) -> tuple[str, ...]:
    core = _items(_value(_pairs(sections.get("keywords", [])), "kernliste"), MAX_KEYWORDS)
    return core or _directions(sections.get("suchrichtungen", []))


def job_terms(text: str) -> tuple[str, ...]:
    return _job_terms(_sections(text))


def parse(text: str, postal_code: str | None = None) -> SearchPlan:
    """The search plan from the profile text; postal_code (from cv.yaml) stands in for missing PLZ."""
    sections = _sections(text)
    if APPRENTICESHIP_MARK in text:
        return _parse_apprenticeship(sections)
    region = _pairs(sections.get("region", []))
    words = _pairs(sections.get("keywords", []))
    titles = _pairs(sections.get("titelfilter", []))
    keywords = _job_terms(sections)
    if not keywords:
        raise ValueError("In Ihrer Suche steht noch nichts. Unter „Welche Stellen passen zu Ihnen?“ schlägt Ihnen die KI Begriffe vor.")
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


def kind_of_folder(data_dir: pathlib.Path) -> str:
    """The kind of search, also for a profile that cannot be searched with yet: pages use it for their wording."""
    path = data_dir / PROFILE
    if path.is_file() and APPRENTICESHIP_MARK in path.read_text(encoding="utf-8"):
        return KIND_APPRENTICESHIP
    return KIND_JOB


def for_folder(data_dir: pathlib.Path) -> SearchPlan:
    path = data_dir / PROFILE
    if not path.is_file():
        raise ValueError("Es gibt noch kein Suchprofil. Zuerst den Einstieg abschliessen.")
    return parse(path.read_text(encoding="utf-8"), _postal_code(data_dir))
