"""Routes for suggestions of professions (MIN-375), only with an apprenticeship profile and only for the page of the app."""
import routes_ai
import search_plan
from ai import career
from dateien import schreibe_atomar
from server import json_antwort

ONLY_APPRENTICESHIP = "Berufsvorschläge gibt es vorerst nur bei der Lehrstellensuche."
BOTH_NEEDED = "Schreib zu beidem etwas: was du gern machst und was du gut kannst."
NO_PROFESSION = "Das ist kein Beruf mit EFZ oder EBA."


def _require_apprenticeship(k) -> None:
    if search_plan.kind_of_folder(k.daten) != search_plan.KIND_APPRENTICESHIP:
        raise ValueError(ONLY_APPRENTICESHIP)


def _searched(k) -> list[str]:
    """What the profile names; a profile that cannot be searched with yet may have none."""
    return list(search_plan.professions_in((k.daten / search_plan.PROFILE).read_text(encoding="utf-8")))


def suggest(k, parameter, body):
    _require_apprenticeship(k)
    answers = career.clean_answers(body)
    if not answers["interests"] or not answers["strengths"]:
        raise ValueError(BOTH_NEEDED)

    def task():
        gateway, material = routes_ai.ai_gateway(k)
        return career.recommend(gateway, material, answers)

    result = routes_ai.run_ai(task)
    searched = set(map(search_plan.profession_words, _searched(k)))
    return json_antwort({"vorschlaege": [
        {"beruf": item["profession"], "warum": item["why"], "alltag": item["daily"], "pruefen": item["check"],
         "schon_gesucht": search_plan.profession_words(item["profession"]) in searched} for item in result["recommendations"]]})


def add(k, parameter, body):
    _require_apprenticeship(k)
    name = body.get("beruf") if isinstance(body, dict) else None
    if not career.is_profession(name):
        raise ValueError(NO_PROFESSION)
    path = k.daten / search_plan.PROFILE

    def write() -> None:
        # read under the lock: two quick clicks, or a change of the offers, must not lose each other's line
        changed = search_plan.with_profession(path.read_text(encoding="utf-8"), name.strip())
        schreibe_atomar(path, changed.encode("utf-8"))

    k.mit_entwurf(path, f"Beruf aufgenommen: {name.strip()}", write)
    return json_antwort({"berufe": _searched(k)})


GET: dict = {}
POST = {"/api/beruf/vorschlag": suggest, "/api/beruf/aufnehmen": add}
