"""Routes for what to search for (MIN-375): suggestions from the AI, adding and removing; only for the page of the app."""
import routes_ai
import search_plan
import search_terms
from ai import career
from dateien import schreibe_atomar
from server import json_antwort

NO_PROFILE = "Es gibt noch kein Suchprofil. Zuerst den Einstieg abschliessen."
BOTH_NEEDED = {search_plan.KIND_APPRENTICESHIP: "Schreib zu beidem etwas: was du gern machst und was du gut kannst.",
               search_plan.KIND_JOB: "Schreiben Sie zu beidem etwas: was Sie gern machen und was Sie gut können."}
NOT_VALID = {search_plan.KIND_APPRENTICESHIP: "Das ist kein Beruf mit EFZ oder EBA.",
             search_plan.KIND_JOB: "Das passt nicht als Suchbegriff."}
NO_NAME = "Welcher Eintrag soll weg?"


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
    kind = search_plan.kind_of_folder(k.daten)
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


def _change(k, path, description: str, change) -> dict:
    def write() -> None:
        # read under the lock: two quick clicks, or a change of the offers, must not lose each other's line
        text = path.read_text(encoding="utf-8")
        changed = change(text)
        if changed != text:
            schreibe_atomar(path, changed.encode("utf-8"))

    k.mit_entwurf(path, description, write)
    now = searched_now(k)
    return json_antwort({"berufe": now["gesuchte_berufe"], "schluessel": now["gesuchte_schluessel"]})


def add(k, parameter, body):
    path = _profile(k)
    kind = search_plan.kind_of_folder(k.daten)
    name = body.get("beruf") if isinstance(body, dict) else None
    if not career.is_valid_name(name, kind):
        raise ValueError(NOT_VALID[kind])
    clean = name.strip()
    return _change(k, path, f"In die Suche aufgenommen: {clean}", lambda text: search_terms.added(text, clean))


def remove(k, parameter, body):
    path = _profile(k)
    name = body.get("beruf") if isinstance(body, dict) else None
    if not isinstance(name, str) or not name.strip() or len(name) > career.MAX_NAME:
        raise ValueError(NO_NAME)
    clean = name.strip()
    return _change(k, path, f"Aus der Suche entfernt: {clean}", lambda text: search_terms.removed(text, clean))


GET: dict = {}
POST = {"/api/beruf/vorschlag": suggest, "/api/beruf/aufnehmen": add, "/api/beruf/entfernen": remove}
