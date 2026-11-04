"""AI help for the fields of a form (MIN-346): which value a field asks for, and drafts for open questions.

The assignment sees what the page shows and the names of the values, none of the values themselves. Drafts come from
the person's pseudonymized files. The page is a stranger: its texts are data, the labels of a request are new for
every call, and only known keys come back. A draft that would give contact details to the page is dropped.
"""
import dataclasses
import re
import secrets

from ai import prompts, tasks
from ai.errors import AiError, AnswerError, BAD_ANSWER
from ai.gateway import Gateway, Request
from ai.personal import secrets_from_building_blocks, secrets_from_cv
from ai.pseudonym import Pseudonymizer

KEYS = {
    "full_name": "Vor- und Nachname zusammen in einem Feld", "first_name": "Vorname", "last_name": "Nachname",
    "last_first": "Nachname, Vorname in einem Feld", "postal_city": "PLZ und Ort in einem Feld", "email": "E-Mail",
    "phone": "Telefon", "street": "Strasse und Hausnummer", "postal_code": "Postleitzahl", "city": "Wohnort",
    "country": "Land des Wohnorts", "website": "eigene Website", "linkedin": "LinkedIn-Profil", "github": "GitHub-Profil",
    "availability": "frühester Eintritt", "notice": "Kündigungsfrist", "salary": "Lohnvorstellung",
}
UNCLEAR = "unklar"
QUESTION = "frage"
KINDS = (UNCLEAR, QUESTION)
MAX_FIELDS = 12
MAX_LABEL = 300
MAX_NAME = 100
MAX_HINT = 150
MAX_OPTION = 60
MAX_OPTIONS = 20
MAX_ANSWER_CHARS = 1500
MAX_LINE_CHARS = 200
LABEL_BYTES = 2
REF = re.compile(r"f\d{1,6}")
# A name is what a person signs with; a short number or a user name can be an ordinary word in a text.
ALLOWED_IN_DRAFTS = ("NAME", "POSTAL_CODE", "PROFILE_USER")
UNKNOWN_FORM = "Die Felder haben eine unbekannte Form."
TOO_MANY = f"Pro Anfrage gehen höchstens {MAX_FIELDS} Felder."
NO_AD = "Für Textentwürfe fehlt das Inserat. Offene Fragen bleiben bei Ihnen."
SUSPICIOUS = "Im Formular stehen Zeilen, die sich an eine KI richten. Entwürfe bitte besonders genau prüfen."
DROPPED = "Ein Entwurf nannte Kontaktangaben oder Referenzen und wurde verworfen. Diese Frage bleibt bei Ihnen."


@dataclasses.dataclass(frozen=True)
class FormField:
    ref: str
    is_question: bool
    label: str
    name: str
    hint: str
    options: tuple[str, ...]
    limit: int
    one_line: bool

    def shown(self) -> dict[str, str]:
        return {"Beschriftung": self.label, "Feldname": self.name, "Hinweis": self.hint,
                "Auswahlwerte": " | ".join(self.options)}

    def asked(self) -> dict[str, str]:
        return {"Frage": self.label or self.hint or self.name, "Hinweis": self.hint if self.label else "",
                "Länge": f"höchstens {self.limit} Zeichen{', einzeilig' if self.one_line else ''}"}


def _short(value: object, limit: int) -> str:
    return " ".join(value.split())[:limit] if isinstance(value, str) else ""


def _limit(raw: dict) -> int:
    one_line = raw.get("einzeilig") is not False
    longest = MAX_LINE_CHARS if one_line else MAX_ANSWER_CHARS
    allowed = raw.get("laenge")
    return min(allowed, longest) if isinstance(allowed, int) and not isinstance(allowed, bool) and allowed > 0 else longest


def _clean_field(raw: object) -> FormField:
    if not isinstance(raw, dict) or not isinstance(raw.get("ref"), str) or not REF.fullmatch(raw["ref"]) or raw.get("art") not in KINDS:
        raise ValueError(UNKNOWN_FORM)
    options = raw.get("optionen")
    shown = options[:MAX_OPTIONS] if isinstance(options, list) else []
    return FormField(raw["ref"], raw["art"] == QUESTION, _short(raw.get("label"), MAX_LABEL), _short(raw.get("name"), MAX_NAME),
                     _short(raw.get("hinweis"), MAX_HINT), tuple(t for t in (_short(o, MAX_OPTION) for o in shown) if t),
                     _limit(raw), raw.get("einzeilig") is not False)


def clean_fields(raw: object) -> list[FormField]:
    """The request as the page's content came in; fields without any text have nothing to decide."""
    if not isinstance(raw, list) or not raw:
        raise ValueError(UNKNOWN_FORM)
    if len(raw) > MAX_FIELDS:
        raise ValueError(TOO_MANY)
    fields = [_clean_field(item) for item in raw]
    if len({f.ref for f in fields}) != len(fields):
        raise ValueError(UNKNOWN_FORM)
    return [f for f in fields if f.label or f.name or f.hint]


def _labels(fields: list[FormField]) -> dict[str, FormField]:
    return {f"F{n}-{secrets.token_hex(LABEL_BYTES)}": field for n, field in enumerate(fields, 1)}


def _entries(data: object, list_key: str, labels: dict) -> dict[str, dict]:
    """Entries of this request only, each label once: a label named twice says nothing."""
    entries = data.get(list_key) if isinstance(data, dict) else None
    if not isinstance(entries, list):
        raise AnswerError(BAD_ANSWER)
    named = [e.get("id") for e in entries if isinstance(e, dict)]
    return {e["id"]: e for e in entries if isinstance(e, dict) and e.get("id") in labels and named.count(e["id"]) == 1}


def _suspicious(data: dict) -> bool:
    lines = data.get("suspicious_lines")
    return isinstance(lines, list) and any(isinstance(line, str) and line.strip() for line in lines)


def _assign(gateway: Gateway, fields: list[FormField]) -> tuple[dict[str, str], list[FormField], bool]:
    """(ref → key, fields that turned out to be questions, lines aimed at an AI found)."""
    labels = _labels(fields)
    instructions = prompts.FORM_FIELDS.format(keys="\n".join(f"- {key}: {text}" for key, text in KEYS.items()))
    answer = gateway.ask(Request(
        task="form_fields", model=tasks.MODELS["form_fields"], rules=prompts.FORM_FIELD_RULES, context="",
        instructions=instructions, prompt=prompts.form_fields_prompt([(label, f.shown()) for label, f in labels.items()]),
        max_tokens=tasks.MAX_TOKENS["form_fields"], schema=prompts.form_fields_schema(list(labels), [*KEYS, *KINDS])))
    found = _entries(answer.data, "fields", labels)
    keys = {labels[label].ref: e["key"] for label, e in found.items() if e.get("key") in KEYS}
    questions = [labels[label] for label, e in found.items() if e.get("key") == QUESTION and not labels[label].options]
    return keys, questions, _suspicious(answer.data)


def _contact_details(material: tasks.Material) -> Pseudonymizer:
    """The same matching as for masking: a phone number or a link is found in all its forms, a name only as a word."""
    found = secrets_from_cv(material.cv, minor=material.minor) + secrets_from_building_blocks(material.blocks)
    return Pseudonymizer([s for s in found if not s.field.startswith(ALLOWED_IN_DRAFTS)])


def _usable_draft(text: object, field: FormField) -> str:
    if not isinstance(text, str):
        return ""
    clean = " ".join(text.split()) if field.one_line else text.strip()
    return clean if len(clean) <= field.limit and "{{" not in clean else ""


def _draft(gateway: Gateway, material: tasks.Material, entry: dict, ad: str, letter: str,
           questions: list[FormField]) -> tuple[dict[str, str], list[str]]:
    """(ref → draft, notes for the person)."""
    labels = _labels(questions)
    details = {"Firma": str(entry.get("firma") or ""), "Stelle": str(entry.get("stelle") or "")}
    prompt = prompts.form_answers_prompt(ad, letter, details, [(label, f.asked()) for label, f in labels.items()])
    answer = gateway.ask(Request(
        task="form_answers", model=tasks.MODELS["form_answers"], rules=prompts.RULES, context=material.context,
        instructions=prompts.FORM_ANSWERS_TRIAL if entry.get("art") == tasks.TRIAL else prompts.FORM_ANSWERS,
        prompt=prompt, max_tokens=tasks.MAX_TOKENS["form_answers"], schema=prompts.form_answers_schema(list(labels))))
    contact = _contact_details(material)
    drafts, notes = {}, [SUSPICIOUS] if _suspicious(answer.data) else []
    for label, found in _entries(answer.data, "answers", labels).items():
        text = _usable_draft(found.get("text"), labels[label])
        if contact.finds(text):
            notes = [*notes, DROPPED]
        elif text:
            drafts[labels[label].ref] = text
    return drafts, notes


def assist(gateway: Gateway, material: tasks.Material, entry: dict, ad: str, letter: str, fields: list[FormField]) -> dict:
    """What is known for these fields. A failing step leaves the other one and a note: the form works without the AI.
    `wiederholen` says that a later try could know more; a field the AI left open stays open without it."""
    unclear = [f for f in fields if not f.is_question]
    questions = [f for f in fields if f.is_question]
    keys, notes, failed = {}, [], False
    if unclear:
        try:
            keys, found, suspicious = _assign(gateway, unclear)
            questions, notes = [*questions, *found], [SUSPICIOUS] if suspicious else []
        except AiError as error:
            notes, failed = [str(error)], True
    drafts = {}
    if questions and not ad.strip():
        notes = [*notes, NO_AD]
    elif questions:
        try:
            drafts, drafted = _draft(gateway, material, entry, ad[:tasks.MAX_AD_CHARS], letter, questions)
            notes = [*notes, *drafted]
        except AiError as error:
            notes, failed = [*notes, str(error)], True
    return {"zuordnung": keys, "entwuerfe": drafts, "hinweise": list(dict.fromkeys(notes)), "wiederholen": failed}
