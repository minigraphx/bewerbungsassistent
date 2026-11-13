"""Routes for checking the search terms (#210, G45), only for job searches and only for the page of the app.

The hint after a search and the evidence are counted by the app, without AI or cost. A proposal of the AI lives only
while the app runs (`k.cache`): the page refers to it by its id and to its changes by their place, so nothing the page
sends can become a change. Writing takes the chosen changes, after the drafts of `mit_entwurf`; Rückgängig brings the
former profile back only while nothing else changed it.
"""
import hashlib
import re
import secrets

import preferences
import routes_ai
import search_plan
import term_changes
import term_evidence
from ai import tasks, term_review
from ai.errors import SETUP_ACTION, AiError, SetupNeeded
from dateien import schreibe_atomar
from hits import HIDDEN_TERMS, Hits
from server import ActionError, json_antwort, pflicht

CACHE_KEY = "suchbegriffe-vorschlaege"
KEPT_PROPOSALS = 10
ID_BYTES = 12
SHA256 = re.compile(r"[0-9a-f]{64}")
ONLY_JOBS = "Suchbegriffe prüfen gibt es vorerst nur bei der Stellensuche."
GONE = "Dieser Vorschlag gilt nicht mehr. Bitte neu vorschlagen lassen."
STALE = "Vorschlag veraltet. Die Suchbegriffe haben sich seit dem Vorschlag geändert. Bitte neu vorschlagen lassen."
FEEDBACK_NEEDED = "Bitte schreiben, was anders sein soll."
FAILED = "Kein Vorschlag. {reason} {cost} Am Suchprofil hat sich nichts geändert."
CHARGED = "Berechnet: {cost:.2f} USD."
NOT_CHARGED = "Nichts berechnet."
NO_UNDO = ("Rückgängig geht nicht mehr: Das Suchprofil hat sich seither geändert. Der frühere Stand liegt unter "
           "Entwürfe und Versionen.")
ADOPTED = "Suchbegriffe nach Vorschlag der KI: {count} {word}"
UNDONE = "Vorschlag der KI rückgängig gemacht"


def _profile(k):
    path = k.daten / search_plan.PROFILE
    if not path.is_file():
        raise ValueError(search_plan.NO_PROFILE)
    text = path.read_text(encoding="utf-8")
    if search_plan.APPRENTICESHIP_MARK in text or preferences.strictest_kind(k.daten) == preferences.APPRENTICESHIP:
        raise ValueError(ONLY_JOBS)
    return path, text


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _preview(k, current: term_changes.Terms, hits: list[dict]) -> str:
    """The text with placeholders, as it would go to the AI; nothing is sent, so no consent is needed to read it."""
    material = tasks.load_material(k.daten, partial=True)
    gateway = tasks.make_gateway(k.daten, material, client=None)
    return gateway.preview(term_review.request(material, term_review.prompt(current, hits)))


def _estimate(text: str) -> float:
    return term_review.estimate_usd(text, tasks.MODELS[term_review.TASK])


def hint(k, parameter, body):
    """What the page shows after a search: the strongest case, unless the person hid it, and what a check costs."""
    try:
        _, text = _profile(k)
    except ValueError:
        return json_antwort({"verfuegbar": False, "hinweis": None})
    store = Hits(k.daten)
    hits, current = store.all(), term_changes.terms_of(text)
    strong = term_evidence.strongest(hits, current.positive)
    shown = strong if strong is not None and strong.term.casefold() not in store.settings()[HIDDEN_TERMS] else None
    return json_antwort({"verfuegbar": True, "hinweis": shown.as_dict() if shown else None,
                         "kosten_usd": _estimate(_preview(k, current, hits)),
                         "treffer": len(term_evidence.rated(hits)), "seit": term_evidence.since(hits)})


def hide(k, parameter, body):
    term = body.get("begriff") if isinstance(body, dict) else None
    Hits(k.daten).hide_term(term)
    return json_antwort({"ok": True})


def sent_text(k, parameter, body):
    _, text = _profile(k)
    preview = _preview(k, term_changes.terms_of(text), Hits(k.daten).all())
    return json_antwort({"text": preview, "kosten_usd": _estimate(preview)})


def evidence_ids(k, parameter, body):
    """The hits behind „Diese Treffer ansehen“: those that came in only through this term."""
    _, text = _profile(k)
    term = pflicht(parameter, "begriff")
    found = term_evidence.evidence(Hits(k.daten).all(), term_changes.terms_of(text).positive).get(term.casefold())
    return json_antwort({"begriff": found.term if found else term, "ids": list(found.ids) if found else []})


def _proposals(k) -> tuple[dict, ...]:
    return k.cache.get(CACHE_KEY, ())


def _proposal(k, wanted: object) -> dict:
    found = next((p for p in _proposals(k) if isinstance(wanted, str) and p["id"] == wanted), None)
    if found is None:
        raise ValueError(GONE)
    return found


def _keep(k, proposal: dict) -> None:
    k.cache[CACHE_KEY] = (*_proposals(k), proposal)[-KEPT_PROPOSALS:]


def _failed(error: AiError) -> ValueError:
    cost = getattr(error, "cost_usd", None)
    message = FAILED.format(reason=error, cost=CHARGED.format(cost=cost) if cost else NOT_CHARGED)
    return ActionError(message, SETUP_ACTION) if isinstance(error, SetupNeeded) else ValueError(message)


def _by_effect(changes: tuple, found: dict) -> tuple:
    """The change with the most evidence first; the rest in the order of the AI."""
    def weight(change) -> int:
        return max((len(found[t.casefold()].ids) for t in change.remove if t.casefold() in found), default=0) \
            if change.area == term_changes.POSITIVE else 0
    return tuple(sorted(changes, key=weight, reverse=True))


def _change_view(index: int, change: term_changes.Change, found: dict) -> dict:
    evidence = next((found[t.casefold()] for t in change.remove
                     if change.area == term_changes.POSITIVE and t.casefold() in found), None)
    return {"nummer": index, "bereich": change.area, "bereich_name": term_changes.AREA_NAMES[change.area],
            "satz": term_changes.sentence(change), "entfaellt": list(change.remove), "neu": list(change.add),
            "grund": change.reason, "beleg": evidence.as_dict() if evidence else None,
            "zu_allgemein": bool(evidence and evidence.too_general)}


def _outcome(text: str, changes: tuple) -> dict:
    current = term_changes.terms_of(text)
    after = term_changes.outcome(current, changes)
    gone = [term for change in changes for term in change.remove]
    return {"endstand": after.as_dict(), "entfaellt": gone,
            "grenzen": term_changes.limits(current, after, term_changes.places_factor(text))}


def propose(k, parameter, body):
    """A proposal, or with `vorher` and `hinweis` a revised one; the profile stays as it is."""
    body = body if isinstance(body, dict) else {}
    path, text = _profile(k)
    former = _proposal(k, body["vorher"]) if body.get("vorher") is not None else None
    feedback = term_review.clean_feedback(body.get("hinweis"))
    if former is not None and not feedback:
        raise ValueError(FEEDBACK_NEEDED)
    hits, current = Hits(k.daten).all(), term_changes.terms_of(text)
    try:
        gateway, material = routes_ai.ai_gateway(k, partial=True)
        prompt = term_review.prompt(current, hits, feedback, former["changes"] if former else None)
        result = term_review.review(gateway, material, current, term_changes.avoided_words(text), prompt)
    except AiError as error:
        raise _failed(error) from error
    found = term_evidence.evidence(hits, current.positive)
    changes = _by_effect(result["changes"], found)
    spent = (former["spent"] if former else 0) + (result["cost_usd"] or 0)
    proposal = {"id": secrets.token_urlsafe(ID_BYTES), "stand": current.digest, "changes": changes,
                "round": former["round"] + 1 if former else 1, "spent": spent}
    _keep(k, proposal)
    return json_antwort({
        "vorschlag": proposal["id"], "runde": proposal["round"], "zusammenfassung": result["summary"],
        "geaendert": result["changed"] if former else "", "hinweis": feedback,
        "aenderungen": [_change_view(i, change, found) for i, change in enumerate(changes)],
        "kosten_usd": result["cost_usd"], "kosten_bisher": round(spent, 6), "modell": result["model"],
        "datum": k.heute().isoformat(), "treffer": len(term_evidence.rated(hits)), "seit": term_evidence.since(hits),
        "jetzt": current.as_dict(), **_outcome(text, changes)})


def outcome(k, parameter, body):
    """What the search looks for after the ticked changes, and whether the limits allow it."""
    body = body if isinstance(body, dict) else {}
    _, text = _profile(k)
    proposal = _proposal(k, body.get("vorschlag"))
    if term_changes.terms_of(text).digest != proposal["stand"]:
        return json_antwort({"veraltet": True, "meldung": STALE})
    if body.get("gewaehlt") == []:
        unchanged = _outcome(text, ())
        return json_antwort({**unchanged, "grenzen": {**unchanged["grenzen"], "gesperrt": term_changes.NOTHING_CHOSEN}})
    return json_antwort(_outcome(text, term_changes.chosen(proposal["changes"], body.get("gewaehlt"))))


def _write(k, path, description: str, change) -> str:
    """The text before; `change` runs under the lock with the current text, so a click elsewhere is not lost."""
    def write() -> str:
        text = path.read_text(encoding="utf-8")
        changed = change(text)
        if changed != text:
            schreibe_atomar(path, changed.encode("utf-8"))
        return text
    return k.mit_entwurf(path, description, write)


def adopt(k, parameter, body):
    body = body if isinstance(body, dict) else {}
    path, _ = _profile(k)
    proposal = _proposal(k, body.get("vorschlag"))
    picked = term_changes.chosen(proposal["changes"], body.get("gewaehlt"))

    def change(text: str) -> str:
        current = term_changes.terms_of(text)
        if current.digest != proposal["stand"]:
            raise ValueError(STALE)
        blocked = term_changes.limits(current, term_changes.outcome(current, picked),
                                      term_changes.places_factor(text))["gesperrt"]
        if blocked:
            raise ValueError(blocked)
        return term_changes.applied(text, picked)

    word = "Änderung" if len(picked) == 1 else "Änderungen"
    before = _write(k, path, ADOPTED.format(count=len(picked), word=word), change)
    after = path.read_text(encoding="utf-8")
    return json_antwort({"anzahl": len(picked), "vorher": _digest(before), "nachher": _digest(after),
                         "jetzt": term_changes.terms_of(after).as_dict()})


def undo(k, parameter, body):
    body = body if isinstance(body, dict) else {}
    path, _ = _profile(k)
    before, after = body.get("vorher"), body.get("nachher")
    if not all(isinstance(value, str) and SHA256.fullmatch(value) for value in (before, after)):
        raise ValueError(NO_UNDO)
    found = next((draft for draft in k.ablage.liste(path) if draft.hash == before), None)

    def change(text: str) -> str:
        if found is None or _digest(text) != after:
            raise ValueError(NO_UNDO)
        return k.ablage.inhalt(found.id).decode("utf-8")

    _write(k, path, UNDONE, change)
    return json_antwort({"jetzt": term_changes.terms_of(path.read_text(encoding="utf-8")).as_dict()})


GET = {"/api/suchbegriffe/hinweis": hint, "/api/suchbegriffe/text": sent_text, "/api/suchbegriffe/beleg": evidence_ids}
POST = {"/api/suchbegriffe/ausblenden": hide, "/api/suchbegriffe/vorschlag": propose,
        "/api/suchbegriffe/endstand": outcome, "/api/suchbegriffe/uebernehmen": adopt,
        "/api/suchbegriffe/rueckgaengig": undo}
