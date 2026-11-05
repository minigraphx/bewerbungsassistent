"""API routes for the AI tasks (MIN-334, MIN-338): status, rate a job, draft the cover letter, review content.

Every call goes through `ai.gateway.Gateway`, so nothing leaves the computer unpseudonymized. AI calls run
outside the lock; only writing the letter holds it (via `mit_entwurf`, which also saves drafts).
"""
import yaml

import letter_approval
import unterlagen
from ai import form_help, invitation, tasks
from ai.connection import find_connection, make_client, mediation_url, own_key
from ai.errors import AiError
from ai.usage import UsageLog
from dateien import schreibe_atomar
from server import json_antwort, pflicht

LETTER_FILE = "anschreiben.yaml"
STELLE_FILE = "stelle.md"
NO_AD = "Zuerst den Stellentext einfügen und speichern."
OWN_LETTER_NO_DRAFT = "Für diese Bewerbung gilt das eigene Anschreiben. Für einen Entwurf zuerst die Datei entfernen."
OWN_LETTER_NO_REVIEW = "Das eigene Anschreiben geht nicht an die KI. Bitte selbst mit dem Inserat vergleichen."


def new_client():
    """Client for the configured connection; replaced in tests."""
    return make_client(find_connection())


def _folder(k, application_id: str):
    return unterlagen.bewerbungsordner(k.daten, application_id)


def _ad_text(k, application_id: str) -> str:
    path = _folder(k, application_id) / STELLE_FILE
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if not text.strip():
        raise ValueError(NO_AD)
    return text


def _letter(k, application_id: str) -> dict | None:
    path = _folder(k, application_id) / LETTER_FILE
    if not path.is_file():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ValueError(f"{LETTER_FILE} lässt sich nicht lesen.") from error
    if not isinstance(data, dict):
        raise ValueError(f"{LETTER_FILE} lässt sich nicht lesen.")
    return data


def _letter_text(letter: dict) -> str:
    parts = [letter.get("betreff"), letter.get("anrede"), letter.get("text"), letter.get("gruss")]
    return "\n\n".join(str(p).strip() for p in parts if p and str(p).strip())


def ai_gateway(k, entry: dict | None = None, letter: dict | None = None, partial: bool = False):
    material = tasks.load_material(k.daten, partial)
    return tasks.make_gateway(k.daten, material, new_client(), entry, letter), material


def run_ai(task):
    """AI errors are meant for the person: they become 400 with the German message."""
    try:
        return task()
    except AiError as error:
        raise ValueError(str(error)) from error


def connected() -> bool:
    """Is an AI set up? Without one a form is filled by the rules alone, and nobody needs to hear about it."""
    try:
        find_connection()
    except AiError:
        return False
    return True


def form_fields(k, entry: dict, fields: list[form_help.FormField]) -> dict:
    """Help for the open fields of a form. The ad may be missing: then only the assignment runs."""
    path = _folder(k, entry["id"]) / STELLE_FILE
    ad = path.read_text(encoding="utf-8") if path.is_file() else ""
    # With an own letter the draft may say something else than what goes out, and the own letter stays away from the AI.
    letter = None if unterlagen.own_letter(k.daten, entry) else _letter(k, entry["id"])

    def task():
        gateway, material = ai_gateway(k, entry, letter, partial=True)
        return form_help.assist(gateway, material, entry, ad, _letter_text(letter) if letter else "", fields)

    return run_ai(task)


def _status(k) -> dict:
    month = k.heute().strftime("%Y-%m")
    result = {"monat": month, "kosten_usd": UsageLog(k.daten).month_total_usd(month)}
    try:
        connection = find_connection()
    except AiError as error:
        try:
            invite = mediation_url() is not None
        except AiError:
            invite = False
        return {**result, "eingerichtet": False, "hinweis": str(error), "einladung": invite}
    result = {**result, "eingerichtet": True, "vermittlung": connection.via_mediation,
              "eigener_schluessel": own_key() is not None}
    if connection.via_mediation:
        try:
            konto = invitation.account(connection.base_url, connection.access)
            result = {**result, "budget_usd": konto.get("budget_usd"), "verbraucht_usd": konto.get("spent_usd")}
        except AiError as error:
            result = {**result, "hinweis": str(error)}
    return result


def status(k, parameter, body):
    return json_antwort(_status(k))


def redeem(k, parameter, body):
    if not isinstance(body, dict) or not isinstance(body.get("code"), str):
        raise ValueError("code erwartet")
    url = run_ai(mediation_url)
    if url is None:
        raise ValueError("Für diese App ist keine KI-Vermittlung eingerichtet.")
    run_ai(lambda: invitation.redeem(url, body["code"]))
    return json_antwort(_status(k))


def rate(k, parameter, body):
    entry = k.register().hole(pflicht(parameter, "id"))
    ad = _ad_text(k, entry["id"])

    def task():
        gateway, material = ai_gateway(k, entry, _letter(k, entry["id"]))
        return tasks.rate_match(gateway, material, ad)

    return json_antwort(run_ai(task))


def draft(k, parameter, body):
    entry = k.register().hole(pflicht(parameter, "id"))
    if unterlagen.own_letter(k.daten, entry):
        raise ValueError(OWN_LETTER_NO_DRAFT)
    ad = _ad_text(k, entry["id"])

    def task():
        gateway, material = ai_gateway(k, entry, _letter(k, entry["id"]))
        return tasks.draft_letter(gateway, material, entry, ad), material

    result, material = run_ai(task)
    path = _folder(k, entry["id"]) / LETTER_FILE

    def write() -> None:
        # read again under the lock: changes made while the AI was writing (recipient, place) stay
        letter = tasks.letter_file(result, material, entry, k.heute(), _letter(k, entry["id"]))
        schreibe_atomar(path, yaml.safe_dump(letter, allow_unicode=True, sort_keys=False).encode("utf-8"))

    k.mit_entwurf(path, f"Anschreiben {entry['firma']} von der KI entworfen", write)
    return json_antwort({key: result.get(key) for key in ("claims", "gaps_named", "suspicious_lines", "model",
                                                           "cost_usd")})


def review(k, parameter, body):
    entry = k.register().hole(pflicht(parameter, "id"))
    if unterlagen.own_letter(k.daten, entry):  # the draft may say something else than what will go out
        raise ValueError(OWN_LETTER_NO_REVIEW)
    ad = _ad_text(k, entry["id"])
    letter = _letter(k, entry["id"])
    if letter is None:
        raise ValueError("Zuerst ein Anschreiben entwerfen.")

    def task():
        gateway, material = ai_gateway(k, entry, letter)
        return tasks.review_content(gateway, material, ad, _letter_text(letter))

    result = run_ai(task)
    letter_approval.keep_review(k.daten, entry["id"], result, k.heute())  # shown until the letter changes (MIN-369)
    return json_antwort(result)


GET = {"/api/ki/status": status}
POST = {"/api/ki/einladung": redeem, "/api/ki/bewerten": rate, "/api/ki/anschreiben": draft,
        "/api/ki/pruefen": review}
