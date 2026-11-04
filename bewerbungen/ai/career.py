"""What to search for when the person does not know yet (MIN-375): from interests, abilities and the profile.

An apprenticeship needs the name of a basic training with its certificate, a job a short term that portals can search.
What comes back is checked before anyone sees it. Nothing is written here; adding to the search is the person's step.
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
JOB_TERM = re.compile(r"[^\x00-\x1f\x85\u2028\u2029#<>,()`:|/][^\x00-\x1f\x85\u2028\u2029<>,()`:|/]+")
MAX_TERM = 50
MAX_TERM_WORDS = 5
GENDER_FORM = re.compile(r"/-?(?:in|r)\b")
TEXT_KEYS = ("why", "daily", "check")
MIN_AVOIDED_WORD = 4
ONLY_AVOIDED = "Alle Vorschläge enthielten etwas, das ausgeschlossen ist. Bitte nochmals versuchen oder die Angaben anpassen."
TOO_LONG = f"Bitte je Feld höchstens {MAX_TEXT} Zeichen."
ANSWERS_EXPECTED = "Interessen und Stärken erwartet."


def is_profession(name: object) -> bool:
    return isinstance(name, str) and len(name) <= MAX_NAME and bool(BASIC_TRAINING.fullmatch(name.strip()))


def is_job_term(name: object) -> bool:
    return (isinstance(name, str) and len(name) <= MAX_TERM and len(name.split()) <= MAX_TERM_WORDS
            and bool(JOB_TERM.fullmatch(name.strip())))


def is_valid_name(name: object, kind: str) -> bool:
    return is_profession(name) if kind == search_plan.KIND_APPRENTICESHIP else is_job_term(name)


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


def _clean(raw: object, kind: str) -> dict | None:
    if isinstance(raw, dict) and kind == search_plan.KIND_JOB and isinstance(raw.get("profession"), str):
        raw = {**raw, "profession": GENDER_FORM.sub("", raw["profession"])}  # one word finds more on the portals
    if not isinstance(raw, dict) or not is_valid_name(raw.get("profession"), kind):
        return None
    texts = {key: raw.get(key).strip()[:MAX_LINE] for key in TEXT_KEYS if isinstance(raw.get(key), str) and raw.get(key).strip()}
    return {"profession": " ".join(raw["profession"].split()), **texts} if len(texts) == len(TEXT_KEYS) else None


def _suggestions(data: object, kind: str = search_plan.KIND_APPRENTICESHIP) -> list[dict]:
    raw = data.get("recommendations") if isinstance(data, dict) else None
    found = [item for item in (_clean(entry, kind) for entry in (raw if isinstance(raw, list) else [])) if item]
    unique: dict[frozenset[str], dict] = {}
    for item in found:
        unique.setdefault(search_plan.profession_words(item["profession"]), item)
    return list(unique.values())[:MAX_RECOMMENDATIONS]


def _avoids(name: str, avoid: str) -> bool:
    """A name with a word the person ruled out: the model is told so too, but this cannot slip through."""
    words = (word for word in re.findall(r"\w+", avoid.casefold()) if len(word) >= MIN_AVOIDED_WORD)
    return any(word in name.casefold() for word in words)


def recommend(gateway: Gateway, material: tasks.Material, answers: dict[str, str], kind: str = search_plan.KIND_APPRENTICESHIP,
              model: str | None = None) -> dict:
    instructions = prompts.CAREER if kind == search_plan.KIND_APPRENTICESHIP else prompts.CAREER_JOB
    answer = gateway.ask(Request(task="career", model=model or tasks.MODELS["career"], rules=prompts.RULES,
                                 context=material.context, instructions=instructions, prompt=prompts.career_prompt(answers),
                                 max_tokens=tasks.MAX_TOKENS["career"], schema=prompts.CAREER_SCHEMA))
    suggestions = _suggestions(answer.data, kind)
    if not suggestions:
        raise AiError(BAD_ANSWER)
    wanted = [item for item in suggestions if not _avoids(item["profession"], answers["avoid"])]
    if not wanted:
        raise AiError(ONLY_AVOIDED)
    return {"recommendations": wanted, "model": answer.model, "cost_usd": answer.cost_usd}
