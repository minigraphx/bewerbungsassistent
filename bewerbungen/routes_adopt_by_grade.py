"""„Alle ab Note … merken“ on Stellen (#214, design A3): save every rated new hit from a chosen grade on.

`GET /api/suche/ab-note?note=4` names how many hits and which ones, and changes nothing. The person confirms on the
page; `POST /api/suche/ab-note` then saves exactly the confirmed ids, each like „Merken“ (`routes_search.take_over_hit`).
A hit is saved only while it is still new, shown and rated by the AI at or above the grade; anything else is skipped, so
unrated, saved and discarded hits stay as they are. Nothing here calls the AI; the extension and Claude cannot reach it.
"""
import excluded_companies
import routes_search
from hits import Hits
from server import json_antwort
from ui_texts import T

MIN_GRADE, MAX_GRADE = 1, 6
BAD_GRADE = T("Die Note muss zwischen 1 und 6 liegen, in halben Schritten.")
BAD_IDS = T("ids erwartet (Liste der Treffer)")
NEW = "neu"


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def checked_grade(value) -> float:
    """A grade from 1 to 6 in half steps, as the page offers them."""
    if not _is_number(value) or not MIN_GRADE <= value <= MAX_GRADE or (value * 2) % 1:
        raise ValueError(BAD_GRADE)
    return float(value)


def _grade_from_query(parameter: dict) -> float:
    try:
        return checked_grade(float(str(parameter.get("note", "")).replace(",", ".")))
    except ValueError:
        raise ValueError(BAD_GRADE) from None


def grade_of(hit: dict) -> float | None:
    note = (hit.get("bewertung") or {}).get("note")
    return float(note) if _is_number(note) else None


def qualifies(hit: dict, grade: float, excluded: frozenset[str]) -> bool:
    """New, shown and rated by the AI at or above the grade: unrated hits never count."""
    own = grade_of(hit)
    return (hit.get("zustand") == NEW and own is not None and own >= grade
            and bool(excluded_companies.shown([hit], excluded)))


def _excluded(k) -> frozenset[str]:
    return excluded_companies.keys(k.daten)


def preview(k, parameter, body):
    """How many hits and which, best grade first; nothing is saved."""
    grade = _grade_from_query(parameter)
    excluded = _excluded(k)
    found = [hit for hit in Hits(k.daten).all() if qualifies(hit, grade, excluded)]
    found = sorted(found, key=lambda hit: -grade_of(hit))
    listed = [{"id": hit["id"], "stelle": hit["stelle"], "firma": hit.get("firma", ""), "note": grade_of(hit)}
              for hit in found]
    return json_antwort({"note": grade, "anzahl": len(listed), "treffer": listed})


def _confirmed_ids(body) -> list[str]:
    ids = body.get("ids") if isinstance(body, dict) else None
    if not isinstance(ids, list) or not all(isinstance(wanted, str) for wanted in ids):
        raise ValueError(BAD_IDS)
    return list(dict.fromkeys(ids))


def adopt(k, parameter, body):
    """Saves the confirmed hits that still qualify; the others are named as skipped."""
    grade = checked_grade(body.get("note") if isinstance(body, dict) else None)
    ids = _confirmed_ids(body)
    store, excluded = Hits(k.daten), _excluded(k)
    known = {hit["id"] for hit in store.all()}
    saved, skipped = [], []
    still_fits = lambda hit: qualifies(hit, grade, excluded)  # noqa: E731
    for wanted in ids:
        taken = wanted in known and routes_search.take_over_hit(k, store, wanted, still_fits)
        (saved if taken else skipped).append(wanted)
    return json_antwort({"note": grade, "gemerkt": saved, "uebersprungen": skipped})


GET = {"/api/suche/ab-note": preview}
POST = {"/api/suche/ab-note": adopt}
