"""Ad texts that saved jobs and hits are missing (G37, G38, #275).

At a new start of the app the extension asks which jobs lack their text and loads it, but only from the portals that
allow automatic loading: those with their own adapter in the extension (`hits.DOMAINS`). Every other site, a job
without a link and whatever did not load, the app names with the reason and the way to get the text oneself. Nothing
here goes to the AI.
"""
import re
import urllib.parse

from hits import DOMAINS, Hits, checked_link, company_key, portal_of

TREFFER, BEWERBUNG = "treffer", "bewerbung"
KINDS = (TREFFER, BEWERBUNG)
OPEN_STAGES = ("Gemerkt", "Bewerben")  # sent or closed jobs need no ad any more
HEAD = re.compile(r"^(Art|Stelle|Firma|Ort|Pensum|Lehrbeginn|Link): ")  # the lines hits.ad_with_details puts on top
ID_IN_LINK = {"job-room": re.compile(r"/job-search/([^/?#]+)"), "jobs.ch": re.compile(r"/detail/([^/?#]+)")}

NO_LINK = "Ohne Link zum Inserat kann die Erweiterung den Text nicht holen."
NOT_ALLOWED = "{site} ist keines der Portale, die automatisches Laden erlauben."
PENDING = "Die Erweiterung holt den Text beim nächsten Start der App von {portal}."
FAILED = "Das Laden von {portal} ging nicht ({reason}). Die Erweiterung versucht es beim nächsten Start der App wieder."
UNREADABLE = "Die Seite auf {portal} hatte keinen lesbaren Text."
WAY_SAVED = "Das Inserat öffnen und es mit der Erweiterung speichern, oder den Text unter „Stellentext“ einfügen."
WAY_HIT = "Das Inserat öffnen und es mit der Erweiterung speichern."
WAY_NO_LINK = "Den Text des Inserats unter „Stellentext“ einfügen."


def ad_body(text: str) -> str:
    """The ad without the lines of details on top; empty when only those are there."""
    lines = (text or "").strip().splitlines()
    first = next((i for i, line in enumerate(lines) if not HEAD.match(line)), len(lines))
    return "\n".join(lines[first:]).strip()


def has_ad(text: str) -> bool:
    return bool(ad_body(text))


def portal_id_of(portal: str | None, link: str) -> str:
    """The id job-room and jobs.ch need to load an ad; the other adapters load from the link itself."""
    pattern = ID_IN_LINK.get(portal or "")
    found = pattern.search(urllib.parse.urlsplit(link).path) if pattern else None
    return urllib.parse.unquote(found.group(1)) if found else ""


def _job(kind: str, ident: str, link: str, portal_id: str = "") -> dict:
    portal = portal_of(link)
    return {"art": kind, "id": ident, "portal": portal, "portal_id": portal_id or portal_id_of(portal, link), "link": link}


def loadable(job: dict) -> bool:
    """A portal with its own adapter, a link that belongs to it and, where the adapter needs one, an id."""
    if job["portal"] not in DOMAINS:
        return False
    try:
        checked_link(job["link"], job["portal"])
    except ValueError:
        return False
    return job["portal"] not in ID_IN_LINK or bool(job["portal_id"])


def saved_without_ad(register: list[dict], ad_of, store: Hits) -> list[dict]:
    """Open saved jobs whose stelle.md is missing or has only the details; the id from the hit they came from."""
    from_hits = {hit["bewerbung_id"]: hit for hit in store.all() if hit.get("bewerbung_id")}
    jobs = []
    for entry in register:
        if entry.get("status") not in OPEN_STAGES or has_ad(ad_of(entry["id"])):
            continue
        hit = from_hits.get(entry["id"]) or {}
        same = hit.get("portal") == portal_of(entry.get("link") or "")
        jobs.append(_job(BEWERBUNG, entry["id"], entry.get("link") or "", hit.get("portal_id", "") if same else ""))
    return jobs


def hit_job(hit: dict) -> dict:
    """A hit as a job to load: its portal and id come from the search, not from the link."""
    return {"art": TREFFER, "id": hit["id"], "portal": hit["portal"], "portal_id": hit["portal_id"], "link": hit["link"]}


def hits_without_ad(store: Hits, excluded: frozenset[str] = frozenset()) -> list[dict]:
    """New hits without a text; none of a company the person excluded (#226)."""
    return [_job(TREFFER, hit["id"], hit["link"], hit["portal_id"]) for hit in store.all()
            if hit.get("zustand") == "neu" and not store.text(hit["id"]).strip()
            and company_key(hit.get("firma") or "") not in excluded]


def note(job: dict, failure: str | None) -> dict:
    """Why the text is missing and how to get it oneself."""
    way = WAY_HIT if job["art"] == TREFFER else WAY_SAVED
    if not job["link"]:
        return {"grund": NO_LINK, "weg": WAY_NO_LINK}
    if not loadable(job):
        site = (urllib.parse.urlsplit(job["link"]).hostname or job["link"]).removeprefix("www.")
        return {"grund": NOT_ALLOWED.format(site=site), "weg": way}
    if failure is None:
        return {"grund": PENDING.format(portal=job["portal"]), "weg": way}
    reason = FAILED.format(portal=job["portal"], reason=failure) if failure else UNREADABLE.format(portal=job["portal"])
    return {"grund": reason, "weg": way}
