"""Lokaler Editor für den Fotoausschnitt (`basics.x-image`).

Startet einen Server nur auf 127.0.0.1 und öffnet die Seite im Browser. Die Vorschau rendert Typst,
gespeichert wird direkt in die Datendatei (Sicherung im Build-Ordner).

Beispiel:
  python foto_editor.py ../../daten/cv.yaml --build-dir ../../daten/.build
"""
import argparse
import json
import logging
import mimetypes
import pathlib
import secrets
import sys
import urllib.parse
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import fotoausschnitt
from build import ROOT

SEITE = ROOT / "editor" / "foto.html"
MAX_BODY = 4096
log = logging.getLogger("foto_editor")


class EditorServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, daten: pathlib.Path, build: pathlib.Path, port: int) -> None:
        self.daten = daten
        self.build = build
        self.foto, _ = fotoausschnitt.lies_foto(daten)
        self.vorschau = fotoausschnitt.Vorschau(self.foto, build)
        self.token = secrets.token_urlsafe(32)
        super().__init__(("127.0.0.1", port), Handler)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server_address[1]}/"


class Handler(BaseHTTPRequestHandler):
    server: EditorServer

    # Antworten

    def _senden(self, status: int, typ: str, inhalt: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", typ)
        self.send_header("Content-Length", str(len(inhalt)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(inhalt)

    def _json(self, status: int, wert: object) -> None:
        self._senden(status, "application/json; charset=utf-8", json.dumps(wert, ensure_ascii=False).encode("utf-8"))

    def _fehler(self, status: int, meldung: str) -> None:
        self._json(status, {"fehler": meldung})

    # Zugriffsschutz

    def _host_erlaubt(self) -> bool:
        """Nur 127.0.0.1 oder localhost mit unserem Port: schützt gegen DNS-Rebinding."""
        port = self.server.server_address[1]
        return self.headers.get("Host", "") in (f"127.0.0.1:{port}", f"localhost:{port}")

    def _token_gueltig(self, token: str | None) -> bool:
        # Als Bytes vergleichen: compare_digest wirft sonst bei Nicht-ASCII-Zeichen einen TypeError
        return token is not None and secrets.compare_digest(token.encode("utf-8"), self.server.token.encode("utf-8"))

    # Routen

    def do_GET(self) -> None:
        if not self._host_erlaubt():
            return self._fehler(HTTPStatus.FORBIDDEN, "Unbekannter Host")
        teile = urllib.parse.urlsplit(self.path)
        routen = {"/": self._seite, "/optionen": self._optionen, "/foto": self._foto, "/vorschau.png": self._vorschau}
        route = routen.get(teile.path)
        if route is None:
            return self._fehler(HTTPStatus.NOT_FOUND, "Nicht gefunden")
        parameter = {k: v[-1] for k, v in urllib.parse.parse_qs(teile.query).items()}
        if route != self._seite and not self._token_gueltig(parameter.pop("t", None)):
            return self._fehler(HTTPStatus.FORBIDDEN, "Ungültiges Token")
        self._ausfuehren(route, parameter)

    def do_POST(self) -> None:
        if not self._host_erlaubt():
            return self._fehler(HTTPStatus.FORBIDDEN, "Unbekannter Host")
        if urllib.parse.urlsplit(self.path).path != "/speichern":
            return self._fehler(HTTPStatus.NOT_FOUND, "Nicht gefunden")
        if not self._token_gueltig(self.headers.get("X-Token")):
            return self._fehler(HTTPStatus.FORBIDDEN, "Ungültiges Token")
        if self.headers.get_content_type() != "application/json":
            return self._fehler(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "Erwartet application/json")
        self._ausfuehren(self._speichern, {})

    def _ausfuehren(self, route, parameter: dict) -> None:
        try:
            route(parameter)
        except ValueError as fehler:
            self._fehler(HTTPStatus.BAD_REQUEST, str(fehler))
        except Exception:
            log.exception("Fehler bei %s %s", self.command, self.path)
            self._fehler(HTTPStatus.INTERNAL_SERVER_ERROR, "Interner Fehler, Details in der Konsole")

    def _seite(self, _: dict) -> None:
        html = SEITE.read_text(encoding="utf-8").replace("__TOKEN__", self.server.token)
        self._senden(HTTPStatus.OK, "text/html; charset=utf-8", html.encode("utf-8"))

    def _optionen(self, _: dict) -> None:
        self._json(HTTPStatus.OK, fotoausschnitt.lies_foto(self.server.daten)[1])

    def _foto(self, _: dict) -> None:
        typ = mimetypes.guess_type(self.server.foto.name)[0] or "application/octet-stream"
        self._senden(HTTPStatus.OK, typ, self.server.foto.read_bytes())

    def _vorschau(self, parameter: dict) -> None:
        png = self.server.vorschau.png(fotoausschnitt.optionen_aus_anfrage(parameter))
        self._senden(HTTPStatus.OK, "image/png", png)

    def _speichern(self, _: dict) -> None:
        laenge = int(self.headers.get("Content-Length") or 0)
        if not 0 < laenge <= MAX_BODY:
            raise ValueError(f"Anfrage leer oder grösser als {MAX_BODY} Bytes")
        try:
            optionen = json.loads(self.rfile.read(laenge))
        except json.JSONDecodeError:
            raise ValueError("Ungültiges JSON") from None
        fotoausschnitt.speichere_optionen(self.server.daten, optionen, self.server.build)
        log.info("Gespeichert: %s", optionen)
        self._json(HTTPStatus.OK, fotoausschnitt.lies_foto(self.server.daten)[1])

    def log_message(self, format: str, *args) -> None:
        log.debug(format, *args)


def erstelle_server(daten: pathlib.Path, build: pathlib.Path, port: int = 0) -> EditorServer:
    return EditorServer(daten.resolve(), build.resolve(), port)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Fotoausschnitt des Lebenslaufs im Browser einstellen")
    ap.add_argument("data", help="Stamm-Lebenslauf (YAML) mit basics.image")
    ap.add_argument("--build-dir", help="Ordner für Vorschau und Sicherung (Standard: build/ im Modul)")
    ap.add_argument("--port", type=int, default=0, help="Port (Standard: ein freier Port)")
    ap.add_argument("--kein-browser", action="store_true", help="Browser nicht automatisch öffnen")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    build = pathlib.Path(args.build_dir) if args.build_dir else ROOT / "build"
    try:
        server = erstelle_server(pathlib.Path(args.data), build, args.port)
    except (ValueError, OSError) as fehler:
        sys.exit(f"Fehler: {fehler}")
    log.info("Foto-Editor läuft auf %s (beenden mit Ctrl+C)", server.url)
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
