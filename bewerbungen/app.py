"""Lokale Oberfläche des Bewerbungsbegleiters: Bewerbungen, Unterlagen prüfen, Versand erfassen,
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
import routes_ai
import routes_dossier
import routes_backup
import routes_apply
import routes_certificates
import routes_career
import routes_chat
import routes_companies
import routes_own_files
import routes_own_key
import routes_rav
import routes_page
import routes_preferences
import routes_search
import routes_sites
import pfade  # noqa: F401  (makes the module lebenslauf importable)
import build as lebenslauf_modul
from ablage import Ablage
from dateien import sichere_gitignore
from kontext import Kontext
from server import Activity, Server
from versionen import waehle

SEITEN = {
    "/": "uebersicht.html",
    "/bewerbung": "bewerbung.html",
    "/entwuerfe": "entwuerfe.html",
    "/inhalte": "inhalte.html",
    "/inhalte.js": "inhalte.js",
    "/foto": "foto.html",
    "/dateien": "dateien.html",
    "/dateien.js": "dateien.js",
    "/eigenes-anschreiben.js": "eigenes-anschreiben.js",
    "/dateien-ordner.js": "dateien-ordner.js",
    "/stil.css": "stil.css",
    "/app.js": "app.js",
    "/meldungen.js": "meldungen.js",
    "/uebersicht.js": "uebersicht.js",
    "/uebersicht-logik.js": "uebersicht-logik.js",
    "/bewerbung.js": "bewerbung.js",
    "/bewerbung-logik.js": "bewerbung-logik.js",
    "/lebenslauf-anpassen.js": "lebenslauf-anpassen.js",
    "/unterlagen-wahl.js": "unterlagen-wahl.js",
    "/dossier-texte.js": "dossier-texte.js",
    "/entwuerfe.js": "entwuerfe.js",
    "/entwuerfe-logik.js": "entwuerfe-logik.js",
    "/foto.js": "foto.js",
    "/ki.js": "ki.js",
    "/einwilligung.js": "einwilligung.js",
    "/einrichtung": "einrichtung.html",
    "/einrichtung.js": "einrichtung.js",
    "/einrichtung-logik.js": "einrichtung-logik.js",
    "/texte.js": "texte.js",
    "/treffer": "treffer.html",
    "/treffer.js": "treffer.js",
    "/treffer-logik.js": "treffer-logik.js",
    "/suche-anzeige.js": "suche-anzeige.js",
    "/firmen": "firmen.html",
    "/firmen.js": "firmen.js",
    "/firmen-logik.js": "firmen-logik.js",
    "/kununu-pruefen.js": "kununu-pruefen.js",
    "/treffer-firma.js": "treffer-firma.js",
    "/firmen.css": "firmen.css",
    "/formular-logik.js": "formular-logik.js",
    "/beruf-vorschlag.js": "beruf-vorschlag.js",
    "/portal-wahl.js": "portal-wahl.js",
    "/angaben": "angaben.html",
    "/einstellungen": "einstellungen.html",
    "/einstellungen.js": "einstellungen.js",
    "/claude-abo.js": "claude-abo.js",
    "/vorabversionen.js": "vorabversionen.js",
    "/as-logo.svg": "as-logo.svg",
}
# DM Sans for stil.css and „Meine Angaben“ (MIN-369): the same files as the CV, served by the app, never from a CDN (CSP).
FONT_FILES = ("DMSans-400.ttf", "DMSans-400i.ttf", "DMSans-500.ttf", "DMSans-700.ttf")
SEITEN.update({f"/fonts/{name}": str(lebenslauf_modul.ROOT / "fonts" / name) for name in FONT_FILES})
GITIGNORE = [".entwuerfe/", ".build/", "bewerbungen/*/*.pdf", "bewerbungen/*/*.zip", "bewerbungen/*/an-formular/", "bewerbungen/*/zum-hochladen/", "dokumente/", ".ki/", "suche/", ".sicherung.yaml"]
log = logging.getLogger("bewerbungsbegleiter")


QUESTIONS_PAGES = {"/fragen": "fragen.html", "/fragen.js": "fragen.js"}
QUESTIONS_LINK = '<a href="/fragen">Fragen an die KI</a>'


def erstelle_kontext(daten: pathlib.Path, build: pathlib.Path | None = None) -> Kontext:
    """State for one data folder; the desktop app swaps it when the person chooses another folder."""
    daten = daten.resolve()
    if not daten.is_dir():
        raise ValueError(f"Datenordner nicht gefunden: {daten}")
    sichere_gitignore(daten, GITIGNORE)
    return Kontext(daten=daten, build=(build or daten / ".build").resolve(), ablage=Ablage(daten),
                   versionierung=waehle(daten))


def erstelle_server(daten: pathlib.Path, build: pathlib.Path | None = None, port: int = 0, kontext: Kontext | None = None,
                    extra_routes: tuple[dict, dict] = ({}, {}), body_limits: dict[str, int] | None = None,
                    questions_page: bool = False, activity: Activity | None = None) -> Server:
    """extra_routes: (GET, POST) of the desktop app, e.g. version and update (MIN-342).
    questions_page: the page „Fragen“ (MIN-376); without it neither page, route nor menu entry exist, so no question reaches the AI."""
    k = kontext or erstelle_kontext(daten, build)
    routen_get = {**routen_bewerbungen.GET, **routen_ablage.GET, **routen_foto.GET, **routen_inhalte.GET,
                  **routes_ai.GET, **routes_dossier.GET, **(routes_chat.GET if questions_page else {}), **routes_own_key.GET, **routes_own_files.GET, **routes_sites.GET, **routes_search.GET, **routes_backup.GET, **routes_certificates.GET, **routes_apply.GET, **routes_rav.GET, **routes_career.GET, **routes_preferences.GET, **routes_companies.GET, **extra_routes[0]}
    routen_post = {**routen_bewerbungen.POST, **routen_ablage.POST, **routen_foto.POST, **routen_inhalte.POST,
                   **routes_ai.POST, **routes_dossier.POST, **(routes_chat.POST if questions_page else {}), **routes_own_key.POST, **routes_own_files.POST, **routes_sites.POST, **routes_search.POST, **routes_page.POST, **routes_backup.POST, **routes_certificates.POST, **routes_apply.POST, **routes_rav.POST, **routes_career.POST, **routes_preferences.POST, **routes_companies.POST, **extra_routes[1]}
    limits = {**routes_own_files.BODY_LIMITS, **routen_foto.BODY_LIMITS, **(body_limits or {})}
    if questions_page:
        return Server(k, routen_get, routen_post, {**SEITEN, **QUESTIONS_PAGES}, port, limits, activity=activity)
    return Server(k, routen_get, routen_post, SEITEN, port, limits, hidden_links=(QUESTIONS_LINK,), activity=activity)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Lokale Oberfläche des Bewerbungsbegleiters")
    ap.add_argument("daten", help="Privater Datenordner (mit cv.yaml)")
    ap.add_argument("--build-dir", help="Ordner für Zwischenstände (Standard: <daten>/.build)")
    ap.add_argument("--port", type=int, default=0, help="Port (Standard: ein freier Port)")
    ap.add_argument("--kein-browser", action="store_true", help="Browser nicht automatisch öffnen")
    ap.add_argument("--fragen", action="store_true", help="Seite „Fragen“ einschalten")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        server = erstelle_server(pathlib.Path(args.daten), pathlib.Path(args.build_dir) if args.build_dir else None, args.port, questions_page=args.fragen)
    except (ValueError, OSError) as fehler:
        sys.exit(f"Fehler: {fehler}")
    log.info("Bewerbungsbegleiter läuft auf %s (beenden mit Ctrl+C)", server.entry_url if args.kein_browser else server.url)
    if not args.kein_browser:
        webbrowser.open(server.entry_url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
