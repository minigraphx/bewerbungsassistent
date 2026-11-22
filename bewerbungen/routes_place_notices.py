"""Routes of the place notices on Suche einstellen (G107, #380), only for a job search and only for the page.

GET only proposes. A place goes on the person's click, for exactly the place the page showed, with drafts before and
after; Rückgängig takes the digest of the former profile, whose draft `mit_entwurf` keeps. «Behalten» is remembered
per place in `suche/einstellungen.yaml`. The extension and Claude cannot reach these routes (allow-lists in
desktop/native_host.py and desktop/mcp_tools.py).
"""
import hashlib
import re

import place_notices
import preferences
import search_plan
from dateien import schreibe_atomar
from hits import KEPT_PLACES, PORTALS_OFF, Hits
from server import json_antwort

SHA256 = re.compile(r"[0-9a-f]{64}")


def _job_text(k) -> str | None:
    """The profile of a job search, None for an apprenticeship search or without a profile."""
    path = k.daten / search_plan.PROFILE
    if preferences.load(k.daten).sought != search_plan.KIND_JOB or not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    return None if search_plan.APPRENTICESHIP_MARK in text else text


def _place(body) -> str:
    place = body.get("ort") if isinstance(body, dict) else None
    if not isinstance(place, str) or not place.strip() or len(place) > search_plan.MAX_VALUE:
        raise ValueError(place_notices.GONE)
    return place.strip()


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def found(k, parameter, body):
    text = _job_text(k)
    if text is None:
        return json_antwort(place_notices.NOTHING)
    settings = Hits(k.daten).settings()
    return json_antwort(place_notices.notices(text, search_plan.cv_postal_code(k.daten), settings[PORTALS_OFF],
                                              settings[KEPT_PLACES]))


def remove(k, parameter, body):
    """Removes the place the person chose and says how to undo it."""
    place, text = _place(body), _job_text(k)
    if text is None:
        raise ValueError(place_notices.GONE)
    path = k.daten / search_plan.PROFILE
    postal_code, off = search_plan.cv_postal_code(k.daten), Hits(k.daten).settings()[PORTALS_OFF]
    place_notices.removal(text, place, postal_code, off)  # refuse before any draft is made
    done = {}

    def write() -> None:
        # read under the lock: the profile may have changed since the page loaded
        current = path.read_text(encoding="utf-8")
        removal = place_notices.removal(current, place, postal_code, off)
        schreibe_atomar(path, removal.text.encode("utf-8"))
        done.update(before=current, removal=removal)

    k.mit_entwurf(path, f"Ort für jobs.ch entfernt: {place}", write)
    return json_antwort({"text": done["removal"].done, "ort": place, "rueckgaengig": _digest(done["before"])})


def _former_text(k, path, digest: str) -> str | None:
    draft = next((d for d in k.ablage.liste(path) if d.hash == digest), None)
    return k.ablage.inhalt(draft.id).decode("utf-8") if draft else None


def undo(k, parameter, body):
    """The place back: the former profile if nothing else changed since, else at the end of its line."""
    place, text = _place(body), _job_text(k)
    digest = body.get("vorher")
    if text is None or not isinstance(digest, str) or not SHA256.fullmatch(digest):
        raise ValueError(place_notices.NO_UNDO)
    path = k.daten / search_plan.PROFILE
    former = _former_text(k, path, digest)

    def write() -> None:
        current = path.read_text(encoding="utf-8")
        schreibe_atomar(path, place_notices.restored(former, current, place).encode("utf-8"))

    k.mit_entwurf(path, f"Ort für jobs.ch wieder aufgenommen: {place}", write)
    return json_antwort({"text": place_notices.BACK.format(place=place)})


def keep(k, parameter, body):
    """«Behalten»: the profile stays as it is, and the app does not ask about this place again."""
    place = _place(body)
    Hits(k.daten).keep_place(place)
    return json_antwort({"text": f"{place} bleibt bei den Orten für jobs.ch."})


GET = {"/api/suche/orte-hinweise": found}
POST = {"/api/suche/orte-hinweise/entfernen": remove, "/api/suche/orte-hinweise/rueckgaengig": undo,
        "/api/suche/orte-hinweise/behalten": keep}
