"""AI tasks of the app: rate a job ad, draft a cover letter, review content (MIN-338).

Each task loads the person's files, builds a Gateway with a Pseudonymizer for exactly these files and
returns plain data. Writing files is left to the caller, so it can save drafts (Entwürfe) around it.
"""
import dataclasses
import datetime
import pathlib
import secrets

import yaml

from ai import prompts
from ai.errors import BAD_ANSWER, AiError, AnswerError
from ai.gateway import Answer, Gateway, Request
from ai.personal import secrets_from_application, secrets_from_building_blocks, secrets_from_cv, with_written_monogram
from ai.pseudonym import Pseudonymizer
from ai.usage import UsageLog
import preferences
from dateien import im_ordner

FILES = {"cv": "cv.yaml", "profile": "suchprofil.md", "style": "anschreiben/stil.md",
         "blocks": "anschreiben/bausteine.md"}
TRIAL = "Schnupperlehre"  # register field „art“
APPRENTICESHIP_MARK = "## Lehrbeginn"  # section only the apprenticeship search profile has
MODELS = {"rate": "claude-sonnet-5-5", "draft": "claude-opus-5-5", "review": "claude-sonnet-5-5",
          "prefill": "claude-sonnet-5-5", "rate_package": "claude-sonnet-5-5", "form_fields": "claude-haiku-5-5",
          "form_answers": "claude-sonnet-5-5", "career": "claude-sonnet-5-5", "site_list": "claude-haiku-5-5", "chat": "claude-haiku-5-5",
          "dossier_texts": "claude-sonnet-5-5", "terms": "claude-haiku-5-5"}
MAX_TOKENS = {"rate": 8000, "draft": 16000, "review": 12000, "prefill": 16000, "rate_package": 12000,
              "form_fields": 2000, "form_answers": 8000, "career": 4000, "site_list": 6000, "chat": 1500, "dossier_texts": 4000,
              "terms": 3000}
GRADES = {g / 2 for g in range(2, 13)}  # 1, 1.5, … 6
MAX_AD_CHARS = 30_000
PACKAGE_SIZE = 10
MAX_PACKAGE_AD_CHARS = 12_000  # ten long ads must not cost as much as a book; ads are rarely longer
LABEL_BYTES = 2
MISSING = "Für die KI fehlt noch {name}. Zuerst Meine Angaben abschliessen."


@dataclasses.dataclass(frozen=True)
class Material:
    """The person's basics as the AI sees them (before pseudonymization)."""
    cv: dict
    cv_text: str
    profile: str
    style: str
    blocks: str
    missing: tuple[str, ...] = ()
    address: str = preferences.SIE  # how the AI speaks to the person (MIN-369)
    apprenticeship_chosen: bool = False  # in the setup, also before the search profile says so (MIN-401)

    @property
    def minor(self) -> bool:
        """Without a search profile nobody knows: then the stricter masking applies."""
        return self.apprenticeship_chosen or APPRENTICESHIP_MARK in self.profile or FILES["profile"] in self.missing

    @property
    def context(self) -> str:
        return prompts.context(self.cv_text, self.profile, self.style, self.blocks)


def load_material(data_dir: pathlib.Path, partial: bool = False) -> Material:
    """`partial` is for tasks that use only what the page shows: whoever uploaded their own files has no style profile."""
    paths = {key: im_ordner(data_dir, rel) for key, rel in FILES.items()}
    missing = tuple(FILES[key] for key, path in paths.items() if not path.is_file())
    if missing and not partial:
        raise AiError(MISSING.format(name=missing[0]))
    texts = {key: path.read_text(encoding="utf-8") if path.is_file() else "" for key, path in paths.items()}
    try:
        cv = yaml.safe_load(texts["cv"]) or {}
    except yaml.YAMLError as error:
        raise AiError("cv.yaml lässt sich nicht lesen.") from error
    if not isinstance(cv, dict):
        raise AiError("cv.yaml lässt sich nicht lesen.")
    return Material(with_written_monogram(cv, texts["cv"]), texts["cv"], texts["profile"], texts["style"], texts["blocks"], missing,
                    preferences.load(data_dir).address,
                    preferences.strictest_kind(data_dir) == preferences.APPRENTICESHIP)


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
    return gateway.ask(Request(task=task, model=model or MODELS[task], rules=prompts.rules(material.address),
                               context=material.context,
                               instructions=instructions, prompt=prompt, max_tokens=MAX_TOKENS[task], schema=schema))


def rate_match(gateway: Gateway, material: Material, ad_text: str, model: str | None = None) -> dict:
    instructions = prompts.RATE_APPRENTICESHIP if material.minor else prompts.RATE
    answer = _ask(gateway, material, "rate", instructions, prompts.job_prompt(_ad(ad_text)), prompts.RATE_SCHEMA, model)
    data = answer.data
    if not isinstance(data, dict) or not _is_grade(data.get("grade")):
        raise AiError(BAD_ANSWER)
    return {**data, "model": answer.model, "cost_usd": answer.cost_usd}


def _is_grade(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and value in GRADES


def _texts(value: object) -> list[str]:
    return [line for line in value if isinstance(line, str)] if isinstance(value, list) else []


def _clean_rating(raw: dict, minor: bool) -> dict | None:
    if not _is_grade(raw.get("grade")):
        return None
    rating = {"grade": raw["grade"], "summary": raw["summary"] if isinstance(raw.get("summary"), str) else "",
              "fits": _texts(raw.get("fits")), "hooks": _texts(raw.get("hooks")), "new_gaps": _texts(raw.get("new_gaps")),
              "suspicious_lines": _texts(raw.get("suspicious_lines")),
              "uncertain": raw["uncertain"].strip() if isinstance(raw.get("uncertain"), str) else ""}
    if minor and _is_grade(raw.get("profession_grade")):
        return {**rating, "profession_grade": raw["profession_grade"]}
    return rating


def _ratings_by_label(data: object, labels: list[str], minor: bool) -> dict[str, dict]:
    """Only entries whose label belongs to this request, each label once; a label named twice says nothing."""
    entries = data.get("ratings") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        raise AnswerError(BAD_ANSWER)
    named = [e.get("id") for e in entries if isinstance(e, dict)]
    usable = {e["id"]: _clean_rating(e, minor) for e in entries
              if isinstance(e, dict) and e.get("id") in labels and named.count(e["id"]) == 1}
    return {label: rating for label, rating in usable.items() if rating}


def rate_package(gateway: Gateway, material: Material, ads: list[tuple[str, str]], model: str | None = None) -> dict:
    """Rate several ads in one call; ads are (id, text). The label of an ad is new for every call, so a text cannot
    aim at another ad, and a rating belongs to an id only through its label. Ids without a usable answer are `missing`."""
    if not 1 <= len(ads) <= PACKAGE_SIZE:
        raise ValueError(f"Ein Paket hat 1 bis {PACKAGE_SIZE} Inserate.")
    labels = [f"T{number}-{secrets.token_hex(LABEL_BYTES)}" for number in range(1, len(ads) + 1)]
    by_label = {label: ad_id for label, (ad_id, _) in zip(labels, ads)}
    texts = [(label, _ad(text[:MAX_PACKAGE_AD_CHARS])) for label, (_, text) in zip(labels, ads)]
    instructions = prompts.RATE_PACKAGE_APPRENTICESHIP if material.minor else prompts.RATE_PACKAGE
    schema = prompts.rate_package_schema(labels, material.minor)
    answer = _ask(gateway, material, "rate_package", instructions, prompts.package_prompt(texts), schema, model)
    try:
        found = _ratings_by_label(answer.data, labels, material.minor)
    except AnswerError as error:
        raise AnswerError(str(error), cost_usd=answer.cost_usd) from error
    ratings = {by_label[label]: rating for label, rating in found.items()}
    return {"ratings": ratings, "missing": [ad_id for ad_id, _ in ads if ad_id not in ratings],
            "model": answer.model, "cost_usd": answer.cost_usd}


def draft_letter(gateway: Gateway, material: Material, entry: dict, ad_text: str, model: str | None = None) -> dict:
    prompt = prompts.job_prompt(_ad(ad_text), _details(entry))
    instructions = prompts.DRAFT_TRIAL if entry.get("art") == TRIAL else prompts.DRAFT
    answer = _ask(gateway, material, "draft", instructions, prompt, prompts.DRAFT_SCHEMA, model)
    data = answer.data
    if not _is_draft(data):
        raise AiError(BAD_ANSWER)
    return {**data, "model": answer.model, "cost_usd": answer.cost_usd}


def _is_draft(data) -> bool:
    if not isinstance(data, dict) or not all(isinstance(data.get(k), str) for k in ("subject", "salutation", "closing")):
        return False
    paragraphs = data.get("paragraphs")
    return isinstance(paragraphs, list) and bool(paragraphs) and all(isinstance(p, str) for p in paragraphs)


def draft_dossier_texts(gateway: Gateway, material: Material, entry: dict, ad_text: str, letter_text: str,
                        language: str, model: str | None = None) -> dict:
    """Greeting and thanks of the dossier (G19); the ad may be empty, a long one is cut like in a package."""
    ad = (ad_text or "").strip()[:MAX_AD_CHARS]
    prompt = prompts.dossier_texts_prompt(ad, _details(entry), letter_text, language)
    answer = _ask(gateway, material, "dossier_texts", prompts.DOSSIER_TEXTS, prompt, prompts.DOSSIER_TEXTS_SCHEMA, model)
    data = answer.data
    if not isinstance(data, dict) or not all(isinstance(data.get(key), str) for key in ("greeting", "thanks")):
        raise AiError(BAD_ANSWER)
    return {"greeting": data["greeting"].strip(), "thanks": data["thanks"].strip(),
            "suspicious_lines": _texts(data.get("suspicious_lines")), "model": answer.model,
            "cost_usd": answer.cost_usd}


def review_content(gateway: Gateway, material: Material, ad_text: str, letter_text: str,
                   model: str | None = None) -> dict:
    prompt = prompts.review_prompt(_ad(ad_text), letter_text)
    answer = _ask(gateway, material, "review", prompts.REVIEW, prompt, prompts.REVIEW_SCHEMA, model)
    data = answer.data
    if not isinstance(data, dict) or not isinstance(data.get("requirements"), list):
        raise AiError(BAD_ANSWER)
    return {**data, "model": answer.model, "cost_usd": answer.cost_usd}


def suggest_from_documents(gateway: Gateway, prompt: str, field_guide: str, model: str | None = None) -> dict:
    """Suggestions for the form from uploaded documents. There are no files of the person yet, so no shared context."""
    answer = gateway.ask(Request(task="prefill", model=model or MODELS["prefill"], rules=prompts.PREFILL_RULES,
                                 context="", instructions=f"{prompts.PREFILL}\n\n{prompts.PREFILL_FIELDS}\n{field_guide}", prompt=prompt,
                                 max_tokens=MAX_TOKENS["prefill"], schema=prompts.PREFILL_SCHEMA))
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
