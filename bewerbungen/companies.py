"""Companies from hits and applications, with what kununu says about them (G35, #188).

One row per company, grouped by `hits.company_key`, so a choice made for a company holds for all its hits and
applications. What is known from kununu lives in `firmen.yaml` of the data folder, one entry per company key;
every change leaves drafts before and after. The person assigns a kununu page by link or picks one of several
candidates; the extension reads score and number of reviews on the person's click (#189), and when it cannot, the
person enters them by hand. Nothing of this goes to the AI.
"""
import datetime
import re
import urllib.parse

from dateien import lies_yaml, schreibe_yaml
from hits import Hits, company_key

FILE = "firmen.yaml"
HEADER = "# Firmen mit kununu-Bewertung, geschrieben vom Bewerbungsbegleiter\n"
UNKNOWN_COMPANY = "unbekannt"  # what hits.validate stores without a company
STATES = ("gefunden", "keine", "mehrere", "nicht_gefunden", "fehler", "zugeordnet")
SITES = ("ch", "de")
KUNUNU_HOSTS = ("kununu.com", "www.kununu.com")
OLD_GERMAN_HOSTS = ("kununu.de", "www.kununu.de")  # kununu.de leads to kununu.com/de
NOT_A_COMPANY = ("search", "suche", "login", "user", "jobs")
MAX_LINK = 500
MAX_TEXT = 200
MAX_CANDIDATES = 10
BAD_LINK = "Das ist kein Link zu einer Firma bei kununu."
UNKNOWN_CANDIDATE = "Diese Firma stand nicht zur Wahl. Bitte die Seite neu laden."
READ_STATES = ("gefunden", "keine", "mehrere", "nicht_gefunden")  # what a reading of kununu can say
BAD_READING = "Was die Erweiterung bei kununu gelesen hat, passt nicht."
BAD_VALUE = "Der Wert muss eine Zahl von 1 bis 5 sein."
BAD_COUNT = "Die Anzahl Bewertungen muss eine ganze Zahl ab 0 sein."
SEARCH = "https://www.kununu.com/{site}/search?q={name}"


def kununu_link(value) -> tuple[str, str]:
    """A link to a company on kununu as https without query and fragment, and its site ("ch" or "de")."""
    text = value.strip() if isinstance(value, str) else ""
    if not text or len(text) > MAX_LINK or any(c in text for c in "\\@ \t\n"):
        raise ValueError(BAD_LINK)
    parts = urllib.parse.urlsplit(text if "://" in text else "https://" + text)
    try:
        port = parts.port
    except ValueError as error:
        raise ValueError(BAD_LINK) from error
    host = (parts.hostname or "").lower()
    segments = [s for s in parts.path.split("/") if s]
    if parts.scheme not in ("http", "https") or port is not None:
        raise ValueError(BAD_LINK)
    if host in KUNUNU_HOSTS and len(segments) >= 2 and segments[0] in SITES:
        site, company = segments[0], segments[1:]
    elif host in OLD_GERMAN_HOSTS and segments:
        site, company = "de", segments
    else:
        raise ValueError(BAD_LINK)
    if company[0].lower() in NOT_A_COMPANY or not re.fullmatch(r"[\w.-]+", company[0]):
        raise ValueError(BAD_LINK)
    return f"https://www.kununu.com/{site}/{'/'.join(company)}", site


def search_link(name: str, site: str = "ch") -> str:
    return SEARCH.format(site=site, name=urllib.parse.quote(name))


def _number(value, low: float, high: float) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if low <= value <= high else None


def _text(value) -> str:
    return value.strip()[:MAX_TEXT] if isinstance(value, str) else ""


def _date(value) -> str:
    try:
        return datetime.date.fromisoformat(str(value)).isoformat() if value else ""
    except ValueError:
        return ""


def _link(value) -> str:
    try:
        return kununu_link(value)[0]
    except ValueError:
        return ""


def _reviews(raw) -> dict:
    """Score and number of reviews, for the company or for its apprentices."""
    if not isinstance(raw, dict):
        return {}
    values = {"wert": _number(raw.get("wert"), 1, 5), "bewertungen": _number(raw.get("bewertungen"), 0, 10 ** 7)}
    return {k: v for k, v in values.items() if v is not None}


def _candidate(raw) -> dict | None:
    if not isinstance(raw, dict) or not _link(raw.get("link")) or not _text(raw.get("name")):
        return None
    found = {"name": _text(raw.get("name")), "ort": _text(raw.get("ort")), "branche": _text(raw.get("branche")),
             "bewertungen": _number(raw.get("bewertungen"), 0, 10 ** 7), "link": _link(raw.get("link"))}
    return {k: v for k, v in found.items() if v not in ("", None)}


def clean(raw) -> dict | None:
    """One stored kununu entry with known fields only; the file is data the person may have edited."""
    if not isinstance(raw, dict) or raw.get("zustand") not in STATES:
        return None
    entry = {"zustand": raw["zustand"], **_reviews(raw), "empfehlung": _number(raw.get("empfehlung"), 0, 100),
             "geprueft_am": _date(raw.get("geprueft_am")), "seite": raw.get("seite") if raw.get("seite") in SITES else "",
             "link": _link(raw.get("link")), "lernende": _reviews(raw.get("lernende")),
             "von_hand": True if raw.get("von_hand") is True else None}
    listed = raw.get("kandidaten") if isinstance(raw.get("kandidaten"), list) else []
    candidates = [c for c in map(_candidate, listed[:MAX_CANDIDATES]) if c]
    return {k: v for k, v in {**entry, "kandidaten": candidates}.items() if v not in ("", None, {}, [])}


def stored(data_dir) -> dict[str, dict]:
    raw = lies_yaml(data_dir / FILE, {})
    if not isinstance(raw, dict):
        return {}
    entries = {str(key): clean(value) for key, value in raw.items()}
    return {key: value for key, value in entries.items() if value}


def _key(name) -> str:
    key = company_key(name if isinstance(name, str) else "")
    return "" if key in ("", UNKNOWN_COMPANY) else key


def _company(name: str, ort: str) -> tuple[str, str, str]:
    """(key, name, place) of a hit or an application; no key without a company."""
    return _key(name), name.strip(), ort.strip()


def _merged(group: list[tuple[str, str, dict, dict | None]]) -> dict:
    """One row from (name, place, application, hit) pairs of one company: applications come first, so their name wins."""
    places = [place for _, place, _, _ in group if place]
    return {"name": group[0][0], "ort": places[0] if places else "",
            "bewerbungen": [entry for _, _, entry, _ in group if entry],
            "treffer": [hit for _, _, _, hit in group if hit]}


def rows(data_dir, applications: list[dict]) -> list[dict]:
    """One row per company with its hits, its applications and what kununu says, in no particular order."""
    seen = [(*_company(e.get("firma") or "", e.get("ort") or ""),
             {"id": e.get("id"), "stelle": e.get("stelle") or "", "status": e.get("status") or ""}, None) for e in applications]
    seen += [(*_company(h.get("firma") or "", h.get("ort") or ""), None,
              {"id": h.get("id"), "stelle": h.get("stelle") or "", "zustand": h.get("zustand") or "neu"}) for h in Hits(data_dir).all()]
    keys = list(dict.fromkeys(key for key, *_ in seen if key))
    known = stored(data_dir)
    result = []
    for key in keys:
        row = _merged([(name, place, entry, hit) for k, name, place, entry, hit in seen if k == key])
        result.append({"schluessel": key, **row, "kununu": known.get(key), "suche": search_link(row["name"])})
    return result


def _row(data_dir, applications: list[dict], key: str) -> dict:
    found = next((row for row in rows(data_dir, applications) if row["schluessel"] == key), None)
    if found is None:
        raise KeyError(key)
    return found


def _write(k, key: str, name: str, entry: dict | None, description: str) -> dict | None:
    path = k.daten / FILE

    def write():
        raw = lies_yaml(path, {})
        current = raw if isinstance(raw, dict) else {}
        updated = {**{other: value for other, value in current.items() if other != key}, **({key: entry} if entry else {})}
        schreibe_yaml(path, updated, HEADER)

    k.mit_entwurf(path, f"Firmen: {description} ({name})", write)
    return entry


def assign(k, applications: list[dict], key: str, link) -> dict:
    """The person names the kununu page of a company; its values come with the next check."""
    row = _row(k.daten, applications, key)
    url, site = kununu_link(link)
    entry = {"zustand": "zugeordnet", "link": url, "seite": site}
    return _write(k, key, row["name"], entry, "kununu-Seite zugeordnet")


def choose(k, applications: list[dict], key: str, link, today: datetime.date) -> dict:
    """One of several companies kununu listed, or none of them (link None): then the company is not found."""
    row = _row(k.daten, applications, key)
    candidates = (row["kununu"] or {}).get("kandidaten") or []
    if link is None:
        entry = {"zustand": "nicht_gefunden", "geprueft_am": today.isoformat()}
        return _write(k, key, row["name"], entry, "keine Firma bei kununu passt")
    url, site = kununu_link(link)
    if url not in {c["link"] for c in candidates}:
        raise ValueError(UNKNOWN_CANDIDATE)
    entry = {"zustand": "zugeordnet", "link": url, "seite": site}
    return _write(k, key, row["name"], entry, "Firma bei kununu gewählt")


def _rating(value) -> float:
    if _number(value, 1, 5) is None:
        raise ValueError(BAD_VALUE)
    return value


def _count(value) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(BAD_COUNT)
    return value


def _reading(raw, today: datetime.date) -> dict:
    """A reading as the extension sends it, checked field by field; the date is the app's own."""
    if not isinstance(raw, dict) or raw.get("zustand") not in READ_STATES:
        raise ValueError(BAD_READING)
    state, checked = raw["zustand"], {"geprueft_am": today.isoformat()}
    if state == "nicht_gefunden":
        return {"zustand": state, **checked}
    if state == "mehrere":
        listed = raw.get("kandidaten") if isinstance(raw.get("kandidaten"), list) else []
        candidates = [c for c in map(_candidate, listed[:MAX_CANDIDATES]) if c]
        if not candidates:
            raise ValueError(BAD_READING)
        return {"zustand": state, "kandidaten": candidates, **checked}
    url, site = kununu_link(raw.get("link"))
    values = {"wert": _rating(raw.get("wert")), "bewertungen": _count(raw.get("bewertungen"))} if state == "gefunden" else {}
    return {"zustand": state, **values, "link": url, "seite": site, **checked}


def store_reading(k, applications: list[dict], key: str, raw, today: datetime.date) -> dict:
    """What the extension read at kununu on the person's click (#189)."""
    row = _row(k.daten, applications, key)
    return _write(k, key, row["name"], _reading(raw, today), "von kununu gelesen")


def enter_by_hand(k, applications: list[dict], key: str, raw, today: datetime.date) -> dict:
    """Score and number of reviews the person read at kununu; the page known so far stays."""
    row = _row(k.daten, applications, key)
    values = raw if isinstance(raw, dict) else {}
    known = row["kununu"] or {}
    page = {field: known[field] for field in ("link", "seite") if known.get(field)}
    entry = {"zustand": "gefunden", "wert": _rating(values.get("wert")), "bewertungen": _count(values.get("bewertungen")),
             **page, "geprueft_am": today.isoformat(), "von_hand": True}
    return _write(k, key, row["name"], entry, "kununu-Wert von Hand")
