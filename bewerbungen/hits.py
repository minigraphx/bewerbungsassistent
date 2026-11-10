"""Hits of the job search in the browser (MIN-339): checked, stored and offered to the person.

The extension sends what it found on the portals. Hits are kept apart from the register in
`suche/treffer.yaml`, ad texts in `suche/texte/`; the person rates them, takes them over into the register
or discards them. The register stays the only source for applications; this file only prevents that the
same hit comes again.
"""
import dataclasses
import datetime
import hashlib
import html
import pathlib
import re
import threading
import urllib.parse

from dateien import lies_yaml, schreibe_atomar, schreibe_yaml
from preferences import SAVED_IN, SIE
from register import slug

FOLDER = "suche"
HITS_FILE = "treffer.yaml"
RUN_FILE = "letzte-suche.yaml"
LAST_SUCCESS = "erfolgreich_am"
SETTINGS_FILE = "einstellungen.yaml"
OWN_SITES = "weitere_seiten"
PORTALS_OFF = "portale_aus"
MAX_STARS = 5
TEXTS = "texte"
DOMAINS = {"job-room": "job-room.ch", "jobs.ch": "jobs.ch", "jobscout24": "jobscout24.ch", "ictjobs": "ictjobs.ch",
           "LENA": "berufsberatung.ch", "yousty": "yousty.ch"}
# Say who clicked or which session it was, not which ad; they stay out of the register, and the AI gets no address at all.
TRACKING = {"refid", "trk", "trackingid", "ref", "src", "source", "gclid", "fbclid", "mc_cid", "mc_eid", "midtoken", "midsig",
            "lipi", "eid", "token", "otptoken", "sid", "sessionid", "session"}
ROUTE_FRAGMENT = ("/", "!/")
STATES = ("neu", "uebernommen", "verworfen")
MAX_FIELD = 200
MAX_ID = 200
MAX_TEXT = 30_000
MAX_HITS_PER_CALL = 100
NO_POSITIVE_TERM = "kein Positivbegriff im Titel"
LEGAL_FORMS = {"ag", "gmbh", "sa", "sarl", "sagl", "ltd", "llc", "inc", "kg", "co", "se", "plc", "bv"}
TRIAL = "Schnupperlehre"
OWN_STARS = "eigene_sterne"  # the person's own rating of a hit (G22); never part of an AI request
ORDERS = ("note", "eigene", "datum")  # how the list of hits is sorted; the grade first, as before G22
CLOSED = {"Absage", "Verworfen", "Zurückgezogen"}
# G34: staffing agencies post jobs of other companies; the search profile can add more („## Vermittler“).
AGENCIES = ("Adecco", "Manpower", "Randstad", "Hays", "Michael Page", "Page Personnel", "Robert Half", "Kelly Services",
            "Gi Group", "Universal-Job", "Careerplus", "Coople", "Interiman", "Persona Service", "Yellowshark")
AGENCY_CLOSED = CLOSED | {"Zusage"}
AGENCY_TWIN = "Könnte dieselbe Stelle sein wie „{stelle}“ bei {firma} ({status}) {saved_in}."
TITLE_FILLERS = frozenset({"und", "mit", "für", "fuer", "der", "die", "das", "als", "im", "in", "zur", "zum", "von"})
MIN_TITLE_OVERLAP = 0.75  # share of the shorter title's words both titles have
_LOCK = threading.Lock()
MARKUP = re.compile(r"</?[a-zA-Z][^<>]*>")
POSTAL_CODE = re.compile(r"\b\d{4}\b")
POSTAL_AREA = 2


def plain_text(value):
    """Portals mark search terms with tags and send entities (job-room: <em>, &amp;). Anything but text stays as it is."""
    return " ".join(MARKUP.sub("", html.unescape(value)).split()) if isinstance(value, str) else value


def is_near(place: str, homes: tuple[str, ...], postal_codes: tuple[str, ...]) -> bool:
    """Is this the home or the same postal area (the first two digits)? There are no distances to work with."""
    if any(re.search(rf"\b{re.escape(home)}\b", place, re.IGNORECASE) for home in homes):
        return True
    areas = {code[:POSTAL_AREA] for code in postal_codes}
    return any(code[:POSTAL_AREA] in areas for code in POSTAL_CODE.findall(place))


def bounded_text(value, field: str, required: bool = False, limit: int = MAX_FIELD) -> str:
    if value is None:
        value = ""
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        raise ValueError(f"{field} muss Text sein")
    text = " ".join(str(value).split())[:limit]
    if required and not text:
        raise ValueError(f"{field} fehlt")
    return text


def without_tracking(query: str) -> list[tuple[str, str]]:
    pairs = urllib.parse.parse_qsl(query, keep_blank_values=True)
    return [(k, v) for k, v in pairs if k.lower() not in TRACKING and not k.lower().startswith("utm_")]


def comparable_link(link: str, any_fragment: bool = False) -> str:
    """The same ad under another scheme, with or without www, a slash or tracking values gives the same text.

    `any_fragment` is for links the search builds: there „#schnupperlehre“ tells a trial from the apprenticeship."""
    parts = urllib.parse.urlsplit(link or "")
    query = urllib.parse.urlencode(sorted(without_tracking(parts.query)))
    fragment = parts.fragment if any_fragment or parts.fragment.startswith(ROUTE_FRAGMENT) else ""
    host = (parts.hostname or "").lower().removeprefix("www.")
    return f"{host}{parts.path.rstrip('/')}?{query}#{fragment}"


def is_trial(link: str, kind: str = "") -> bool:
    """A trial apprenticeship: yousty shows it on the apprenticeship's page, only „#schnupperlehre“ tells them apart."""
    return kind == TRIAL or urllib.parse.urlsplit(link or "").fragment == TRIAL.lower()


def portal_of(link: str) -> str | None:
    """The portal whose site the link is on, by name as the search stores it; None for any other site."""
    host = (urllib.parse.urlsplit(link or "").hostname or "").lower()
    return next((portal for portal, domain in DOMAINS.items() if host == domain or host.endswith("." + domain)), None)


def checked_link(value, portal: str) -> str:
    link = bounded_text(value, "Link", required=True, limit=1000)
    # Browsers read "\\" as "/" and take the host before "@" differently than urlsplit: refuse both.
    if any(c in link for c in "\\@ ") or any(ord(c) < 0x20 for c in link):
        raise ValueError(f"Link gehört nicht zu {portal}")
    parts = urllib.parse.urlsplit(link)
    host = (parts.hostname or "").lower()
    domain = DOMAINS.get(portal, portal)  # a site the person named has its host as its name (MIN-348)
    if parts.scheme != "https" or parts.netloc.lower() != host or not (host == domain or host.endswith("." + domain)):
        raise ValueError(f"Link gehört nicht zu {portal}")
    return link


def _age(value) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("alter_tage muss eine Zahl sein")
    return value


def validate(raw, own_portals: frozenset[str] = frozenset()) -> dict:
    """A hit as the extension sends it, checked and bounded; the text stays separate. `own_portals`: sites the
    person named, while they count (MIN-348)."""
    if not isinstance(raw, dict):
        raise ValueError("Treffer muss ein Objekt sein")
    portal = raw.get("portal")
    if portal not in DOMAINS and portal not in own_portals:
        raise ValueError(f"Unbekanntes Portal: {portal!r}")
    hit = {"portal": portal, "portal_id": bounded_text(raw.get("portal_id"), "portal_id", True, MAX_ID),
           "stelle": bounded_text(plain_text(raw.get("stelle")), "stelle", True),
           "firma": bounded_text(plain_text(raw.get("firma")), "firma") or "unbekannt",
           "ort": bounded_text(raw.get("ort"), "ort"), "pensum": bounded_text(raw.get("pensum"), "pensum"),
           "link": checked_link(raw.get("link"), portal), "alter_tage": _age(raw.get("alter_tage")),
           "art": bounded_text(raw.get("art"), "art"), "beruf": bounded_text(raw.get("beruf"), "beruf"),
           "lehrbeginn": bounded_text(raw.get("lehrbeginn"), "lehrbeginn")}
    text = raw.get("text")
    if text is not None and not isinstance(text, str):
        raise ValueError("text muss Text sein")
    return {**{k: v for k, v in hit.items() if v not in ("", None)}, "text": (text or "").strip()[:MAX_TEXT]}


NOT_A_PLACE = frozenset({"schweiz", "suisse", "svizzera", "switzerland", "homeoffice", "home", "office", "remote", "und", "oder", "bei", "region", "raum",
                         "kanton", "bad", "sankt"})  # „Bern, Schweiz“ and „Zürich, Schweiz“ share a word, not a place
# With m or w: „D/F“ in a Swiss title means German and French.
_TITLE_GENDER = re.compile(r"\(?\b(?=[dfx/|\s]*[mw])[mwfdx](?:\s*[/|]\s*[mwfdx]){1,3}\b\)?", re.IGNORECASE)
_TITLE_ENDING = re.compile(r"\s*[/:*_]\s*-?in(?:nen)?\b")  # Entwickler/in, Entwickler:in, Ingenieur/-in
_TITLE_PENSUM = re.compile(r"(?:\bPensum\b\s*:?\s*)?\b\d{1,3}\s*(?:(?:-|–|—|bis)\s*\d{1,3}\s*)?%", re.IGNORECASE)


def key(hit: dict) -> str:
    return f"{hit['portal']}:{hit['portal_id']}"


def hit_id(hit: dict) -> str:
    digest = hashlib.sha256(key(hit).encode("utf-8")).hexdigest()[:12]
    return f"{slug(hit['portal'])}-{digest}"


def company_key(name: str) -> str:
    words = [w for w in slug(name or "").split("-") if w and w not in LEGAL_FORMS]
    return "-".join(words)


def _title_key(title: str) -> str:
    """The title without what says nothing about the job. Only that: merging two jobs would lose one, a double hit costs a click."""
    cleaned = _TITLE_PENSUM.sub(" ", _TITLE_ENDING.sub("", _TITLE_GENDER.sub(" ", title)))
    return slug(cleaned) or slug(title)


def _title_pensum(title: str) -> str:
    found = _TITLE_PENSUM.search(_TITLE_GENDER.sub(" ", title))
    return "".join(re.findall(r"\d+", found.group())) if found else ""


def _job_key(hit: dict) -> str:
    """Company and job. The portals name a profession differently, so the search's own name for it counts first.

    A trial apprenticeship and an apprenticeship at one company are two offers.
    """
    return f"{company_key(hit['firma'])}|{_title_key(hit.get('beruf') or hit['stelle'])}|{hit.get('art') == TRIAL}"


def _places(ort: str) -> set[str]:
    return set(re.findall(r"[^\W\d_]{3,}", (ort or "").lower())) - NOT_A_PLACE


def _has_other_ad_of_portal(stored: dict, hit: dict) -> bool:
    """A link from this portal is already merged into the stored hit. The same link again stays known; another one is a second job."""
    merged = stored.get("weitere", [])
    return any(o["portal"] == hit["portal"] for o in merged) and all(o["link"] != hit["link"] for o in merged)


def _find_twin(hit: dict, stored: list[dict]) -> dict | None:
    """The same job already stored from another portal: same company, title and place.

    Two ads on one portal are two jobs, and without a company name nothing is merged.
    """
    company = company_key(hit["firma"])
    if not company or company == "unbekannt":
        return None
    job, places, pensum = _job_key(hit), _places(hit.get("ort", "")), _title_pensum(hit["stelle"])
    for other in stored:
        if other["portal"] == hit["portal"] or _job_key(other) != job or _has_other_ad_of_portal(other, hit):
            continue
        other_pensum = _title_pensum(other["stelle"])
        if pensum and other_pensum and pensum != other_pensum:  # „Koch 50%“ and „Koch 100%“ can be two jobs
            continue
        other_places = _places(other.get("ort", ""))
        if not places or not other_places or places & other_places:
            return other
    return None


def _with_link(stored: list[dict], twin: dict, hit: dict) -> list[dict] | None:
    """The stored hits with the link of the other portal added to the twin; None when it is there already."""
    others = twin.get("weitere", [])
    if twin["link"] == hit["link"] or any(o["link"] == hit["link"] for o in others):
        return None
    merged = {**twin, "weitere": [*others, {"portal": hit["portal"], "link": hit["link"]}]}
    return [merged if h is twin else h for h in stored]


def _title_match(title: str, terms: tuple[str, ...]) -> str | None:
    for term in terms:
        if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", title, re.IGNORECASE):
            return term
    return None


def company_hint(hit: dict, register: list[dict]) -> str:
    company = company_key(hit["firma"])
    if not company or company == "unbekannt":
        return ""
    same = [b for b in register if b.get("status") not in CLOSED
            and company in (company_key(b.get("firma_schluessel") or ""), company_key(b.get("firma") or ""))]
    return "; ".join(f"Bei {b['firma']} gibt es schon: {b['stelle']} ({b['status']})" for b in same[:2])


def _is_agency(company: str, agencies: tuple[str, ...]) -> bool:
    found = f"-{company_key(company)}-"
    return any(key and f"-{key}-" in found for key in map(company_key, agencies))


def _title_words(title: str) -> frozenset[str]:
    return frozenset(word for word in _title_key(title).split("-") if len(word) > 1 and word not in TITLE_FILLERS)


def _pensum_range(text: str) -> tuple[int, int] | None:
    found = _TITLE_PENSUM.search(text or "")
    numbers = [int(n) for n in re.findall(r"\d+", found.group())] if found else []
    return (min(numbers), max(numbers)) if numbers else None


def _same_pensum(hit: dict, entry: dict) -> bool:
    """Unknown on either side counts as the same; „80–100 %“ and „80 %“ overlap."""
    ours, theirs = _pensum_range(hit.get("pensum") or hit["stelle"]), _pensum_range(entry.get("pensum") or entry.get("stelle", ""))
    return ours is None or theirs is None or (ours[0] <= theirs[1] and theirs[0] <= ours[1])


def _close_title(title: str, other: str) -> bool:
    ours, theirs = _title_words(title), _title_words(other)
    shared = len(ours & theirs)
    return bool(shared) and shared / min(len(ours), len(theirs)) >= MIN_TITLE_OVERLAP


def agency_hint(hit: dict, register: list[dict], agencies: tuple[str, ...], saved_in: str = SAVED_IN[SIE]) -> str:
    """An agency hides the company: an open entry with a close title and the same pensum may be this job (G34)."""
    if not _is_agency(hit["firma"], (*AGENCIES, *agencies)):
        return ""
    same = [b for b in register if b.get("status") not in AGENCY_CLOSED and b.get("stelle")
            and _close_title(hit["stelle"], b["stelle"]) and _same_pensum(hit, b)]
    return " ".join(AGENCY_TWIN.format(stelle=b["stelle"], firma=b.get("firma") or "unbekannt", status=b.get("status") or "Gemerkt",
                                       saved_in=saved_in)
                    for b in same[:2])


def ad_with_details(hit: dict, body: str) -> str:
    """Details and text of an ad, as the AI rates it and as it goes into stelle.md."""
    labels = (("Stelle", "stelle"), ("Firma", "firma"), ("Ort", "ort"), ("Pensum", "pensum"),
              ("Lehrbeginn", "lehrbeginn"), ("Link", "link"))
    kind = [f"Art: {TRIAL}"] if hit.get("art") == TRIAL else []
    head = "\n".join(kind + [f"{label}: {hit[field]}" for label, field in labels if hit.get(field)])
    return f"{head}\n\n{body}" if body else head


@dataclasses.dataclass(frozen=True)
class Hits:
    data_dir: pathlib.Path

    @property
    def folder(self) -> pathlib.Path:
        return self.data_dir / FOLDER

    def all(self) -> list[dict]:
        found = lies_yaml(self.folder / HITS_FILE, [])
        if not isinstance(found, list):
            return []
        # Hits stored before titles were cleaned read clean too.
        return [{**h, "stelle": plain_text(h.get("stelle")), "firma": plain_text(h.get("firma"))}
                for h in found if isinstance(h, dict) and isinstance(h.get("id"), str)]

    def get(self, wanted: str) -> dict:
        for hit in self.all():
            if hit["id"] == wanted:
                return hit
        raise KeyError(f"Treffer {wanted!r} nicht gefunden")

    def _text_path(self, wanted: str) -> pathlib.Path:
        if not re.fullmatch(r"[a-z0-9-]+", wanted):
            raise KeyError(f"Treffer {wanted!r} nicht gefunden")
        return self.folder / TEXTS / f"{wanted}.txt"

    def text(self, wanted: str) -> str:
        path = self._text_path(wanted)
        return path.read_text(encoding="utf-8") if path.is_file() else ""

    def ad_text(self, wanted: str) -> str:
        """Details and text of the ad, as the AI rates it and as it goes into stelle.md."""
        return ad_with_details(self.get(wanted), self.text(wanted))

    def _write(self, all_hits: list[dict]) -> None:
        schreibe_yaml(self.folder / HITS_FILE, all_hits, "# Treffer der Stellensuche, geschrieben vom Bewerbungsbegleiter\n")

    def screen(self, listing: list, title_exclude: tuple[str, ...], max_age: int, register: list[dict],
               own_portals: frozenset[str] = frozenset(), near=lambda place: False,
               title_positive: tuple[str, ...] = (), max_age_by_portal: dict[str, int] | None = None) -> dict:
        """Which hits of a result list the extension should open for the full text, and which of them are near the home.

        The same job from another portal needs no text: its link goes to the stored hit right away. With positive
        terms (G31), a title needs one of them; the others are screened out before their text counts against the limit.
        `max_age_by_portal` shortens the window per portal after a successful run (G32).
        """
        fetch, nearby, filtered, known, merged = [], [], [], 0, 0
        ages = max_age_by_portal or {}
        with _LOCK:
            stored = self.all()
            known_keys = {key(h) for h in stored}
            links = ([b.get("link") for b in register] + [h.get("link") for h in stored]
                     + [o["link"] for h in stored for o in h.get("weitere", [])])
            known_links = {comparable_link(link, any_fragment=True) for link in links if link}
            for raw in listing[:MAX_HITS_PER_CALL * 5]:
                try:
                    hit = validate(raw, own_portals)
                except ValueError:
                    continue
                if key(hit) in known_keys or comparable_link(hit["link"], any_fragment=True) in known_links:
                    known += 1
                    continue
                twin = _find_twin(hit, stored)
                if twin is not None:
                    updated = _with_link(stored, twin, hit)
                    if updated is not None:
                        stored, merged = updated, merged + 1
                    continue
                term = _title_match(hit["stelle"], title_exclude)
                if term:
                    filtered.append({"stelle": hit["stelle"], "grund": f"Titel: {term}"})
                elif title_positive and _title_match(hit["stelle"], title_positive) is None:
                    filtered.append({"stelle": hit["stelle"], "grund": NO_POSITIVE_TERM})
                elif hit.get("alter_tage") is not None and hit["alter_tage"] > ages.get(hit["portal"], max_age):
                    days = ages.get(hit["portal"], max_age)
                    filtered.append({"stelle": hit["stelle"], "grund": f"älter als {days} {'Tag' if days == 1 else 'Tage'}"})
                elif key(hit) not in fetch:
                    fetch.append(key(hit))
                    if near(hit.get("ort", "")):
                        nearby.append(key(hit))
            if merged:
                self._write(stored)
        return {"holen": fetch, "nah": nearby, "bekannt": known, "gefiltert": filtered, "zusammengefuehrt": merged}

    def add(self, raw_hits: list, register: list[dict], today: datetime.date,
            own_portals: frozenset[str] = frozenset(), agencies: tuple[str, ...] = (),
            check=lambda title, text: "", saved_in: str = SAVED_IN[SIE]) -> dict:
        """Store new hits; the same job from another portal only adds its link. `agencies`: more from the profile (G34).

        `check` is the pre-check by fixed rules (G33): its reason stays on the hit as `vorpruefung`, the hit stays too.
        """
        rejected, new, merged = [], 0, 0
        with _LOCK:
            stored = self.all()
            by_key = {key(h) for h in stored}
            for raw in raw_hits[:MAX_HITS_PER_CALL]:
                try:
                    hit = validate(raw, own_portals)
                except ValueError as error:
                    rejected.append(str(error))
                    continue
                if key(hit) in by_key:
                    continue
                twin = _find_twin(hit, stored)
                if twin is not None:
                    updated = _with_link(stored, twin, hit)
                    if updated is not None:
                        stored, merged = updated, merged + 1
                    continue
                text = hit.pop("text")
                entry = {"id": hit_id(hit), **hit, "gefunden_am": today.isoformat(), "zustand": "neu"}
                hint = company_hint(entry, register) or agency_hint(entry, register, agencies, saved_in)
                if hint:
                    entry["hinweis"] = hint
                reason = check(entry["stelle"], text) if text else ""
                if reason:
                    entry["vorpruefung"] = reason
                if text:
                    schreibe_atomar(self._text_path(entry["id"]), text.encode("utf-8"))
                stored.append(entry)
                by_key.add(key(hit))
                new += 1
            self._write(stored)
        return {"neu": new, "zusammengefuehrt": merged, "abgelehnt": rejected}

    def update(self, wanted: str, **fields) -> dict:
        if "zustand" in fields and fields["zustand"] not in STATES:
            raise ValueError(f"zustand muss eines von {', '.join(STATES)} sein")
        with _LOCK:
            stored = self.all()
            for index, hit in enumerate(stored):
                if hit["id"] == wanted:
                    stored[index] = {**hit, **fields}
                    self._write(stored)
                    return stored[index]
        raise KeyError(f"Treffer {wanted!r} nicht gefunden")

    def update_many(self, fields_by_id: dict[str, dict]) -> list[dict]:
        """One write for many hits; a hit that is gone by now is left out."""
        with _LOCK:
            stored = self.all()
            updated = [{**hit, **fields_by_id.get(hit["id"], {})} for hit in stored]
            self._write(updated)
        return [hit for hit in updated if hit["id"] in fields_by_id]

    def settings(self) -> dict:
        raw = lies_yaml(self.folder / SETTINGS_FILE, {})
        raw = raw if isinstance(raw, dict) else {}
        stars = raw.get("beruf_sterne") if isinstance(raw.get("beruf_sterne"), dict) else {}
        clean = {str(k): v for k, v in stars.items() if type(v) is int and 1 <= v <= MAX_STARS}
        return {"auto_bewerten": raw.get("auto_bewerten") is not False, "zuschauen": raw.get("zuschauen") is True, "beruf_sterne": clean,
                "sortierung": raw.get("sortierung") if raw.get("sortierung") in ORDERS else ORDERS[0],
                OWN_SITES: raw.get(OWN_SITES) if isinstance(raw.get(OWN_SITES), list) else [],
                PORTALS_OFF: [p for p in raw[PORTALS_OFF] if isinstance(p, str)] if isinstance(raw.get(PORTALS_OFF), list) else None}

    def _save_settings(self, settings: dict) -> dict:
        schreibe_yaml(self.folder / SETTINGS_FILE, settings)
        return settings

    def set_own_sites(self, addresses: list[str]) -> dict:
        with _LOCK:
            return self._save_settings({**self.settings(), OWN_SITES: addresses})

    def set_auto_rating(self, enabled: bool) -> dict:
        with _LOCK:
            return self._save_settings({**self.settings(), "auto_bewerten": enabled})

    def set_portals_off(self, portals: list[str]) -> dict:
        with _LOCK:
            return self._save_settings({**self.settings(), PORTALS_OFF: portals})

    def set_watching(self, enabled: bool) -> dict:
        with _LOCK:
            return self._save_settings({**self.settings(), "zuschauen": enabled})

    def set_order(self, order: str) -> dict:
        if order not in ORDERS:
            raise ValueError(f"Sortierung: {', '.join(ORDERS)}.")
        with _LOCK:
            return self._save_settings({**self.settings(), "sortierung": order})

    def set_own_stars(self, wanted: str, stars: int) -> dict:
        """The person's own rating of one hit, 1 to 5; 0 takes it away. The grade of the AI stays as it is."""
        if type(stars) is not int or not 0 <= stars <= MAX_STARS:
            raise ValueError(f"Sterne: 0 bis {MAX_STARS}.")
        with _LOCK:
            stored = self.all()
            hit = next((h for h in stored if h["id"] == wanted), None)
            if hit is None:
                raise KeyError(f"Treffer {wanted!r} nicht gefunden")
            rest = {key: value for key, value in hit.items() if key != OWN_STARS}
            changed = {**rest, OWN_STARS: stars} if stars else rest
            self._write([changed if h["id"] == wanted else h for h in stored])
            return changed

    def set_stars(self, profession: str, stars: int) -> dict:
        """The person's own rating of a profession, 1 to 5; 0 takes it away."""
        name = bounded_text(profession, "Beruf", required=True)
        if type(stars) is not int or not 0 <= stars <= MAX_STARS:
            raise ValueError(f"Sterne: 0 bis {MAX_STARS}.")
        with _LOCK:
            current = self.settings()
            others = {k: v for k, v in current["beruf_sterne"].items() if k != name}
            return self._save_settings({**current, "beruf_sterne": {**others, **({name: stars} if stars else {})}})

    def save_run(self, summary: dict, today: datetime.date) -> dict:
        """The run as the page shows it; each portal without a problem also counts as its last success (G32)."""
        succeeded = {name: today.isoformat() for name, portal in summary.get("portale", {}).items() if not portal.get("problem")}
        run = {"datum": today.isoformat(), **summary, LAST_SUCCESS: {**self.last_success(), **succeeded}}
        schreibe_yaml(self.folder / RUN_FILE, run)
        return run

    def last_success(self) -> dict[str, str]:
        """Portal → date of its last run without a problem."""
        found = (self.last_run() or {}).get(LAST_SUCCESS)
        return {str(k): str(v) for k, v in found.items()} if isinstance(found, dict) else {}

    def last_run(self) -> dict | None:
        run = lies_yaml(self.folder / RUN_FILE, None)
        return run if isinstance(run, dict) else None
