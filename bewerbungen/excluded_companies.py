"""Companies the search no longer shows (#226, G65): their hits are screened out and hidden from the list.

The list is a file in the data folder, one name per entry as the person wrote it; every change leaves drafts before
and after. Names match by `hits.company_key`, like the page Firmen, so "Muster Bau" also catches "Muster Bau AG".
Taking a company back shows its listed hits again: hiding happens on reading, nothing is deleted. Neither the
extension nor Claude reach the routes (allow lists in desktop/native_host.py and desktop/mcp_tools.py).
"""
import pathlib

from dateien import lies_yaml, schreibe_yaml
from hits import MAX_FIELD, company_key

FILE = "firmen-ausgeschlossen.yaml"
HEADER = "# Firmen, deren Inserate die Suche nicht mehr zeigt, geschrieben vom Bewerbungsbegleiter\n"
UNKNOWN_COMPANY = "unbekannt"  # what hits.validate stores without a company
MAX_COMPANIES = 100
NOT_A_LIST = "Firmen: bitte als Liste senden."
NOT_A_NAME = "„{name}“ ist kein Firmenname."
NO_NAME = "Bitte eine Firma angeben."
TOO_LONG = "Ein Firmenname hat höchstens {limit} Zeichen."
TOO_MANY = "Höchstens {limit} Firmen."
NOT_LISTED = "Diese Firma ist nicht ausgeschlossen."


def key_of(name) -> str:
    """The key a company is grouped and matched by; empty without a usable name."""
    key = company_key(name if isinstance(name, str) else "")
    return "" if key in ("", UNKNOWN_COMPANY) else key


def _unique(names: list[str]) -> list[str]:
    """Names with a key, the first of each key."""
    seen: dict[str, str] = {}
    for name in names:
        seen.setdefault(key_of(name), name)
    return [name for key, name in seen.items() if key]


def _entries(names: list[str]) -> list[dict]:
    return [{"name": name, "schluessel": key_of(name)} for name in names]


def _stored(data_dir: pathlib.Path) -> list[str]:
    """The names in the file; the file is data the person may have edited, so odd entries are left out."""
    raw = lies_yaml(data_dir / FILE, [])
    listed = raw if isinstance(raw, list) else []
    return _unique([" ".join(value.split())[:MAX_FIELD] for value in listed if isinstance(value, str)])


def listing(data_dir: pathlib.Path) -> list[dict]:
    return _entries(_stored(data_dir))


def keys(data_dir: pathlib.Path) -> frozenset[str]:
    return frozenset(key_of(name) for name in _stored(data_dir))


def shown(hits: list[dict], excluded: frozenset[str]) -> list[dict]:
    """The hits whose company is not excluded."""
    return [hit for hit in hits if key_of(hit.get("firma")) not in excluded] if excluded else hits


def _name(value) -> str:
    """One name the person entered, checked; blank lines are no names."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(NO_NAME)
    name = " ".join(value.split())
    if len(name) > MAX_FIELD:
        raise ValueError(TOO_LONG.format(limit=MAX_FIELD))
    if not key_of(name):
        raise ValueError(NOT_A_NAME.format(name=name))
    return name


def checked(raw) -> list[str]:
    """The whole list as the person edited it on Suche einstellen; blank lines and repeats are dropped."""
    if not isinstance(raw, list):
        raise ValueError(NOT_A_LIST)
    names = _unique([_name(value) for value in raw if not (isinstance(value, str) and not value.strip())])
    if len(names) > MAX_COMPANIES:
        raise ValueError(TOO_MANY.format(limit=MAX_COMPANIES))
    return names


def _write(k, names: list[str], description: str) -> list[dict]:
    path = k.daten / FILE
    k.mit_entwurf(path, f"Ausgeschlossene Firmen: {description}", lambda: schreibe_yaml(path, names, HEADER))
    return _entries(names)


def replace(k, raw) -> list[dict]:
    return _write(k, checked(raw), "Liste geändert")


def add(k, raw) -> dict:
    """Exclude one company, from a hit, from Firmen or from an application; a company already listed stays once."""
    name = _name(raw)
    current = _stored(k.daten)
    if key_of(name) not in {key_of(other) for other in current}:
        _write(k, checked([*current, name]), name)
    return {"schluessel": key_of(name), "ausgeschlossen": True}


def remove(k, key) -> dict:
    """Show the company again; its hits come back to the list."""
    current = _stored(k.daten)
    kept = [name for name in current if key_of(name) != key]
    if len(kept) == len(current):
        raise KeyError(NOT_LISTED)
    removed = next(name for name in current if key_of(name) == key)
    _write(k, kept, f"{removed} wieder gezeigt")
    return {"schluessel": key, "ausgeschlossen": False}
