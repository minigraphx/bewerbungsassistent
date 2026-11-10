"""Data extensions of the dossier (docs/design/dossier.md), read and checked before Typst sees them.

Every function returns new values and leaves its input alone. Levels are never invented: an entry without one
stays `None`, and the theme draws the empty dashed form for it only when its group has a level elsewhere.
"""
from collections.abc import Iterable

MAX_LEVEL = 6
CEFR = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}
MAX_MONOGRAM = 3
MAX_STEPS = 6
APPLICATION_AS = {"de": "Bewerbung als", "en": "Application as"}
DOSSIER_FIELDS = {"lebenslauf", "anschreiben", "gruss", "dank", "kennzahlen", "anlagen"}


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
