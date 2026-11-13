"""Routes for „Lebenslauf erstellen“ on the page of an application (G17, #118); what they write: cv_creation.py.

Neither the extension nor Claude reach them (desktop/native_host.py and desktop/mcp_tools.py list what they may).
"""
import cv_creation
import unterlagen
from server import json_antwort, pflicht

ROUTE = "/api/lebenslauf/erstellen"
DOSSIER_LATER = "Gespeichert. Das Dossier entsteht mit „Unterlagen erstellen“ neu, mit diesem Lebenslauf."


def _open_entry(k, entry_id: str) -> dict:
    entry = k.register().hole(entry_id)
    if entry.get("versand"):
        raise ValueError(unterlagen.SENT_STAYS)
    return entry


def show(k, parameter, body):
    return json_antwort(cv_creation.form(k.daten, k.register().hole(pflicht(parameter, "id"))))


def _write(k, entry: dict, choice: cv_creation.Choice, job: dict) -> dict:
    """Tailoring, variant and application, each with drafts before and after."""
    what = f"Lebenslauf für {entry['stelle']}, {entry['firma']}"
    variant_id = cv_creation.variant_id_for(k.daten, entry["id"])
    path = cv_creation.job_path(k.daten, variant_id)
    k.mit_entwurf(path, f"{what} erstellt", lambda: cv_creation.write_tailoring(path, job))
    variants = k.varianten()
    saved = k.mit_entwurf(variants.pfad, f"Variante {variant_id} für {what}",
                          lambda: variants.speichere(cv_creation.variant(variant_id, entry, choice)))
    register = k.register()
    k.mit_entwurf(register.pfad, f"Bewerbung {entry['id']}: {what} gewählt", lambda: register.speichere(
        {**register.hole(entry["id"]), "variante": variant_id, "lebenslauf_design": choice.design}))
    return saved


def _build(k, entry_id: str) -> tuple[bool, str | None]:
    """The new CV as PDF; with a dossier chosen it is built together with the dossier, later."""
    with k.sperre:
        entry = k.register().hole(entry_id)
        if unterlagen.wants_dossier(entry):
            return False, DOSSIER_LATER
        try:
            unterlagen.build_cv(k.daten, entry, k.build)
        except ValueError as error:  # saved already; the person learns why there is no PDF yet
            return False, f"Gespeichert, aber das PDF fehlt noch: {error}"
    return True, None


def create(k, parameter, body):
    body = body if isinstance(body, dict) else {}
    entry = _open_entry(k, pflicht(body, "id"))
    cv, stand = cv_creation.load_cv(k.daten)
    choice = cv_creation.parse(cv, stand, body)
    saved = _write(k, entry, choice, cv_creation.tailoring(cv, entry["id"], choice))
    built, note = _build(k, entry["id"])
    return json_antwort({"variante": saved, "bewerbung": k.register().hole(entry["id"]), "gebaut": built,
                         "hinweis": note})


GET = {ROUTE: show}
POST = {ROUTE: create}
