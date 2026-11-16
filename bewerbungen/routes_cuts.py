"""Routes of the cuts and the third page of one application (G92, #323), for the check and the step Lebenslauf.

Both store the choice with drafts before and after and build the documents anew, the dossier with its single files
when it is chosen; no letter is drafted. Neither the browser extension nor Claude reach these routes (allow lists in
desktop/native_host.py and desktop/mcp_tools.py).
"""
from collections.abc import Callable

import cut_choice
import cv_cuts
import unterlagen
from server import json_antwort, pflicht

PATH = "/api/kuerzungen"
BACK_PATH = "/api/kuerzungen/zurueckholen"
DESCRIPTION = "Kürzungen des Lebenslaufs für diese Bewerbung"


def _body(body) -> dict:
    if not isinstance(body, dict):
        raise ValueError("id erwartet")
    return body


def _store_and_build(k, entry_id: str, change: Callable[[dict], dict]):
    """Stores what `change` makes of the choice, with drafts and under the lock of mit_entwurf, then builds."""
    def store() -> dict:
        entry = k.register().hole(entry_id)
        cut_choice.write(k.daten, entry_id, change(entry))
        return entry

    entry = k.mit_entwurf(cv_cuts.path(k.daten, entry_id), DESCRIPTION, store)
    with k.sperre:
        try:
            unterlagen.baue(k.daten, entry, k.build)
            built, problem = True, None
        except ValueError as error:  # stored all the same; the message says what keeps the build back
            built, problem = False, str(error)
    return json_antwort({"neu_erstellt": built, "fehler": problem, "kuerzungen": cut_choice.state(k.daten, entry)})


def cut(k, parameter, body):
    """The ticked cuts (`weglassen`) or three pages (`drei_seiten`) for this application, then build anew."""
    body = _body(body)
    return _store_and_build(k, pflicht(body, "id"),
                            lambda entry: cut_choice.choose(k.daten, entry, body.get("weglassen"), body.get("drei_seiten")))


def take_back(k, parameter, body):
    """Brings one cut (`kuerzung`) back, or takes the third page back, then builds anew."""
    body = _body(body)
    return _store_and_build(k, pflicht(body, "id"),
                            lambda entry: cut_choice.take_back(k.daten, entry, body.get("kuerzung")))


POST = {PATH: cut, BACK_PATH: take_back}
