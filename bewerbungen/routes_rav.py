"""Routes for entering applications in Job-Room (MIN-347): the choice in the overview and what the extension needs.

Only the person saves in Job-Room; `eingetragen` records it afterwards. Nothing here goes through the AI.
"""
import preferences
import rav
from server import json_antwort, pflicht

NONE_CHOSEN = "Bitte zuerst Bewerbungen ankreuzen."
TOO_MANY = f"Pro Durchgang gehen höchstens {rav.MAX_PER_RUN} Bewerbungen."


def _body_id(body) -> str:
    if not isinstance(body, dict) or not isinstance(body.get("id"), str):
        raise ValueError("Bewerbung mit id erwartet")
    return body["id"]


def _chosen_ids(body) -> list[str]:
    ids = body.get("ids") if isinstance(body, dict) else None
    if not isinstance(ids, list) or not ids or not all(isinstance(i, str) for i in ids):
        raise ValueError(NONE_CHOSEN)
    if len(set(ids)) > rav.MAX_PER_RUN:
        raise ValueError(TOO_MANY)
    return list(dict.fromkeys(ids))


def choice(k, parameter, body):
    if not rav.applies(k.daten):
        return json_antwort({"sichtbar": False, "bewerbungen": [], "hoechstens": rav.MAX_PER_RUN, "erinnerung": None})
    entries = k.register().alle()
    rows = [{"id": entry["id"], "grund": rav.blocker(entry)} for entry in entries]
    return json_antwort({"sichtbar": True, "bewerbungen": rows, "hoechstens": rav.MAX_PER_RUN,
                         "erinnerung": rav.reminder(entries, k.heute())})


def start(k, parameter, body):
    """Checks a run and writes nothing."""
    register = k.register()
    chosen = [register.hole(i) for i in _chosen_ids(body)]
    refused = [{"id": entry["id"], "firma": entry.get("firma"), "grund": rav.blocker(entry)} for entry in chosen if rav.blocker(entry)]
    ready = [{"id": entry["id"], "firma": entry.get("firma"), "stelle": entry.get("stelle"), "beworben_am": entry.get("beworben_am")}
             for entry in chosen if not rav.blocker(entry)]
    return json_antwort({"abgelehnt": refused, "bereit": ready, "textsatz": preferences.load(k.daten).text_set})


def values(k, parameter, body):
    entry = k.register().hole(pflicht(parameter, "id"))
    reason = rav.blocker(entry)
    if reason:
        raise ValueError(reason)
    return json_antwort({"werte": rav.form_values(entry)})


def entered(k, parameter, body):
    wanted = _body_id(body)
    register = k.register()

    def write():
        entry = register.hole(wanted)
        if entry.get("rav_eingetragen_am"):
            return entry  # the bar and the page may both report it: the first day counts
        if not entry.get("beworben_am"):
            raise ValueError(rav.NOT_APPLIED)
        return register.speichere({**entry, "rav_eingetragen_am": k.heute().isoformat()})

    saved = k.mit_entwurf(register.pfad, f"{wanted} im RAV eingetragen", write)
    return json_antwort({"rav_eingetragen_am": saved["rav_eingetragen_am"]})


def undo(k, parameter, body):
    wanted = _body_id(body)
    register = k.register()

    def write():
        entry = register.hole(wanted)
        return register.speichere({key: value for key, value in entry.items() if key != "rav_eingetragen_am"})

    k.mit_entwurf(register.pfad, f"{wanted}: Eintrag im RAV zurückgesetzt", write)
    return json_antwort({"rav_eingetragen_am": None})


GET = {"/api/rav/auswahl": choice, "/api/rav/angaben": values}
POST = {"/api/rav/start": start, "/api/rav/eingetragen": entered, "/api/rav/zuruecksetzen": undo}
