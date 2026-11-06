"""The page „Fragen“ (MIN-376); only for the page of the app, the extension and Claude over the local connection have no way here."""
import preferences
import routes_ai
import search_plan
from ai import chat
from ai.usage import UsageLog
from server import json_antwort

USED_UP = "Für heute sind Ihre Fragen aufgebraucht. Morgen geht es weiter."
ADULTS_ONLY = "Der Chat steht nur ab 18 Jahren zur Verfügung und ist bei der Lehrstellensuche ausgeschaltet."


def _remaining(k) -> int:
    return chat.remaining_today(UsageLog(k.daten), k.heute())


def _allowed(k) -> bool:
    """Minors do not talk to the AI directly (MIN-401): the search for an apprenticeship has no chat."""
    return preferences.strictest_kind(k.daten) != search_plan.KIND_APPRENTICESHIP


def state(k, parameter, body):
    return json_antwort({"eingerichtet": routes_ai.connected(), "erlaubt": _allowed(k), "hinweis": ADULTS_ONLY, "uebrig": _remaining(k), "grenze": chat.MAX_PER_DAY})


def send(k, parameter, body):
    if not _allowed(k):
        raise ValueError(ADULTS_ONLY)
    question, history = chat.clean_conversation(body)
    if _remaining(k) <= 0:
        raise ValueError(USED_UP)

    def task():
        gateway, material = routes_ai.ai_gateway(k)
        return chat.answer(gateway, material, question, history)

    result = routes_ai.run_ai(task)
    return json_antwort({"antwort": result["text"], "modell": result["model"], "kosten_usd": result["cost_usd"], "uebrig": _remaining(k)})


GET = {"/api/fragen/stand": state}
POST = {"/api/fragen/senden": send}
