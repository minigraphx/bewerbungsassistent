"""Suggestions for professions (MIN-375): which apprenticeship could fit, from interests, strengths and the profile.

The answer is only ever a suggestion for a young person: it names a basic training with its certificate and says why,
and what comes back is checked before anyone sees it. Nothing is written here; adding to the search is the person's step.
"""
import re

import search_plan
from ai import prompts, tasks
from ai.errors import BAD_ANSWER, AiError
from ai.gateway import Gateway, Request

MAX_TEXT = 1000
MAX_RECOMMENDATIONS = 6
MAX_NAME = search_plan.MAX_VALUE
MAX_LINE = 400
BASIC_TRAINING = re.compile(r"[^\x00-\x1f\x85\u2028\u2029#<>]* (?:EFZ|EBA)(?:, Fachrichtung [^\x00-\x1f\x85\u2028\u2029#<>]+)?")
FIELDS = {"interessen": "interests", "staerken": "strengths", "vermeiden": "avoid"}
TEXT_KEYS = ("why", "daily", "check")
TOO_LONG = f"Bitte je Feld höchstens {MAX_TEXT} Zeichen."
ANSWERS_EXPECTED = "Interessen und Stärken erwartet."


def is_profession(name: object) -> bool:
    return isinstance(name, str) and len(name) <= MAX_NAME and bool(BASIC_TRAINING.fullmatch(name.strip()))


def clean_answers(body: object) -> dict[str, str]:
    if not isinstance(body, dict):
        raise ValueError(ANSWERS_EXPECTED)
    answers = {}
    for field, key in FIELDS.items():
        value = body.get(field)
        if value is not None and not isinstance(value, str):
            raise ValueError(ANSWERS_EXPECTED)
        answers[key] = (value or "").strip()
        if len(answers[key]) > MAX_TEXT:
            raise ValueError(TOO_LONG)
    return answers


def _clean(raw: object) -> dict | None:
    if not isinstance(raw, dict) or not is_profession(raw.get("profession")):
        return None
    texts = {key: raw.get(key).strip()[:MAX_LINE] for key in TEXT_KEYS if isinstance(raw.get(key), str) and raw.get(key).strip()}
    return {"profession": " ".join(raw["profession"].split()), **texts} if len(texts) == len(TEXT_KEYS) else None


def _suggestions(data: object) -> list[dict]:
    raw = data.get("recommendations") if isinstance(data, dict) else None
    found = [item for item in map(_clean, raw if isinstance(raw, list) else []) if item]
    unique: dict[frozenset[str], dict] = {}
    for item in found:
        unique.setdefault(search_plan.profession_words(item["profession"]), item)
    return list(unique.values())[:MAX_RECOMMENDATIONS]


def recommend(gateway: Gateway, material: tasks.Material, answers: dict[str, str], model: str | None = None) -> dict:
    answer = gateway.ask(Request(task="career", model=model or tasks.MODELS["career"], rules=prompts.RULES,
                                 context=material.context, instructions=prompts.CAREER, prompt=prompts.career_prompt(answers),
                                 max_tokens=tasks.MAX_TOKENS["career"], schema=prompts.CAREER_SCHEMA))
    suggestions = _suggestions(answer.data)
    if not suggestions:
        raise AiError(BAD_ANSWER)
    return {"recommendations": suggestions, "model": answer.model, "cost_usd": answer.cost_usd}
