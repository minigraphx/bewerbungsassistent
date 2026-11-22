"""Known jobs by their content (G109, #385): a hit with a new id and link may be a job the person knows already.

A sure match has the same company key, a close title (`hits._close_title`), the place as `hits._find_twin` compares
it and the pensum as `hits._same_pensum`; without a company name nothing matches, and a trial apprenticeship never
matches the apprenticeship. A register entry or a discarded hit that is surely the same job takes the new ad as a
repost (`reposts`): the hit is not new and needs neither its text nor the AI. A recruiter hides the company, so its
ad is surely the same only when the same recruiter sends the same title, place and pensum again; behind another
company's name it is only a suggestion (`suspects`), and the person decides.

Ads of one portal count as one job only when company, title, place and pensum are all the same (`is_same_ad`).
"""
import dataclasses
import datetime
import pathlib

import hits
import reposts
from dateien import lies_yaml, schreibe_yaml

RUN_FILE = "wieder-offen.yaml"  # what the screening of the open run recognized, until the run ends
SAME_ADS_FILE = "gleiche-offen.yaml"  # links of the same ad seen again before the first one was stored
IN_REGISTER, DISCARDED = "bewerbungen", "verworfen"
DISCARDED_STATE = "verworfen"
MAX_SUSPECTS = 2
MAX_WAITING_LINKS = 50


def _companies(record: dict) -> set[str]:
    return {key for key in (hits.company_key(record.get("firma_schluessel") or ""), hits.company_key(record.get("firma") or ""))
            if key}


def _is_trial(record: dict) -> bool:
    return hits.is_trial(record.get("link") or "", record.get("art") or "")


def _title(record: dict) -> str:
    return record.get("beruf") or record.get("stelle") or ""


def _known_company(hit: dict) -> str:
    company = hits.company_key(hit["firma"])
    return "" if company in ("", "unbekannt") else company


def is_same_ad(hit: dict, other: dict) -> bool:
    """Company, title, place and pensum all the same; a portal says nothing here, the caller compares it."""
    company = _known_company(hit)
    return (bool(company) and company in _companies(other) and _is_trial(hit) == _is_trial(other)
            and hits._title_key(_title(hit)) == hits._title_key(_title(other))
            and hits._places(hit.get("ort", "")) == hits._places(other.get("ort", ""))
            and hits._title_pensum(hit["stelle"]) == hits._title_pensum(other.get("stelle", ""))
            and hits._pensum_range(hit.get("pensum") or hit["stelle"]) == hits._pensum_range(other.get("pensum") or other.get("stelle", "")))


def is_same_job(hit: dict, record: dict, agencies: tuple[str, ...]) -> bool:
    """Surely the job of `record`, a register entry or a stored hit."""
    company = _known_company(hit)
    if not company or company not in _companies(record) or _is_trial(hit) != _is_trial(record) or not record.get("stelle"):
        return False
    if hits._is_agency(hit["firma"], (*hits.AGENCIES, *agencies)):
        return is_same_ad(hit, record)
    places, theirs = hits._places(hit.get("ort", "")), hits._places(record.get("ort", ""))
    return (hits._close_title(_title(hit), _title(record)) and (not places or not theirs or bool(places & theirs))
            and hits._same_pensum(hit, record))


def in_register(hit: dict, register: list[dict], agencies: tuple[str, ...]) -> dict | None:
    """The entry this hit surely is; an open one first, then any, since a job with a rejection is not new either."""
    same = [entry for entry in register if isinstance(entry.get("id"), str) and is_same_job(hit, entry, agencies)]
    return next((entry for entry in same if entry.get("status") not in hits.CLOSED), same[0] if same else None)


def discarded(hit: dict, stored: list[dict], agencies: tuple[str, ...]) -> dict | None:
    return next((other for other in stored if other.get("zustand") == DISCARDED_STATE and is_same_job(hit, other, agencies)), None)


def suspects(hit: dict, register: list[dict], agencies: tuple[str, ...]) -> list[dict]:
    """The open entries a recruiter's ad may be (G34), each with id and title, for the link beside the hit."""
    return [{"id": entry["id"], "stelle": entry["stelle"]}
            for entry in hits.agency_suspects(hit, register, agencies)[:MAX_SUSPECTS] if isinstance(entry.get("id"), str)]


@dataclasses.dataclass(frozen=True)
class Screening:
    """What one screening has learned so far; every step gives a new one."""
    stored: list[dict]
    links: frozenset[str]  # comparable links known by now, so an ad that comes again in the listing is known at once
    reposts: dict[str, list[dict]] = dataclasses.field(default_factory=dict)  # register entry id → its new reposts
    counts: dict[str, int] = dataclasses.field(default_factory=dict)
    waiting: tuple[tuple[str, dict], ...] = ()  # (key of the first ad, link of the same ad seen again)
    asked: tuple[dict, ...] = ()  # the hits this screening asks the text of
    merged: int = 0
    changed: bool = False  # stored hits to be written


def known_links(register: list[dict], stored: list[dict]) -> frozenset[str]:
    links = [*(b.get("link") for b in register), *(link for b in register for link in reposts.links(b)),
             *(h.get("link") for h in stored), *(o["link"] for h in stored for o in h.get("weitere", [])),
             *(link for h in stored for link in reposts.links(h))]
    return frozenset(hits.comparable_link(link, any_fragment=True) for link in links if link)


def _plus(counts: dict[str, int], name: str) -> dict[str, int]:
    return {**counts, name: counts.get(name, 0) + 1}


def asking(seen: Screening, hit: dict) -> Screening:
    return dataclasses.replace(seen, asked=(*seen.asked, hit))


def recognized(hit: dict, seen: Screening, register: list[dict], agencies: tuple[str, ...],
               today: datetime.date) -> Screening | None:
    """The screening after a hit it knows: a saved or discarded job, a twin, the same ad again; None for a new one."""
    links = seen.links | {hits.comparable_link(hit["link"], any_fragment=True)}
    entry = in_register(hit, register, agencies)
    if entry is not None:
        noted = [*seen.reposts.get(entry["id"], []), reposts.record(hit, today)]
        return dataclasses.replace(seen, links=links, reposts={**seen.reposts, entry["id"]: noted}, counts=_plus(seen.counts, IN_REGISTER))
    old = discarded(hit, seen.stored, agencies)
    if old is not None:
        stored = [reposts.appended(h, [reposts.record(hit, today)]) if h is old else h for h in seen.stored]
        return dataclasses.replace(seen, stored=stored, links=links, counts=_plus(seen.counts, DISCARDED), changed=True)
    twin = hits._find_twin(hit, seen.stored)
    if twin is not None:
        updated = hits._with_link(seen.stored, twin, hit, today)
        return seen if updated is None else dataclasses.replace(seen, stored=updated, links=links, merged=seen.merged + 1, changed=True)
    first = next((other for other in seen.asked if other["portal"] == hit["portal"] and is_same_ad(hit, other)), None)
    if first is None:
        return None
    link = {"portal": hit["portal"], "link": hit["link"], "datum": ad_day(hit, today)}
    return dataclasses.replace(seen, links=links, waiting=(*seen.waiting, (hits.key(first), link)))


def ad_day(hit: dict, today: datetime.date) -> str:
    """The day the portal shows the ad since, or today when it says nothing."""
    age = hit.get("alter_tage")
    return (today - datetime.timedelta(days=age) if isinstance(age, int) else today).isoformat()


def note_run(folder: pathlib.Path, counts: dict[str, int]) -> None:
    """Add what one screening recognized to the open run; the caller holds the lock of the hits."""
    if not any(counts.values()):
        return
    current = _counts(lies_yaml(folder / RUN_FILE, {}))
    schreibe_yaml(folder / RUN_FILE, {name: current.get(name, 0) + counts.get(name, 0) for name in (IN_REGISTER, DISCARDED)})


def _counts(raw) -> dict[str, int]:
    if not isinstance(raw, dict):
        return {}
    return {name: raw[name] for name in (IN_REGISTER, DISCARDED) if type(raw.get(name)) is int and raw[name] >= 0}


def close_run(folder: pathlib.Path) -> dict[str, int]:
    """What the run recognized, for the hint after it; the waiting files are empty afterwards."""
    counts = _counts(lies_yaml(folder / RUN_FILE, {}))
    for name in (RUN_FILE, SAME_ADS_FILE):
        if (folder / name).is_file():
            schreibe_yaml(folder / name, {})
    return counts if any(counts.values()) else {}


def note_same_ads(folder: pathlib.Path, waiting: list[tuple[str, dict]]) -> None:
    """Links of an ad seen again in one listing, by the key of its first ad, until that one is stored."""
    current = _waiting(lies_yaml(folder / SAME_ADS_FILE, {}))
    merged = dict(current)
    for first, link in waiting:
        known = merged.get(first, [])
        if all(entry["link"] != link["link"] for entry in known):
            merged = {**merged, first: [*known, link][:MAX_WAITING_LINKS]}
    schreibe_yaml(folder / SAME_ADS_FILE, merged)


def _waiting(raw) -> dict[str, list[dict]]:
    if not isinstance(raw, dict):
        return {}
    return {str(first): [link for link in links if isinstance(link, dict) and isinstance(link.get("link"), str)]
            for first, links in raw.items() if isinstance(links, list)}


def take_same_ads(folder: pathlib.Path, first: str) -> list[dict]:
    """The waiting links of the ad stored now; they are gone from the file afterwards."""
    current = _waiting(lies_yaml(folder / SAME_ADS_FILE, {}))
    if first not in current:
        return []
    schreibe_yaml(folder / SAME_ADS_FILE, {name: links for name, links in current.items() if name != first})
    return current[first]
