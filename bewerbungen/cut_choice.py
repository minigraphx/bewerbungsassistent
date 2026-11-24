"""The person cuts the CV of one application or allows it three pages (G92, #323).

The check before sending offers the cuts of lebenslauf/cuts.py for the CV as this application builds it (its variant or
the base CV, with what it already leaves out), so a cut chosen once is gone from the next offer and the next one comes
first. What is chosen lands in bewerbungen/<id>/kuerzungen.yaml (cv_cuts.py); the step Lebenslauf lists it with
«Zurückholen». After sending, nothing changes any more.
"""
import pathlib

import yaml

import cuts
import cv_cuts
import page_limit
import unterlagen
from dateien import schreibe_atomar
from ui_message import T

NONE_CHOSEN = "Bitte mindestens eine Kürzung anhaken oder drei Seiten erlauben."
UNKNOWN = "Diese Kürzung gibt es nicht mehr. Bitte erneut prüfen."
THREE_PAGES = "drei-seiten"  # the id of the allowed third page among what is left out
# The sections of lebenslauf/cuts.py in the app language (#428); in German they read as cuts.SECTION_NAMES.
SECTION_NAMES = {"more-projects": T("Weitere Projekte"), "interests": T("Interessen"), "volunteer": T("Engagement"),
                 "awards": T("Auszeichnungen")}


def cut_text(cut: cuts.Cut) -> T:
    """What a cut takes away, in the app language; the station's name stays as Meine Angaben has it. In German it is
    `cut.text` byte for byte."""
    if cut.section:
        return T("Abschnitt «{name}»", name=SECTION_NAMES[cut.section])
    if cut.years:
        start, end = cut.years
        years = {"von": start, "bis": end or T("heute")}
        if cut.count == 1:
            return T("1 Stichpunkt bei «{station}» ({von}–{bis})", station=cut.name, **years)
        return T("{anzahl} Stichpunkte bei «{station}» ({von}–{bis})", anzahl=cut.count, station=cut.name, **years)
    if cut.count == 1:
        return T("1 Stichpunkt bei «{station}»", station=cut.name)
    return T("{anzahl} Stichpunkte bei «{station}»", anzahl=cut.count, station=cut.name)


def options(daten: pathlib.Path, entry: dict) -> list[cuts.Cut]:
    """The cuts that can still go from this application's CV; none for an own PDF or a finished variant file."""
    if not unterlagen.cuts_apply(daten, entry):
        return []
    return cuts.options(unterlagen.tailored_cv(daten, entry))


def offer(daten: pathlib.Path, entry: dict, limit: int) -> dict:
    """What the finding of a CV over `limit` offers: the cuts, and three pages while fewer are allowed."""
    allowed = unterlagen.cuts_apply(daten, entry) and limit < page_limit.MOST
    return {"optionen": [{"id": cut.id, "text": cut_text(cut)} for cut in options(daten, entry)], "drei_seiten": allowed}


def _picked(daten: pathlib.Path, entry: dict, ids) -> list[cuts.Cut]:
    if ids is None:
        return []
    if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
        raise ValueError(NONE_CHOSEN)
    available = {cut.id: cut for cut in options(daten, entry)}
    if any(i not in available for i in ids):
        raise ValueError(UNKNOWN)
    return [available[i] for i in dict.fromkeys(ids)]


def choose(daten: pathlib.Path, entry: dict, ids, three) -> dict:
    """The stored choice with the cuts `ids` and, with `three` true, three pages; ValueError in German."""
    if entry.get("versand"):
        raise ValueError(unterlagen.SENT_STAYS)
    picked = _picked(daten, entry, ids)
    if not picked and three is not True:
        raise ValueError(NONE_CHOSEN)
    stored = cv_cuts.load(daten, entry["id"])
    result = cuts.chosen(picked, stored) if picked else stored
    return {**result, cv_cuts.THREE_PAGES: True} if three is True else result


def take_back(daten: pathlib.Path, entry: dict, which) -> dict:
    """The stored choice without the cut `which`, or without the third page; ValueError when it is not there."""
    if entry.get("versand"):
        raise ValueError(unterlagen.SENT_STAYS)
    stored = cv_cuts.load(daten, entry["id"])
    if which == THREE_PAGES and stored.get(cv_cuts.THREE_PAGES) is True:
        return {key: value for key, value in stored.items() if key != cv_cuts.THREE_PAGES}
    if which not in [cut.id for cut in _left_out(daten, entry, stored)]:
        raise ValueError(UNKNOWN)
    return cuts.without(stored, which)


def write(daten: pathlib.Path, entry_id: str, stored: dict) -> None:
    path = cv_cuts.path(daten, entry_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    schreibe_atomar(path, yaml.safe_dump(stored, allow_unicode=True, sort_keys=False).encode("utf-8"))


def store_choice(daten: pathlib.Path, entry: dict, ids, three) -> dict:
    """Choose and store at once, without drafts; the route stores with drafts (routes_cuts.py)."""
    stored = choose(daten, entry, ids, three)
    write(daten, entry["id"], stored)
    return stored


def _left_out(daten: pathlib.Path, entry: dict, stored: dict) -> list[cuts.Cut]:
    return cuts.left_out(unterlagen.tailored_cv(daten, entry, with_cuts=False), stored) if stored else []


def state(daten: pathlib.Path, entry: dict) -> dict:
    """What this application leaves out, named as when it was offered, and whether it allows three pages."""
    stored = cv_cuts.load(daten, entry["id"])
    return {"weggelassen": [{"id": cut.id, "text": cut_text(cut)} for cut in _left_out(daten, entry, stored)],
            "drei_seiten": stored.get(cv_cuts.THREE_PAGES) is True}
