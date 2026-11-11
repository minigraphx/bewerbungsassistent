"""Routes for mark and accent colour of the dossier (G18): read, choose, upload and remove the logo, reset.

Every choice is saved at once, with drafts of cv.yaml before and after (`mark_settings.py`). The extension and
Claude do not reach these routes, and the logo never goes to the AI.
"""
import base64
import binascii

import logo_file
import mark_settings
from server import Antwort, json_antwort

UPLOAD_ROUTE = "/api/dossier/logo"
BODY_LIMITS = {UPLOAD_ROUTE: int(logo_file.MAX_BYTES * 4 / 3) + 10_000}  # base64 and the JSON around it


def show(k, parameter, body):
    return json_antwort(mark_settings.state(k))


def choose(k, parameter, body):
    return json_antwort(mark_settings.save(k, body))


def _logo_bytes(body) -> bytes:
    data = body.get("daten") if isinstance(body, dict) else None
    if not isinstance(data, str):
        raise ValueError(logo_file.FORMAT)
    if len(data) > BODY_LIMITS[UPLOAD_ROUTE]:
        raise ValueError(logo_file.TOO_LARGE)
    try:
        return base64.b64decode(data, validate=True)
    except binascii.Error as error:
        raise ValueError(logo_file.UNREADABLE) from error


def upload(k, parameter, body):
    return json_antwort(mark_settings.upload(k, _logo_bytes(body)))


def remove(k, parameter, body):
    return json_antwort(mark_settings.remove_logo(k))


def reset(k, parameter, body):
    return json_antwort(mark_settings.reset(k))


def logo(k, parameter, body):
    content_type, data = mark_settings.logo_bytes(k)
    return Antwort(200, content_type, data)


GET = {"/api/dossier/zeichen": show, "/api/dossier/logo": logo}
POST = {"/api/dossier/zeichen": choose, UPLOAD_ROUTE: upload, "/api/dossier/logo-entfernen": remove,
        "/api/dossier/zeichen-zuruecksetzen": reset}
