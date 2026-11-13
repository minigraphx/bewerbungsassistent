"""Routes for missing ad texts (G37, G38, #275).

The extension reaches the two POST routes through its host: once per start of the app it gets the jobs it may load,
and hands back texts or the reason a text did not load. Only jobs handed out in this start take a text, and a text that
is there stays. The pages read `text_fehlt` through `note_for_saved` and `note_for_hit`. Nothing here calls the AI.
"""
import threading

import missing_ads
import precheck
import unterlagen
from dateien import schreibe_atomar
from hits import MAX_TEXT, Hits, ad_with_details
from server import json_antwort

HANDED_OUT = "inserate_ausgegeben"  # in k.cache: lives as long as this start of the app
FAILURES = "inserate_fehler"
MAX_ITEMS = 100
MAX_ID = 200
MAX_REASON = 300
AD_FIELDS = ("stelle", "firma", "ort", "pensum", "lehrbeginn", "link", "art")
_LOCK = threading.Lock()


def _ad_path(k, entry_id: str):
    return unterlagen.bewerbungsordner(k.daten, entry_id) / "stelle.md"


def _ad_of(k):
    def read(entry_id: str) -> str:
        path = _ad_path(k, entry_id)
        return path.read_text(encoding="utf-8") if path.is_file() else ""
    return read


def _missing(k, store: Hits) -> list[dict]:
    return [*missing_ads.saved_without_ad(k.register().alle(), _ad_of(k), store), *missing_ads.hits_without_ad(store)]


def hand_out(k, parameter, body):
    """The jobs to load now; each one once per start, so a second page asking at the same time gets nothing."""
    with _LOCK:
        given = k.cache.get(HANDED_OUT, frozenset())
        fresh = [job for job in _missing(k, Hits(k.daten))
                 if missing_ads.loadable(job) and (job["art"], job["id"]) not in given]
        k.cache[HANDED_OUT] = given | {(job["art"], job["id"]) for job in fresh}
    return json_antwort({"laden": fresh})


def _item(raw) -> dict:
    if not isinstance(raw, dict) or raw.get("art") not in missing_ads.KINDS:
        raise ValueError("art muss treffer oder bewerbung sein")
    ident, text, reason = raw.get("id"), raw.get("text"), raw.get("fehler", "")
    if not isinstance(ident, str) or not ident or len(ident) > MAX_ID:
        raise ValueError("id erwartet")
    if not isinstance(text, str) or not isinstance(reason, str):
        raise ValueError("text und fehler müssen Text sein")
    return {"art": raw["art"], "id": ident, "text": text.strip()[:MAX_TEXT], "fehler": " ".join(reason.split())[:MAX_REASON]}


def _items(body) -> list[dict]:
    raw = body.get("texte") if isinstance(body, dict) else None
    if not isinstance(raw, list):
        raise ValueError("texte erwartet (Liste)")
    return [_item(entry) for entry in raw[:MAX_ITEMS]]


def _store_saved(k, entry_id: str, text: str) -> bool:
    try:
        entry = k.register().hole(entry_id)
    except KeyError:
        return False
    path = _ad_path(k, entry_id)
    if entry.get("status") not in missing_ads.OPEN_STAGES or missing_ads.has_ad(_ad_of(k)(entry_id)):
        return False
    ad = ad_with_details({field: entry.get(field) for field in AD_FIELDS}, text)
    path.parent.mkdir(parents=True, exist_ok=True)
    k.mit_entwurf(path, f"Stellentext {entry['firma']}", lambda: schreibe_atomar(path, ad.encode("utf-8")))
    return True


def _store(k, store: Hits, item: dict) -> bool:
    if item["art"] == missing_ads.TREFFER:
        person = precheck.for_folder(k.daten)  # the pre-check by fixed rules runs on every full text (G33)
        return store.fill_text(item["id"], item["text"], check=lambda title, text: precheck.check(title, text, person))
    return _store_saved(k, item["id"], item["text"])


def receive(k, parameter, body):
    """Texts and reasons from the extension; a job not handed out in this start is ignored."""
    items = _items(body)
    saved = 0
    with _LOCK:
        given = k.cache.get(HANDED_OUT, frozenset())
        failures = dict(k.cache.get(FAILURES, {}))
        store = Hits(k.daten)
        for item in items:
            key = (item["art"], item["id"])
            if key not in given:
                continue
            if item["text"] and _store(k, store, item):
                saved += 1
                failures = {known: reason for known, reason in failures.items() if known != key}
            elif not item["text"]:
                failures = {**failures, key: item["fehler"]}
        k.cache[FAILURES] = failures
    return json_antwort({"gespeichert": saved})


def _failure(k, kind: str, ident: str) -> str | None:
    return k.cache.get(FAILURES, {}).get((kind, ident))


def note_for_saved(k, entry: dict) -> dict | None:
    """Reason and way for a saved job without its ad text, None when it has one or needs none."""
    if entry.get("status") not in missing_ads.OPEN_STAGES:
        return None
    jobs = missing_ads.saved_without_ad([entry], _ad_of(k), Hits(k.daten))
    return missing_ads.note(jobs[0], _failure(k, missing_ads.BEWERBUNG, entry["id"])) if jobs else None


def note_for_hit(k, hit: dict) -> dict:
    job = {"art": missing_ads.TREFFER, "id": hit["id"], "portal": hit["portal"], "portal_id": hit["portal_id"], "link": hit["link"]}
    return missing_ads.note(job, _failure(k, missing_ads.TREFFER, hit["id"]))


GET: dict = {}
POST = {"/api/inserate/holen": hand_out, "/api/inserate/texte": receive}
