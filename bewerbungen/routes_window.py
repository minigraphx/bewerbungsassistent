"""Zeitfenster der Suche (#208, G32): what Stellen and Suche einstellen (#263) say about the window, and changing it.

The window is the line `- Zeitfenster: N Tage` under „Portale und Rhythmus“ in the search profile; the card writes it
there, with a draft before and after. Only for the job search: apprenticeship portals search without a date.
"""
import re

import preferences
import search_plan
import search_window
from dateien import schreibe_atomar
from hits import PORTALS_OFF, Hits
from server import json_antwort

SECTION = "## Portale und Rhythmus"
BEFORE = "## Region"  # where a profile without the section gets it
LINE = "- Zeitfenster: {days} Tage"
WINDOW_LINE = re.compile(r"^-\s+zeitfenster\s*:", re.IGNORECASE)
BAD_DAYS = f"Erlaubt sind {search_plan.MIN_WINDOW_DAYS} bis {search_plan.MAX_WINDOW_DAYS} Tage."
NO_PROFILE = "Zuerst Meine Angaben abschliessen."
ONLY_JOBS = "Das Zeitfenster gilt nur für die Stellensuche."
SAVED = "Zeitfenster der Suche: {days} Tage"


def display_for(k) -> dict:
    """search_window.display for the data folder; without a readable profile the default window and all job portals."""
    kind = preferences.load(k.daten).sought
    store = Hits(k.daten)
    window, portals = search_plan.MAX_AGE_DAYS, search_plan.PORTALS
    try:
        current = search_plan.chosen(search_plan.for_folder(k.daten), store.settings()[PORTALS_OFF])
        window, portals = current.max_age_days, current.portals
    except ValueError:  # no profile or a gap in it: the page says so elsewhere
        pass
    return {**search_window.display(kind, window, portals, store.last_run(), k.heute()), "art": kind}


def with_window(text: str, days: int) -> str:
    """The profile with this window: the line replaced where it stands, else added to its section."""
    lines = text.split("\n")
    start, end = search_plan.section_bounds(lines, SECTION[3:].strip().lower())
    if start is not None:
        found = next((i for i in range(start + 1, end) if WINDOW_LINE.match(lines[i].strip())), None)
        if found is not None:
            return "\n".join([*lines[:found], LINE.format(days=days), *lines[found + 1:]])
    return search_plan.with_section_line(text, SECTION, LINE.format(days=days), BEFORE)


def _days(body) -> int:
    days = body.get("tage") if isinstance(body, dict) else None
    if type(days) is not int or not search_plan.MIN_WINDOW_DAYS <= days <= search_plan.MAX_WINDOW_DAYS:
        raise ValueError(BAD_DAYS)
    return days


def state(k, parameter, body):
    return json_antwort(display_for(k))


def frame(k, parameter, body):
    """Workload, exclusions and title filters for Suche einstellen (#263); empty without a profile."""
    path = k.daten / search_plan.PROFILE
    return json_antwort(search_plan.frame(path.read_text(encoding="utf-8") if path.is_file() else ""))


def change(k, parameter, body):
    days = _days(body)
    if preferences.load(k.daten).sought == search_plan.KIND_APPRENTICESHIP:
        raise ValueError(ONLY_JOBS)
    path = k.daten / search_plan.PROFILE
    if not path.is_file():
        raise ValueError(NO_PROFILE)

    def write() -> str:
        text = path.read_text(encoding="utf-8")
        changed = with_window(text, days)
        if changed != text:
            schreibe_atomar(path, changed.encode("utf-8"))
        return text
    k.mit_entwurf(path, SAVED.format(days=days), write)
    return json_antwort(display_for(k))


GET = {"/api/suche/zeitfenster": state, "/api/suche/rahmen": frame}
POST = {"/api/suche/zeitfenster": change}
