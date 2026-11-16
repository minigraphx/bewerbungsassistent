"""What could be cut when a document stays over its page limit after tightening (G49, G51, G92).

Only names candidates for the person to decide; nothing here touches the person's files. For a CV: about half the
points of the stations with the most of them, older stations first, then sections a reader misses least. For a
letter: its longest paragraph.

What the person ticks is stored per application (bewerbungen/<id>/kuerzungen.yaml) as records: `stichpunkte`, the
stations by their fields with the points they keep, and `abschnitte`, the keys of sections left out. `apply` takes them
out of a copy of the tailored CV; the builds take the file with `--kuerzungen`.
"""
import dataclasses
import hashlib
import json

from tailor import STATION_FIELDS, same_station, tailor

MAX_NAMED = 4
MAX_STATIONS = 2
MIN_POINTS = 2  # a station with a single point keeps it: cutting it saves too little
OPENING_WORDS = 5
ID_LENGTH = 12
UNTIL_TODAY = "heute"
POINTS, SECTION = "stichpunkte", "abschnitt"  # the kinds of cut, as prefix of their id
STORED_POINTS, STORED_SECTIONS, KEEP = "stichpunkte", "abschnitte", "behalten"
# Sections a CV can do without, in the order they are offered; keys of the JSON Resume schema
OPTIONAL_SECTIONS = (("more-projects", "Weitere Projekte"), ("interests", "Interessen"), ("volunteer", "Engagement"),
                     ("awards", "Auszeichnungen"))
SECTION_NAMES = dict(OPTIONAL_SECTIONS)


@dataclasses.dataclass(frozen=True)
class Cut:
    id: str
    text: str  # what goes, as the check names it
    station: dict | None = None  # the fields that find the station
    keep: int | None = None  # the points the station keeps
    section: str | None = None


def _points(station: dict) -> int:
    highlights = station.get("highlights")
    return len(highlights) if isinstance(highlights, list) else 0


def _end(station: dict) -> str:
    """For sorting: a station without end runs until today, so it comes last among equals."""
    return str(station.get("endDate") or "9999")


def _year(value) -> str:
    return str(value)[:4] if value else ""


def _years(station: dict) -> str:
    start, end = _year(station.get("startDate")), _year(station.get("endDate")) or UNTIL_TODAY
    return f" ({start}–{end})" if start else ""


def _fields(station: dict) -> dict:
    return {key: station.get(key) for key in STATION_FIELDS}


def _station_id(fields: dict) -> str:
    text = json.dumps([str(fields.get(key) or "") for key in STATION_FIELDS], ensure_ascii=False)
    return f"{POINTS}:{hashlib.sha256(text.encode('utf-8')).hexdigest()[:ID_LENGTH]}"


def _station_name(station: dict) -> str:
    return ", ".join(str(station[key]) for key in ("position", "name") if station.get(key))


def _points_text(count: int, station: dict) -> str:
    noun = "Stichpunkt" if count == 1 else "Stichpunkte"
    return f"{count} {noun} bei «{_station_name(station)}»{_years(station)}"


def _station_cuts(cv: dict) -> list[Cut]:
    stations = [s for s in cv.get("work") or [] if isinstance(s, dict) and _points(s) >= MIN_POINTS]
    ordered = sorted(stations, key=lambda s: (-_points(s), _end(s)))[:MAX_STATIONS]
    cuts = []
    for station in ordered:
        going = (_points(station) + 1) // 2
        cuts.append(Cut(_station_id(station), _points_text(going, station), _fields(station),
                        keep=_points(station) - going))
    return cuts


def _has_section(cv: dict, key: str) -> bool:
    if key == "more-projects":
        return any(isinstance(p, dict) and p.get("group") == "more" for p in cv.get("projects") or [])
    return bool(cv.get(key))


def _section_cut(key: str) -> Cut:
    return Cut(f"{SECTION}:{key}", f"Abschnitt «{SECTION_NAMES[key]}»", section=key)


def options(cv: dict) -> list[Cut]:
    """Candidates to cut from a CV, as the check before sending offers them; the first is the one to suggest."""
    sections = [_section_cut(key) for key, _ in OPTIONAL_SECTIONS if _has_section(cv, key)]
    return (_station_cuts(cv) + sections)[:MAX_NAMED]


def _records(stored) -> list[dict]:
    """The stored station records that can be applied; anything else is left out."""
    records = stored.get(STORED_POINTS) if isinstance(stored, dict) else None
    return [r for r in records or [] if isinstance(r, dict) and isinstance(r.get(KEEP), int)
            and not isinstance(r.get(KEEP), bool) and r[KEEP] >= 0] if isinstance(records, list) else []


def _sections(stored) -> list[str]:
    sections = stored.get(STORED_SECTIONS) if isinstance(stored, dict) else None
    return [s for s in sections if s in SECTION_NAMES] if isinstance(sections, list) else []


def chosen(cuts: list[Cut], stored) -> dict:
    """The stored cuts with `cuts` added; a station cut again replaces its record, so it keeps fewer points."""
    records = _records(stored)
    for cut in (c for c in cuts if c.station is not None):
        record = {**{k: str(v) if v is not None else None for k, v in cut.station.items()}, KEEP: cut.keep}
        records = [r for r in records if not same_station(r, cut.station)] + [record]
    sections = _sections(stored) + [c.section for c in cuts if c.section and c.section not in _sections(stored)]
    return {**(stored if isinstance(stored, dict) else {}), STORED_POINTS: records, STORED_SECTIONS: sections}


def _without_sections(cv: dict, sections: list[str]) -> dict:
    out = {key: value for key, value in cv.items() if key not in sections}
    if "more-projects" in sections and isinstance(cv.get("projects"), list):
        out["projects"] = [p for p in cv["projects"] if not (isinstance(p, dict) and p.get("group") == "more")]
    return out


def apply(cv: dict, stored) -> dict:
    """A copy of `cv` without what `stored` leaves out; broken entries change nothing."""
    limits = [{**{key: r.get(key) for key in STATION_FIELDS}, "max": r[KEEP]} for r in _records(stored)]
    return _without_sections(tailor(cv, {"max_highlights_per_station": limits}), _sections(stored))


def left_out(cv: dict, stored) -> list[Cut]:
    """What `stored` leaves out of `cv` (the CV before the cuts), named as when it was offered."""
    found = []
    for record in _records(stored):
        station = next((s for s in cv.get("work") or [] if same_station(s, record)), None)
        if station is not None and _points(station) > record[KEEP]:
            found.append(Cut(_station_id(record), _points_text(_points(station) - record[KEEP], station),
                             _fields(station), keep=record[KEEP]))
    return found + [_section_cut(key) for key in _sections(stored)]


def without(stored, cut_id: str) -> dict:
    """The stored cuts without the one `cut_id` names."""
    records = [r for r in _records(stored) if _station_id(r) != cut_id]
    sections = [s for s in _sections(stored) if f"{SECTION}:{s}" != cut_id]
    return {**(stored if isinstance(stored, dict) else {}), STORED_POINTS: records, STORED_SECTIONS: sections}


def for_letter(text: str) -> list[str]:
    """The candidate to cut from a letter: its longest paragraph, named by its first words."""
    from anschreiben import absaetze  # here, since build.py imports this module and anschreiben imports build
    paragraphs = absaetze(text or "")
    if not paragraphs:
        return []
    longest = max(paragraphs, key=len)
    words = longest.split()
    opening = " ".join(words[:OPENING_WORDS]) + (" …" if len(words) > OPENING_WORDS else "")
    return [f"der längste Absatz («{opening}»)"]
