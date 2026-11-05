"""The page „Fragen“ (MIN-376); only for the page of the app, the extension and Claude over the local connection have no way here."""
import routes_ai
import search_plan
from ai import chat
from ai.usage import UsageLog
from server import json_antwort

USED_UP = {search_plan.KIND_APPRENTICESHIP: "Für heute sind deine Fragen aufgebraucht. Morgen geht es weiter.",
           search_plan.KIND_JOB: "Für heute sind Ihre Fragen aufgebraucht. Morgen geht es weiter."}


def _remaining(k) -> int:
    return chat.remaining_today(UsageLog(k.daten), k.heute())


def state(k, parameter, body):
    return json_antwort({"eingerichtet": routes_ai.connected(), "art": search_plan.kind_of_folder(k.daten), "uebrig": _remaining(k), "grenze": chat.MAX_PER_DAY})


def send(k, parameter, body):
    question, history = chat.clean_conversation(body)
    kind = search_plan.kind_of_folder(k.daten)
    if _remaining(k) <= 0:
        raise ValueError(USED_UP[kind])

    def task():
        gateway, material = routes_ai.ai_gateway(k)
        return chat.answer(gateway, material, question, history, kind)

    result = routes_ai.run_ai(task)
    return json_antwort({"antwort": result["text"], "modell": result["model"], "kosten_usd": result["cost_usd"], "uebrig": _remaining(k)})


GET = {"/api/fragen/stand": state}
POST = {"/api/fragen/senden": send}
