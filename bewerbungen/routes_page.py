"""An ad from a page the person has open (MIN-345), e.g. LinkedIn or the career page of a company.

The extension reads the open tab only after a click and sends the ad through the app's Native Messaging host.
Checking rates it and says what is there already, and stores nothing. Saving makes an application with the ad.
Text from a page is data: it reaches the AI only through the gateway, and the link only if it is a web address.

Claude on the person's own subscription (MIN-377) saves through its own route, which the extension cannot reach. The
extension takes the address of the tab the person has open; Claude only names one, and a text on a page can make it name
any. „Bewerben“ opens that address and fills in the person's data, so only known sites get a link; others go to the note.
"""
import threading
import urllib.parse

import own_sites
import routes_ai
import unterlagen
from ai import tasks
from dateien import schreibe_atomar
from hits import (CLOSED, DOMAINS, MAX_TEXT, ROUTE_FRAGMENT, Hits, _close_title, ad_with_details, bounded_text,
                  comparable_link, company_hint, company_key, portal_of, without_tracking)
from routes_search import BAD_RATING, note_for, rating_fields
from server import json_antwort

AD_ID = "seite"
WEB_SCHEMES = ("http", "https")
MIN_GRADE, MAX_GRADE = 1, 6
BAD_LINK = "Diese Seite hat keine gültige Webadresse."
NO_TEXT = "Der Text des Inserats fehlt."
BAD_GRADE = "Die Bewertung hat eine unbekannte Form."
SUMMARY_FIELDS = ("id", "firma", "stelle", "status")
SITES_WITHOUT_PORTAL = ("linkedin.com",)  # the person gives Claude these ads, the search has no list of them
LINK_NOT_TAKEN = "Adresse von Claude, nicht geprüft: {link}. Stimmt sie, bitte von Hand bei „Link zum Inserat“ eintragen."
_SAVE = threading.Lock()


def _link(value) -> str:
    link = bounded_text(value, "Link", required=True, limit=1000)
    # Browsers read "\\" as "/" and take the host before "@" differently than urlsplit: refuse both.
    if any(c in link for c in "\\@ "):
        raise ValueError(BAD_LINK)
    parts = urllib.parse.urlsplit(link)
    if parts.scheme not in WEB_SCHEMES or not parts.hostname:
        raise ValueError(BAD_LINK)
    query = urllib.parse.urlencode(without_tracking(parts.query))
    fragment = parts.fragment if parts.fragment.startswith(ROUTE_FRAGMENT) else ""  # „#/job/12“ names the ad, „#bewerben“ does not
    return urllib.parse.urlunsplit(parts._replace(query=query, fragment=fragment))


def _ad(body) -> dict:
    if not isinstance(body, dict):
        raise ValueError("Die Anfrage hat eine unbekannte Form.")
    text = body.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError(NO_TEXT)
    return {"stelle": bounded_text(body.get("stelle"), "Stelle", required=True), "firma": bounded_text(body.get("firma"), "Firma"),
            "ort": bounded_text(body.get("ort"), "Ort"), "link": _link(body.get("link")), "text": text.strip()[:MAX_TEXT]}


def _rating(value) -> dict | None:
    """The rating the extension got from the check; only what goes into the register, and only in the known form."""
    if value is None:
        return None
    grade = value.get("note") if isinstance(value, dict) else None
    if type(grade) not in (int, float) or not MIN_GRADE <= grade <= MAX_GRADE:
        raise ValueError(BAD_GRADE)
    hooks = value.get("haken", [])
    if not isinstance(hooks, list) or not all(isinstance(h, str) for h in hooks):
        raise ValueError(BAD_GRADE)
    return {"note": grade, "zusammenfassung": bounded_text(value.get("zusammenfassung"), "Bewertung", limit=2000),
            "haken": [bounded_text(h, "Bewertung", limit=500) for h in hooks],
            "unsicher": bounded_text(value.get("unsicher"), "Bewertung", limit=500)}


def _matches(ad: dict, register: list[dict]) -> list[dict]:
    """Applications for this ad. On a portal a link names one ad, whatever the title says (#197); elsewhere several ads
    can share one address, so the title must be close too, and then the same link or company counts."""
    link = comparable_link(ad["link"])
    on_portal = portal_of(ad["link"]) is not None
    company = company_key(ad["firma"])

    def same(entry: dict) -> bool:
        same_link = bool(entry.get("link")) and comparable_link(entry["link"]) == link
        if on_portal and same_link:
            return True
        if not _close_title(ad["stelle"], entry.get("stelle") or ""):
            return False
        return same_link or (bool(company) and company in {company_key(entry.get("firma_schluessel") or ""),
                                                           company_key(entry.get("firma") or "")})

    return [entry for entry in register if same(entry)]


def _open_match(matches: list[dict]) -> dict | None:
    return next((entry for entry in matches if entry.get("status") not in CLOSED), None)


def _summary(entry: dict | None) -> dict | None:
    return None if entry is None else {field: entry.get(field) for field in SUMMARY_FIELDS}


def check(k, parameter, body):
    ad = _ad(body)
    register = k.register().alle()

    def task():
        gateway, material = routes_ai.ai_gateway(k)
        return tasks.rate_package(gateway, material, [(AD_ID, ad_with_details({**ad, "link": ""}, ad["text"]))])

    result = routes_ai.run_ai(task)
    rating = result["ratings"].get(AD_ID)
    if rating is None:
        raise ValueError(BAD_RATING)
    matches = _matches(ad, register)
    existing = _open_match(matches) or next(iter(matches), None)
    return json_antwort({"bewertung": rating_fields(rating, result["cost_usd"], result["model"]), "vorhanden": _summary(existing),
                         "hinweis": "" if existing else company_hint({**ad, "firma": ad["firma"] or "unbekannt"}, register)})


def _write_ad(k, entry: dict, ad: dict) -> None:
    path = unterlagen.bewerbungsordner(k.daten, entry["id"]) / "stelle.md"
    text = ad_with_details(ad, ad["text"])
    k.mit_entwurf(path, f"Stellentext {entry['firma']}", lambda: schreibe_atomar(path, text.encode("utf-8")))


def _has_ad(k, entry: dict) -> bool:
    return (unterlagen.bewerbungsordner(k.daten, entry["id"]) / "stelle.md").is_file()


def _store(k, ad: dict, rating: dict | None, link: str | None, note: str = "") -> dict:
    """One open application per ad: asked twice, the second answer names the first. If writing the text failed the
    first time, the second try brings it; a text that is there stays, the person may have changed it."""
    if not ad["firma"]:
        raise ValueError("Firma fehlt. Bitte in der Erweiterung eintragen.")
    with _SAVE:
        register = k.register()
        existing = _open_match(_matches(ad, register.alle()))
        if existing is not None:
            if not _has_ad(k, existing):
                _write_ad(k, existing, ad)
            return {"bewerbung": _summary(existing), "neu": False}
        host = (urllib.parse.urlsplit(ad["link"]).hostname or "").removeprefix("www.")
        fields = {"firma_schluessel": company_key(ad["firma"]), "ort": ad["ort"], "portal": portal_of(ad["link"]) or host, "link": link, "status": "Gemerkt",
                  "notiz": "\n".join(part for part in (note_for({"bewertung": rating}), note) if part), "passung": (rating or {}).get("note")}
        entry = k.mit_entwurf(register.pfad, f"Stelle von Seite: {ad['firma']} – {ad['stelle']}",
                              lambda: register.neu(firma=ad["firma"], stelle=ad["stelle"],
                                                   **{key: v for key, v in fields.items() if v not in (None, "")}))
        _write_ad(k, entry, ad)
    return {"bewerbung": _summary(entry), "neu": True}


def save(k, parameter, body):
    ad = _ad(body)
    return json_antwort(_store(k, ad, _rating(body.get("bewertung")), ad["link"]))


def _known_site(k, link: str) -> bool:
    parts = urllib.parse.urlsplit(link)
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or parts.netloc.lower() != host:
        return False
    named = (site["portal"] for site in own_sites.configured(Hits(k.daten)))
    return any(host == site or host.endswith("." + site) for site in (*DOMAINS.values(), *SITES_WITHOUT_PORTAL, *named))


def save_from_claude(k, parameter, body):
    """An ad Claude saves: the same as `save`, but a link only for a site the app or the person knows."""
    ad = _ad(body)
    known = _known_site(k, ad["link"])
    stored = _store(k, ad, None, ad["link"] if known else None, "" if known else LINK_NOT_TAKEN.format(link=ad["link"]))
    return json_antwort({**stored, "link_gespeichert": known})


POST = {"/api/seite/pruefen": check, "/api/seite/speichern": save, "/api/seite/von-claude": save_from_claude}
