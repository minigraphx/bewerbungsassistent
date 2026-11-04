"""Routes for applying through a form (MIN-346): the choice in the overview, and what the extension needs for a tab.

Only `abgeschickt` records a dispatch, and the extension calls it only after the person pressed its button.
"""
import base64

import apply
import pruefung
import versand
from register import FORM_STATES
from server import json_antwort, pflicht

OPENED, FILLED, SENT = FORM_STATES
TOO_MANY = f"Pro Durchgang gehen höchstens {apply.MAX_PER_RUN} Bewerbungen."
NONE_CHOSEN = "Bitte zuerst Bewerbungen ankreuzen."
BAD_STATE = "Dieser Stand ist unbekannt."


def _body_id(body) -> str:
    if not isinstance(body, dict) or not isinstance(body.get("id"), str):
        raise ValueError("Bewerbung mit id erwartet")
    return body["id"]


def choice(k, parameter, body):
    rows = [{"id": b["id"], "grund": apply.blocker(k.daten, b)} for b in k.register().alle()]
    return json_antwort({"bewerbungen": rows, "hoechstens": apply.MAX_PER_RUN})


def _problem(k, entry: dict) -> str | None:
    """Everything that speaks against opening it, with the full check of the documents."""
    reason = apply.blocker(k.daten, entry)
    if reason:
        return reason
    errors = [b.text for b in pruefung.pruefe(k.daten, entry, k.heute()) if b.stufe == "fehler"]
    return f"Prüfung: {errors[0]}" if errors else None


def _chosen_ids(body) -> list[str]:
    ids = body.get("ids") if isinstance(body, dict) else None
    if not isinstance(ids, list) or not ids or not all(isinstance(i, str) for i in ids):
        raise ValueError(NONE_CHOSEN)
    if len(set(ids)) > apply.MAX_PER_RUN:
        raise ValueError(TOO_MANY)
    return list(dict.fromkeys(ids))


def start(k, parameter, body):
    """Checks a run and writes nothing: the state changes when the tab is really open."""
    register = k.register()
    chosen = [register.hole(i) for i in _chosen_ids(body)]
    refused = [{"id": b["id"], "firma": b.get("firma"), "grund": reason}
               for b, reason in ((b, _problem(k, b)) for b in chosen) if reason]
    twice = apply.duplicates(register.alle(), chosen)
    if refused or (twice and body.get("bestaetigt") is not True):
        return json_antwort({"abgelehnt": refused, "doppelt": twice, "bereit": []})
    ready = [{"id": b["id"], "firma": b.get("firma"), "stelle": b.get("stelle"), "link": apply.form_link(b)} for b in chosen]
    return json_antwort({"abgelehnt": [], "doppelt": twice, "bereit": ready})


def values(k, parameter, body):
    wanted = pflicht(parameter, "id")
    entry = k.register().hole(wanted)
    reason = apply.blocker(k.daten, entry)
    if reason:
        raise ValueError(reason)
    return json_antwort({"werte": apply.form_values(k.daten),
                         "dateien": apply.describe_uploads(apply.uploads(k.daten, wanted))})


def _part_number(parameter: dict) -> int:
    try:
        return int(parameter.get("teil", "0"))
    except ValueError as error:
        raise ValueError(apply.UNKNOWN_PART) from error


def file_part(k, parameter, body):
    wanted = pflicht(parameter, "id")
    entry = k.register().hole(wanted)
    reason = apply.blocker(k.daten, entry)
    if reason:
        raise ValueError(reason)
    upload = apply.uploads(k.daten, wanted).get(pflicht(parameter, "schluessel"))
    if upload is None:
        raise ValueError(apply.UNKNOWN_FILE)
    data, parts = apply.read_part(upload, _part_number(parameter))
    return json_antwort({"name": upload.name, "typ": apply.content_type(upload.name), "teile": parts,
                         "daten": base64.b64encode(data).decode("ascii")})


def state(k, parameter, body):
    wanted = _body_id(body)
    if body.get("stand") not in (OPENED, FILLED):
        raise ValueError(BAD_STATE)
    register = k.register()

    def write():
        entry = register.hole(wanted)
        if entry.get("versand"):
            return entry  # a late message from the tab changes nothing any more
        return register.speichere({**entry, "ausfuellen": body["stand"]})

    entry = k.mit_entwurf(register.pfad, f"Formular für {wanted}: {body['stand']}", write)
    return json_antwort({"stand": entry.get("ausfuellen")})


def sent(k, parameter, body):
    wanted = _body_id(body)
    with k.sperre:
        result = versand.erfasse_versand(k.daten, wanted, k.heute(), k.versionierung, zusatz={"ausfuellen": SENT})
    return json_antwort({"stand": SENT, "hinweise": result["hinweise"]})


GET = {"/api/bewerben/auswahl": choice, "/api/bewerben/daten": values, "/api/bewerben/datei": file_part}
POST = {"/api/bewerben/start": start, "/api/bewerben/stand": state, "/api/bewerben/abgeschickt": sent}
