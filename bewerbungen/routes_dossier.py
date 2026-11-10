"""Routes for greeting and thanks of the dossier (G19): read, save what the person wrote, draft them by the AI.

The AI draft goes through `routes_ai.ai_gateway` like the cover letter, so the person's data leaves the computer
only as placeholders. Both writes save drafts before and after. The extension and Claude do not reach these routes.
"""
import dossier_texts
import routes_ai
import unterlagen
from ai import tasks
from server import json_antwort, pflicht

DEFAULT_LANGUAGE = "de"


def _open_entry(k, entry_id: str) -> dict:
    entry = k.register().hole(entry_id)
    if entry.get("versand"):  # what went out stays as it was
        raise ValueError(unterlagen.SENT_STAYS)
    return entry


def _save(k, entry: dict, texts: dict[str, str], what: str) -> dict[str, str]:
    file = dossier_texts.path(k.daten, entry["id"])
    return k.mit_entwurf(file, f"{what} {entry['firma']}", lambda: dossier_texts.write(k.daten, entry["id"], texts))


def show(k, parameter, body):
    entry = k.register().hole(pflicht(parameter, "id"))
    return json_antwort(dossier_texts.read(k.daten, entry["id"]))


def save(k, parameter, body):
    texts = dossier_texts.checked(body)
    entry = _open_entry(k, pflicht(parameter, "id"))
    return json_antwort(_save(k, entry, texts, "Begrüssung und Dank im Dossier"))


def _ad(k, entry_id: str) -> str:
    file = unterlagen.bewerbungsordner(k.daten, entry_id) / routes_ai.STELLE_FILE
    return file.read_text(encoding="utf-8") if file.is_file() else ""


def draft(k, parameter, body):
    entry = _open_entry(k, pflicht(parameter, "id"))
    letter, letter_text = routes_ai.letter_for_ai(k, entry)
    language = str((letter or {}).get("sprache") or DEFAULT_LANGUAGE)
    ad = _ad(k, entry["id"])

    def task():
        gateway, material = routes_ai.ai_gateway(k, entry, letter)
        return tasks.draft_dossier_texts(gateway, material, entry, ad, letter_text, language)

    result = routes_ai.run_ai(task)
    texts = dossier_texts.checked({"gruss": result["greeting"], "dank": result["thanks"]})
    saved = _save(k, _open_entry(k, entry["id"]), texts, "Begrüssung und Dank im Dossier von der KI entworfen")
    return json_antwort({**saved, **{key: result[key] for key in ("suspicious_lines", "model", "cost_usd")}})


GET = {"/api/dossier/texte": show}
POST = {"/api/dossier/texte": save, "/api/ki/dossier-texte": draft}
