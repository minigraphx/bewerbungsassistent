"""Questions to the AI (MIN-376): bounded by topic and by cost, and it cannot do anything.

The conversation lives only on the page and comes along with each question; nothing is stored but the usual usage line
without content. The AI sees what every task sees (CV, profile, style, building blocks), never the register or anything
for the RAV, and it has no tools. The topic is bounded by its instructions, the cost by the model, short answers, the
length of what goes along and a number per day; with the mediation its monthly budget counts on top.
"""
import datetime

import search_plan
from ai import prompts, tasks
from ai.errors import BAD_ANSWER, AnswerError
from ai.gateway import Gateway, Request
from ai.usage import UsageLog

TASK = "chat"
MAX_QUESTION = 1000
MAX_TURN_TEXT = 2000
MAX_TURNS = 12  # older turns stay on the page but do not go along
MAX_HISTORY = 200  # what is accepted at all; a longer one did not come from the page
MAX_PER_DAY = 30
ROLES = ("person", "ki")
NO_QUESTION = "Bitte eine Frage schreiben."
TOO_LONG = f"Bitte höchstens {MAX_QUESTION} Zeichen."
BAD_FORM = "Die Anfrage hat eine unbekannte Form."


def _turn(raw: object) -> dict:
    if not isinstance(raw, dict) or raw.get("rolle") not in ROLES or not isinstance(raw.get("text"), str) or len(raw["text"]) > MAX_TURN_TEXT:
        raise ValueError(BAD_FORM)
    return {"rolle": raw["rolle"], "text": raw["text"]}


def clean_conversation(body: object) -> tuple[str, list[dict]]:
    if not isinstance(body, dict) or not isinstance(body.get("frage"), str) or not body["frage"].strip():
        raise ValueError(NO_QUESTION)
    question = body["frage"].strip()
    if len(question) > MAX_QUESTION:
        raise ValueError(TOO_LONG)
    history = body.get("verlauf", [])
    if not isinstance(history, list) or len(history) > MAX_HISTORY:
        raise ValueError(BAD_FORM)
    return question, [_turn(turn) for turn in history]


def remaining_today(log: UsageLog, today: datetime.date) -> int:
    asked = sum(1 for entry in log.entries() if entry.get("task") == TASK and str(entry.get("time", "")).startswith(today.isoformat()))
    return max(0, MAX_PER_DAY - asked)


def answer(gateway: Gateway, material: tasks.Material, question: str, history: list[dict], kind: str = search_plan.KIND_JOB) -> dict:
    instructions = prompts.CHAT_APPRENTICESHIP if kind == search_plan.KIND_APPRENTICESHIP else prompts.CHAT
    reply = gateway.ask(Request(task=TASK, model=tasks.MODELS[TASK], rules=prompts.RULES, context=material.context, instructions=instructions,
                                prompt=prompts.chat_prompt(history[-MAX_TURNS:], question), max_tokens=tasks.MAX_TOKENS[TASK]))
    if not reply.text.strip():
        raise AnswerError(BAD_ANSWER, cost_usd=reply.cost_usd)
    return {"text": reply.text.strip(), "model": reply.model, "cost_usd": reply.cost_usd}
