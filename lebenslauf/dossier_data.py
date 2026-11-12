"""Data extensions of the dossier (docs/design/dossier.md), read and checked before Typst sees them.

Every function returns new values and leaves its input alone. Levels are never invented: an entry without one
stays `None`, and the theme draws the empty dashed form for it only when its group has a level elsewhere.
"""
import datetime
import re
from collections.abc import Iterable

MAX_LEVEL = 6
CEFR = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}
MAX_MONOGRAM = 3
MAX_STEPS = 6
TIMELINE_YEARS = 15
MIN_TICK_GAP = 3
APPLICATION_AS = {"de": "Bewerbung als", "en": "Application as"}
DOSSIER_FIELDS = {"lebenslauf", "anschreiben", "gruss", "dank", "kennzahlen", "anlagen"}
# The initials as written under basics, quoted or not; for files from before #248, where NO was read as False
MONOGRAM_FIELD = re.compile(r"^[ \t]+x-monogramm[ \t]*:[ \t]*([\"']?)(?P<value>[^\W\d_]{1,3})\1[ \t]*(?:#.*)?$", re.MULTILINE)


def parse_level(value, where: str) -> int | None:
    """A level 1–6, also written as A1–C2; missing is None."""
    if value is None:
        return None
    if isinstance(value, str) and value.strip().upper() in CEFR:
        return CEFR[value.strip().upper()]
    if isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= MAX_LEVEL:
        return value
    raise ValueError(f"{where}: Niveau muss 1 bis 6 oder A1 bis C2 sein, nicht {value!r}")


def _keyword(value, where: str) -> dict:
    if isinstance(value, str):
        return {"name": value, "level": None}
    if isinstance(value, dict) and isinstance(value.get("name"), str) and value["name"].strip():
        return {"name": value["name"], "level": parse_level(value.get("level"), where)}
    raise ValueError(f"{where}: ein Stichwort ist Text oder {{name, level}}, nicht {value!r}")


def _with_graphic(items: list[dict]) -> bool:
    return any(item["level"] is not None for item in items)


def skill_groups(skills: Iterable[dict]) -> list[dict]:
    """Skills per group; a group shows the level graphic as soon as one of its keywords has a level."""
    groups = []
    for group in skills or []:
        name = group.get("name", "")
        items = [_keyword(k, f"skills {name}") for k in group.get("keywords") or []]
        groups.append({"name": name, "graphic": _with_graphic(items), "items": items})
    return groups


def language_group(languages: Iterable[dict]) -> dict:
    """Languages with `x-level`; the fluency text always stays."""
    items = [{"language": entry.get("language", ""), "fluency": entry.get("fluency"),
              "level": parse_level(entry.get("x-level"), f"languages {entry.get('language', '')}")}
             for entry in languages or []]
    return {"graphic": _with_graphic(items), "items": items}


def with_written_monogram(cv: dict, text: str) -> dict:
    """cv with the initials as cv.yaml writes them, when YAML 1.1 read them as something else (NO as False, #248)."""
    basics = cv.get("basics") if isinstance(cv.get("basics"), dict) else None
    if basics is None or "x-monogramm" not in basics or isinstance(basics["x-monogramm"], str):
        return cv
    found = MONOGRAM_FIELD.search(text)
    return {**cv, "basics": {**basics, "x-monogramm": found.group("value")}} if found else cv


def monogram(basics: dict) -> str:
    """Initials for the mark: `x-monogramm` (1–3 letters) or first and last word of the name."""
    own = basics.get("x-monogramm")
    if own is not None:
        if not isinstance(own, str) or not own.isalpha() or not 1 <= len(own) <= MAX_MONOGRAM:
            raise ValueError(f"basics.x-monogramm muss 1 bis {MAX_MONOGRAM} Buchstaben haben, nicht {own!r}")
        return own
    words = str(basics.get("name") or "").split()
    if not words:
        return ""
    ends = words if len(words) == 1 else [words[0], words[-1]]
    return "".join(word[0] for word in ends).upper()


def interests(items: Iterable[dict], catalogue: set[str]) -> list[dict]:
    """Interests with an optional icon name from the catalogue; without one only the word shows."""
    result = []
    for item in items or []:
        icon = item.get("x-icon")
        if icon is not None and icon not in catalogue:
            raise ValueError(f"interests {item.get('name', '')}: x-icon {icon!r} ist unbekannt; "
                             f"möglich sind {', '.join(sorted(catalogue))}")
        result.append({"name": item.get("name", ""), "icon": icon})
    return result


def _text(value) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def letter_heading(letter: dict, language: str) -> dict:
    """Heading fields of the letter; company falls back to the first recipient line, the line to the subject."""
    position = _text(letter.get("stelle"))
    recipients = letter.get("empfaenger") or []
    return {
        "company": _text(letter.get("firma")) or (recipients[0] if recipients else None),
        "position": position,
        "workload": _text(letter.get("pensum")),
        "reference": _text(letter.get("referenz")),
        "intro": APPLICATION_AS[language] if position else None,
        "line": f"{APPLICATION_AS[language]} {position}" if position else letter.get("betreff"),
    }


def _optional_text(data: dict, key: str) -> str | None:
    value = data.get(key)
    if value is not None and not isinstance(value, str):
        raise ValueError(f"Dossier: {key} muss Text sein")
    return _text(value)


def _figure(value) -> dict:
    if not isinstance(value, dict) or value.get("wert") in (None, "") or not _text(value.get("text")):
        raise ValueError(f"Dossier: eine Kennzahl braucht wert und text, nicht {value!r}")
    return {"value": str(value["wert"]), "text": value["text"].strip()}


def _attachment(value) -> dict:
    if isinstance(value, str) and value.strip():
        return {"name": value.strip(), "date": None}
    if isinstance(value, dict) and _text(value.get("name")):
        date = value.get("datum")
        return {"name": value["name"].strip(), "date": str(date) if date is not None else None}
    raise ValueError(f"Dossier: eine Anlage ist Text oder {{name, datum}}, nicht {value!r}")


def _list(data: dict, key: str) -> list:
    value = data.get(key) or []
    if not isinstance(value, list):
        raise ValueError(f"Dossier: {key} muss eine Liste sein")
    return value


def dossier_pages(data: dict) -> dict:
    """Contents of the optional pages from the dossier file; a missing field drops its page."""
    if not isinstance(data, dict):
        raise ValueError("Die Dossier-Datei muss eine YAML-Zuordnung sein")
    unknown = set(data) - DOSSIER_FIELDS
    if unknown:
        raise ValueError(f"Dossier: unbekannte Felder {sorted(unknown)}; erlaubt sind {', '.join(sorted(DOSSIER_FIELDS))}")
    return {
        "greeting": _optional_text(data, "gruss"),
        "thanks": _optional_text(data, "dank"),
        "figures": [_figure(v) for v in _list(data, "kennzahlen")],
        "attachments": [_attachment(v) for v in _list(data, "anlagen")],
    }


def contact(basics: dict) -> list[str]:
    """Contact lines: address, phone, e-mail, web."""
    place = basics.get("location") or {}
    town = " ".join(str(x) for x in (place.get("postalCode"), place.get("city")) if x)
    address = ", ".join(str(x) for x in (place.get("address"), town) if x)
    return [str(x) for x in (address, basics.get("phone"), basics.get("email"), basics.get("url")) if x]


def steps_done(cv: dict) -> int:
    """Past stations for the step path of the cover, at most MAX_STEPS."""
    return min(len(cv.get("work") or []) + len(cv.get("education") or []), MAX_STEPS)


def _month(value, end: bool) -> int | None:
    """Months since year 0 for "2019-03" or 2019; a bare year starts in January and ends in December."""
    if value in (None, ""):
        return None
    parts = str(value).split("-")
    month = int(parts[1]) if len(parts) > 1 else (12 if end else 1)
    return int(parts[0]) * 12 + month - 1


def _lanes(stations: list[tuple]) -> tuple[list[int], int]:
    """A lane per station so that overlapping stations lie on top of each other."""
    ends: list[int] = []
    lanes = []
    for _, start, end, _ in stations:
        lane = next((i for i, last in enumerate(ends) if last < start), len(ends))
        ends = ends[:lane] + [end] + ends[lane + 1:]
        lanes.append(lane)
    return lanes, len(ends)


def _ticks(begin: int, total: int, today: datetime.date) -> list[dict]:
    """Year labels at the start of each year on the axis: the first, every fifth and the current one, at least
    MIN_TICK_GAP apart. An axis that holds no start of a year, as for a first job begun this year, gets its year."""
    first = -(-begin // 12)
    if first > today.year:
        return [{"year": today.year, "at": 0.0}]
    kept = [first]
    for year in range(first + 1, today.year):
        if year % 5 == 0 and year - kept[-1] >= MIN_TICK_GAP:
            kept = kept + [year]
    if today.year != kept[-1]:
        crowded = today.year - kept[-1] < MIN_TICK_GAP and len(kept) > 1
        kept = (kept[:-1] if crowded else kept) + [today.year]
    return [{"year": y, "at": round((y * 12 - begin) / total, 4)} for y in kept]


def timeline(work: Iterable[dict], today: datetime.date) -> dict:
    """Horizontal axis of the career (design Raster): bars as shares of the axis, numbered like the CV.

    The axis runs from the first start to today, at most TIMELINE_YEARS back; older stations are cut at its
    start, and those that ended before it are only marked as `earlier`.
    """
    now = today.year * 12 + today.month - 1
    stations = []
    for number, entry in enumerate(work or [], start=1):
        start = _month(entry.get("startDate"), end=False)
        if start is None or start > now:  # a job not begun yet has no place on an axis that ends today
            continue
        end = _month(entry.get("endDate"), end=True)
        stations.append((number, start, max(start, min(now if end is None else end, now)), end is None))
    if not stations:
        return {"bars": [], "ticks": [], "lanes": 0, "earlier": False}
    first = min(start for _, start, _, _ in stations)
    begin = max(first, now - TIMELINE_YEARS * 12)
    total = now + 1 - begin
    shown = sorted(((n, max(s, begin), e, c) for n, s, e, c in stations if e >= begin), key=lambda s: s[1])
    lanes, count = _lanes(shown)
    bars = [{"number": n, "from": round((s - begin) / total, 4), "to": round((e + 1 - begin) / total, 4),
             "lane": lane, "current": c} for (n, s, e, c), lane in zip(shown, lanes)]
    return {"bars": sorted(bars, key=lambda b: b["number"]), "ticks": _ticks(begin, total, today),
            "lanes": count, "earlier": first < begin}


DURATION_UNITS = {"de": ("J.", "M."), "en": ("yrs", "mos")}


def duration(entry: dict, today: datetime.date, language: str) -> str | None:
    """Length of a station as "7 J. 8 M.", from its dates up to today when it runs on; None without a start."""
    start = _month(entry.get("startDate"), end=False)
    if start is None:
        return None
    end = _month(entry.get("endDate"), end=True)
    now = today.year * 12 + today.month - 1
    months = max(min(now if end is None else end, now) - start + 1, 1)
    years, rest = divmod(months, 12)
    year_unit, month_unit = DURATION_UNITS[language]
    parts = ([f"{years} {year_unit}"] if years else []) + ([f"{rest} {month_unit}"] if rest else [])
    return " ".join(parts)


def durations(cv: dict, today: datetime.date, language: str) -> dict:
    """Durations per station for the sections with dates, in the order of the CV."""
    return {key: [duration(entry, today, language) for entry in cv.get(key) or []]
            for key in ("work", "teaching", "education")}
