"""Hits of the job search in the browser (MIN-339): checked, stored and offered to the person.

The extension sends what it found on the portals. Hits are kept apart from the register in
`suche/treffer.yaml`, ad texts in `suche/texte/`; the person rates them, takes them over into the register
or discards them. The register stays the only source for applications; this file only prevents that the
same hit comes again.
"""
import dataclasses
import datetime
import hashlib
import pathlib
import re
import threading
import urllib.parse

from dateien import lies_yaml, schreibe_atomar, schreibe_yaml
from register import slug

FOLDER = "suche"
HITS_FILE = "treffer.yaml"
RUN_FILE = "letzte-suche.yaml"
SETTINGS_FILE = "einstellungen.yaml"
MAX_STARS = 5
TEXTS = "texte"
DOMAINS = {"job-room": "job-room.ch", "jobs.ch": "jobs.ch", "jobscout24": "jobscout24.ch", "ictjobs": "ictjobs.ch",
           "LENA": "berufsberatung.ch", "yousty": "yousty.ch"}
STATES = ("neu", "uebernommen", "verworfen")
MAX_FIELD = 200
MAX_ID = 200
MAX_TEXT = 30_000
MAX_HITS_PER_CALL = 100
LEGAL_FORMS = {"ag", "gmbh", "sa", "sarl", "sagl", "ltd", "llc", "inc", "kg", "co", "se", "plc", "bv"}
TRIAL = "Schnupperlehre"
CLOSED = {"Absage", "Verworfen", "Zurückgezogen"}
_LOCK = threading.Lock()


def bounded_text(value, field: str, required: bool = False, limit: int = MAX_FIELD) -> str:
    if value is None:
        value = ""
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        raise ValueError(f"{field} muss Text sein")
    text = " ".join(str(value).split())[:limit]
    if required and not text:
        raise ValueError(f"{field} fehlt")
    return text


def _link(value, portal: str) -> str:
    link = bounded_text(value, "Link", required=True, limit=1000)
    # Browsers read "\\" as "/" and take the host before "@" differently than urlsplit: refuse both.
    if any(c in link for c in "\\@ ") or any(ord(c) < 0x20 for c in link):
        raise ValueError(f"Link gehört nicht zu {portal}")
    parts = urllib.parse.urlsplit(link)
    host = (parts.hostname or "").lower()
    domain = DOMAINS[portal]
    if parts.scheme != "https" or parts.netloc.lower() != host or not (host == domain or host.endswith("." + domain)):
        raise ValueError(f"Link gehört nicht zu {portal}")
    return link


def _age(value) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("alter_tage muss eine Zahl sein")
    return value


def validate(raw) -> dict:
    """A hit as the extension sends it, checked and bounded; the text stays separate."""
    if not isinstance(raw, dict):
        raise ValueError("Treffer muss ein Objekt sein")
    portal = raw.get("portal")
    if portal not in DOMAINS:
        raise ValueError(f"Unbekanntes Portal: {portal!r}")
    hit = {"portal": portal, "portal_id": bounded_text(raw.get("portal_id"), "portal_id", True, MAX_ID),
           "stelle": bounded_text(raw.get("stelle"), "stelle", True), "firma": bounded_text(raw.get("firma"), "firma") or "unbekannt",
           "ort": bounded_text(raw.get("ort"), "ort"), "pensum": bounded_text(raw.get("pensum"), "pensum"),
           "link": _link(raw.get("link"), portal), "alter_tage": _age(raw.get("alter_tage")),
           "art": bounded_text(raw.get("art"), "art"), "beruf": bounded_text(raw.get("beruf"), "beruf"),
           "lehrbeginn": bounded_text(raw.get("lehrbeginn"), "lehrbeginn")}
    text = raw.get("text")
    if text is not None and not isinstance(text, str):
        raise ValueError("text muss Text sein")
    return {**{k: v for k, v in hit.items() if v not in ("", None)}, "text": (text or "").strip()[:MAX_TEXT]}


def key(hit: dict) -> str:
    return f"{hit['portal']}:{hit['portal_id']}"


def hit_id(hit: dict) -> str:
    digest = hashlib.sha256(key(hit).encode("utf-8")).hexdigest()[:12]
    return f"{slug(hit['portal'])}-{digest}"


def company_key(name: str) -> str:
    words = [w for w in slug(name or "").split("-") if w and w not in LEGAL_FORMS]
    return "-".join(words)


def _job_key(hit: dict) -> str:
    """Company and job. The portals name a profession differently, so the search's own name for it counts first.

    A trial apprenticeship and an apprenticeship at one company are two offers.
    """
    return f"{company_key(hit['firma'])}|{slug(hit.get('beruf') or hit['stelle'])}|{hit.get('art') == TRIAL}"


def _places(ort: str) -> set[str]:
    return set(re.findall(r"[^\W\d_]{3,}", (ort or "").lower()))


def _find_twin(hit: dict, stored: list[dict]) -> dict | None:
    """The same job already stored from another portal: same company, title and place.

    Two ads on one portal are two jobs, and without a company name nothing is merged.
    """
    company = company_key(hit["firma"])
    if not company or company == "unbekannt":
        return None
    job, places = _job_key(hit), _places(hit.get("ort", ""))
    for other in stored:
        if other["portal"] == hit["portal"] or _job_key(other) != job:
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
        return [h for h in found if isinstance(h, dict) and isinstance(h.get("id"), str)] if isinstance(found, list) else []

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
        schreibe_yaml(self.folder / HITS_FILE, all_hits, "# Treffer der Stellensuche, geschrieben vom Bewerbungsassistenten\n")

    def screen(self, listing: list, title_exclude: tuple[str, ...], max_age: int, register: list[dict]) -> dict:
        """Which hits of a result list the extension should open for the full text.

        The same job from another portal needs no text: its link goes to the stored hit right away.
        """
        fetch, filtered, known, merged = [], [], 0, 0
        with _LOCK:
            stored = self.all()
            known_keys = {key(h) for h in stored}
            known_links = ({b.get("link") for b in register if b.get("link")} | {h.get("link") for h in stored}
                           | {o["link"] for h in stored for o in h.get("weitere", [])})
            for raw in listing[:MAX_HITS_PER_CALL * 5]:
                try:
                    hit = validate(raw)
                except ValueError:
                    continue
                if key(hit) in known_keys or hit["link"] in known_links:
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
                elif hit.get("alter_tage") is not None and hit["alter_tage"] > max_age:
                    filtered.append({"stelle": hit["stelle"], "grund": f"älter als {max_age} Tage"})
                elif key(hit) not in fetch:
                    fetch.append(key(hit))
            if merged:
                self._write(stored)
        return {"holen": fetch, "bekannt": known, "gefiltert": filtered, "zusammengefuehrt": merged}

    def add(self, raw_hits: list, register: list[dict], today: datetime.date) -> dict:
        """Store new hits; the same job from another portal only adds its link."""
        rejected, new, merged = [], 0, 0
        with _LOCK:
            stored = self.all()
            by_key = {key(h) for h in stored}
            for raw in raw_hits[:MAX_HITS_PER_CALL]:
                try:
                    hit = validate(raw)
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
                hint = company_hint(entry, register)
                if hint:
                    entry["hinweis"] = hint
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
        return {"auto_bewerten": raw.get("auto_bewerten") is not False, "zuschauen": raw.get("zuschauen") is True, "beruf_sterne": clean}

    def _save_settings(self, settings: dict) -> dict:
        schreibe_yaml(self.folder / SETTINGS_FILE, settings)
        return settings

    def set_auto_rating(self, enabled: bool) -> dict:
        with _LOCK:
            return self._save_settings({**self.settings(), "auto_bewerten": enabled})

    def set_watching(self, enabled: bool) -> dict:
        with _LOCK:
            return self._save_settings({**self.settings(), "zuschauen": enabled})

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
        run = {"datum": today.isoformat(), **summary}
        schreibe_yaml(self.folder / RUN_FILE, run)
        return run

    def last_run(self) -> dict | None:
        run = lies_yaml(self.folder / RUN_FILE, None)
        return run if isinstance(run, dict) else None
