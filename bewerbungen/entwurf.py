"""Änderungen ausserhalb der Oberfläche als Entwurf sichern (z.B. wenn Claude im Chat Dateien ändert).

Vor und nach jeder Änderung aufrufen: Der erste Aufruf sichert den alten Stand (falls noch nicht gesichert),
der zweite den neuen. Ein unveränderter Stand ergibt keinen neuen Entwurf. Die Entwürfe erscheinen in der
Oberfläche unter „Entwürfe“ und lassen sich dort ansehen, vergleichen und wiederherstellen.

  python entwurf.py ../../daten cv.yaml bewerbungen/<id>/anschreiben.yaml -m "Anschreiben <Firma> entworfen"
"""
import argparse
import json
import pathlib

from ablage import Ablage
from dateien import im_ordner

STANDARD = "Änderung ausserhalb der Oberfläche"


def sichere(daten: pathlib.Path, dateien: list[str], beschreibung: str) -> list[dict]:
    ablage = Ablage(daten)
    ablage.sichere_gitignore()
    ergebnis = []
    for rel in dateien:
        pfad = im_ordner(ablage.ordner, rel)
        if not pfad.is_file():
            ergebnis.append({"datei": rel, "entwurf": None, "hinweis": "existiert noch nicht"})
            continue
        e = ablage.speichere(pfad, beschreibung)
        ergebnis.append({"datei": rel, "entwurf": e.id if e else None, **({} if e else {"hinweis": "unverändert"})})
    return ergebnis


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Dateien im Datenordner als Entwurf sichern")
    ap.add_argument("daten", help="Datenordner")
    ap.add_argument("dateien", nargs="+", help="Dateien relativ zum Datenordner")
    ap.add_argument("-m", "--beschreibung", default=STANDARD)
    args = ap.parse_args(argv)
    print(json.dumps(sichere(pathlib.Path(args.daten), args.dateien, args.beschreibung), ensure_ascii=False))


if __name__ == "__main__":
    main()
