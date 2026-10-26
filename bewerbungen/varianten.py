"""Lebenslauf-Varianten (MIN-307): bestehende Fassung wiederverwenden oder neue erstellen.

Jede Variante steht in `varianten.yaml` im Datenordner, mit Beschreibung, Tags (Profil, z.B. ki, fullstack,
bildung) und Stichworten (Technologien und Begriffe) zum Wiederfinden, für Menschen wie für ein LLM.
Quelle ist entweder ein Zuschnitt (`quelle: jobs/<name>.yaml`, wird gebaut), ein fertiges PDF im
Datenordner (`datei:`) oder ein Hinweis auf eine externe Fassung (`extern:`, z.B. Canva in Google Drive).

  python varianten.py liste ../../daten --tag ki
  python varianten.py vorschlag ../../daten --stelle ../../daten/bewerbungen/<id>/stelle.md
"""
import argparse
import json
import pathlib
import re
import threading

import pfade  # noqa: F401  (macht das Modul lebenslauf importierbar)
import build as lebenslauf_modul
from dateien import im_ordner, lies_yaml, schreibe_yaml
from register import ID_MUSTER

DATEI = "varianten.yaml"
ARTEN = ("lebenslauf",)
QUELLEN = ("quelle", "datei", "extern")
FELDER = ("id", "art", *QUELLEN, "beschreibung", "tags", "stichworte", "sprache")


def _liste(v, feld: str) -> list[str]:
    if v is None:
        return []
    if not isinstance(v, list) or not all(isinstance(x, str) and x.strip() for x in v):
        raise ValueError(f"{feld} muss eine Liste von Wörtern sein, z.B. [ki, fullstack]")
    return [x.strip() for x in v]


def pruefe_variante(v: dict, ordner: pathlib.Path | None = None) -> dict:
    if not isinstance(v, dict):
        raise ValueError("Variante muss eine Zuordnung sein")
    unbekannt = set(v) - set(FELDER)
    if unbekannt:
        raise ValueError(f"Unbekannte Felder: {sorted(unbekannt)}")
    if not isinstance(v.get("id"), str) or not ID_MUSTER.fullmatch(v["id"]):
        raise ValueError(f"id muss aus Kleinbuchstaben, Ziffern und Bindestrichen bestehen, nicht {v.get('id')!r}")
    art = v.get("art") or "lebenslauf"
    if art not in ARTEN:
        raise ValueError(f"art muss eine von {', '.join(ARTEN)} sein")
    if (v.get("sprache") or "de") not in lebenslauf_modul.SPRACHEN:
        raise ValueError(f"sprache muss eine von {', '.join(lebenslauf_modul.SPRACHEN)} sein")
    quellen = [q for q in QUELLEN if v.get(q)]
    if not quellen:
        raise ValueError("Es braucht quelle (Zuschnitt), datei (PDF) oder extern (Hinweis)")
    if len(quellen) > 1:
        raise ValueError(f"Bitte nur eine Quelle angeben, nicht {', '.join(quellen)}")
    for q in ("quelle", "datei"):
        if v.get(q):
            pfad = str(v[q])
            if pfad.startswith("/") or ".." in pathlib.PurePosixPath(pfad).parts:
                raise ValueError(f"{q} muss ein Pfad innerhalb des Datenordners sein: {pfad!r}")
            if ordner is not None:
                im_ordner(ordner, pfad)
    neu = {"id": v["id"], "art": art, quellen[0]: str(v[quellen[0]]).strip(),
           "beschreibung": str(v.get("beschreibung") or "").strip(),
           "tags": _liste(v.get("tags"), "tags"), "stichworte": _liste(v.get("stichworte"), "stichworte"),
           "sprache": v.get("sprache") or "de"}
    return neu


class Varianten:
    def __init__(self, ordner: pathlib.Path) -> None:
        self.ordner = ordner.resolve()
        self.pfad = self.ordner / DATEI
        self._sperre = threading.Lock()

    def alle(self) -> list[dict]:
        return [pruefe_variante(v) for v in lies_yaml(self.pfad, [])]

    def hole(self, variante_id: str) -> dict:
        for v in self.alle():
            if v["id"] == variante_id:
                return v
        raise KeyError(f"Variante {variante_id!r} nicht gefunden")

    def speichere(self, variante: dict) -> dict:
        neu = pruefe_variante(variante, self.ordner)
        with self._sperre:
            alle = self.alle()
            ids = [v["id"] for v in alle]
            liste = [neu if v["id"] == neu["id"] else v for v in alle] if neu["id"] in ids else alle + [neu]
            schreibe_yaml(self.pfad, liste, "# Lebenslauf-Varianten mit Tags (MIN-307)\n")
        return neu

    def finde(self, tags: list[str]) -> list[dict]:
        """Varianten, die alle genannten Tags tragen."""
        gesucht = {t.lower() for t in tags}
        return [v for v in self.alle() if gesucht <= {t.lower() for t in v["tags"]}]


def _kommt_vor(begriff: str, text: str) -> bool:
    return re.search(rf"(?<![\w]){re.escape(begriff)}(?![\w])", text, re.IGNORECASE) is not None


def vorschlagen(stellentext: str, alle: list[dict], anzahl: int = 3) -> list[dict]:
    """Varianten nach Übereinstimmung mit dem Stellentext ordnen.

    treffer: Stichworte und Tags der Variante, die im Text vorkommen.
    fehlt: Begriffe anderer Varianten, die im Text vorkommen, dieser aber fehlen (Hinweis auf Lücken).
    Varianten ohne Treffer entfallen.
    """
    def begriffe(v: dict) -> set[str]:
        return set(v["stichworte"]) | set(v["tags"])

    im_text = {b for v in alle for b in begriffe(v) if _kommt_vor(b, stellentext)}
    vorschlaege = []
    for v in alle:
        treffer = sorted(b for b in begriffe(v) if b in im_text)
        if not treffer:
            continue
        eigene = {b.lower() for b in begriffe(v)}
        fehlt = sorted(b for b in im_text if b.lower() not in eigene)
        vorschlaege.append({"id": v["id"], "beschreibung": v["beschreibung"], "punkte": len(treffer),
                            "treffer": treffer, "fehlt": fehlt})
    return sorted(vorschlaege, key=lambda x: (-x["punkte"], len(x["fehlt"]), x["id"]))[:anzahl]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Lebenslauf-Varianten auflisten und zur Stelle vorschlagen")
    sub = ap.add_subparsers(dest="befehl", required=True)
    liste = sub.add_parser("liste")
    liste.add_argument("daten")
    liste.add_argument("--tag", action="append", default=[])
    vor = sub.add_parser("vorschlag")
    vor.add_argument("daten")
    vor.add_argument("--stelle", required=True, help="Text der Stellenausschreibung (Datei)")
    args = ap.parse_args(argv)
    var = Varianten(pathlib.Path(args.daten))
    if args.befehl == "liste":
        ergebnis = var.finde(args.tag) if args.tag else var.alle()
    else:
        ergebnis = vorschlagen(pathlib.Path(args.stelle).read_text(encoding="utf-8"), var.alle())
    print(json.dumps(ergebnis, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
