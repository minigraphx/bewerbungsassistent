"""Routes of the job search in the browser (MIN-339).

The extension reaches them through the app's Native Messaging host: it fetches the search plan, lets the
app screen a result list (`sichten`), sends the full hits and finally a summary per portal. The page
„Treffer“ lists the hits; rating goes through the AI gateway, taking over writes register and stelle.md
with drafts (Entwürfe).
"""
import threading

import routes_ai
import search_plan
import unterlagen
from ai import tasks
from dateien import schreibe_atomar
from hits import Hits, company_key
from server import json_antwort, pflicht

MAX_PROBLEM = 600
_TAKE_OVER = threading.Lock()
NO_TEXT = "Für diesen Treffer fehlt der Text des Inserats. Bitte das Inserat öffnen und die Stelle von Hand erfassen."


def _hits(k) -> Hits:
    return Hits(k.daten)


def _list(body, field: str = "treffer") -> list:
    value = body.get(field) if isinstance(body, dict) else None
    if not isinstance(value, list):
        raise ValueError(f"{field} erwartet (Liste)")
    return value


def plan(k, parameter, body):
    return json_antwort({"plan": search_plan.for_folder(k.daten).as_dict()})


def screen(k, parameter, body):
    current = search_plan.for_folder(k.daten)
    result = _hits(k).screen(_list(body), current.title_exclude, search_plan.MAX_AGE_DAYS, k.register().alle())
    return json_antwort(result)


def receive(k, parameter, body):
    return json_antwort(_hits(k).add(_list(body), k.register().alle(), k.heute()))


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
    if not isinstance(portals, dict) or not set(portals) <= set(search_plan.ALL_PORTALS):
        raise ValueError("portale erwartet")
    run = _hits(k).save_run({"portale": {name: _portal_summary(v) for name, v in portals.items()}}, k.heute())
    return json_antwort(run)


def overview(k, parameter, body):
    store = _hits(k)
    kind = search_plan.kind_of_folder(k.daten)
    portals = search_plan.APPRENTICESHIP_PORTALS if kind == search_plan.KIND_APPRENTICESHIP else search_plan.PORTALS
    try:
        current = search_plan.for_folder(k.daten)
        hints, portals = list(current.hints), current.portals
    except ValueError as error:
        hints = [str(error)]
    return json_antwort({"treffer": sorted(store.all(), key=lambda h: h.get("gefunden_am", ""), reverse=True),
                         "letzte_suche": store.last_run(), "hinweise": hints, "art": kind, "portale": list(portals)})


def text(k, parameter, body):
    store = _hits(k)
    wanted = pflicht(parameter, "id")
    store.get(wanted)
    return json_antwort({"text": store.text(wanted)})


def rate(k, parameter, body):
    store = _hits(k)
    hit = store.get(pflicht(parameter, "id"))
    if not store.text(hit["id"]).strip():
        raise ValueError(NO_TEXT)
    ad = store.ad_text(hit["id"])

    def task():
        gateway, material = routes_ai.ai_gateway(k)
        return tasks.rate_match(gateway, material, ad)

    result = routes_ai.run_ai(task)
    rating = {"note": result["grade"], "zusammenfassung": result.get("summary", ""),
              "passt": result.get("fits", []), "haken": result.get("hooks", []),
              "neue_luecken": result.get("new_gaps", []), "auffaellig": result.get("suspicious_lines", []),
              "modell": result.get("model"), "kosten_usd": result.get("cost_usd")}
    return json_antwort(store.update(hit["id"], bewertung=rating))


def _note(hit: dict) -> str:
    rating = hit.get("bewertung") or {}
    parts = [rating.get("zusammenfassung", "")]
    if rating.get("haken"):
        parts.append("Haken: " + "; ".join(rating["haken"]))
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
            raise ValueError("Dieser Treffer ist schon im Register.")
        register = k.register()
        portals = ", ".join(dict.fromkeys([hit["portal"], *(o["portal"] for o in hit.get("weitere", []))]))
        fields = {"firma_schluessel": company_key(hit["firma"]), "ort": hit.get("ort"), "pensum": hit.get("pensum"),
                  "portal": portals, "link": hit["link"], "status": "Gemerkt", "notiz": _note(hit),
                  "passung": (hit.get("bewertung") or {}).get("note")}
        entry = k.mit_entwurf(register.pfad, f"Treffer {hit['firma']} – {hit['stelle']} übernommen",
                              lambda: register.neu(firma=hit["firma"], stelle=hit["stelle"],
                                                   **{key: v for key, v in fields.items() if v not in (None, "")}))
        taken = store.update(hit["id"], zustand="uebernommen", bewerbung_id=entry["id"])
    ad = store.ad_text(hit["id"])
    path = unterlagen.bewerbungsordner(k.daten, entry["id"]) / "stelle.md"
    k.mit_entwurf(path, f"Stellentext {entry['firma']}", lambda: schreibe_atomar(path, ad.encode("utf-8")))
    return json_antwort(taken)


def discard(k, parameter, body):
    restore = isinstance(body, dict) and body.get("zurueck") is True
    return json_antwort(_hits(k).update(pflicht(parameter, "id"), zustand="neu" if restore else "verworfen"))


GET = {"/api/suche/plan": plan, "/api/suche/liste": overview, "/api/suche/text": text}
POST = {"/api/suche/sichten": screen, "/api/suche/treffer": receive, "/api/suche/abschluss": finish,
        "/api/suche/bewerten": rate, "/api/suche/uebernehmen": take_over, "/api/suche/verwerfen": discard}
