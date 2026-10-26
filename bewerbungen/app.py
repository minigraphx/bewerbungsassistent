"""Lokale Oberfläche des Bewerbungsassistenten: Bewerbungen, Unterlagen prüfen, Versand erfassen,
Entwürfe und Versionen, Fotoausschnitt. Läuft nur auf 127.0.0.1.

  python app.py ../../bewerbungsassistent-daten
"""
import argparse
import logging
import pathlib
import sys
import webbrowser

import routen_ablage
import routen_bewerbungen
import routen_foto
import routen_inhalte
from ablage import Ablage
from dateien import sichere_gitignore
from kontext import Kontext
from server import Server
from versionen import OhneGit, waehle

SEITEN = {
    "/": "uebersicht.html",
    "/bewerbung": "bewerbung.html",
    "/entwuerfe": "entwuerfe.html",
    "/inhalte": "inhalte.html",
    "/inhalte.js": "inhalte.js",
    "/foto": "foto.html",
    "/stil.css": "stil.css",
    "/app.js": "app.js",
    "/uebersicht.js": "uebersicht.js",
    "/bewerbung.js": "bewerbung.js",
    "/entwuerfe.js": "entwuerfe.js",
    "/foto.js": "foto.js",
}
GITIGNORE = [".entwuerfe/", ".build/", "bewerbungen/*/*.pdf"]
log = logging.getLogger("bewerbungsassistent")


def erstelle_server(daten: pathlib.Path, build: pathlib.Path | None = None, port: int = 0, kontext: Kontext | None = None) -> Server:
    daten = daten.resolve()
    if not daten.is_dir():
        raise ValueError(f"Datenordner nicht gefunden: {daten}")
    sichere_gitignore(daten, GITIGNORE)
    k = kontext or Kontext(daten=daten, build=(build or daten / ".build").resolve(), ablage=Ablage(daten),
                           versionierung=waehle(daten))
    routen_get = {**routen_bewerbungen.GET, **routen_ablage.GET, **routen_foto.GET, **routen_inhalte.GET}
    routen_post = {**routen_bewerbungen.POST, **routen_ablage.POST, **routen_foto.POST, **routen_inhalte.POST}
    return Server(k, routen_get, routen_post, SEITEN, port)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Lokale Oberfläche des Bewerbungsassistenten")
    ap.add_argument("daten", help="Privater Datenordner (mit cv.yaml)")
    ap.add_argument("--build-dir", help="Ordner für Zwischenstände (Standard: <daten>/.build)")
    ap.add_argument("--port", type=int, default=0, help="Port (Standard: ein freier Port)")
    ap.add_argument("--kein-browser", action="store_true", help="Browser nicht automatisch öffnen")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        server = erstelle_server(pathlib.Path(args.daten), pathlib.Path(args.build_dir) if args.build_dir else None, args.port)
    except (ValueError, OSError) as fehler:
        sys.exit(f"Fehler: {fehler}")
    if isinstance(server.kontext.versionierung, OhneGit):
        log.warning(server.kontext.versionierung.hinweis)
    log.info("Bewerbungsassistent läuft auf %s (beenden mit Ctrl+C)", server.url)
    if not args.kein_browser:
        webbrowser.open(server.url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
