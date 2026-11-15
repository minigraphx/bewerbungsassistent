"""Region, Pensum, exclusions and title filter on Suche einstellen (#263, #286, G64): show them and change them.

A change goes into suchprofil.md with a draft before and after (`search_frame.py` says which line). Was Sie nicht
sehen wollen also holds the excluded companies (#226, G65); its route saves both together or neither (#303). Neither
the extension nor Claude reach the POST routes: they are not listed in desktop/native_host.py or desktop/mcp_tools.py.
"""
import logging
import pathlib
from typing import Callable

import excluded_companies
import portal_places
import search_frame
import search_plan
from dateien import schreibe_atomar
from server import json_antwort

log = logging.getLogger(__name__)

NO_PROFILE = "Zuerst Meine Angaben abschliessen."
NO_VALUES = "Angaben fehlen"
SAVED = "Suche einstellen: {fields}"
TAKEN_BACK = "Suche einstellen: {fields} zurückgenommen, die Firmen liessen sich nicht speichern"
# The parts of the card Was Sie nicht sehen wollen, as the person reads them there.
NOT_WANTED_KEYS = ("ausschluss", "titel_ausschluss")
PROFILE_PART = "Inserat und Titel"
COMPANIES_PART = "Firmen"
REFUSED = "{part}: {reason} {kept}"
PROFILE_KEPT = "Inserat und Titel bleiben wie vorher."
COMPANIES_KEPT = "Die Firmen bleiben wie vorher."
HALF_SAVED = "Die Firmen sind nicht gespeichert, Inserat und Titel sind gespeichert. Bitte nochmals speichern."


def _answer(text: str) -> dict:
    values = search_frame.values(text)
    return {**search_plan.frame(text), "art": search_frame.kind_of(text), "werte": values,
            "laengen": search_frame.lengths(text), "alle_kantone": list(search_plan.CANTONS),
            "orte_pro_portal": portal_places.shown(text),
            "alle_regionen": portal_places.region_choices(values["regionen"])}


def frame(k, parameter, body):
    """What the cards show and their fields hold; empty without a profile."""
    path = k.daten / search_plan.PROFILE
    return json_antwort(_answer(path.read_text(encoding="utf-8") if path.is_file() else ""))


def _profile(k) -> pathlib.Path:
    path = k.daten / search_plan.PROFILE
    if not path.is_file():
        raise ValueError(NO_PROFILE)
    return path


def _fields(body: dict) -> str:
    return ", ".join(search_frame.FIELDS[key].label for key in body)


def _write_profile(k, path: pathlib.Path, body: dict) -> tuple[str, str]:
    """The profile with the change, with drafts before and after; returns the text before and after."""
    def write() -> tuple[str, str]:
        text = path.read_text(encoding="utf-8")
        changed = search_frame.with_values(text, body)
        if changed != text:
            schreibe_atomar(path, changed.encode("utf-8"))
        return text, changed
    return k.mit_entwurf(path, SAVED.format(fields=_fields(body)), write)


def change(k, parameter, body):
    path = _profile(k)
    search_frame.with_values(path.read_text(encoding="utf-8"), body)  # refuse before any draft is made
    return json_antwort(_answer(_write_profile(k, path, body)[1]))


def _refused(part: str, kept: str, check: Callable):
    """The check's result; its refusal names the part and says the other part stays as it was."""
    try:
        return check()
    except ValueError as error:
        raise ValueError(REFUSED.format(part=part, reason=error, kept=kept)) from error


def _take_back(k, path: pathlib.Path, change: dict, before: str) -> None:
    """The companies could not be written, so the profile goes back; if that fails too, say what is saved."""
    try:
        k.mit_entwurf(path, TAKEN_BACK.format(fields=_fields(change)), lambda: schreibe_atomar(path, before.encode("utf-8")))
    except OSError as error:
        log.exception("Suchprofil liess sich nicht zurücknehmen")
        raise ValueError(HALF_SAVED) from error


def not_wanted(k, parameter, body):
    """Was Sie nicht sehen wollen: exclusions in the profile and the excluded companies, together or neither. An
    apprenticeship's card has only the companies."""
    if not isinstance(body, dict):
        raise ValueError(NO_VALUES)
    change = {key: body[key] for key in NOT_WANTED_KEYS if key in body}
    if not change:
        return json_antwort({"firmen": excluded_companies.replace(k, body.get("firmen"))})
    path = _profile(k)
    names = _refused(COMPANIES_PART, PROFILE_KEPT, lambda: excluded_companies.checked(body.get("firmen")))
    _refused(PROFILE_PART, COMPANIES_KEPT, lambda: search_frame.with_values(path.read_text(encoding="utf-8"), change))
    before, changed = _write_profile(k, path, change)
    try:
        companies = excluded_companies.replace(k, names)
    except Exception:
        _take_back(k, path, change, before)
        raise
    return json_antwort({**_answer(changed), "firmen": companies})


GET = {"/api/suche/rahmen": frame}
POST = {"/api/suche/rahmen": change, "/api/suche/was-nicht": not_wanted}
