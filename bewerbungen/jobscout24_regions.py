"""The regions of jobscout24 (G107, #380), for the line «- Regionen (jobscout24): …» under Region.

jobscout24 searches a fixed 20 km around a postcode, so nearby postcodes find the same ads again; its region filter
(`regidl`, repeated once per region) covers them in one search per term. The ids and names are jobscout24's own:
the checkboxes of «Region wählen» in the search form of https://www.jobscout24.ch/de/jobs/, read on 22.11.2026.
Only «Home Office / Remote Work» carries the shorter name of the UI/UX review; jobscout24's own name is read too.
The profile line may name a region by id, by its full name or by the name before the cantons, in any case.
"""
import re

# (id, name) in the order of jobscout24's form
REGIONS: tuple[tuple[str, str], ...] = (
    ("1", "Nordwestschweiz (AG/BL/BS/SO)"), ("2", "Region Zürich (AG/SH/ZG/ZH)"), ("3", "Region Bern (BE/FR/SO)"),
    ("13", "Mittelland (AG/BE/SO)"), ("4", "Ostschweiz (AI/AR/GL/SG/SH/TG)"),
    ("5", "Zentralschweiz (LU/NW/OW/SZ/UR/ZG)"), ("6", "Graubünden (GR)"), ("7", "Valais / Wallis (VS)"),
    ("8", "Région Lémanique (GE/VD)"), ("9", "Nord Romandie (FR/JU/JuraBE/NE)"), ("10", "Ticino (TI)"),
    ("11", "Ausland"), ("14", "Homeoffice / Remote"),
)
NAMES = dict(REGIONS)
OTHER_SPELLINGS = {"home office / remote work": "14"}  # as jobscout24 writes it
CANTONS_IN_NAME = re.compile(r"\s*\([^()]*\)$")


def _key(text: str) -> str:
    return " ".join(text.split()).lower()


_BY_KEY = {**{_key(name): id_ for id_, name in REGIONS}, **{_key(CANTONS_IN_NAME.sub("", name)): id_ for id_, name in REGIONS},
           **{id_: id_ for id_, _ in REGIONS}, **OTHER_SPELLINGS}


def region_id(entry: str) -> str | None:
    """The id of a region as the profile names it, or None for one jobscout24 does not have."""
    return _BY_KEY.get(_key(entry))


def ids(entries: tuple[str, ...] | list[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """The ids of the known entries, each once and in order, and the entries jobscout24 does not know."""
    found = [(entry, region_id(entry)) for entry in entries]
    return tuple(dict.fromkeys(id_ for _, id_ in found if id_)), tuple(entry for entry, id_ in found if not id_)


def written(entry: str) -> str:
    """The entry as the app writes it: jobscout24's name, or as it stands for a region the app does not know."""
    id_ = region_id(entry)
    return NAMES[id_] if id_ else entry


def choices(listed: list[str]) -> list[dict]:
    """Every region jobscout24 offers, then any other the profile line already has, so saving keeps it."""
    known = [{"wert": name, "name": name} for _, name in REGIONS]
    return [*known, *({"wert": entry, "name": entry} for entry in listed if not region_id(entry))]
