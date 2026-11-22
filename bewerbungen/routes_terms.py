"""Routes for checking the search terms (#210, G45), only for job searches and only for the page of the app.

The hint after a search and the evidence are counted by the app, without AI or cost. A proposal of the AI lives only
while the app runs (`k.cache`): the page refers to it by its id and names the terms that are switched on (#371), of
which the app takes only current and proposed ones, so nothing else the page sends can become a change. Writing takes
exactly those, after the drafts of `mit_entwurf`; Rückgängig brings the former profile back only while nothing else
changed it.
"""
import hashlib
import re
import secrets

import excluded_companies
import preferences
import routes_ai
import routes_rate_all
import search_plan
import term_changes
import term_evidence
import term_moves
from ai import tasks, term_review
from ai.connection import currency_now
from ai.errors import SETUP_ACTION, AiError, SetupNeeded
from amount_text import money_text
from dateien import schreibe_atomar
from hits import HIDDEN_TERMS, Hits
from query_log import QueryLog
from server import ActionError, json_antwort, pflicht

CACHE_KEY = "suchbegriffe-vorschlaege"
KEPT_PROPOSALS = 10
ID_BYTES = 12
SHA256 = re.compile(r"[0-9a-f]{64}")
MINUTES = 1  # one call, mostly under 30 seconds
ONLY_JOBS = "Suchbegriffe prüfen gibt es vorerst nur bei der Stellensuche."
GONE = "Dieser Vorschlag gilt nicht mehr. Bitte neu vorschlagen lassen."
STALE = "Vorschlag veraltet. Die Suchbegriffe haben sich seit dem Vorschlag geändert. Bitte neu vorschlagen lassen."
FEEDBACK_NEEDED = "Bitte schreiben, was anders sein soll."
FAILED = "Kein Vorschlag. {reason} {cost} Am Suchprofil hat sich nichts geändert."
CHARGED = "Berechnet: {cost}."
NOT_CHARGED = "Nichts berechnet."
UNDER_A_CENT = "weniger als {cent}"
CENT = 0.01
NO_UNDO = ("Rückgängig geht nicht mehr: Das Suchprofil hat sich seither geändert. Der frühere Stand liegt unter "
           "Entwürfe und Versionen.")
ADOPTED = "Suchbegriffe nach Vorschlag der KI: {added} neu, {gone} entfallen"
MOVED = ", {moved} verschoben"
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


def _run_evidence(k, text: str, current: term_changes.Terms) -> term_review.RunEvidence:
    """What the last runs brought per keyword (G108), counted over the hits the list shows, as on Suche einstellen."""
    runs = QueryLog(k.daten).runs()
    shown = excluded_companies.shown(Hits(k.daten).all(), excluded_companies.keys(k.daten))
    return term_review.RunEvidence(term_evidence.keyword_counts(runs, shown, current.keywords),
                                   tuple(term_evidence.screened_titles(runs)), term_moves.placement_of(text))


def _prompt(k, text: str, hits: list[dict], feedback: str = "", former: dict | None = None) -> tuple[str, term_review.RunEvidence]:
    current = term_changes.terms_of(text)
    runs = _run_evidence(k, text, current)
    return term_review.prompt(current, hits, feedback, former["changes"] if former else None, runs), runs


def _preview(k, text: str, hits: list[dict]) -> str:
    """The text with placeholders, as it would go to the AI; nothing is sent, so no consent is needed to read it."""
    material = tasks.load_material(k.daten, partial=True)
    gateway = tasks.make_gateway(k.daten, material, client=None)
    return gateway.preview(term_review.request(material, _prompt(k, text, hits)[0]))


def _estimate(text: str) -> float:
    return term_review.estimate_usd(text, tasks.MODELS[term_review.TASK])


def hint(k, parameter, body):
    """What the page shows after a search: the strongest case, unless the person hid it.

    No amount: the pages ask `estimate`, which prices in the currency of the way (#334).
    """
    try:
        _, text = _profile(k)
    except ValueError:
        return json_antwort({"verfuegbar": False, "hinweis": None})
    store = Hits(k.daten)
    hits, current = store.all(), term_changes.terms_of(text)
    strong = term_evidence.strongest(hits, current.positive)
    shown = strong if strong is not None and strong.term.casefold() not in store.settings()[HIDDEN_TERMS] else None
    return json_antwort({"verfuegbar": True, "hinweis": shown.as_dict() if shown else None,
                         "treffer": len(term_evidence.rated(hits)), "seit": term_evidence.since(hits)})


def estimate(k, parameter, body):
    """Cost and time of a check before the click, priced like „Alle prüfen“ (#329, G44, G46, G80); nothing is sent.

    `anzahl` is the one request that goes, whatever the number of hits in it, as with the CV suggestions.
    """
    try:
        _, text = _profile(k)
    except ValueError:
        return json_antwort({"verfuegbar": False})
    hits = Hits(k.daten).all()
    sent = routes_ai.run_ai(lambda: _preview(k, text, hits))
    money = routes_rate_all.priced(_estimate(sent), with_credit=True)
    return json_antwort({"verfuegbar": True, "anzahl": 1, **money.fields(), "dauer_minuten": MINUTES,
                         "reicht_fuer": None})


def hide(k, parameter, body):
    term = body.get("begriff") if isinstance(body, dict) else None
    Hits(k.daten).hide_term(term)
    return json_antwort({"ok": True})


def sent_text(k, parameter, body):
    _, text = _profile(k)
    preview = _preview(k, text, Hits(k.daten).all())
    return json_antwort({"text": preview, "kosten_usd": _estimate(preview), "waehrung": currency_now()})


def counts(k, parameter, body):
    """«Was die App gezählt hat» (G108): per keyword what the last runs brought and its mark, without AI or cost, so
    the page shows it at once while the AI works."""
    try:
        _, text = _profile(k)
    except ValueError:
        return json_antwort({"verfuegbar": False})
    counted = _run_evidence(k, text, term_changes.terms_of(text)).counted
    return json_antwort({"verfuegbar": True, **counted.as_dict()})


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


def charged(cost: float) -> str:
    """A call under half a cent still cost something, so it never reads as CHF 0.00 (#339)."""
    currency = currency_now()
    if round(cost, 2) < CENT:
        return CHARGED.format(cost=UNDER_A_CENT.format(cent=money_text(CENT, currency)))
    return CHARGED.format(cost=money_text(cost, currency))


def _failed(error: AiError) -> ValueError:
    cost = getattr(error, "cost_usd", None)
    message = FAILED.format(reason=error, cost=charged(cost) if cost else NOT_CHARGED)
    return ActionError(message, SETUP_ACTION) if isinstance(error, SetupNeeded) else ValueError(message)


def _by_effect(changes: tuple, found: dict) -> tuple:
    """The change with the most evidence first; the rest in the order of the AI."""
    def weight(change) -> int:
        return max((len(found[t.casefold()].ids) for t in change.remove if t.casefold() in found), default=0) \
            if change.area == term_changes.POSITIVE else 0
    return tuple(sorted(changes, key=weight, reverse=True))


def _mark(change: term_changes.Change, counted: term_evidence.Counted) -> str | None:
    """The mark of the keyword a change concerns (G108), for the chip on its area line."""
    if change.area != term_changes.KEYWORDS:
        return None
    return next(filter(None, (counted.mark_of(term) for term in (change.moved, *change.remove) if term)), None)


def _change_view(index: int, change: term_changes.Change, found: dict, counted: term_evidence.Counted) -> dict:
    evidence = next((found[t.casefold()] for t in change.remove
                     if change.area == term_changes.POSITIVE and t.casefold() in found), None)
    return {"nummer": index, "bereich": change.area, "bereich_name": term_changes.AREA_NAMES[change.area],
            "satz": term_changes.sentence(change), "entfaellt": list(change.remove), "neu": list(change.add),
            "grund": change.reason, "beleg": evidence.as_dict() if evidence else None,
            "zu_allgemein": bool(evidence and evidence.too_general), "art": change.kind,
            "verschoben": change.moved or None, "in": change.into or None, "marke": _mark(change, counted),
            "verschoben_wort": term_moves.word(change.kind, change.portals) if change.is_move else None}


def _outcome(text: str, changes: tuple) -> dict:
    """The result of these changes, with the niches and «Nur» lines it leaves (G108), and its limits."""
    current = term_changes.terms_of(text)
    after = term_changes.outcome(current, changes)
    gone = [term for change in changes for term in change.remove]
    moves = term_changes.moves_of(changes)
    before = term_moves.placement_of(text)
    now = term_moves.after(before, moves, tuple(gone))
    return {"endstand": after.as_dict(), "entfaellt": gone,
            "nischen": term_moves.niche_view(before, now), "nur_zeilen": term_moves.limit_view(before, now),
            "grenzen": term_changes.limits(current, after, term_changes.places_factor(text), len(moves))}


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
        prompt, runs = _prompt(k, text, hits, feedback, former)
        result = term_review.review(gateway, material, current, term_changes.avoided_words(text), prompt, runs=runs)
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
        "aenderungen": [_change_view(i, change, found, runs.counted) for i, change in enumerate(changes)],
        "verschoben": [change.moved for change in changes if change.is_move],
        "kosten_usd": result["cost_usd"], "kosten_bisher": round(spent, 6), "waehrung": currency_now(),
        "modell": result["model"],
        "datum": k.heute().isoformat(), "treffer": len(term_evidence.rated(hits)), "seit": term_evidence.since(hits),
        "jetzt": current.as_dict(), "bisherige": term_changes.untouched(current, changes).as_dict(),
        **_outcome(text, changes)})


def outcome(k, parameter, body):
    """What the search looks for with the terms switched on, worked out by the app, and whether the limits allow it."""
    body = body if isinstance(body, dict) else {}
    _, text = _profile(k)
    proposal = _proposal(k, body.get("vorschlag"))
    current = term_changes.terms_of(text)
    if current.digest != proposal["stand"]:
        return json_antwort({"veraltet": True, "meldung": STALE})
    return json_antwort(_outcome(text, term_changes.selected(current, proposal["changes"], body.get("danach"))))


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
    path, text = _profile(k)
    proposal = _proposal(k, body.get("vorschlag"))
    if term_changes.terms_of(text).digest != proposal["stand"]:
        raise ValueError(STALE)
    picked = term_changes.selected(term_changes.terms_of(text), proposal["changes"], body.get("danach"))

    def change(text: str) -> str:
        current = term_changes.terms_of(text)
        if current.digest != proposal["stand"]:
            raise ValueError(STALE)
        blocked = term_changes.limits(current, term_changes.outcome(current, picked), term_changes.places_factor(text),
                                      len(term_changes.moves_of(picked)))["gesperrt"]
        if blocked:
            raise ValueError(blocked)
        return term_changes.applied(text, picked)

    added = sum(len(area.add) for area in picked)
    gone = sum(len(area.remove) for area in picked)
    moved = len(term_changes.moves_of(picked))
    before = _write(k, path, ADOPTED.format(added=added, gone=gone) + (MOVED.format(moved=moved) if moved else ""), change)
    after = path.read_text(encoding="utf-8")
    return json_antwort({"neu": added, "entfallen": gone, "verschoben": moved, "vorher": _digest(before),
                         "nachher": _digest(after), "jetzt": term_changes.terms_of(after).as_dict()})


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


GET = {"/api/suchbegriffe/hinweis": hint, "/api/suchbegriffe/schaetzung": estimate,
       "/api/suchbegriffe/text": sent_text, "/api/suchbegriffe/beleg": evidence_ids,
       "/api/suchbegriffe/gezaehlt": counts}
POST = {"/api/suchbegriffe/ausblenden": hide, "/api/suchbegriffe/vorschlag": propose,
        "/api/suchbegriffe/endstand": outcome, "/api/suchbegriffe/uebernehmen": adopt,
        "/api/suchbegriffe/rueckgaengig": undo}
