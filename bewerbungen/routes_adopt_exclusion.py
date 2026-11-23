"""A point of a hit's AI rating taken over as an exclusion (#224, G83), only for job searches.

`GET /api/suche/haken-ausschluss?id=…&punkt=N` says what the app would add for point N under „Was fehlt oder unsicher
ist“ (`rating_exclusion.py`) and changes nothing. The person confirms or edits it; `POST` then writes it through
`search_frame`, the path Suche einstellen uses, with drafts before and after. Rückgängig takes out exactly that entry
again, also with drafts; `add_entry` and `remove_entry` do the same for the AI's proposals (#319). `GET …/punkte`
names the points an entry already excludes, so the page shows «Ausgeschlossen» there. Nothing here calls the AI; neither the extension nor Claude reach the routes: they are not
listed in desktop/native_host.py or desktop/mcp_tools.py.
"""
import pathlib

import preferences
import profile_limits
import rating_exclusion
import search_frame
import search_plan
from dateien import schreibe_atomar
from hits import Hits
from server import json_antwort
from ui_texts import T

ONLY_JOBS = T("Ausschlüsse aus der Einschätzung gibt es nur bei der Stellensuche.")
NO_POINT = T("Diesen Punkt gibt es in der Einschätzung nicht mehr.")
BAD_KIND = T("Bitte «Im Titel» oder «Im Inserat» wählen.")
EMPTY = T("Bitte angeben, was nicht mehr kommen soll.")
COMMA = T("Bitte ohne Komma, ein Ausschluss pro Eintrag.")
ALREADY = "«{value}» steht schon unter «{place}»."
NO_UNDO = "Rückgängig geht nicht mehr: «{value}» steht nicht mehr unter «{place}»."
ADOPTED = "Stellen: «{value}» unter «{place}» ausgeschlossen"
UNDONE = "Stellen: «{value}» unter «{place}» wieder entfernt"


def _job_profile(k) -> tuple[pathlib.Path, str]:
    """The profile of a job search; an apprenticeship has neither title filter nor these exclusions."""
    path = k.daten / search_plan.PROFILE
    if not path.is_file():
        raise ValueError(search_plan.NO_PROFILE)
    text = path.read_text(encoding="utf-8")
    if search_frame.kind_of(text) != search_plan.KIND_JOB or preferences.strictest_kind(k.daten) == preferences.APPRENTICESHIP:
        raise ValueError(ONLY_JOBS)
    return path, text


def _point(k, hit_id, index) -> tuple[dict, str]:
    """The hit (KeyError if unknown) and the text of its point; a point it no longer has is refused."""
    hit = Hits(k.daten).get(hit_id if isinstance(hit_id, str) else "")
    points = (hit.get("bewertung") or {}).get("haken") or []
    if type(index) is not int or not 0 <= index < len(points) or not isinstance(points[index], str):
        raise ValueError(NO_POINT)
    return hit, points[index]


def _index_from_query(value) -> int | str:
    text = str(value or "")
    return int(text) if text.isdigit() else text


def _shown(text: str) -> dict:
    current = search_frame.values(text)
    return {kind: current[kind] for kind in rating_exclusion.KINDS}


def preview(k, parameter, body):
    """What the app would add for this point, and the lists as they are; nothing is written."""
    _, text = _job_profile(k)
    index = _index_from_query(parameter.get("punkt"))
    hit, point = _point(k, parameter.get("id"), index)
    chars = profile_limits.of(search_plan.KIND_JOB, search_frame.FIELDS[rating_exclusion.AD].form_id).chars
    found = rating_exclusion.propose(point, hit.get("stelle", ""), search_plan.title_terms(text, "positiv"),
                                     search_plan.title_terms(text, "ausschluss"), chars)
    return json_antwort({"id": hit["id"], "punkt": index, "text": point, "art": found.kind,
                         "wert": found.value, "werte": _shown(text)})


def excluded_points(k, parameter, body):
    """Per point of the hit's rating, whether an entry already excludes it, so the page shows «Ausgeschlossen»."""
    _, text = _job_profile(k)
    hit = Hits(k.daten).get(parameter.get("id") if isinstance(parameter.get("id"), str) else "")
    points = (hit.get("bewertung") or {}).get("haken") or []
    entries = [entry for values in _shown(text).values() for entry in values]
    return json_antwort({"ausgeschlossen": [isinstance(point, str) and rating_exclusion.is_excluded(point, entries)
                                            for point in points]})


def _entry(body: dict) -> tuple[str, str]:
    kind, value = body.get("art"), body.get("wert")
    if kind not in rating_exclusion.KINDS:
        raise ValueError(BAD_KIND)
    value = " ".join(value.split()) if isinstance(value, str) else ""
    if not value:
        raise ValueError(EMPTY)
    if "," in value:
        raise ValueError(COMMA)
    return kind, value


def _has(text: str, kind: str, value: str) -> bool:
    return any(item.casefold() == value.casefold() for item in search_frame.values(text)[kind])


def _write(k, path: pathlib.Path, description: str, change) -> str:
    """The profile changed with drafts before and after; returns the new text."""
    def write() -> str:
        text = path.read_text(encoding="utf-8")
        changed = change(text)
        if changed != text:
            schreibe_atomar(path, changed.encode("utf-8"))
        return changed
    return k.mit_entwurf(path, description, write)


def add_entry(k, kind: str, value: str, adopted: str = ADOPTED) -> dict:
    """Adds an entry to the title filter or the exclusions of the ad, with drafts; also for the AI's proposals (#319).
    `adopted` describes the draft, with {value} and {place}."""
    path, text = _job_profile(k)
    kind, value = _entry({"art": kind, "wert": value})
    place = rating_exclusion.PLACES[kind]

    def added(current: str) -> str:
        if _has(current, kind, value):
            raise ValueError(T(ALREADY, value=value, place=T(place)))
        return search_frame.with_values(current, {kind: [*search_frame.values(current)[kind], value]})

    added(text)  # refuse before any draft is made
    changed = _write(k, path, adopted.format(value=value, place=place), added)
    return {"art": kind, "wert": value, "werte": _shown(changed)}


def remove_entry(k, kind, value, undone: str = UNDONE) -> dict:
    """Takes out exactly this entry, wherever it stands in its list now, with drafts."""
    path, text = _job_profile(k)
    kind, value = _entry({"art": kind, "wert": value})
    place = rating_exclusion.PLACES[kind]

    def removed(current: str) -> str:
        if not _has(current, kind, value):
            raise ValueError(T(NO_UNDO, value=value, place=T(place)))
        kept = [item for item in search_frame.values(current)[kind] if item.casefold() != value.casefold()]
        return search_frame.with_values(current, {kind: kept})

    removed(text)
    changed = _write(k, path, undone.format(value=value, place=place), removed)
    return {"art": kind, "wert": value, "werte": _shown(changed)}


def adopt(k, parameter, body):
    """Adds the confirmed or edited entry to the title filter or the exclusions of the ad."""
    body = body if isinstance(body, dict) else {}
    _job_profile(k)
    _point(k, body.get("id"), body.get("punkt"))
    kind, value = _entry(body)
    return json_antwort(add_entry(k, kind, value))


def undo(k, parameter, body):
    """Takes out exactly the adopted entry, wherever it stands in its list now."""
    body = body if isinstance(body, dict) else {}
    return json_antwort(remove_entry(k, body.get("art"), body.get("wert")))


GET = {"/api/suche/haken-ausschluss": preview, "/api/suche/haken-ausschluss/punkte": excluded_points}
POST = {"/api/suche/haken-ausschluss": adopt, "/api/suche/haken-ausschluss/rueckgaengig": undo}
