"""What could be cut when a document stays over its page limit after tightening (G49, G51).

Only names candidates for the person to decide; nothing here removes content. For a CV: the points of the stations
with the most of them, older stations first, then sections a reader misses least. For a letter: its longest paragraph.
"""
from anschreiben import absaetze

MAX_NAMED = 4
MAX_STATIONS = 2
MIN_POINTS = 2  # a station with a single point keeps it: cutting it saves too little
OPENING_WORDS = 5
# Sections a CV can do without, in the order they are offered; keys of the JSON Resume schema
OPTIONAL_SECTIONS = (("more-projects", "Weitere Projekte"), ("interests", "Interessen"), ("volunteer", "Engagement"),
                     ("awards", "Auszeichnungen"))


def _points(station: dict) -> int:
    highlights = station.get("highlights")
    return len(highlights) if isinstance(highlights, list) else 0


def _end(station: dict) -> str:
    """For sorting: a station without end runs until today, so it comes last among equals."""
    return str(station.get("endDate") or "9999")


def _station_cuts(cv: dict) -> list[str]:
    stations = [s for s in cv.get("work") or [] if isinstance(s, dict) and _points(s) >= MIN_POINTS]
    ordered = sorted(stations, key=lambda s: (-_points(s), _end(s)))[:MAX_STATIONS]
    named = (", ".join(str(s[key]) for key in ("position", "name") if s.get(key)) for s in ordered)
    return [f"Stichpunkte bei «{name}» ({_points(s)})" for name, s in zip(named, ordered)]


def _has_section(cv: dict, key: str) -> bool:
    if key == "more-projects":
        return any(isinstance(p, dict) and p.get("group") == "more" for p in cv.get("projects") or [])
    return bool(cv.get(key))


def for_cv(cv: dict) -> list[str]:
    """Candidates to cut from a CV, as the check before sending names them."""
    sections = [f"Abschnitt «{label}»" for key, label in OPTIONAL_SECTIONS if _has_section(cv, key)]
    return (_station_cuts(cv) + sections)[:MAX_NAMED]


def for_letter(text: str) -> list[str]:
    """The candidate to cut from a letter: its longest paragraph, named by its first words."""
    paragraphs = absaetze(text or "")
    if not paragraphs:
        return []
    longest = max(paragraphs, key=len)
    words = longest.split()
    opening = " ".join(words[:OPENING_WORDS]) + (" …" if len(words) > OPENING_WORDS else "")
    return [f"der längste Absatz («{opening}»)"]
