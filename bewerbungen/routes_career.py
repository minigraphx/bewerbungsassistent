"""Routes for what to search for (MIN-375): suggestions from the AI, adding and removing; only for the page of the app.

A person adds own terms through the same route as a suggestion (#216). Rückgängig after Entfernen brings the former
profile back only if it differs from the current one in exactly that term; otherwise the term goes back at the end.
"""
import hashlib
import re

import preferences
import routes_ai
import search_plan
import search_terms
from ai import career
from dateien import schreibe_atomar
from server import json_antwort

NO_PROFILE = search_plan.NO_PROFILE
BOTH_NEEDED = {search_plan.KIND_APPRENTICESHIP: "Schreib zu beidem etwas: was du gern machst und was du gut kannst.",
               search_plan.KIND_JOB: "Bitte zu beidem etwas schreiben: Interessen und Fähigkeiten."}
NOT_VALID = {search_plan.KIND_APPRENTICESHIP: "Das ist kein Beruf mit EFZ oder EBA.",
             search_plan.KIND_JOB: "Das passt nicht als Suchbegriff."}
NO_NAME = "Welcher Eintrag soll weg?"
EMPTY = {search_plan.KIND_APPRENTICESHIP: "Bitte einen Beruf mit EFZ oder EBA eintragen.",
         search_plan.KIND_JOB: "Bitte einen Suchbegriff eintragen."}
ALREADY = "„{name}“ wird schon gesucht."
NO_UNDO = "Rückgängig geht hier nicht mehr. Bitte den Begriff neu aufnehmen."
SHA256 = re.compile(r"[0-9a-f]{64}")


def _profile(k):
    path = k.daten / search_plan.PROFILE
    if not path.is_file():
        raise ValueError(NO_PROFILE)
    return path


def _searched(path) -> list[str]:
    return list(search_terms.current(path.read_text(encoding="utf-8")))


def searched_now(k) -> dict:
    """What the profile names, also if the plan cannot search yet: the page lists it and compares its suggestions with it."""
    path = k.daten / search_plan.PROFILE
    names = _searched(path) if path.is_file() else []
    return {"gesuchte_berufe": names, "gesuchte_schluessel": [search_terms.key(name) for name in names]}


def suggest(k, parameter, body):
    path = _profile(k)
    kind = preferences.strictest_kind(k.daten)
    answers = career.clean_answers(body)
    if not answers["interests"] or not answers["strengths"]:
        raise ValueError(BOTH_NEEDED[kind])

    def task():
        gateway, material = routes_ai.ai_gateway(k)
        return career.recommend(gateway, material, answers, kind)

    result = routes_ai.run_ai(task)
    searched = set(map(search_plan.profession_words, _searched(path)))
    return json_antwort({"vorschlaege": [
        {"beruf": item["profession"], "warum": item["why"], "alltag": item["daily"], "pruefen": item["check"],
         "schon_gesucht": search_plan.profession_words(item["profession"]) in searched,
         "schluessel": search_terms.key(item["profession"])} for item in result["recommendations"]]})


def _write(k, path, description: str, change) -> str:
    """The text before the change; `change` runs under the lock with the current text."""
    def write() -> str:
        # read under the lock: two quick clicks, or a change of the offers, must not lose each other's line
        text = path.read_text(encoding="utf-8")
        changed = change(text)
        if changed != text:
            schreibe_atomar(path, changed.encode("utf-8"))
        return text

    return k.mit_entwurf(path, description, write)


def _answer(k, **extra) -> dict:
    now = searched_now(k)
    return json_antwort({"berufe": now["gesuchte_berufe"], "schluessel": now["gesuchte_schluessel"], **extra})


def _change(k, path, description: str, change) -> dict:
    _write(k, path, description, change)
    return _answer(k)


def _removed_name(body) -> str:
    name = body.get("beruf") if isinstance(body, dict) else None
    if not isinstance(name, str) or not name.strip() or len(name) > career.MAX_NAME:
        raise ValueError(NO_NAME)
    return name.strip()


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def add(k, parameter, body):
    path = _profile(k)
    kind = preferences.strictest_kind(k.daten)
    name = body.get("beruf") if isinstance(body, dict) else None
    if name is None or (isinstance(name, str) and not name.strip()):
        raise ValueError(EMPTY[kind])
    if not career.is_valid_name(name, kind):
        raise ValueError(NOT_VALID[kind])
    clean = " ".join(name.split())
    sought = preferences.load(k.daten).sought

    def change(text: str) -> str:
        if search_terms.is_searched(text, clean):
            raise ValueError(ALREADY.format(name=clean))
        return search_terms.added(text, clean, sought)

    return _change(k, path, f"In die Suche aufgenommen: {clean}", change)


def remove(k, parameter, body):
    """Also says how to undo it: the digest of the former profile, whose draft `mit_entwurf` keeps."""
    path = _profile(k)
    clean = _removed_name(body)
    changed = {}

    def change(text: str) -> str:
        changed["after"] = search_terms.removed(text, clean)
        return changed["after"]

    before = _write(k, path, f"Aus der Suche entfernt: {clean}", change)
    return _answer(k, rueckgaengig=_digest(before) if changed["after"] != before else None)


def _former_text(k, path, digest: str) -> str | None:
    found = next((d for d in k.ablage.liste(path) if d.hash == digest), None)
    return k.ablage.inhalt(found.id).decode("utf-8") if found else None


def undo(k, parameter, body):
    """Rückgängig after Entfernen: the term back at its former place, or at the end if the profile changed since."""
    path = _profile(k)
    clean = _removed_name(body)
    digest = body.get("vorher")
    if not isinstance(digest, str) or not SHA256.fullmatch(digest):
        raise ValueError(NO_UNDO)
    former = _former_text(k, path, digest)
    kind = preferences.strictest_kind(k.daten)
    sought = preferences.load(k.daten).sought
    at_end = {"value": False}

    def change(text: str) -> str:
        if former is not None and former != text and search_terms.removed(former, clean) == text:
            return former
        at_end["value"] = True
        if search_terms.is_searched(text, clean):
            return text
        if not career.is_valid_name(clean, kind):
            raise ValueError(NO_UNDO)
        return search_terms.added(text, clean, sought)

    _write(k, path, f"Wieder in die Suche aufgenommen: {clean}", change)
    return _answer(k, am_ende=at_end["value"])


GET: dict = {}
POST = {"/api/beruf/vorschlag": suggest, "/api/beruf/aufnehmen": add, "/api/beruf/entfernen": remove,
        "/api/beruf/rueckgaengig": undo}
