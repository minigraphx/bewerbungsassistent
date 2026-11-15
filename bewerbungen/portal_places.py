"""The place lines of single portals on Suche einstellen (#301, G64): Orte for jobs.ch, PLZ for jobscout24, Regionen
for ictjobs.

Such a line takes priority over Wohnort and Kantone for its portal, so a region change alone may not reach it. The
region card therefore shows these lines and lets the person change or empty them; an empty line goes, and the portal
follows Wohnort and Kantone again. No place is guessed from Wohnort or Kantone: a postal code or region the app made
up could send a portal to the wrong place without anyone noticing. Each new entry must be one the portal takes; an
entry the line already has stays allowed, so changing one entry never refuses the others.
"""
import re

import search_plan

KEYS = ("orte", "plz", "regionen")
PORTAL_OF = {"orte": "jobs.ch", "plz": "jobscout24", "regionen": "ictjobs"}
POSTAL_CODE = re.compile(r"\d{4}")
REGION_NAMES = {
    "grossraum-zuerich": "Grossraum Zürich", "grossraum-bern": "Grossraum Bern", "grossraum-basel": "Grossraum Basel",
    "aargau": "Aargau", "solothurn": "Solothurn", "zentralschweiz": "Zentralschweiz",
    "nord-ostschweiz-fl": "Nord- und Ostschweiz, Liechtenstein", "graubuenden": "Graubünden", "wallis": "Wallis",
    "westschweiz": "Westschweiz", "tessin": "Tessin",
}
NOT_A_LIST = "{name}: bitte als Liste senden."
TOO_LONG = "„{value}…“ ist zu lang: höchstens {limit} Zeichen."
TOO_MANY = "{name}: höchstens {limit} Einträge, mehr liest die Suche nicht."
BAD_POSTAL_CODE = "„{value}“ ist keine Postleitzahl: bitte vier Ziffern."
BAD_REGION = "Unbekannte Region für ictjobs: {value}."
NAMES = {"orte": "Orte für jobs.ch", "plz": "PLZ für jobscout24", "regionen": "Regionen für ictjobs"}


def _cantons_of(region: str) -> list[str]:
    return [canton for canton, value in search_plan.ICTJOBS_REGIONS.items() if value == region]


def region_choices(listed: list[str]) -> list[dict]:
    """Every region ictjobs knows, with its cantons, then any other region the profile already has."""
    known = [{"wert": region, "name": f"{REGION_NAMES.get(region, region)} ({', '.join(_cantons_of(region))})"}
             for region in dict.fromkeys(search_plan.ICTJOBS_REGIONS.values())]
    others = [{"wert": region, "name": region} for region in listed if region not in REGION_NAMES]
    return [*known, *others]


def shown(text: str) -> list[dict]:
    """Per portal with its own line, where it searches, as the search reads the line; nothing for an apprenticeship."""
    if search_plan.APPRENTICESHIP_MARK in text:
        return []
    own = search_plan.own_places(text)
    return [{"portal": portal, "orte": [REGION_NAMES.get(place, place) if portal == "ictjobs" else place
                                        for place in own[portal]]}
            for portal in PORTAL_OF.values() if own[portal]]


def _entries(key: str, value) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(NOT_A_LIST.format(name=NAMES[key]))
    unique: dict[str, str] = {}
    for item in (" ".join(item.split()) for item in value):
        if len(item) > search_plan.MAX_VALUE:
            raise ValueError(TOO_LONG.format(value=item[:20], limit=search_plan.MAX_VALUE))
        if item:
            unique.setdefault(item.lower(), item)
    return list(unique.values())


def _check_entry(key: str, entry: str) -> None:
    if key == "plz" and not POSTAL_CODE.fullmatch(entry):
        raise ValueError(BAD_POSTAL_CODE.format(value=entry))
    if key == "regionen" and entry not in REGION_NAMES:
        raise ValueError(BAD_REGION.format(value=entry))


def checked(key: str, value, listed: list[str]) -> list[str]:
    """The entries for the line of `key`; ValueError with a message for the person if the portal cannot take them.

    `listed` is what the line holds now: those entries stay allowed as they are."""
    entries = _entries(key, value)
    for entry in entries:
        if entry not in listed:
            _check_entry(key, entry)
    read = search_plan.split_terms(", ".join(entries)) if key == "orte" else entries
    if len([term for term in read if term.strip()]) > search_plan.MAX_PLACES:
        raise ValueError(TOO_MANY.format(name=NAMES[key], limit=search_plan.MAX_PLACES))
    return entries
