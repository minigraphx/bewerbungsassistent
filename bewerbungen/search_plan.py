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
PORTAL_HINTS = {"job-room": "Stellen der RAV, alle Berufe", "jobs.ch": "alle Berufe", "jobscout24": "alle Berufe",
                "ictjobs": "nur Informatik", "LENA": "offizielle Lehrstellen der Kantone", "yousty": "Lehrstellen und Schnupperlehren"}
SPECIALIST_PORTAL = "ictjobs"
# Word starts alone match too much (#107): Administration, Datenschutz, Systemgastronomie, Testfahrer.
COMPUTING = re.compile(r"informati|software|entwickl|developer|programm|devops|cloud|netzwerk|cyber|security"
                       r"|\bsystems?\b|system(?:admin|techni|ingenieur|engineer|spezialist|integrat|architekt|betreu)"
                       r"|\badmin\b|(?:sys|system|netzwerk|datenbank|server)admin"
                       r"|\bit\b|\bict\b|\bki\b|\bai\b|data|daten(?:bank|analy|ingenieur|wissenschaft|management|architekt)"
                       r"|digital|applikation|web|frontend|backend|fullstack"
                       r"|engineer|python|java|typescript|sql|linux|sap|product owner|scrum|business analy|helpdesk|service desk"
                       r"|\btest(?:er|ing|ingenieur|automat|analy|manag|engineer)?\b|\btest(?:ingenieur|automat|analy|manag)"
                       r"|\bux\b|\bui\b|mediamatik", re.IGNORECASE)
NO_PORTAL_LEFT = "Mindestens ein Portal muss gewählt bleiben, sonst findet die Suche nichts."
BAD_CHOICE = "Diese Auswahl der Portale geht nicht."
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
MAX_LISTED = 100  # terms read from the profile before the limit, so that a hint can name what is not searched
MAX_PLACES = 6
MAX_PAGES = 3  # per keyword and place, as in the skill
MAX_QUERIES = 30  # keyword × place combinations per portal
MAX_TEXTS = 150  # new ads per portal and run: a search all over Switzerland can find thousands; the rest comes next run
MAX_AGE_DAYS = 45
MAX_VALUE = 80
MAX_PROFESSIONS = 8
MAX_APPRENTICESHIP_PAGES = 20  # the lists are short pages, and only the search area is asked for
DEFAULT_RADIUS_KM = 25
MIN_RADIUS_KM = 5
MAX_RADIUS_KM = 100
APPRENTICESHIP_MARK = "## Lehrbeginn"
AGENCIES_SECTION = "## Vermittler"
NO_PROFESSION = "In deiner Suche steht noch kein Beruf. Unter „Welcher Beruf passt zu dir?“ schlägt dir die KI Berufe vor."
NO_TERMS = "In der Suche steht noch nichts. Auf der Seite der Suche schlägt die KI Begriffe vor."
PLACE_SHARE = ("{portal}: {limit} Suchen reichen nicht für alle {terms} Begriffe in {places} Orten; pro Ort laufen die ersten "
               "{share}. Wichtige Begriffe nach vorne stellen.")
TOO_MANY_TERMS = "Gesucht werden höchstens {limit} Begriffe. Nicht gesucht: {terms}. Weniger wichtige Begriffe entfernen."
CORE_LABEL = "kernliste"
NICHE_LABEL = "nischen"
NOTHING_OF_KIND = {KIND_APPRENTICESHIP: NO_PROFESSION, KIND_JOB: NO_TERMS}
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
FIELD_CANTONS = "searchJob.cantons"
FIELD_HOME = "searchJob.home"
FIELD_POSTAL_CODE = "person.postalCode"
FIELD_APPRENTICESHIP_HOME = "searchApprenticeship.home"
NATIONWIDE_NOTE = "Gesucht wird in der ganzen Schweiz, Stellen nahe dem Wohnort stehen zuerst. Eingrenzen: Kantone wählen."
REMARK = re.compile(r"\s*\([^()]*\b(?:priorität|ersatz|falls|wenn|notfalls)\b[^()]*\)\s*$", re.IGNORECASE)
# A remark such as „Biel (kleine Gemeinden liefern 0 Treffer)“ is no part of the value; portals and the title filter
# match whole terms, so „Java/.NET“ means two. A gender form such as „Sachbearbeiter/in“ stays one term.
BRACKETS = re.compile(r"\s*\([^()]*\)")
SLASH = re.compile(r"\s*/(?!-?(?:in|innen|frau|mann|euse|r)\b)\s*", re.IGNORECASE)
YEAR = re.compile(r"\b20\d\d\b")
NUMBER = re.compile(r"\d+")


class ProfileGap(ValueError):
    """Something the search needs is missing; `field` is where „Meine Angaben“ asks for it."""

    def __init__(self, message: str, field: str) -> None:
        super().__init__(message)
        self.field = field


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
    nationwide: bool = False
    hint_targets: tuple[tuple[str, str], ...] = ()  # hint → field in „Meine Angaben“

    def as_dict(self) -> dict:
        pages = MAX_APPRENTICESHIP_PAGES if self.kind == KIND_APPRENTICESHIP else MAX_PAGES
        return {"art": self.kind, "portale": list(self.portals), "stichworte": list(self.keywords),
                "nischen": list(self.niche_keywords), "kantone": list(self.cantons), "orte": list(self.places),
                "plz": list(self.postal_codes), "regionen": list(self.regions),
                "titel_ausschluss": list(self.title_exclude), "umkreis_km": self.radius_km,
                "lehrbeginn_jahre": list(self.start_years), "angebote": list(self.offers), "max_seiten": pages, "max_abfragen": MAX_QUERIES,
                "max_alter_tage": MAX_AGE_DAYS, "max_texte": MAX_TEXTS, "hinweise": list(self.hints), "schweizweit": self.nationwide,
                "hinweis_ziele": dict(self.hint_targets)}


def _portals_of_kind(kind: str) -> tuple[str, ...]:
    return APPRENTICESHIP_PORTALS if kind == KIND_APPRENTICESHIP else PORTALS


def _off(plan: SearchPlan, switched_off: list[str] | None) -> frozenset[str]:
    """The choice of the person; until there is one, the profile, and a specialist portal only if it can fit."""
    if switched_off is not None:
        return frozenset(switched_off)
    unfit = plan.keywords and _computing_term(plan) is None
    from_profile = frozenset(p for p in _portals_of_kind(plan.kind) if p not in plan.portals)
    others_left = any(p not in from_profile and p != SPECIALIST_PORTAL for p in _portals_of_kind(plan.kind))
    return from_profile | {SPECIALIST_PORTAL} if unfit and others_left else from_profile


def chosen(plan: SearchPlan, switched_off: list[str] | None) -> SearchPlan:
    """The plan with the portals the person wants (MIN-388); nothing about a portal that is off."""
    off = _off(plan, switched_off)
    targets = tuple(pair for pair in plan.hint_targets if pair[0].split(":")[0] not in off)
    return dataclasses.replace(plan, portals=tuple(p for p in _portals_of_kind(plan.kind) if p not in off),
                               hints=tuple(h for h in plan.hints if h.split(":")[0] not in off), hint_targets=targets)


def _computing_term(plan: SearchPlan) -> str | None:
    return next((term for term in (*plan.keywords, *plan.niche_keywords) if COMPUTING.search(term)), None)


def _specialist_reason(plan: SearchPlan, switched_off: list[str] | None, on: bool) -> dict:
    """Why ictjobs is on or off (#107): chosen by the person, no terms yet, a term that fits, or none fits."""
    if switched_off is not None:
        return {"grund": "gewaehlt"}
    if SPECIALIST_PORTAL not in plan.portals:
        return {}  # off in the profile itself; the box says enough
    if not plan.keywords:
        return {"grund": "keine"}
    term = _computing_term(plan)
    if term:
        return {"grund": "passt", "begriff": term}
    return {} if on else {"grund": "aus"}  # on although nothing fits: the only portal left


def portal_choice(plan: SearchPlan, switched_off: list[str] | None) -> list[dict]:
    off = _off(plan, switched_off)
    choice = []
    for name in _portals_of_kind(plan.kind):
        item = {"name": name, "hinweis": PORTAL_HINTS[name], "an": name not in off}
        reason = _specialist_reason(plan, switched_off, item["an"]) if name == SPECIALIST_PORTAL else {}
        choice.append({**item, **reason})
    return choice


def checked_choice(switched_off, kind: str) -> list[str]:
    """What may be stored as the portals that are off; ValueError with a message for the person if not."""
    if not isinstance(switched_off, list) or any(p not in ALL_PORTALS for p in switched_off):
        raise ValueError(BAD_CHOICE)
    if all(p in switched_off for p in _portals_of_kind(kind)):
        raise ValueError(NO_PORTAL_LEFT)
    return list(dict.fromkeys(switched_off))


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


def _gender_pair(left: str, right: str) -> bool:
    """„Koch/Köchin EFZ“ or „Fachfrau/Fachmann“: the words at the slash are one word in two forms."""
    last, first = left.lower().split()[-1:], right.lower().split()[:1]
    return bool(last and first) and _neutral_word(last[0]) == _neutral_word(first[0])


def _slash_terms(value: str) -> list[str]:
    terms: list[str] = []
    for piece in SLASH.split(value):
        if terms and _gender_pair(terms[-1], piece):
            terms = [*terms[:-1], f"{terms[-1]}/{piece}"]
        else:
            terms = [*terms, piece]
    return terms


def split_terms(text: str) -> list[str]:
    """The single terms of a value: without remarks in brackets, split on commas and on slashes."""
    return [part for value in BRACKETS.sub("", text).split(",") for part in _slash_terms(value)]


def _terms(text: str, limit: int) -> tuple[str, ...]:
    return _items(",".join(split_terms(text)), limit)


def _directions(lines: list[str], limit: int = MAX_KEYWORDS) -> tuple[str, ...]:
    """Numbered search directions without the remark in brackets, e.g. „(Priorität 2, …)“."""
    names = [DIRECTION.match(line).group(1) for line in lines if DIRECTION.match(line)]
    return _items(",".join(re.sub(r"\s*\(.*$", "", name) for name in names), limit)


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


def profession_forms(name: str) -> tuple[str, ...]:
    """The forms of a name such as „Bäckerin-Konditorin EFZ / Bäcker-Konditor EFZ“; only „ / “ with spaces separates them."""
    return tuple(form.strip() for form in re.split(r"\s+/\s+", name) if form.strip())


def profession_words(name: str) -> frozenset[str]:
    """What makes two names the same profession on the portals: „Fachfrau/Fachmann Gesundheit EFZ“ and „Fachfrau Gesundheit EFZ“.

    A name in two forms counts by its first, as portals/common.js does.
    """
    forms = profession_forms(name)
    plain = re.sub(r"/-?(?:in|frau|mann|euse|r)\b", "", forms[0].lower() if forms else "")
    words = ("-".join(map(_neutral_word, word.split("-"))) for word in re.split(r"[\s,;()/]+", plain) if word and word not in FILLER_WORDS)
    return frozenset(word for word in words if word.replace("-", ""))


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
        raise ValueError(NO_PROFESSION)
    region = _pairs(sections.get("region", []))
    cantons = tuple(c for c in dict.fromkeys(_items(_value(region, "kantone"), len(CANTONS))) if c in CANTONS)
    places = _items(_value(region, "wohnort"), 1)
    if not places and not cantons:
        raise ProfileGap("Im Suchprofil fehlt der Wohnort oder ein Kanton (Abschnitt „Region“).", FIELD_APPRENTICESHIP_HOME)
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


def section_lines(text: str, title: str) -> list[str]:
    """The filled lines of a section as they are written."""
    lines = text.split("\n")
    start, end = section_bounds(lines, title[3:].strip().lower())
    return [] if start is None else [row for row in lines[start + 1:end] if row.strip()]


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


def _listed_terms(sections: dict[str, list[str]]) -> tuple[str, ...]:
    """The first core list, then every other named line under Keywords but the niches (#174); else the search directions."""
    pairs = _pairs(sections.get("keywords", []))
    others = [value for label, value in pairs.items() if not label.startswith((CORE_LABEL, NICHE_LABEL))]
    terms = _terms(",".join([_value(pairs, CORE_LABEL), *others]), MAX_LISTED)
    return terms or _directions(sections.get("suchrichtungen", []), MAX_LISTED)


def _job_terms(sections: dict[str, list[str]]) -> tuple[str, ...]:
    return _listed_terms(sections)[:MAX_KEYWORDS]


def job_terms(text: str) -> tuple[str, ...]:
    return _job_terms(_sections(text))


def _job_hints(nationwide: bool, portals: tuple[str, ...], cantons: tuple[str, ...], regions: tuple[str, ...],
               places: tuple[str, ...], postal_codes: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    """What the person may want to add, each with the field to add it in. No portal is skipped for a missing place."""
    if nationwide:
        return ((NATIONWIDE_NOTE, FIELD_CANTONS),)
    gaps = (("job-room", cantons, "Kantone", FIELD_CANTONS), ("jobs.ch", places, "Wohnort", FIELD_HOME),
            ("jobscout24", postal_codes, "PLZ", FIELD_POSTAL_CODE), ("ictjobs", regions, "Kantone", FIELD_CANTONS))
    return tuple((f"{portal}: Ohne {name} sucht dieses Portal in der ganzen Schweiz. {name} ergänzen.", field)
                 for portal, known, name, field in gaps if portal in portals and not known)


def _place_shares(portals: tuple[str, ...], keywords: int, niches: int,
                  places_of: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    """Where the places of a portal share its limit, how far each gets; as erweiterung/lib/queries.js placeQuotas (#175)."""
    hints = []
    for portal, places in places_of.items():
        free = niches if portal == "jobs.ch" else 0
        share = max(len(places), MAX_QUERIES - free) // len(places) if places else keywords
        if portal in portals and share < keywords:
            hints = [*hints, PLACE_SHARE.format(portal=portal, limit=MAX_QUERIES, terms=keywords, places=len(places), share=share)]
    return tuple(hints)


def parse(text: str, postal_code: str | None = None) -> SearchPlan:
    """The search plan from the profile text; postal_code (from cv.yaml) stands in for missing PLZ."""
    sections = _sections(text)
    if APPRENTICESHIP_MARK in text:
        return _parse_apprenticeship(sections)
    region = _pairs(sections.get("region", []))
    words = _pairs(sections.get("keywords", []))
    titles = _pairs(sections.get("titelfilter", []))
    listed = _listed_terms(sections)
    keywords = listed[:MAX_KEYWORDS]
    if not keywords:
        raise ValueError(NO_TERMS)
    niches = _terms(_value(words, NICHE_LABEL), MAX_LISTED)
    cantons = tuple(c for c in dict.fromkeys(_items(_value(region, "kantone"), len(CANTONS))) if c in CANTONS)
    places = _terms(_value(region, "orte"), MAX_PLACES) or _terms(_value(region, "wohnort"), 1)
    postal_codes = _items(_value(region, "plz"), MAX_PLACES) or _items(postal_code or "", 1)
    regions = _items(_value(region, "regionen"), MAX_PLACES) or _regions(cantons)
    modes = _modes(sections.get("portale und rhythmus", []))
    portals = tuple(portal for portal in PORTALS if modes.get(portal) != MODE_OFF)
    nationwide = not cantons and not any(_value(region, name) for name in ("orte", "plz", "regionen"))
    targets = _job_hints(nationwide, portals, cantons, regions, places, postal_codes)
    dropped = (*listed[MAX_KEYWORDS:], *niches[MAX_KEYWORDS:])
    limit_hint = (TOO_MANY_TERMS.format(limit=MAX_KEYWORDS, terms=", ".join(dropped)),) if dropped else ()
    shares = _place_shares(portals, len(keywords), len(niches[:MAX_KEYWORDS]),
                           {"jobs.ch": places, "jobscout24": postal_codes, "ictjobs": regions})
    return SearchPlan(keywords=keywords, niche_keywords=niches[:MAX_KEYWORDS],
                      cantons=cantons, places=places, postal_codes=postal_codes, regions=regions,
                      title_exclude=_terms(_value(titles, "ausschluss"), 30), portals=portals,
                      hints=(*limit_hint, *shares, *(hint for hint, _ in targets)), nationwide=nationwide,
                      hint_targets=targets)


def agencies_in(text: str) -> tuple[str, ...]:
    """Staffing agencies the profile adds to the known ones (G34), section „Vermittler“."""
    values = [match[2] for match in map(PAIR.match, section_lines(text, AGENCIES_SECTION)) if match]
    return tuple(dict.fromkeys(name.strip() for value in values for name in value.split(",") if name.strip()))


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
