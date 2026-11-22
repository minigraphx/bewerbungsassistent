"""Routes of «Doppelt gesucht» on Suche einstellen (G106, #377), only for a job search and only for the page.

GET only proposes. A removal happens on the person's click, for exactly the pair and entry the page showed, with
drafts before and after; Rückgängig then goes through the route of the term list (`/api/beruf/rueckgaengig`), with
the line for a removal from one line. «Beide behalten» is remembered per pair in `suche/einstellungen.yaml`.
The extension and Claude cannot reach these routes (allow-lists in desktop/native_host.py and desktop/mcp_tools.py).
"""
import hashlib

import excluded_companies
import preferences
import search_plan
import term_pair_texts
import term_pairs
from dateien import schreibe_atomar
from hits import KEPT_PAIRS, PORTALS_OFF, Hits
from server import json_antwort

SIDES = ("a", "b")


def _job_text(k) -> str | None:
    """The profile of a job search, None for an apprenticeship search or without a profile."""
    path = k.daten / search_plan.PROFILE
    if preferences.load(k.daten).sought != search_plan.KIND_JOB or not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    return None if search_plan.APPRENTICESHIP_MARK in text else text


def _pair_id(body) -> str:
    pair = body.get("paar") if isinstance(body, dict) else None
    if not isinstance(pair, str) or len(pair) > term_pairs.MAX_ID or not pair.startswith(term_pairs.PREFIXES):
        raise ValueError(term_pairs.GONE)
    return pair


def pairs(k, parameter, body):
    text = _job_text(k)
    if text is None:
        return json_antwort({"paare": []})
    store = Hits(k.daten)
    settings = store.settings()
    shown = excluded_companies.shown(store.all(), excluded_companies.keys(k.daten))
    found = term_pairs.pairs(text, search_plan.cv_postal_code(k.daten), settings[PORTALS_OFF], settings[KEPT_PAIRS], shown)
    return json_antwort({"paare": found})


def remove(k, parameter, body):
    """Removes the entry the person chose and says how to undo it: the digest of the former profile, whose draft
    `mit_entwurf` keeps."""
    pair, side = _pair_id(body), body.get("seite")
    text = _job_text(k)
    if side not in SIDES or text is None:
        raise ValueError(term_pairs.GONE)
    path = k.daten / search_plan.PROFILE
    postal_code, off = search_plan.cv_postal_code(k.daten), Hits(k.daten).settings()[PORTALS_OFF]
    preview = term_pairs.removal(text, pair, side, postal_code, off)
    done = {}

    def write() -> None:
        # read under the lock: the profile may have changed since the page loaded
        current = path.read_text(encoding="utf-8")
        removal = term_pairs.removal(current, pair, side, postal_code, off)
        schreibe_atomar(path, removal.text.encode("utf-8"))
        done.update(before=current, removal=removal)

    k.mit_entwurf(path, f"Doppelt gesucht, entfernt: {preview.term}", write)
    removal = done["removal"]
    return json_antwort({"text": removal.done, "beruf": removal.term, "zeile": removal.line, "zurueck": removal.back,
                         "rueckgaengig": hashlib.sha256(done["before"].encode("utf-8")).hexdigest()})


def keep(k, parameter, body):
    """«Beide behalten»: the profile stays as it is, and the app does not ask about this pair again."""
    Hits(k.daten).keep_pair(_pair_id(body))
    return json_antwort({"text": term_pair_texts.KEPT})


GET = {"/api/suche/doppelt": pairs}
POST = {"/api/suche/doppelt/entfernen": remove, "/api/suche/doppelt/behalten": keep}
