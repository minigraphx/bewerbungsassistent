"""Routes of the preview in „Lebenslauf erstellen“ (G76, #294); what they build: cv_preview.py.

POST builds the preview of the choice as the page has it and writes nothing; the two GET routes give its pages as PNG
and the PDF. Neither the extension nor Claude reach them (desktop/native_host.py and desktop/mcp_tools.py list what
they may), and nothing goes to the AI.
"""
from http import HTTPStatus

import cv_creation
import cv_preview
import unterlagen
from server import ActionError, Antwort, json_antwort, pflicht

ROUTE = "/api/lebenslauf/erstellen/vorschau"
WRONG_PAGE = "Die Seite muss eine Zahl sein."


def _open_entry(k, entry_id: str) -> dict:
    entry = k.register().hole(entry_id)
    if entry.get("versand"):
        raise ValueError(unterlagen.SENT_STAYS)
    return entry


# Answers the page turns into a next step (cv_preview.CHECK_DATA, cv_preview.REOPEN); other refusals stay plain.
_ACTIONS = {cv_creation.UNREADABLE: cv_preview.CHECK_DATA, cv_creation.CHANGED: cv_preview.REOPEN,
            cv_creation.WRONG_STATION: cv_preview.REOPEN}


def _choice(k, body: dict) -> tuple[dict, cv_creation.Choice]:
    try:
        cv, stand = cv_creation.load_cv(k.daten)
        return cv, cv_creation.parse(cv, stand, body, k.daten)
    except ActionError:
        raise
    except ValueError as error:
        action = _ACTIONS.get(str(error))
        if action is None:
            raise
        raise ActionError(str(error), action) from error


def create(k, parameter, body):
    """Built outside the lock: the preview has its own temporary folder and writes nothing shared."""
    body = body if isinstance(body, dict) else {}
    entry = _open_entry(k, pflicht(body, "id"))
    cv, choice = _choice(k, body)
    preview = cv_preview.build(k.daten, entry, cv, choice, k.build)
    cv_preview.remember(k.cache, entry["id"], preview)
    return json_antwort({"schluessel": preview.key, "seiten": preview.pages})


def _page_number(parameter) -> int:
    try:
        return int(pflicht(parameter, "seite"))
    except ValueError as error:
        raise ValueError(WRONG_PAGE) from error


def page(k, parameter, body):
    entry_id = k.register().hole(pflicht(parameter, "id"))["id"]
    image = cv_preview.page_image(k.cache, entry_id, pflicht(parameter, "schluessel"), _page_number(parameter),
                                  parameter.get("groesse") or "klein", k.build)
    return Antwort(HTTPStatus.OK, "image/png", image)


def pdf(k, parameter, body):
    entry_id = k.register().hole(pflicht(parameter, "id"))["id"]
    preview = cv_preview.find(k.cache, entry_id, pflicht(parameter, "schluessel"))
    return Antwort(HTTPStatus.OK, "application/pdf", preview.pdf,
                   (("Content-Disposition", 'inline; filename="lebenslauf-vorschau.pdf"'),))


GET = {f"{ROUTE}/seite": page, f"{ROUTE}/pdf": pdf}
POST = {ROUTE: create}
