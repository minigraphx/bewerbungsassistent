"""Region, Pensum, exclusions and title filter on Suche einstellen (#263, #286, G64): show them and change them.

A change goes into suchprofil.md with a draft before and after (`search_frame.py` says which line). Neither the
extension nor Claude reach the POST route: it is not listed in desktop/native_host.py or desktop/mcp_tools.py.
"""
import search_frame
import search_plan
from dateien import schreibe_atomar
from server import json_antwort

NO_PROFILE = "Zuerst Meine Angaben abschliessen."
SAVED = "Suche einstellen: {fields}"


def _answer(text: str) -> dict:
    return {**search_plan.frame(text), "art": search_frame.kind_of(text), "werte": search_frame.values(text),
            "alle_kantone": list(search_plan.CANTONS)}


def frame(k, parameter, body):
    """What the cards show and their fields hold; empty without a profile."""
    path = k.daten / search_plan.PROFILE
    return json_antwort(_answer(path.read_text(encoding="utf-8") if path.is_file() else ""))


def change(k, parameter, body):
    path = k.daten / search_plan.PROFILE
    if not path.is_file():
        raise ValueError(NO_PROFILE)
    search_frame.with_values(path.read_text(encoding="utf-8"), body)  # refuse before any draft is made

    def write() -> str:
        text = path.read_text(encoding="utf-8")
        changed = search_frame.with_values(text, body)
        if changed != text:
            schreibe_atomar(path, changed.encode("utf-8"))
        return changed
    fields = ", ".join(search_frame.FIELDS[key].label for key in body)
    return json_antwort(_answer(k.mit_entwurf(path, SAVED.format(fields=fields), write)))


GET = {"/api/suche/rahmen": frame}
POST = {"/api/suche/rahmen": change}
