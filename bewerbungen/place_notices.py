"""Notices on the places of the region card (G107, #380), only for a job search, without AI.

jobs.ch searches a place together with its whole canton, so a second place in the same canton brings few new ads but
costs one search per term; the card says so for the later place and offers to remove it. Only places whose canton
the app knows for sure count (`place_cantons.py`), and only one that stands alone in the line «Orte (jobs.ch)» can be
removed from it. jobscout24 searches 20 km around each postcode, so with several postcodes and no region the card
suggests choosing regions.
"""
import dataclasses

import place_cantons
import search_frame
import search_plan
import search_stages
from ui_message import T

ORTE = "orte"
JOBS_CH = "jobs.ch"
JOBSCOUT24 = "jobscout24"
MIN_POSTAL_CODES = 2
POSTAL_CODE_RADIUS_KM = 20  # jobscout24's fixed radius around a postcode (measured 21.11.2026)
SAME_CANTON = ("{first} und {place} liegen beide im Kanton {canton}. jobs.ch sucht bei jedem Ort auch im ganzen "
               "Kanton, ein zweiter Ort im selben Kanton bringt darum kaum neue Stellen. {place} kostet {cost} pro "
               "Suchlauf.")
REMOVE = "{place} entfernen"
KEEP = "Behalten"
REMOVED = "{place} entfernt. jobs.ch sucht weiter im ganzen Kanton {canton}, und der nächste Suchlauf spart {saved}."
BACK = "{place} ist wieder bei den Orten für jobs.ch."
POSTAL_CODES = ("jobscout24 sucht an {count} PLZ, jede mit {radius} km Umkreis; nahe PLZ finden oft dieselben Stellen. "
                "Mit einer Region sucht jobscout24 einmal pro Begriff.")
CHOOSE_REGIONS = "Regionen wählen"
GONE = "Dieser Hinweis gilt nicht mehr. Die Seite zeigt jetzt, was im Suchprofil steht."
NO_UNDO = "Das lässt sich nicht mehr rückgängig machen."
NOTHING = {"orte": [], "plz": None}


@dataclasses.dataclass(frozen=True)
class Removal:
    text: str
    place: str
    done: str


def _plan(text: str, postal_code: str | None, switched_off: list[str] | None) -> search_plan.SearchPlan | None:
    if search_plan.APPRENTICESHIP_MARK in text:
        return None
    try:
        return search_plan.chosen(search_plan.parse(text, postal_code), switched_off)
    except ValueError:  # a profile that searches nothing yet has no places to speak of
        return None


def _entries(text: str) -> list[str]:
    return [entry.strip() for entry in search_plan.ENTRY_COMMA.split(search_frame.raw_value(text, ORTE)) if entry.strip()]


def _searches(count: int) -> T:
    """«1 Suche» or «3 Suchen», each its own catalog key, so French and English get their singular too."""
    return T("1 Suche") if count == 1 else T("{anzahl} Suchen", anzahl=count)


def back(place: str) -> T:
    """What Rückgängig says once the place is back."""
    return T(BACK, place=place)


def _alone(entry: str) -> str | None:
    """The place of an entry that names one place only, a remark in brackets aside."""
    terms = [term.strip() for term in search_plan.split_terms(entry) if term.strip()]
    return terms[0] if len(terms) == 1 else None


def _cost(plan: search_plan.SearchPlan, place: str) -> int:
    """What the next run saves without the place, counted as the estimate counts (G43)."""
    with_place = plan.as_dict()
    without = {**with_place, "orte": [p for p in with_place["orte"] if p.lower() != place.lower()]}
    return (search_stages.searches_per_portal(with_place).get(JOBS_CH, 0)
            - search_stages.searches_per_portal(without).get(JOBS_CH, 0))


def _same_canton(text: str, plan: search_plan.SearchPlan, kept: list[str]) -> list[dict]:
    first: dict[str, str] = {}
    found = []
    for entry in _entries(text):
        alone = _alone(entry)
        for place in (term.strip() for term in search_plan.split_terms(entry) if term.strip()):
            canton = place_cantons.canton_of(place)
            if canton is None or first.setdefault(canton, place).lower() == place.lower():
                continue
            cost = _cost(plan, place)
            if alone == place and place.lower() not in kept and cost:
                found.append({"ort": place, "kanton": canton, "spart": cost, "text": T(
                    SAME_CANTON, first=first[canton], place=place, canton=place_cantons.CANTON_NAMES[canton],
                    cost=_searches(cost)),
                    "knopf": T(REMOVE, place=place), "behalten": T(KEEP)})
    return found


def _postal_codes(plan: search_plan.SearchPlan) -> dict | None:
    if JOBSCOUT24 not in plan.portals or plan.jobscout24_regions or len(plan.postal_codes) < MIN_POSTAL_CODES:
        return None
    return {"text": T(POSTAL_CODES, count=len(plan.postal_codes), radius=POSTAL_CODE_RADIUS_KM),
            "knopf": T(CHOOSE_REGIONS)}


def notices(text: str, postal_code: str | None, switched_off: list[str] | None, kept: list[str]) -> dict:
    """The notices of the region card: jobs.ch places in a canton already searched, and the nudge to regions."""
    plan = _plan(text, postal_code, switched_off)
    if plan is None:
        return NOTHING
    places = _same_canton(text, plan, [place.lower() for place in kept]) if JOBS_CH in plan.portals else []
    return {"orte": places, "plz": _postal_codes(plan)}


def removal(text: str, place: str, postal_code: str | None, switched_off: list[str] | None) -> Removal:
    """The profile without this place, if the card offers to remove it now; ValueError otherwise."""
    offered = next((n for n in notices(text, postal_code, switched_off, [])["orte"] if n["ort"] == place), None)
    if offered is None:
        raise ValueError(GONE)
    rest = [entry for entry in _entries(text) if _alone(entry) != place]
    done = T(REMOVED, place=place, canton=place_cantons.CANTON_NAMES[offered["kanton"]],
             saved=_searches(offered["spart"]))
    return Removal(search_frame.with_raw_value(text, ORTE, ", ".join(rest)), place, done)


def restored(former: str | None, current: str, place: str) -> str:
    """Rückgängig: the profile before, if only this removal happened since; else the place back at the end of its line."""
    if former is not None and any(_alone(entry) == place for entry in _entries(former)):
        rest = [entry for entry in _entries(former) if _alone(entry) != place]
        if search_frame.with_raw_value(former, ORTE, ", ".join(rest)) == current:
            return former
    entries = _entries(current)
    if not entries:
        raise ValueError(NO_UNDO)
    searched = {term.strip().lower() for entry in entries for term in search_plan.split_terms(entry)}
    if place.lower() in searched:
        return current
    return search_frame.with_raw_value(current, ORTE, ", ".join([*entries, place]))
