"""Stamm-Lebenslauf auf eine Stelle zuschneiden.

Regeln:
- Ein Eintrag oder Stichpunkt ohne `tags` ist immer dabei.
- Ein Eintrag oder Stichpunkt mit `tags` ist nur dabei, wenn er mindestens
  einen der Tags der Bewerbung trägt.
- `hide` entfernt Einträge nach Name, Titel oder Text.
- `basics` in der Bewerbungsdatei überschreibt Felder (z.B. label, summary).
- `max_highlights` begrenzt die Stichpunkte pro Station.
- `max_highlights_per_station` begrenzt sie für einzelne Stationen der Berufserfahrung (G92): eine Liste von
  `{position: …, name: …, startDate: …, max: N}`, gefunden über diese Felder als Text (ein Jahr ohne Anführungszeichen
  passt zu demselben Jahr als Text).
- `sections` überschreibt ganze Abschnitte (z.B. eine eigene Fähigkeitenliste).
- `select` wählt pro Abschnitt Stationen und ihre Reihenfolge (G17): eine Liste von Feldern wie
  `{position: …, name: …, startDate: …}`; genommen wird je Liste der erste Eintrag mit genau diesen Werten,
  jeder höchstens einmal. Ein Abschnitt, den `select` nicht nennt, bleibt; was nicht mehr passt, fällt weg.
Danach werden `tags` und `prio` entfernt; Stichpunkte werden zu reinem Text.
"""
from copy import deepcopy

META = {"tags", "prio"}


def _passt(item, tags):
    if not isinstance(item, dict):
        return True
    t = item.get("tags")
    return not t or not tags or bool(set(t) & set(tags))


def _versteckt(item, hide):
    if not hide or not isinstance(item, dict):
        return False
    werte = {str(item.get(k, "")) for k in ("name", "position", "title", "text", "language", "institution")}
    return bool(werte & set(hide))


def _bereinigen(x, tags, hide, max_hl):
    if isinstance(x, list):
        out = []
        for item in x:
            if not _passt(item, tags) or _versteckt(item, hide):
                continue
            out.append(_bereinigen(item, tags, hide, max_hl))
        return out
    if isinstance(x, dict):
        d = {k: _bereinigen(v, tags, hide, max_hl) for k, v in x.items() if k not in META}
        if "highlights" in d:
            # {text:, tags:} wird zu Text; mehrsprachige Texte ({de:, en:}) bleiben für build.waehle_sprache
            hl = [h["text"] if isinstance(h, dict) and "text" in h else h for h in d["highlights"]]
            if max_hl:
                hl = hl[:max_hl]
            d["highlights"] = hl
        return d
    return x


def _fits(item, fields):
    return isinstance(item, dict) and isinstance(fields, dict) and all(item.get(k) == v for k, v in fields.items())


def _selected(entries, wanted):
    """The entries `wanted` names, in its order; each entry at most once."""
    taken = []
    for fields in wanted or []:
        match = next((i for i, item in enumerate(entries) if i not in taken and _fits(item, fields)), None)
        if match is not None:
            taken.append(match)
    return [entries[i] for i in taken]


STATION_FIELDS = ("position", "name", "startDate")


def same_station(station, fields) -> bool:
    """Whether `station` is the one `fields` names, compared as text: YAML reads 2015 as a number, a stored copy may
    hold it as text."""
    return (isinstance(station, dict) and isinstance(fields, dict)
            and all(str(station.get(key) or "") == str(fields.get(key) or "") for key in STATION_FIELDS))


def _limit_stations(work, limits):
    """Each station of `work` with at most the points its entry in `limits` allows; the first fitting entry counts."""
    def limited(station):
        limit = next((entry.get("max") for entry in limits if same_station(station, entry)), None)
        if not isinstance(limit, int) or isinstance(limit, bool) or not isinstance(station.get("highlights"), list):
            return station
        return {**station, "highlights": station["highlights"][:max(limit, 0)]}
    return [limited(station) for station in work]


def tailor(cv, job=None):
    job = job or {}
    tags = job.get("tags", [])
    out = _bereinigen(deepcopy(cv), tags, job.get("hide", []), job.get("max_highlights"))
    limits = job.get("max_highlights_per_station")
    if isinstance(limits, list) and isinstance(out.get("work"), list):
        out["work"] = _limit_stations(out["work"], limits)
    out.setdefault("basics", {}).update(job.get("basics", {}))
    for key, wanted in job.get("select", {}).items():
        if isinstance(out.get(key), list):
            out[key] = _selected(out[key], wanted)
    for key, value in job.get("sections", {}).items():
        out[key] = value
    return out
