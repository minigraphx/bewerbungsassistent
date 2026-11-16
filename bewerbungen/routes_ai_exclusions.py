"""Exclusion reasons the AI proposes from dismissed hits, on Suche einstellen (#319, G86), only for job searches.

`GET /api/suche/ki-ausschluesse` names how many dismissed hits would go and what the call costs, in the currency and
with the credit of „Alle prüfen“ (G44, G46, G80), and calls no AI; below three dismissed hits it names only the count,
so the page shows its empty state. It also names what the profile excludes, so proposals already shown follow it. `…/text` shows the text with placeholders without sending it (G15). A proposal lives
only while the app runs (`k.cache`): the page refers to it by its id and number, so nothing the page sends becomes an
entry. Adopting writes through `routes_adopt_exclusion.add_entry`, with drafts before and after; Rückgängig takes out
exactly that entry again. Neither the extension nor Claude reach the routes: they are not listed in
desktop/native_host.py or desktop/mcp_tools.py.
"""
import secrets

import excluded_companies
import preferences
import profile_limits
import rating_exclusion
import routes_adopt_exclusion
import routes_ai
import routes_rate_all
import routes_terms
import search_frame
import search_plan
from ai import exclusion_reasons, tasks
from ai.connection import currency_now
from ai.errors import SETUP_ACTION, AiError, SetupNeeded
from hits import Hits
from server import ActionError, json_antwort

CACHE_KEY = "ki-ausschluesse"
KEPT_PROPOSALS = 5
ID_BYTES = 12
MINUTES = 1  # one call
SHOWN_FIELDS = ("id", "stelle", "firma", "ort", "pensum")  # what the page names of a hit a proposal rests on
ONLY_JOBS = "Ausschlüsse von der KI gibt es nur bei der Stellensuche."
TOO_FEW = "Die KI schlägt erst ab {count} verworfenen Stellen Ausschlüsse vor."
GONE = "Diesen Vorschlag gibt es nicht mehr. Bitte neu vorschlagen lassen."
FAILED = "Kein Vorschlag. {reason} {cost} Am Suchprofil hat sich nichts geändert."
ADOPTED = "Suche einstellen: «{value}» unter «{place}» ausgeschlossen, Vorschlag der KI"
UNDONE = "Suche einstellen: «{value}» unter «{place}» wieder entfernt"


def _job_profile(k) -> str | None:
    """The profile of a job search, or None: an apprenticeship has neither title filter nor these exclusions."""
    path = k.daten / search_plan.PROFILE
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    if search_frame.kind_of(text) != search_plan.KIND_JOB or preferences.strictest_kind(k.daten) == preferences.APPRENTICESHIP:
        return None
    return text


def _required_profile(k) -> str:
    text = _job_profile(k)
    if text is None:
        raise ValueError(ONLY_JOBS if (k.daten / search_plan.PROFILE).is_file() else search_plan.NO_PROFILE)
    return text


def _dismissed(k, text: str) -> list[dict]:
    """The dismissed hits the list shows; those of an excluded company are out of sight and stay here."""
    shown = excluded_companies.shown(Hits(k.daten).all(), excluded_companies.keys(k.daten))
    return exclusion_reasons.dismissed(shown, search_plan.title_terms(text, "ausschluss"))


def _frame(text: str) -> exclusion_reasons.Frame:
    chars = profile_limits.of(search_plan.KIND_JOB, search_frame.FIELDS[rating_exclusion.AD].form_id).chars
    return exclusion_reasons.Frame(positive=search_plan.title_terms(text, "positiv"),
                                   titles=search_plan.title_terms(text, "ausschluss"),
                                   ads=tuple(search_frame.values(text)[rating_exclusion.AD]), chars=chars)


def _preview(k, hits: list[dict]) -> str:
    """The text with placeholders, as it would go to the AI; nothing is sent, so no consent is needed to read it."""
    def task() -> str:
        material = tasks.load_material(k.daten, partial=True)
        gateway = tasks.make_gateway(k.daten, material, client=None)
        return gateway.preview(exclusion_reasons.request(exclusion_reasons.labelled(hits)))
    return routes_ai.run_ai(task)


def overview(k, parameter, body):
    text = _job_profile(k)
    if text is None:
        return json_antwort({"verfuegbar": False})
    hits = _dismissed(k, text)
    frame = _frame(text)
    # What the profile excludes now, so proposals still shown follow an entry another card added or removed.
    present = {rating_exclusion.TITLE: list(frame.titles), rating_exclusion.AD: list(frame.ads)}
    found = {"verfuegbar": True, "anzahl": len(hits), "mindestens": exclusion_reasons.MIN_DISMISSED,
             "vorhanden": present}
    if len(hits) < exclusion_reasons.MIN_DISMISSED:
        return json_antwort(found)
    money = routes_rate_all.priced(exclusion_reasons.estimate_usd(_preview(k, hits)), with_credit=True)
    return json_antwort({**found, **money.fields(), "dauer_minuten": MINUTES, "reicht_fuer": None})


def sent_text(k, parameter, body):
    return json_antwort({"text": _preview(k, _dismissed(k, _required_profile(k)))})


def _failed(error: AiError) -> ValueError:
    cost = getattr(error, "cost_usd", None)
    message = FAILED.format(reason=error, cost=routes_terms.charged(cost) if cost else routes_terms.NOT_CHARGED)
    return ActionError(message, SETUP_ACTION) if isinstance(error, SetupNeeded) else ValueError(message)


def _hit_view(hit: dict) -> dict:
    return {key: str(hit.get(key) or "") for key in SHOWN_FIELDS}


def _view(number: int, proposal: exclusion_reasons.Proposal, hits: dict[str, dict]) -> dict:
    return {"nummer": number, "art": proposal.kind, "ort": rating_exclusion.PLACES[proposal.kind],
            "kategorie": exclusion_reasons.CATEGORIES[proposal.category], "wert": proposal.value,
            "grund": proposal.reason, "treffer": [_hit_view(hits[i]) for i in proposal.ids]}


def _keep(k, proposal: dict) -> None:
    k.cache[CACHE_KEY] = (*k.cache.get(CACHE_KEY, ()), proposal)[-KEPT_PROPOSALS:]


def propose(k, parameter, body):
    """Asks the AI; the profile stays as it is."""
    text = _required_profile(k)
    hits = _dismissed(k, text)
    if len(hits) < exclusion_reasons.MIN_DISMISSED:
        raise ValueError(TOO_FEW.format(count=exclusion_reasons.MIN_DISMISSED))
    try:
        gateway, _ = routes_ai.ai_gateway(k, partial=True)
        result = exclusion_reasons.propose(gateway, exclusion_reasons.labelled(hits), _frame(text))
    except AiError as error:
        raise _failed(error) from error
    proposal = {"id": secrets.token_urlsafe(ID_BYTES), "proposals": result["proposals"]}
    _keep(k, proposal)
    by_id = {hit["id"]: hit for hit in hits}
    return json_antwort({"vorschlag": proposal["id"], "anzahl": len(hits),
                         "vorschlaege": [_view(i, p, by_id) for i, p in enumerate(result["proposals"])],
                         "kosten_usd": result["cost_usd"], "waehrung": currency_now()})


def _proposal(k, wanted: object, number: object) -> exclusion_reasons.Proposal:
    """A proposal of this run of the app, by id and number; anything else is refused."""
    found = next((p for p in k.cache.get(CACHE_KEY, ()) if isinstance(wanted, str) and p["id"] == wanted), None)
    if found is None or type(number) is not int or not 0 <= number < len(found["proposals"]):
        raise ValueError(GONE)
    return found["proposals"][number]


def adopt(k, parameter, body):
    body = body if isinstance(body, dict) else {}
    _required_profile(k)
    proposal = _proposal(k, body.get("vorschlag"), body.get("nummer"))
    return json_antwort(routes_adopt_exclusion.add_entry(k, proposal.kind, proposal.value, ADOPTED))


def undo(k, parameter, body):
    body = body if isinstance(body, dict) else {}
    _required_profile(k)
    return json_antwort(routes_adopt_exclusion.remove_entry(k, body.get("art"), body.get("wert"), UNDONE))


GET = {"/api/suche/ki-ausschluesse": overview, "/api/suche/ki-ausschluesse/text": sent_text}
POST = {"/api/suche/ki-ausschluesse/vorschlag": propose, "/api/suche/ki-ausschluesse/uebernehmen": adopt,
        "/api/suche/ki-ausschluesse/rueckgaengig": undo}
