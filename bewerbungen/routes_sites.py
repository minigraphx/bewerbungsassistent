"""Routes for further sites of the search (MIN-348): the list for the page, and reading one page for the extension.

Only with an own API key; the extension reaches just the reading (list in `desktop/native_host.py`).
"""
import hits
import own_sites
from ai import connection, site_list
from routes_ai import ai_gateway, run_ai
from server import json_antwort

NEEDS_KEY = "Weitere Seiten gehen nur mit einem eigenen API-Schlüssel."
UNKNOWN_SITE = "Diese Seite steht nicht in der Liste der weiteren Seiten."
MAX_INCOMING_LINKS = 5000
MAX_LINK_LENGTH = 1000  # longer ones would be cut when stored and lead elsewhere


def _state(store: hits.Hits) -> dict:
    return {"seiten": own_sites.configured(store), "max_seiten": own_sites.MAX_SITES, "eigener_schluessel": connection.own_key() is not None}


def listing(k, parameter, body):
    return json_antwort(_state(hits.Hits(k.daten)))


def save(k, parameter, body):
    if connection.own_key() is None:
        raise ValueError(NEEDS_KEY)
    store = hits.Hits(k.daten)
    own_sites.save(store, body.get("seiten") if isinstance(body, dict) else None)
    return json_antwort(_state(store))


def _links_on_site(raw, portal: str) -> list[dict]:
    """Bounded and on this site: the rest of a page (ads, share buttons) never reaches the AI."""
    if not isinstance(raw, list):
        raise ValueError("links erwartet (Liste)")
    found = []
    for link in raw[:MAX_INCOMING_LINKS]:
        if not isinstance(link, dict) or not isinstance(link.get("text"), str) or not link["text"].strip():
            continue
        if len(str(link.get("href"))) > MAX_LINK_LENGTH:
            continue
        try:
            found = [*found, {"text": " ".join(link["text"].split()), "href": hits.checked_link(link.get("href"), portal)}]
        except ValueError:
            continue
    return found


def read_page(k, parameter, body):
    """The hits on an open page, as the extension then sends them to `sichten`."""
    if not isinstance(body, dict) or not isinstance(body.get("text"), str):
        raise ValueError("text erwartet")
    if connection.own_key() is None:
        raise ValueError(NEEDS_KEY)
    portal = body.get("portal")
    if portal not in own_sites.active_portals(hits.Hits(k.daten)):
        raise ValueError(UNKNOWN_SITE)
    links = _links_on_site(body.get("links"), portal)
    if not links or not body["text"].strip():
        return json_antwort({"treffer": []})

    def task():
        gateway, _ = ai_gateway(k)
        return site_list.read_list(gateway, str(body.get("titel") or "")[:hits.MAX_FIELD], body["text"], links)

    found = run_ai(task)
    treffer = [{"portal": portal, "portal_id": own_sites.link_id(job["link"]), **job} for job in found["jobs"]]
    return json_antwort({"treffer": treffer, "kosten_usd": found["cost_usd"]})


GET = {"/api/suche/weitere-seiten": listing}
POST = {"/api/suche/weitere-seiten": save, "/api/suche/seite-lesen": read_page}
