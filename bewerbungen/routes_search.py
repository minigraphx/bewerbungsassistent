"""Routes of the job search in the browser (MIN-339).

The extension reaches them through the app's Native Messaging host: it fetches the search plan, lets the
app screen a result list (`sichten`), sends the full hits and finally a summary per portal. The page
„Suche“ lists the hits; rating goes through the AI gateway in packages (MIN-372), taking over writes register and stelle.md
with drafts (Entwürfe).
"""
import threading

import own_sites
import preferences
import routes_ai
import search_plan
import unterlagen
from ai import connection, second_look, tasks
from ai.errors import AnswerError
from dateien import schreibe_atomar
import routes_career
from hits import PORTALS_OFF, TRIAL, Hits, bounded_text, company_key, is_near
from server import json_antwort, pflicht

MAX_PROBLEM = 600
MAX_RATED_PER_RUN = 30  # one search must not use up the budget; the page says how many are left
_TAKE_OVER = threading.Lock()
BAD_RATING = "Die KI hat diesen Treffer nicht bewertet. Bitte nochmals versuchen."
BAD_OWN_RATING = "Die Bewertung braucht eine Note von 1 bis 6 und eine Zusammenfassung."
MIN_OWN_GRADE, MAX_OWN_GRADE = 1, 6
OWN_CLAUDE = "Claude (eigenes Abo)"
ALREADY_IN_REGISTER = "Dieser Treffer ist schon im Register."
NO_TEXT = "Für diesen Treffer fehlt der Text des Inserats. Bitte das Inserat öffnen und die Stelle von Hand erfassen."


def _hits(k) -> Hits:
    return Hits(k.daten)


def _list(body, field: str = "treffer") -> list:
    value = body.get(field) if isinstance(body, dict) else None
    if not isinstance(value, list):
        raise ValueError(f"{field} erwartet (Liste)")
    return value


def plan(k, parameter, body):
    store = _hits(k)
    current = search_plan.chosen(search_plan.for_folder(k.daten), store.settings()[PORTALS_OFF])
    # The form of address of the setup (MIN-369): the popup of the extension speaks like the app.
    return json_antwort({"plan": {**current.as_dict(), "anrede": preferences.load(k.daten).address, "zuschauen": store.settings()["zuschauen"],
                                  "eigener_schluessel": connection.has_own_key(), "weitere_seiten": own_sites.active(store)}})


def screen(k, parameter, body):
    current = search_plan.for_folder(k.daten)
    store = _hits(k)
    result = store.screen(_list(body), current.title_exclude, search_plan.MAX_AGE_DAYS, k.register().alle(),
                          own_sites.active_portals(store),
                          near=lambda place: is_near(str(place), current.places, current.postal_codes),
                          title_positive=current.title_positive)
    return json_antwort(result)


def receive(k, parameter, body):
    store = _hits(k)
    profile = k.daten / search_plan.PROFILE
    agencies = search_plan.agencies_in(profile.read_text(encoding="utf-8")) if profile.is_file() else ()
    return json_antwort(store.add(_list(body), k.register().alle(), k.heute(), own_sites.active_portals(store), agencies))


def _portal_summary(raw) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("Zusammenfassung pro Portal erwartet")
    counts = {name: raw.get(name) for name in ("treffer", "neu")}
    if any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in counts.values()):
        raise ValueError("treffer und neu müssen Zahlen sein")
    problem = raw.get("problem") or ""
    if not isinstance(problem, str):
        raise ValueError("problem muss Text sein")
    return {**counts, "problem": " ".join(problem.split())[:MAX_PROBLEM]}


def finish(k, parameter, body):
    portals = body.get("portale") if isinstance(body, dict) else None
    store = _hits(k)
    # The plan named its sites at the start: the list or the key may have changed since, the rest of the run still counts.
    known = {*search_plan.ALL_PORTALS, *(site["portal"] for site in own_sites.configured(store))}
    kept = {name: value for name, value in portals.items() if name in known} if isinstance(portals, dict) else {}
    if not isinstance(portals, dict) or (portals and not kept):
        raise ValueError("portale erwartet")
    run = store.save_run({"portale": {name: _portal_summary(v) for name, v in kept.items()}}, k.heute())
    return json_antwort(run)


def _page_kind(k) -> str:
    """The kind the page Suche is worded and offers portals for: the setup's choice, else what the profile says."""
    return preferences.load(k.daten).sought


def overview(k, parameter, body):
    store = _hits(k)
    kind = _page_kind(k)
    portals = search_plan.APPRENTICESHIP_PORTALS if kind == search_plan.KIND_APPRENTICESHIP else search_plan.PORTALS
    offers: tuple[str, ...] = ()
    targets: dict[str, str] = {}
    homes: tuple[str, ...] = ()
    postal_codes: tuple[str, ...] = ()
    off = store.settings()[PORTALS_OFF]
    choice = search_plan.portal_choice(search_plan.SearchPlan(keywords=(), kind=kind, portals=portals), off)
    try:
        if (k.daten / search_plan.PROFILE).is_file() and search_plan.kind_of_folder(k.daten) != kind:
            # an apprenticeship profile gets „## Lehrbeginn“ only with a start; until then the choice words the page
            raise ValueError(search_plan.NOTHING_OF_KIND[kind])
        profile = search_plan.for_folder(k.daten)
        current = search_plan.chosen(profile, off)
        choice = search_plan.portal_choice(profile, off)
        hints, portals, offers = list(current.hints), current.portals, current.offers
        targets, homes, postal_codes = dict(current.hint_targets), current.places, current.postal_codes
    except search_plan.ProfileGap as gap:
        hints, targets = [str(gap)], {str(gap): gap.field}
    except ValueError as error:
        hints = [str(error)]
    found = sorted(store.all(), key=lambda h: h.get("gefunden_am", ""), reverse=True)
    return json_antwort({"treffer": [{**hit, "ohne_text": not store.text(hit["id"]).strip(),
                                      "nah": is_near(str(hit.get("ort", "")), homes, postal_codes)} for hit in found],
                         "hinweis_ziele": targets,
                         "angebote": list(offers), **routes_career.searched_now(k),
                         "letzte_suche": store.last_run(), "hinweise": hints, "art": kind, "portale": list(portals), "portale_wahl": choice,
                         "einstellungen": store.settings(), "paket": tasks.PACKAGE_SIZE, "grenze": MAX_RATED_PER_RUN})


def text(k, parameter, body):
    store = _hits(k)
    wanted = pflicht(parameter, "id")
    store.get(wanted)
    return json_antwort({"text": store.text(wanted)})


def rating_fields(result: dict, share_usd: float | None, model: str | None) -> dict:
    fields = {"note": result["grade"], "zusammenfassung": result["summary"], "passt": result["fits"],
              "haken": result["hooks"], "neue_luecken": result["new_gaps"], "auffaellig": result["suspicious_lines"],
              "modell": model, "kosten_usd": share_usd}
    if result["uncertain"]:
        fields = {**fields, "unsicher": result["uncertain"]}
    return {**fields, "beruf_note": result["profession_grade"]} if "profession_grade" in result else fields


def _second_look_fields(look: second_look.Look, share_usd: float | None, model: str | None) -> dict:
    cost = None if share_usd is None and look.cost_usd is None else (share_usd or 0) + (look.cost_usd or 0)
    return {**rating_fields(look.rating, cost, model),
            "nachpruefung": {"im_paket": look.first_grade, "noten": list(look.grades)}}


def _rate_ads(k, store: Hits, ads: list[tuple[str, str]]) -> dict:
    """One AI call and its results stored, the cost shared among the hits that got a rating. Good grades are then
    looked at again; they are stored first, so an aborted second look loses nothing."""
    def package():
        gateway, material = routes_ai.ai_gateway(k)
        return gateway, material, tasks.rate_package(gateway, material, ads)

    gateway, material, result = routes_ai.run_ai(package)
    ratings, model = result["ratings"], result["model"]
    share = result["cost_usd"] / len(ratings) if ratings and result["cost_usd"] is not None else None
    stored = store.update_many({ad_id: {"bewertung": rating_fields(rating, share, model)} for ad_id, rating in ratings.items()})
    good = {ad_id: rating for ad_id, rating in ratings.items() if second_look.deserved(rating)}
    looks = second_look.look_again(gateway, material, ads, good)
    looked = store.update_many({ad_id: {"bewertung": _second_look_fields(look, share, model)} for ad_id, look in looks.items()})
    final = {hit["id"]: hit for hit in [*stored, *looked]}
    extra = sum(look.cost_usd or 0 for look in looks.values())
    cost = None if result["cost_usd"] is None and not extra else (result["cost_usd"] or 0) + extra
    return {"bewertet": list(final.values()), "offen": result["missing"], "kosten_usd": cost}


def rate(k, parameter, body):
    store = _hits(k)
    hit = store.get(pflicht(parameter, "id"))
    if not store.text(hit["id"]).strip():
        raise ValueError(NO_TEXT)
    result = _rate_ads(k, store, [(hit["id"], store.ad_text(hit["id"]))])
    if not result["bewertet"]:
        raise ValueError(BAD_RATING)
    return json_antwort(result["bewertet"][0])


def _strings(body: dict, name: str) -> list[str]:
    value = body.get(name, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(BAD_OWN_RATING)
    return [bounded_text(item, "Bewertung", limit=500) for item in value]


def own_rating(k, parameter, body):
    """The rating of Claude on the person's own subscription (MIN-377): stored as it came, no AI call and no cost here."""
    grade = body.get("note") if isinstance(body, dict) else None
    if type(grade) not in (int, float) or not MIN_OWN_GRADE <= grade <= MAX_OWN_GRADE or grade * 2 != int(grade * 2):  # the register takes half steps
        raise ValueError(BAD_OWN_RATING)
    fields = {"note": grade, "zusammenfassung": bounded_text(body.get("zusammenfassung"), "Bewertung", required=True, limit=2000),
              **{name: _strings(body, name) for name in ("passt", "haken", "neue_luecken", "auffaellig")},
              "modell": OWN_CLAUDE, "kosten_usd": None}
    uncertain = bounded_text(body.get("unsicher"), "Bewertung", limit=500)
    store = _hits(k)
    store.get(pflicht(parameter, "id"))
    return json_antwort(store.update(pflicht(parameter, "id"), bewertung={**fields, "unsicher": uncertain} if uncertain else fields))


def _package_ids(body) -> list[str]:
    ids = _list(body, "ids")
    if not 1 <= len(ids) <= tasks.PACKAGE_SIZE or not all(isinstance(i, str) for i in ids) or len(set(ids)) != len(ids):
        raise ValueError(f"ids: 1 bis {tasks.PACKAGE_SIZE} verschiedene Treffer erwartet")
    return ids


def rate_package(k, parameter, body):
    """Up to ten hits in one call. Hits without an answer stay unrated; an answer that cannot be used at all is no
    error for the others, the page tries those hits one by one. Connection, access and budget errors stop the run."""
    store = _hits(k)
    ids = _package_ids(body)
    for wanted in ids:
        store.get(wanted)
    without_text = [wanted for wanted in ids if not store.text(wanted).strip()]
    ads = [(wanted, store.ad_text(wanted)) for wanted in ids if wanted not in without_text]
    if not ads:
        return json_antwort({"bewertet": [], "offen": [], "ohne_text": without_text, "kosten_usd": None})
    try:
        result = _rate_ads(k, store, ads)
    except ValueError as error:
        cause = error.__cause__
        if not isinstance(cause, AnswerError):
            raise
        return json_antwort({"bewertet": [], "offen": [ad for ad, _ in ads], "ohne_text": without_text,
                             "kosten_usd": cause.cost_usd, "meldung": str(error)})
    return json_antwort({**result, "ohne_text": without_text})


def settings(k, parameter, body):
    if isinstance(body, dict) and PORTALS_OFF in body:
        wanted = search_plan.checked_choice(body[PORTALS_OFF], _page_kind(k))
        return json_antwort(_hits(k).set_portals_off(wanted))
    if isinstance(body, dict) and isinstance(body.get("zuschauen"), bool):
        return json_antwort(_hits(k).set_watching(body["zuschauen"]))
    if not isinstance(body, dict) or not isinstance(body.get("auto_bewerten"), bool):
        raise ValueError("auto_bewerten oder zuschauen erwartet (ja oder nein)")
    return json_antwort(_hits(k).set_auto_rating(body["auto_bewerten"]))


def stars(k, parameter, body):
    if not isinstance(body, dict):
        raise ValueError("beruf und sterne erwartet")
    return json_antwort(_hits(k).set_stars(body.get("beruf"), body.get("sterne")))


def note_for(hit: dict) -> str:
    rating = hit.get("bewertung") or {}
    parts = [rating.get("zusammenfassung", "")]
    if rating.get("haken"):
        parts.append("Haken: " + "; ".join(rating["haken"]))
    if rating.get("unsicher"):
        parts.append(f"Note unsicher: {rating['unsicher']}")
    if hit.get("lehrbeginn"):
        parts.append(f"Lehrbeginn: {hit['lehrbeginn']}")
    if hit.get("hinweis"):
        parts.append(hit["hinweis"])
    return " ".join(p for p in parts if p)


def take_over(k, parameter, body):
    """Register entry and stelle.md; the hit is marked right after the entry, so a retry never adds a second one."""
    store = _hits(k)
    with _TAKE_OVER:
        hit = store.get(pflicht(parameter, "id"))
        if hit.get("zustand") == "uebernommen":
            raise ValueError(ALREADY_IN_REGISTER)
        register = k.register()
        portals = ", ".join(dict.fromkeys([hit["portal"], *(o["portal"] for o in hit.get("weitere", []))]))
        fields = {"firma_schluessel": company_key(hit["firma"]), "ort": hit.get("ort"), "pensum": hit.get("pensum"),
                  "portal": portals, "link": hit["link"], "status": "Gemerkt", "notiz": note_for(hit),
                  "passung": (hit.get("bewertung") or {}).get("note")}
        trial = hit.get("art") == TRIAL
        if trial:
            fields = {**fields, "art": TRIAL}
        title = f"{TRIAL} {hit['stelle']}" if trial else hit["stelle"]
        entry = k.mit_entwurf(register.pfad, f"Treffer {hit['firma']} – {title} übernommen",
                              lambda: register.neu(firma=hit["firma"], stelle=title,
                                                   **{key: v for key, v in fields.items() if v not in (None, "")}))
        taken = store.update(hit["id"], zustand="uebernommen", bewerbung_id=entry["id"])
    ad = store.ad_text(hit["id"])
    path = unterlagen.bewerbungsordner(k.daten, entry["id"]) / "stelle.md"
    k.mit_entwurf(path, f"Stellentext {entry['firma']}", lambda: schreibe_atomar(path, ad.encode("utf-8")))
    return json_antwort(taken)


def choose_offers(k, parameter, body):
    """The wish from the page goes into the search profile: it stays the only place that says what is searched."""
    choice = body.get("wahl") if isinstance(body, dict) else None
    path = k.daten / search_plan.PROFILE
    if not path.is_file():
        raise ValueError("Es gibt noch kein Suchprofil. Zuerst den Einstieg abschliessen.")
    # Read under the lock of the draft: another change in between must not be overwritten.
    k.mit_entwurf(path, "Gesucht im Suchprofil geändert",
                  lambda: schreibe_atomar(path, search_plan.with_offers(path.read_text(encoding="utf-8"), choice).encode("utf-8")))
    return json_antwort({"angebote": list(search_plan.for_folder(k.daten).offers)})


def discard(k, parameter, body):
    restore = isinstance(body, dict) and body.get("zurueck") is True
    store, wanted = _hits(k), pflicht(parameter, "id")
    if store.get(wanted).get("zustand") == "uebernommen":  # it could be taken over a second time
        raise ValueError(ALREADY_IN_REGISTER)
    return json_antwort(store.update(wanted, zustand="neu" if restore else "verworfen"))


GET = {"/api/suche/plan": plan, "/api/suche/liste": overview, "/api/suche/text": text}
POST = {"/api/suche/sichten": screen, "/api/suche/treffer": receive, "/api/suche/abschluss": finish,
        "/api/suche/bewerten": rate, "/api/suche/bewerten-paket": rate_package, "/api/suche/bewertung": own_rating, "/api/suche/einstellungen": settings,
        "/api/suche/beruf-sterne": stars, "/api/suche/angebot": choose_offers, "/api/suche/uebernehmen": take_over, "/api/suche/verwerfen": discard}
