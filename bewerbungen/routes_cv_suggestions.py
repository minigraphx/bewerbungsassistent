"""Suggestions of the AI for „Lebenslauf erstellen“ (#293, G75); what goes to the AI and what holds: ai/cv_suggestions.py.

The form says with `ki` whether the AI can suggest (`ai_state`). Opening sends nothing (G95): `…/schaetzung` prices the
exact text that would go, as „Alle prüfen“ does, without an AI client. `POST …/vorschlag` asks the AI and writes nothing:
the page applies the suggestion, and only „Lebenslauf übernehmen“ saves, through routes_cv_creation, which checks
every station against `cv.yaml` again. A suggestion stays in `k.cache` for its application, the state of Meine Angaben,
the chosen stations and the ad, so opening the panel again does not pay twice. `…/text` shows the text with
placeholders without sending it (G15). Neither the extension nor Claude reach the routes: they are not listed in
desktop/native_host.py or desktop/mcp_tools.py.
"""
import hashlib

import cv_creation
import missing_ads
import routes_ai
import routes_rate_all
import routes_terms
import unterlagen
from ai import cv_suggestions, tasks
from ai.connection import currency_now
from ai.errors import SETUP_ACTION, AiError, SetupNeeded
from server import ActionError, json_antwort, pflicht

ROUTE = "/api/lebenslauf/erstellen"
CACHE_KEY = "lebenslauf-vorschlaege"
KEPT = 10
READY, NO_AD, OFF = "bereit", "ohne_inserat", "aus"
AD_MISSING = "Für Vorschläge der KI zuerst den Stellentext speichern."
FAILED = "Kein Vorschlag der KI. {reason} {cost} Die Auswahl bleibt, wie sie ist."
LEFT_OUT, MOVED_UP = "{names} weglassen", "{names} nach vorne"
SHORTER, REORDERED = "Kurzprofil gekürzt", "Kurzprofil umgestellt"


def _ad(k, entry_id: str) -> str:
    path = unterlagen.bewerbungsordner(k.daten, entry_id) / routes_ai.STELLE_FILE
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    return text.strip()[:tasks.MAX_AD_CHARS] if missing_ads.has_ad(text) else ""


def ai_state(k, entry: dict) -> str:
    """Whether the panel can offer the AI's suggestion; without it the panel works as before."""
    if not routes_ai.usable(k):
        return OFF
    return READY if _ad(k, entry["id"]) else NO_AD


def _open_entry(k, entry_id: str) -> dict:
    entry = k.register().hole(entry_id)
    if entry.get("versand"):
        raise ValueError(unterlagen.SENT_STAYS)
    return entry


def _stations(cv: dict, shown: dict) -> list[cv_suggestions.Station]:
    """The stations the form has chosen, in its order; a station left out by the person stays on the computer."""
    sections = cv_creation.sections(cv)
    return [cv_suggestions.Station(ref=(part["abschnitt"], row["index"]), title=row["titel"], place=row["zusatz"],
                                   time=row["zeit"], section_title=part["titel"],
                                   texts=tuple(cv_creation.station_texts(sections[part["abschnitt"]][row["index"]])))
            for part in shown["abschnitte"] for row in part["stationen"] if row["gewaehlt"]]


def _material(k, entry: dict, stand: object) -> tuple[str, list[cv_suggestions.Station], str]:
    shown = cv_creation.form(k.daten, entry)
    if stand is not None and stand != shown["stand"]:
        raise ValueError(cv_creation.CHANGED)
    ad = _ad(k, entry["id"])
    if not ad:
        raise ValueError(AD_MISSING)
    cv, _ = cv_creation.load_cv(k.daten)
    return ad, _stations(cv, shown), cv_creation.summary_of(cv)


def _names(refs: tuple, stations: dict) -> str:
    names = [f"«{', '.join(part for part in (stations[ref].title, stations[ref].place) if part)}»" for ref in refs]
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} und {names[-1]}"


def what(recommendation: cv_suggestions.Recommendation, stations: dict, summary: str) -> str:
    """Written by the app from the changes, so it names only stations of Meine Angaben."""
    parts = []
    if recommendation.leave_out:
        parts.append(LEFT_OUT.format(names=_names(recommendation.leave_out, stations)))
    if recommendation.move_up:
        parts.append(MOVED_UP.format(names=_names(recommendation.move_up, stations)))
    if recommendation.summary is not None:
        shorter = len(cv_suggestions.sentences(recommendation.summary)) < len(cv_suggestions.sentences(summary))
        parts.append(SHORTER if shorter else REORDERED)
    return ", ".join(parts)


def _view(number: int, recommendation: cv_suggestions.Recommendation, stations: dict, summary: str) -> dict:
    def refs(found: tuple) -> list[dict]:
        return [{"abschnitt": section, "index": index} for section, index in found]

    return {"nummer": number, "was": what(recommendation, stations, summary), "grund": recommendation.reason,
            "weglassen": refs(recommendation.leave_out), "voran": refs(recommendation.move_up),
            "kurzprofil": recommendation.summary}


def _key(entry_id: str, ad: str, stations: list, summary: str) -> str:
    seen = repr((entry_id, ad, [(s.ref, s.title, s.place, s.time, s.texts) for s in stations], summary))
    return hashlib.sha256(seen.encode("utf-8")).hexdigest()


def _failed(error: AiError) -> ValueError:
    cost = getattr(error, "cost_usd", None)
    message = FAILED.format(reason=error, cost=routes_terms.charged(cost) if cost else routes_terms.NOT_CHARGED)
    return ActionError(message, SETUP_ACTION) if isinstance(error, SetupNeeded) else ValueError(message)


def propose(k, parameter, body):
    """Asks the AI; nothing is written."""
    body = body if isinstance(body, dict) else {}
    entry = _open_entry(k, pflicht(body, "id"))
    ad, stations, summary = _material(k, entry, body.get("stand"))
    key = _key(entry["id"], ad, stations, summary)
    kept = dict(k.cache.get(CACHE_KEY, ()))
    if key in kept:
        return json_antwort({**kept[key], "kosten_usd": 0, "kosten_text": "", "wiederholt": True})
    try:
        gateway, _ = routes_ai.ai_gateway(k, entry, partial=True)
        result = cv_suggestions.propose(gateway, ad, stations, summary)
    except AiError as error:
        raise _failed(error) from error
    by_ref = {station.ref: station for station in stations}
    cost = result["cost_usd"]
    view = {"empfehlungen": [_view(n, r, by_ref, summary) for n, r in enumerate(result["recommendations"])],
            "kosten_usd": cost, "kosten_text": routes_terms.charged(cost) if cost else "",
            "waehrung": currency_now(), "wiederholt": False}
    k.cache[CACHE_KEY] = (*k.cache.get(CACHE_KEY, ()), (key, view))[-KEPT:]
    return json_antwort(view)


def _sent(k, entry: dict) -> str:
    """The text with placeholders exactly as a suggestion would send it now; built without an AI client."""
    ad, stations, summary = _material(k, entry, None)

    def task() -> str:
        material = tasks.load_material(k.daten, partial=True)
        gateway = tasks.make_gateway(k.daten, material, client=None, entry=entry)
        return cv_suggestions.preview(gateway, ad, stations, summary)

    return routes_ai.run_ai(task)


def sent_text(k, parameter, body):
    """The text with placeholders, as it would go to the AI; nothing is sent."""
    return json_antwort({"text": _sent(k, k.register().hole(pflicht(parameter, "id")))})


def estimate(k, parameter, body):
    """Cost and time before the click (G95), worded on the page like „Alle prüfen“; nothing is sent."""
    sent = _sent(k, _open_entry(k, pflicht(parameter, "id")))
    money = routes_rate_all.priced(cv_suggestions.estimate_usd(sent), with_credit=True)
    return json_antwort({"anzahl": 1, **money.fields(), "dauer_minuten": cv_suggestions.EXPECTED_MINUTES,
                         "reicht_fuer": None})


GET = {f"{ROUTE}/text": sent_text, f"{ROUTE}/schaetzung": estimate}
POST = {f"{ROUTE}/vorschlag": propose}
