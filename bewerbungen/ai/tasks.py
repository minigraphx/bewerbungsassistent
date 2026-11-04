"""AI tasks of the app: rate a job ad, draft a cover letter, review content (MIN-338).

Each task loads the person's files, builds a Gateway with a Pseudonymizer for exactly these files and
returns plain data. Writing files is left to the caller, so it can save drafts (Entwürfe) around it.
"""
import dataclasses
import datetime
import pathlib

import yaml

from ai import prompts
from ai.errors import BAD_ANSWER, AiError
from ai.gateway import Answer, Gateway, Request
from ai.personal import secrets_from_application, secrets_from_building_blocks, secrets_from_cv
from ai.pseudonym import Pseudonymizer
from ai.usage import UsageLog
from dateien import im_ordner

FILES = {"cv": "cv.yaml", "profile": "suchprofil.md", "style": "anschreiben/stil.md",
         "blocks": "anschreiben/bausteine.md"}
APPRENTICESHIP_MARK = "## Lehrbeginn"  # section only the apprenticeship search profile has
MODELS = {"rate": "claude-sonnet-5-5", "draft": "claude-opus-5-5", "review": "claude-sonnet-5-5",
          "prefill": "claude-sonnet-5-5"}
MAX_TOKENS = {"rate": 8000, "draft": 16000, "review": 12000, "prefill": 16000}
GRADES = {g / 2 for g in range(2, 13)}  # 1, 1.5, … 6
MAX_AD_CHARS = 30_000
MISSING = "Für die KI fehlt noch {name}. Zuerst den Einstieg abschliessen."


@dataclasses.dataclass(frozen=True)
class Material:
    """The person's basics as the AI sees them (before pseudonymization)."""
    cv: dict
    cv_text: str
    profile: str
    style: str
    blocks: str

    @property
    def minor(self) -> bool:
        return APPRENTICESHIP_MARK in self.profile

    @property
    def context(self) -> str:
        return prompts.context(self.cv_text, self.profile, self.style, self.blocks)


def load_material(data_dir: pathlib.Path) -> Material:
    texts = {}
    for key, rel in FILES.items():
        path = im_ordner(data_dir, rel)
        if not path.is_file():
            raise AiError(MISSING.format(name=rel))
        texts[key] = path.read_text(encoding="utf-8")
    try:
        cv = yaml.safe_load(texts["cv"]) or {}
    except yaml.YAMLError as error:
        raise AiError("cv.yaml lässt sich nicht lesen.") from error
    if not isinstance(cv, dict):
        raise AiError("cv.yaml lässt sich nicht lesen.")
    return Material(cv, texts["cv"], texts["profile"], texts["style"], texts["blocks"])


def make_gateway(data_dir: pathlib.Path, material: Material, client, entry: dict | None = None,
                 letter: dict | None = None) -> Gateway:
    secrets = secrets_from_cv(material.cv, minor=material.minor) + secrets_from_building_blocks(material.blocks)
    if entry is not None:
        secrets += secrets_from_application(entry, letter)
    return Gateway(client, Pseudonymizer(secrets), UsageLog(data_dir))


def _ad(ad_text: str) -> str:
    text = (ad_text or "").strip()
    if not text:
        raise AiError("Der Text des Inserats fehlt.")
    if len(text) > MAX_AD_CHARS:
        raise AiError(f"Das Inserat ist zu lang (höchstens {MAX_AD_CHARS} Zeichen).")
    return text


def _details(entry: dict) -> dict[str, str]:
    keys = {"firma": "Firma", "stelle": "Stelle", "ort": "Ort", "pensum": "Pensum", "kontaktperson": "Ansprechperson",
            "vermittler": "Vermittler"}
    return {label: str(entry[key]) for key, label in keys.items() if entry.get(key)}


def _ask(gateway: Gateway, material: Material, task: str, instructions: str, prompt: str, schema: dict,
         model: str | None) -> Answer:
    return gateway.ask(Request(task=task, model=model or MODELS[task], rules=prompts.RULES,
                               context=material.context,
                               instructions=instructions, prompt=prompt, max_tokens=MAX_TOKENS[task], schema=schema))


def rate_match(gateway: Gateway, material: Material, ad_text: str, model: str | None = None) -> dict:
    answer = _ask(gateway, material, "rate", prompts.RATE, prompts.job_prompt(_ad(ad_text)), prompts.RATE_SCHEMA, model)
    data = answer.data
    grade = data.get("grade") if isinstance(data, dict) else None
    if isinstance(grade, bool) or not isinstance(grade, (int, float)) or grade not in GRADES:
        raise AiError(BAD_ANSWER)
    return {**data, "model": answer.model, "cost_usd": answer.cost_usd}


def draft_letter(gateway: Gateway, material: Material, entry: dict, ad_text: str, model: str | None = None) -> dict:
    prompt = prompts.job_prompt(_ad(ad_text), _details(entry))
    answer = _ask(gateway, material, "draft", prompts.DRAFT, prompt, prompts.DRAFT_SCHEMA, model)
    data = answer.data
    if not _is_draft(data):
        raise AiError(BAD_ANSWER)
    return {**data, "model": answer.model, "cost_usd": answer.cost_usd}


def _is_draft(data) -> bool:
    if not isinstance(data, dict) or not all(isinstance(data.get(k), str) for k in ("subject", "salutation", "closing")):
        return False
    paragraphs = data.get("paragraphs")
    return isinstance(paragraphs, list) and bool(paragraphs) and all(isinstance(p, str) for p in paragraphs)


def review_content(gateway: Gateway, material: Material, ad_text: str, letter_text: str,
                   model: str | None = None) -> dict:
    prompt = prompts.review_prompt(_ad(ad_text), letter_text)
    answer = _ask(gateway, material, "review", prompts.REVIEW, prompt, prompts.REVIEW_SCHEMA, model)
    data = answer.data
    if not isinstance(data, dict) or not isinstance(data.get("requirements"), list):
        raise AiError(BAD_ANSWER)
    return {**data, "model": answer.model, "cost_usd": answer.cost_usd}


def suggest_from_documents(gateway: Gateway, prompt: str, schema: dict, model: str | None = None) -> dict:
    """Suggestions for the form from uploaded documents. There are no files of the person yet, so no shared context."""
    answer = gateway.ask(Request(task="prefill", model=model or MODELS["prefill"], rules=prompts.PREFILL_RULES,
                                 context="", instructions=prompts.PREFILL, prompt=prompt,
                                 max_tokens=MAX_TOKENS["prefill"], schema=schema))
    if not isinstance(answer.data, dict):
        raise AiError(BAD_ANSWER)
    return {**answer.data, "model": answer.model, "cost_usd": answer.cost_usd}


def letter_file(draft: dict, material: Material, entry: dict, today: datetime.date,
                existing: dict | None = None) -> dict:
    """Content of anschreiben.yaml from a draft. Everything else in an existing file stays (sender,
    signature, language, recipient, place); only date, subject, salutation, text and closing are new."""
    old = dict(existing or {})
    basics = material.cv.get("basics") if isinstance(material.cv.get("basics"), dict) else {}
    location = basics.get("location") if isinstance(basics.get("location"), dict) else {}
    recipient = old.get("empfaenger") or [line for line in (entry.get("firma"), entry.get("kontaktperson")) if line]
    return {
        "lebenslauf": "../../cv.yaml",
        **old,
        "empfaenger": recipient,
        "ort": old.get("ort") or location.get("city") or "",
        "datum": today.isoformat(),
        "betreff": draft["subject"],
        "anrede": draft["salutation"],
        "text": "\n\n".join(p.strip() for p in draft["paragraphs"] if p.strip()) + "\n",
        "gruss": draft["closing"],
    }
