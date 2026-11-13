"""Stamm-Lebenslauf auf eine Stelle zuschneiden.

Regeln:
- Ein Eintrag oder Stichpunkt ohne `tags` ist immer dabei.
- Ein Eintrag oder Stichpunkt mit `tags` ist nur dabei, wenn er mindestens
  einen der Tags der Bewerbung trägt.
- `hide` entfernt Einträge nach Name, Titel oder Text.
- `basics` in der Bewerbungsdatei überschreibt Felder (z.B. label, summary).
- `max_highlights` begrenzt die Stichpunkte pro Station.
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


def tailor(cv, job=None):
    job = job or {}
    tags = job.get("tags", [])
    out = _bereinigen(deepcopy(cv), tags, job.get("hide", []), job.get("max_highlights"))
    out.setdefault("basics", {}).update(job.get("basics", {}))
    for key, wanted in job.get("select", {}).items():
        if isinstance(out.get(key), list):
            out[key] = _selected(out[key], wanted)
    for key, value in job.get("sections", {}).items():
        out[key] = value
    return out
